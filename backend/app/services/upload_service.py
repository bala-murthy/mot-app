"""File upload, parsing, validation, and DB ingestion."""
from __future__ import annotations

import io
import logging
import uuid
from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from ..constants import HEADER_ALIASES
from ..models import (
    ParameterData,
    RGSData,
    Requirement,
    SkillConsolidatedLookup,
    UploadBatch,
)
from ..schemas import UploadResult
from .transformation_service import TransformationService

log = logging.getLogger(__name__)

MAIN_SHEET_NAMES = ["requirements", "data", "sheet1", "mot", "main", "req"]
RGS_SHEET_NAMES = ["rgs", "rgs sheet", "rgssheet"]
SKILL_SHEET_NAMES = ["skill consolidated lookup", "skill lookup", "skills"]
PARAM_SHEET_NAMES = ["parameters", "params", "parameter"]


def _normalise_header(h: Any) -> str:
    return str(h).strip().lower()


def _map_headers(df: pd.DataFrame) -> dict[str, str]:
    """Return {pandas_col_name -> db_field_name}."""
    mapping: dict[str, str] = {}
    for col in df.columns:
        norm = _normalise_header(col)
        if norm in HEADER_ALIASES:
            mapping[col] = HEADER_ALIASES[norm]
        else:
            # Try stripping spaces and special chars
            condensed = norm.replace(" ", "").replace("_", "").replace("-", "")
            for alias, field in HEADER_ALIASES.items():
                if alias.replace(" ", "") == condensed:
                    mapping[col] = field
                    break
    return mapping


def _parse_date(val: Any) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    try:
        return pd.to_datetime(str(val), dayfirst=False, errors="coerce").date()
    except Exception:
        return None


def _parse_float(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(str(val).replace(",", "").replace("$", "").strip())
    except Exception:
        return None


def _parse_int(val: Any) -> int | None:
    f = _parse_float(val)
    return int(f) if f is not None else None


DATE_FIELDS = {
    "added_date", "requirement_start_date",
    "target_fulfillment_date",
}
FLOAT_FIELDS = {"revenue_impact", "revenue_at_risk", "revenue_won"}
INT_FIELDS = {"sla_breach_days"}


def _coerce_row(raw: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, val in raw.items():
        if isinstance(val, float) and pd.isna(val):
            val = None
        if field in DATE_FIELDS:
            result[field] = _parse_date(val)
        elif field in FLOAT_FIELDS:
            result[field] = _parse_float(val)
        elif field in INT_FIELDS:
            result[field] = _parse_int(val)
        else:
            result[field] = str(val).strip() if val is not None else None
    return result


def _find_sheet(xl: pd.ExcelFile, candidates: list[str]) -> str | None:
    sheets_lower = {s.strip().lower(): s for s in xl.sheet_names}
    for name in candidates:
        if name in sheets_lower:
            return sheets_lower[name]
    return None


def _load_rgs(df: pd.DataFrame, db: Session, batch_id: str) -> int:
    """Upsert RGS reference data from dataframe."""
    rgs_aliases = {
        "requirement id": "requirement_id",
        "requirementid": "requirement_id",
        "req id": "requirement_id",
        "won sp": "won_sp",
        "wonsp": "won_sp",
        "requirement pending with": "requirement_pending_with",
        "pendingwith": "requirement_pending_with",
        "pending with": "requirement_pending_with",
        "gbams rmg name": "gbams_rmg_name",
        "gbamsrmgname": "gbams_rmg_name",
        "evaluator emp name": "evaluator_emp_name",
        "evaluatorempname": "evaluator_emp_name",
        "requirement start date": "requirement_start_date",
        "startdate": "requirement_start_date",
    }
    mapping: dict[str, str] = {}
    for col in df.columns:
        norm = _normalise_header(col)
        if norm in rgs_aliases:
            mapping[col] = rgs_aliases[norm]
        else:
            condensed = norm.replace(" ", "")
            for alias, field in rgs_aliases.items():
                if alias.replace(" ", "") == condensed:
                    mapping[col] = field
                    break

    if "requirement_id" not in mapping.values():
        return 0

    loaded = 0
    for _, row in df.iterrows():
        mapped = {mapping[c]: row[c] for c in mapping if c in row.index}
        req_id = str(mapped.get("requirement_id", "")).strip()
        if not req_id:
            continue
        start = _parse_date(mapped.get("requirement_start_date"))
        existing = db.query(RGSData).filter(RGSData.requirement_id == req_id).first()
        if existing:
            existing.won_sp = str(mapped.get("won_sp", "") or "").strip() or None
            existing.requirement_pending_with = str(mapped.get("requirement_pending_with", "") or "").strip() or None
            existing.gbams_rmg_name = str(mapped.get("gbams_rmg_name", "") or "").strip() or None
            existing.evaluator_emp_name = str(mapped.get("evaluator_emp_name", "") or "").strip() or None
            existing.requirement_start_date = start
            existing.batch_id = batch_id
        else:
            entry = RGSData(
                requirement_id=req_id,
                won_sp=str(mapped.get("won_sp", "") or "").strip() or None,
                requirement_pending_with=str(mapped.get("requirement_pending_with", "") or "").strip() or None,
                gbams_rmg_name=str(mapped.get("gbams_rmg_name", "") or "").strip() or None,
                evaluator_emp_name=str(mapped.get("evaluator_emp_name", "") or "").strip() or None,
                requirement_start_date=start,
                batch_id=batch_id,
            )
            db.add(entry)
        loaded += 1
    return loaded


def _load_skills(df: pd.DataFrame, db: Session) -> int:
    skill_aliases = {
        "input skill": "input_skill",
        "inputskill": "input_skill",
        "skill": "input_skill",
        "consolidated skill": "consolidated_skill",
        "consolidatedskill": "consolidated_skill",
        "second consolidated skill": "second_consolidated_skill",
        "secondconsolidatedskill": "second_consolidated_skill",
        "verify skill flag": "verify_skill_flag",
        "verifyskill": "verify_skill_flag",
        "verify_skill": "verify_skill_flag",
    }
    mapping: dict[str, str] = {}
    for col in df.columns:
        norm = _normalise_header(col)
        if norm in skill_aliases:
            mapping[col] = skill_aliases[norm]
        else:
            condensed = norm.replace(" ", "")
            for alias, field in skill_aliases.items():
                if alias.replace(" ", "") == condensed:
                    mapping[col] = field
                    break

    if "input_skill" not in mapping.values():
        return 0

    # Clear existing to replace
    db.query(SkillConsolidatedLookup).delete()
    loaded = 0
    for _, row in df.iterrows():
        mapped = {mapping[c]: str(row[c]).strip() if row[c] is not None else "" for c in mapping if c in row.index}
        skill = mapped.get("input_skill", "").strip()
        if not skill:
            continue
        entry = SkillConsolidatedLookup(
            input_skill=skill,
            consolidated_skill=mapped.get("consolidated_skill") or None,
            second_consolidated_skill=mapped.get("second_consolidated_skill") or None,
            verify_skill_flag=mapped.get("verify_skill_flag") or None,
        )
        db.add(entry)
        loaded += 1
    return loaded


def _load_params(df: pd.DataFrame, db: Session) -> int:
    param_aliases = {
        "fulfillment status": "fulfillment_status",
        "fulfillmentstatus": "fulfillment_status",
        "status": "fulfillment_status",
        "fulfillment perspective": "fulfillment_perspective",
        "fulfillmentperspective": "fulfillment_perspective",
        "perspective": "fulfillment_perspective",
    }
    mapping: dict[str, str] = {}
    for col in df.columns:
        norm = _normalise_header(col)
        if norm in param_aliases:
            mapping[col] = param_aliases[norm]
        else:
            condensed = norm.replace(" ", "")
            for alias, field in param_aliases.items():
                if alias.replace(" ", "") == condensed:
                    mapping[col] = field
                    break

    if "fulfillment_status" not in mapping.values():
        return 0

    db.query(ParameterData).delete()
    loaded = 0
    for _, row in df.iterrows():
        mapped = {mapping[c]: str(row[c]).strip() if row[c] is not None else "" for c in mapping if c in row.index}
        status = mapped.get("fulfillment_status", "").strip()
        if not status:
            continue
        entry = ParameterData(
            fulfillment_status=status,
            fulfillment_perspective=mapped.get("fulfillment_perspective") or None,
        )
        db.add(entry)
        loaded += 1
    return loaded


def process_upload(file_bytes: bytes, filename: str, db: Session) -> UploadResult:
    batch_id = str(uuid.uuid4())[:8].upper()
    errors: list[str] = []
    transformation_summary: dict[str, Any] = {}

    batch = UploadBatch(batch_id=batch_id, filename=filename)
    db.add(batch)
    db.flush()

    # ── Parse file ────────────────────────────────────────────────────────
    ext = filename.rsplit(".", 1)[-1].lower()
    main_df: pd.DataFrame | None = None
    ref_summary: dict[str, int] = {}

    try:
        if ext in ("xlsx", "xls"):
            xl = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl" if ext == "xlsx" else "xlrd")
            sheets_lower = {s.strip().lower(): s for s in xl.sheet_names}

            # Load reference sheets first
            rgs_sheet = _find_sheet(xl, RGS_SHEET_NAMES)
            if rgs_sheet:
                rgs_df = xl.parse(rgs_sheet, dtype=str)
                ref_summary["rgs_rows"] = _load_rgs(rgs_df, db, batch_id)

            skill_sheet = _find_sheet(xl, SKILL_SHEET_NAMES)
            if skill_sheet:
                skill_df = xl.parse(skill_sheet, dtype=str)
                ref_summary["skill_rows"] = _load_skills(skill_df, db)

            param_sheet = _find_sheet(xl, PARAM_SHEET_NAMES)
            if param_sheet:
                param_df = xl.parse(param_sheet, dtype=str)
                ref_summary["param_rows"] = _load_params(param_df, db)

            # Find main sheet
            main_sheet = _find_sheet(xl, MAIN_SHEET_NAMES)
            if main_sheet is None:
                # Use first sheet that isn't a reference sheet
                ref_names = {rgs_sheet, skill_sheet, param_sheet} - {None}
                for s in xl.sheet_names:
                    if s not in ref_names:
                        main_sheet = s
                        break
            if main_sheet is None:
                main_sheet = xl.sheet_names[0]

            main_df = xl.parse(main_sheet)
        elif ext == "csv":
            main_df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as exc:
        batch.status = "failed"
        batch.error_summary = str(exc)
        db.commit()
        return UploadResult(
            batch_id=batch_id, filename=filename,
            total_rows=0, rows_loaded=0, rows_skipped=0, rows_failed=0,
            status="failed", errors=[str(exc)],
        )

    if main_df is None or main_df.empty:
        batch.status = "failed"
        batch.error_summary = "Uploaded file contains no records."
        db.commit()
        return UploadResult(
            batch_id=batch_id, filename=filename,
            total_rows=0, rows_loaded=0, rows_skipped=0, rows_failed=0,
            status="failed", errors=["Uploaded file contains no records."],
        )

    # Drop fully empty rows
    main_df = main_df.dropna(how="all")

    total_rows = len(main_df)
    header_map = _map_headers(main_df)
    rows_loaded = rows_skipped = rows_failed = 0

    # ── Load requirements ─────────────────────────────────────────────────
    for idx, row in main_df.iterrows():
        # Map to field dict
        raw: dict[str, Any] = {}
        for col, field in header_map.items():
            if col in main_df.columns:
                raw[field] = row[col]

        req_id = str(raw.get("requirement_id", "")).strip()
        if not req_id or req_id.lower() in ("nan", "none", ""):
            rows_skipped += 1
            continue

        coerced = _coerce_row(raw)
        coerced["requirement_id"] = req_id
        coerced["upload_batch_id"] = batch_id

        try:
            existing = db.query(Requirement).filter(Requirement.requirement_id == req_id).first()
            if existing:
                for field, val in coerced.items():
                    if hasattr(existing, field) and val is not None:
                        setattr(existing, field, val)
            else:
                req_obj = Requirement(**{k: v for k, v in coerced.items() if hasattr(Requirement, k)})
                db.add(req_obj)
            rows_loaded += 1
        except Exception as exc:
            log.warning("Row %s failed: %s", idx, exc)
            errors.append(f"Row {idx}: {exc}")
            rows_failed += 1

    db.flush()

    # ── Run transformation engine ─────────────────────────────────────────
    transform_counts = {"applied": 0, "failed": 0}
    try:
        svc = TransformationService(db)
        reqs = db.query(Requirement).filter(Requirement.upload_batch_id == batch_id).all()
        transform_counts = svc.apply_rules_batch(reqs)
    except Exception as exc:
        log.error("Transformation failed: %s", exc)
        errors.append(f"Transformation error: {exc}")

    # ── Finalise batch ────────────────────────────────────────────────────
    batch.total_rows = total_rows
    batch.rows_loaded = rows_loaded
    batch.rows_skipped = rows_skipped
    batch.rows_failed = rows_failed
    batch.status = "completed"

    transformation_summary = {
        **ref_summary,
        "transformation_rules_applied": transform_counts["applied"],
        "transformation_rules_failed": transform_counts["failed"],
    }

    db.commit()
    return UploadResult(
        batch_id=batch_id,
        filename=filename,
        total_rows=total_rows,
        rows_loaded=rows_loaded,
        rows_skipped=rows_skipped,
        rows_failed=rows_failed,
        status="completed",
        errors=errors[:50],
        transformation_summary=transformation_summary,
    )
