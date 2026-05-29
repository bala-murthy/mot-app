"""Export requirements to Excel or CSV."""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from ..models import Requirement

EXPORT_COLUMNS = [
    ("requirement_id", "Requirement ID"),
    ("fulfillment_status", "Fulfillment Status"),
    ("group_customer_name", "Group Customer Name"),
    ("account_name", "Account Name"),
    ("domain", "Domain"),
    ("iou", "IOU"),
    ("sub_iou", "Sub IOU"),
    ("country", "Country"),
    ("branch", "Branch"),
    ("requirement_ageing_calendar_days", "Ageing (Calendar Days)"),
    ("observation", "Observation"),
    ("primary_competency_proficiency_details", "Primary Competency"),
    ("competency", "Competency"),
    ("experience_range", "Experience Range"),
    ("revenue_impact", "Revenue Impact"),
    ("onsite_offshore", "Onsite/Offshore"),
    ("won_sp", "Won SP"),
    ("delivery_manager", "Delivery Manager"),
    ("skill_manually_entered", "Skill (Manual)"),
    ("added_date", "Added Date"),
    ("service_practice", "Service Practice"),
    ("skill_consolidated", "Skill Consolidated"),
    ("skill_consolidated_second_skill", "Skill Consolidated (2nd)"),
    ("fulfillment_perspective", "Fulfillment Perspective"),
    ("target_fulfillment_date", "Target Fulfillment Date"),
    ("revenue_at_risk", "Revenue At Risk"),
    ("revenue_won", "Revenue Won"),
    ("requirement_start_date", "Requirement Start Date"),
    ("candidate_name", "Candidate Name"),
    ("fulfillment_channel", "Fulfillment Channel"),
    ("requirement_ageing_months", "Ageing (Months)"),
    ("pending_with", "Pending With"),
    ("gbams_rmg_name", "GBAMS RMG Name"),
    ("evaluator_emp_name", "Evaluator Emp Name"),
    ("evaluation_status", "Evaluation Status"),
    ("candidate_evaluation_stage", "Candidate Eval Stage"),
    ("sub_practice", "Sub Practice"),
    ("gbams_requirement_id", "GBAMS Requirement ID"),
    ("sla_breach_days", "SLA Breach Days"),
    ("requirement_month", "Requirement Month"),
    ("it_bps", "IT/BPS"),
    ("created_at", "Created At"),
    ("updated_at", "Updated At"),
]


def _build_query(
    db: Session,
    fulfillment_status: str | None,
    requirement_id: str | None,
    group_customer_name: str | None,
    account_name: str | None,
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
    return q


def export_excel(
    db: Session,
    fulfillment_status: str | None = None,
    requirement_id: str | None = None,
    group_customer_name: str | None = None,
    account_name: str | None = None,
) -> bytes:
    import xlsxwriter

    q = _build_query(db, fulfillment_status, requirement_id, group_customer_name, account_name)
    records = q.all()

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("Requirements")

    header_fmt = wb.add_format({"bold": True, "bg_color": "#1a3c5e", "font_color": "white", "border": 1})
    cell_fmt = wb.add_format({"border": 1, "text_wrap": False})
    date_fmt = wb.add_format({"num_format": "yyyy-mm-dd", "border": 1})

    for col_idx, (_, header) in enumerate(EXPORT_COLUMNS):
        ws.write(0, col_idx, header, header_fmt)
        ws.set_column(col_idx, col_idx, 18)

    for row_idx, rec in enumerate(records, start=1):
        for col_idx, (field, _) in enumerate(EXPORT_COLUMNS):
            val = getattr(rec, field, None)
            if val is None:
                ws.write_blank(row_idx, col_idx, None, cell_fmt)
            elif hasattr(val, "strftime"):
                ws.write(row_idx, col_idx, str(val), date_fmt)
            elif isinstance(val, (int, float)):
                ws.write_number(row_idx, col_idx, val, cell_fmt)
            else:
                ws.write_string(row_idx, col_idx, str(val), cell_fmt)

    wb.close()
    buf.seek(0)
    return buf.read()


def export_csv(
    db: Session,
    fulfillment_status: str | None = None,
    requirement_id: str | None = None,
    group_customer_name: str | None = None,
    account_name: str | None = None,
) -> bytes:
    q = _build_query(db, fulfillment_status, requirement_id, group_customer_name, account_name)
    records = q.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([h for _, h in EXPORT_COLUMNS])
    for rec in records:
        writer.writerow([str(getattr(rec, f, "") or "") for f, _ in EXPORT_COLUMNS])
    return buf.getvalue().encode("utf-8")
