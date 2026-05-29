from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog
from ..schemas import UploadResult
from ..services.upload_service import process_upload

router = APIRouter()


@router.post("/upload/requirements", response_model=UploadResult, summary="Upload requirements file")
async def upload_requirements(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    allowed = {"xlsx", "xls", "csv"}
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: .{ext}. Allowed: {allowed}")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded file is empty.")

    result = process_upload(content, file.filename or "upload", db)

    db.add(AuditLog(
        session_id="system",
        action_type="UPLOAD",
        details=f"File: {file.filename}, Batch: {result.batch_id}, "
                f"Loaded: {result.rows_loaded}, Skipped: {result.rows_skipped}",
    ))
    db.commit()

    return result
