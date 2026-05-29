import math
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, RecordLock, Requirement
from ..schemas import LockRequest, LockResponse, RequirementListResponse, RequirementRead, RequirementUpdate
from ..services import lock_service
from ..services.transformation_service import TransformationService

router = APIRouter()


def _to_read(req: Requirement, session_id: str | None = None) -> RequirementRead:
    lock = req.lock
    is_locked = False
    if lock:
        if session_id and lock.session_id == session_id:
            is_locked = False
        else:
            from datetime import datetime
            is_locked = lock.expires_at > datetime.utcnow()
    data = RequirementRead.model_validate(req)
    data.is_locked = is_locked
    return data


@router.get("/requirements", response_model=RequirementListResponse, summary="Search requirements")
def list_requirements(
    fulfillment_status: Optional[str] = Query(None),
    requirement_id: Optional[str] = Query(None),
    group_customer_name: Optional[str] = Query(None),
    account_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Requirement).filter(Requirement.is_deleted == False)
    if fulfillment_status:
        q = q.filter(Requirement.fulfillment_status == fulfillment_status)
    if requirement_id:
        q = q.filter(Requirement.requirement_id.ilike(f"%{requirement_id}%"))
    if group_customer_name:
        q = q.filter(Requirement.group_customer_name.ilike(f"%{group_customer_name}%"))
    if account_name:
        q = q.filter(Requirement.account_name.ilike(f"%{account_name}%"))

    total = q.count()
    items = q.order_by(Requirement.requirement_id).offset((page - 1) * page_size).limit(page_size).all()
    return RequirementListResponse(
        items=[_to_read(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/requirements/{requirement_id}", response_model=RequirementRead, summary="Get single requirement")
def get_requirement(
    requirement_id: str,
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    req = db.query(Requirement).filter(Requirement.requirement_id == requirement_id).first()
    if req is None:
        raise HTTPException(404, "Requirement not found.")
    return _to_read(req, session_id)


@router.put("/requirements/{requirement_id}", response_model=RequirementRead, summary="Update a requirement")
def update_requirement(
    requirement_id: str,
    payload: RequirementUpdate,
    db: Session = Depends(get_db),
):
    req = db.query(Requirement).filter(Requirement.requirement_id == requirement_id).first()
    if req is None:
        raise HTTPException(404, "Requirement not found.")

    if lock_service.is_locked_by_other(requirement_id, payload.session_id, db):
        raise HTTPException(423, "This record is currently being edited by another user. Please try again later.")

    from ..constants import EDITABLE_FIELDS
    update_data = payload.model_dump(exclude={"session_id"}, exclude_none=True)
    for field, val in update_data.items():
        if field in EDITABLE_FIELDS and hasattr(req, field):
            setattr(req, field, val)

    # Re-run transformations
    svc = TransformationService(db)
    svc.apply_all_rules(req)

    db.add(AuditLog(
        session_id=payload.session_id,
        record_id=requirement_id,
        action_type="UPDATE",
        details=f"Fields updated: {list(update_data.keys())}",
    ))
    db.commit()
    db.refresh(req)
    return _to_read(req, payload.session_id)


@router.post("/requirements/{requirement_id}/lock", response_model=LockResponse, summary="Acquire edit lock")
def acquire_lock(
    requirement_id: str,
    payload: LockRequest,
    db: Session = Depends(get_db),
):
    result = lock_service.acquire(requirement_id, payload.session_id, db)
    if result.success:
        db.add(AuditLog(session_id=payload.session_id, record_id=requirement_id, action_type="LOCK_ACQUIRE"))
        db.commit()
    return result


@router.delete("/requirements/{requirement_id}/lock", response_model=LockResponse, summary="Release edit lock")
def release_lock(
    requirement_id: str,
    session_id: str = Query(...),
    db: Session = Depends(get_db),
):
    result = lock_service.release(requirement_id, session_id, db)
    if result.success:
        db.add(AuditLog(session_id=session_id, record_id=requirement_id, action_type="LOCK_RELEASE"))
        db.commit()
    return result


# ── Delete endpoints ─────────────────────────────────────────────────────────

@router.post("/requirements/delete-selected", summary="Soft-delete selected requirement records")
def delete_selected(
    requirement_ids: List[str] = Body(..., embed=True),
    session_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Mark the given requirement IDs as deleted (soft delete)."""
    if not requirement_ids:
        raise HTTPException(400, "No requirement IDs provided.")

    deleted, skipped = [], []
    for req_id in requirement_ids:
        req = db.query(Requirement).filter(Requirement.requirement_id == req_id).first()
        if req is None:
            skipped.append(req_id)
            continue
        # Release any existing lock first
        lock = db.query(RecordLock).filter(RecordLock.requirement_id == req_id).first()
        if lock:
            db.delete(lock)
        req.is_deleted = True
        db.add(AuditLog(
            session_id=session_id,
            record_id=req_id,
            action_type="DELETE",
            details="Soft-deleted via Delete Selected.",
        ))
        deleted.append(req_id)

    db.commit()
    return {
        "deleted_count": len(deleted),
        "skipped_count": len(skipped),
        "deleted_ids": deleted,
        "skipped_ids": skipped,
    }


@router.post("/requirements/delete-all", summary="Soft-delete ALL requirement records")
def delete_all(
    session_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Mark every non-deleted requirement as deleted and clear all locks."""
    # Clear all locks
    db.query(RecordLock).delete()

    # Soft-delete all active records
    count = (
        db.query(Requirement)
        .filter(Requirement.is_deleted == False)
        .update({"is_deleted": True})
    )

    db.add(AuditLog(
        session_id=session_id,
        action_type="DELETE_ALL",
        details=f"All {count} records soft-deleted.",
    ))
    db.commit()
    return {"deleted_count": count, "message": f"{count} records deleted."}
