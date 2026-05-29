from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog
from ..services.download_service import export_csv, export_excel

router = APIRouter()


@router.get("/download/requirements", summary="Download requirements as Excel or CSV")
def download_requirements(
    format: str = Query("excel", regex="^(excel|csv)$"),
    fulfillment_status: Optional[str] = Query(None),
    requirement_id: Optional[str] = Query(None),
    group_customer_name: Optional[str] = Query(None),
    account_name: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    db.add(AuditLog(
        session_id=session_id or "anonymous",
        action_type="DOWNLOAD",
        details=f"Format: {format}, Status filter: {fulfillment_status}",
    ))
    db.commit()

    if format == "excel":
        data = export_excel(db, fulfillment_status, requirement_id, group_customer_name, account_name)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=requirements.xlsx"},
        )
    else:
        data = export_csv(db, fulfillment_status, requirement_id, group_customer_name, account_name)
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=requirements.csv"},
        )
