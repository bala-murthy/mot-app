"""Record locking service."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import settings
from ..models import RecordLock, Requirement
from ..schemas import LockResponse


def _now() -> datetime:
    return datetime.utcnow()


def cleanup_expired(db: Session) -> int:
    expired = (
        db.query(RecordLock)
        .filter(RecordLock.expires_at < _now())
        .all()
    )
    count = len(expired)
    for lock in expired:
        db.delete(lock)
    db.commit()
    return count


def acquire(requirement_id: str, session_id: str, db: Session) -> LockResponse:
    cleanup_expired(db)

    req = db.query(Requirement).filter(Requirement.requirement_id == requirement_id).first()
    if req is None:
        return LockResponse(success=False, message="Record not found.")

    existing = db.query(RecordLock).filter(RecordLock.requirement_id == requirement_id).first()
    if existing:
        if existing.session_id == session_id:
            # Refresh lock
            existing.expires_at = _now() + timedelta(minutes=settings.lock_timeout_minutes)
            db.commit()
            return LockResponse(
                success=True,
                message="Lock refreshed.",
                locked_by_session=session_id,
                expires_at=existing.expires_at,
            )
        return LockResponse(
            success=False,
            message="This record is currently being edited by another user. Please try again later.",
            locked_by_session=existing.session_id,
        )

    lock = RecordLock(
        requirement_id=requirement_id,
        session_id=session_id,
        expires_at=_now() + timedelta(minutes=settings.lock_timeout_minutes),
    )
    db.add(lock)
    db.commit()
    db.refresh(lock)
    return LockResponse(
        success=True,
        message="Lock acquired.",
        locked_by_session=session_id,
        expires_at=lock.expires_at,
    )


def release(requirement_id: str, session_id: str, db: Session) -> LockResponse:
    lock = (
        db.query(RecordLock)
        .filter(RecordLock.requirement_id == requirement_id)
        .first()
    )
    if lock is None:
        return LockResponse(success=True, message="No lock found.")
    if lock.session_id != session_id:
        return LockResponse(success=False, message="Cannot release a lock owned by another session.")
    db.delete(lock)
    db.commit()
    return LockResponse(success=True, message="Lock released.")


def is_locked_by_other(requirement_id: str, session_id: str, db: Session) -> bool:
    cleanup_expired(db)
    lock = db.query(RecordLock).filter(RecordLock.requirement_id == requirement_id).first()
    if lock is None:
        return False
    return lock.session_id != session_id
