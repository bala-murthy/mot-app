"""Dashboard metrics, KPI computation, and chart data."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from ..constants import FULFILLED_STATUSES, OPEN_STATUSES
from ..models import Alert, Requirement
from ..schemas import DashboardFilters, FilterOptions, KPICard


def _apply_filters(q, f: DashboardFilters):
    q = q.filter(Requirement.is_deleted == False)
    if f.iou:
        q = q.filter(Requirement.iou == f.iou)
    if f.sub_iou:
        q = q.filter(Requirement.sub_iou == f.sub_iou)
    if f.service_practice:
        q = q.filter(Requirement.service_practice == f.service_practice)
    if f.delivery_manager:
        q = q.filter(Requirement.delivery_manager == f.delivery_manager)
    if f.gbams_rmg_name:
        q = q.filter(Requirement.gbams_rmg_name == f.gbams_rmg_name)
    if f.group_customer_name:
        q = q.filter(Requirement.group_customer_name == f.group_customer_name)
    if f.account_name:
        q = q.filter(Requirement.account_name == f.account_name)
    if f.domain:
        q = q.filter(Requirement.domain == f.domain)
    if f.country:
        q = q.filter(Requirement.country == f.country)
    if f.branch:
        q = q.filter(Requirement.branch == f.branch)
    if f.onsite_offshore:
        q = q.filter(Requirement.onsite_offshore == f.onsite_offshore)
    if f.fulfillment_status:
        q = q.filter(Requirement.fulfillment_status == f.fulfillment_status)
    if f.requirement_id:
        q = q.filter(Requirement.requirement_id.ilike(f"%{f.requirement_id}%"))
    if f.pending_with:
        q = q.filter(Requirement.pending_with == f.pending_with)
    if f.skill_consolidated:
        q = q.filter(Requirement.skill_consolidated == f.skill_consolidated)
    if f.competency:
        q = q.filter(Requirement.competency == f.competency)
    if f.experience_range:
        q = q.filter(Requirement.experience_range == f.experience_range)
    if f.requirement_month:
        q = q.filter(Requirement.requirement_month == f.requirement_month)
    if f.it_bps:
        q = q.filter(Requirement.it_bps == f.it_bps)
    if f.age_bucket:
        bucket_filters = {
            "0-15": lambda: Requirement.sla_breach_days <= 15,
            "16-30": lambda: and_(Requirement.sla_breach_days > 15, Requirement.sla_breach_days <= 30),
            "31-60": lambda: and_(Requirement.sla_breach_days > 30, Requirement.sla_breach_days <= 60),
            "61-90": lambda: and_(Requirement.sla_breach_days > 60, Requirement.sla_breach_days <= 90),
            "90+": lambda: Requirement.sla_breach_days > 90,
        }
        fn = bucket_filters.get(f.age_bucket)
        if fn:
            q = q.filter(fn())
    return q


def get_kpis(db: Session, filters: DashboardFilters) -> list[KPICard]:
    q = _apply_filters(db.query(Requirement), filters)

    total = q.count()
    revenue_impact = q.with_entities(func.coalesce(func.sum(Requirement.revenue_impact), 0)).scalar() or 0
    revenue_won = q.with_entities(func.coalesce(func.sum(Requirement.revenue_won), 0)).scalar() or 0
    revenue_at_risk = q.with_entities(func.coalesce(func.sum(Requirement.revenue_at_risk), 0)).scalar() or 0

    open_reqs = _apply_filters(db.query(Requirement), filters)
    open_reqs = open_reqs.filter(Requirement.fulfillment_status.in_(list(OPEN_STATUSES))).count()

    fulfilled = _apply_filters(db.query(Requirement), filters)
    fulfilled = fulfilled.filter(Requirement.fulfillment_status.in_(list(FULFILLED_STATUSES))).count()

    fulfillment_rate = round((fulfilled / total * 100) if total > 0 else 0, 1)

    sla_breach = _apply_filters(db.query(Requirement), filters)
    sla_breach = sla_breach.filter(Requirement.sla_breach_days > 0).count()
    sla_pct = round((sla_breach / total * 100) if total > 0 else 0, 1)

    def fmt_currency(v: float) -> str:
        if v >= 1_000_000:
            return f"${v/1_000_000:.2f}M"
        if v >= 1_000:
            return f"${v/1_000:.1f}K"
        return f"${v:,.0f}"

    return [
        KPICard(key="total_revenue", label="Total Revenue Impact", value=revenue_impact,
                formatted_value=fmt_currency(revenue_impact), color="primary", icon="bi-currency-dollar"),
        KPICard(key="revenue_won", label="Revenue Won", value=revenue_won,
                formatted_value=fmt_currency(revenue_won), color="success", icon="bi-trophy"),
        KPICard(key="revenue_at_risk", label="Revenue At Risk", value=revenue_at_risk,
                formatted_value=fmt_currency(revenue_at_risk), color="danger", icon="bi-exclamation-triangle"),
        KPICard(key="fulfillment_rate", label="Fulfillment Rate", value=fulfillment_rate,
                formatted_value=f"{fulfillment_rate}%", color="info", icon="bi-percent"),
        KPICard(key="open_requirements", label="Open Requirements", value=open_reqs,
                formatted_value=str(open_reqs), color="warning", icon="bi-file-earmark-text"),
        KPICard(key="sla_breach_pct", label="SLA Breach %", value=sla_pct,
                formatted_value=f"{sla_pct}%", color="secondary", icon="bi-clock-history"),
    ]


def get_home_tiles(db: Session) -> dict[str, Any]:
    q = db.query(Requirement).filter(Requirement.is_deleted == False)
    total = q.count()
    open_reqs = q.filter(Requirement.fulfillment_status.in_(list(OPEN_STATUSES))).count()
    q2 = db.query(Requirement).filter(Requirement.is_deleted == False)
    fulfilled = q2.filter(Requirement.fulfillment_status.in_(list(FULFILLED_STATUSES))).count()

    q3 = db.query(Requirement).filter(Requirement.is_deleted == False)
    revenue_impact = q3.with_entities(func.coalesce(func.sum(Requirement.revenue_impact), 0)).scalar() or 0
    revenue_at_risk = db.query(func.coalesce(func.sum(Requirement.revenue_at_risk), 0)).filter(Requirement.is_deleted == False).scalar() or 0

    # Average ageing in days (numeric records only)
    all_reqs = db.query(Requirement).filter(
        Requirement.is_deleted == False,
        Requirement.requirement_ageing_calendar_days.isnot(None),
    ).all()
    numeric_ages = []
    for r in all_reqs:
        try:
            numeric_ages.append(int(r.requirement_ageing_calendar_days))
        except (ValueError, TypeError):
            pass
    avg_age = round(sum(numeric_ages) / len(numeric_ages)) if numeric_ages else 0

    def fmt(v: float) -> str:
        if v >= 1_000_000:
            return f"${v/1_000_000:.2f}M"
        if v >= 1_000:
            return f"${v/1_000:.1f}K"
        return f"${v:,.0f}"

    return {
        "total_requirements": total,
        "open_requirements": open_reqs,
        "fulfilled_requirements": fulfilled,
        "revenue_impact": fmt(revenue_impact),
        "revenue_at_risk": fmt(revenue_at_risk),
        "avg_requirement_age": avg_age,
    }


def get_revenue_funnel(db: Session, filters: DashboardFilters) -> dict[str, Any]:
    q = _apply_filters(db.query(Requirement), filters)
    rows = q.with_entities(Requirement.fulfillment_perspective, func.count()).group_by(Requirement.fulfillment_perspective).all()
    data = {r[0] or "Unknown": r[1] for r in rows}
    return {"type": "funnel", "data": data}


def get_revenue_by_status(db: Session, filters: DashboardFilters) -> dict[str, Any]:
    q = _apply_filters(db.query(Requirement), filters)
    rows = q.with_entities(
        Requirement.fulfillment_status,
        func.coalesce(func.sum(Requirement.revenue_impact), 0),
        func.count(),
    ).group_by(Requirement.fulfillment_status).all()
    statuses = [r[0] or "Unknown" for r in rows]
    revenue = [float(r[1]) for r in rows]
    counts = [r[2] for r in rows]
    return {"type": "stacked_bar", "statuses": statuses, "revenue": revenue, "counts": counts}


def get_aging_distribution(db: Session, filters: DashboardFilters) -> dict[str, Any]:
    q = _apply_filters(db.query(Requirement), filters)
    records = q.with_entities(Requirement.requirement_ageing_calendar_days).all()
    buckets = {"0-15": 0, "16-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for (age_str,) in records:
        try:
            age = int(age_str)
            if age <= 15:
                buckets["0-15"] += 1
            elif age <= 30:
                buckets["16-30"] += 1
            elif age <= 60:
                buckets["31-60"] += 1
            elif age <= 90:
                buckets["61-90"] += 1
            else:
                buckets["90+"] += 1
        except (ValueError, TypeError):
            pass
    return {"type": "histogram", "buckets": list(buckets.keys()), "counts": list(buckets.values())}


def get_top_skills(db: Session, filters: DashboardFilters, top_n: int = 10) -> dict[str, Any]:
    q = _apply_filters(db.query(Requirement), filters)
    rows = (
        q.with_entities(Requirement.skill_consolidated, func.count())
        .filter(Requirement.skill_consolidated.isnot(None))
        .filter(Requirement.skill_consolidated != "")
        .filter(Requirement.skill_consolidated != "Invalid RGS")
        .filter(Requirement.skill_consolidated != "Verify the Skill")
        .group_by(Requirement.skill_consolidated)
        .order_by(func.count().desc())
        .limit(top_n)
        .all()
    )
    skills = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    return {"type": "horizontal_bar", "skills": skills, "counts": counts}


def get_custom_chart(
    db: Session,
    filters: DashboardFilters,
    measure: str,
    dimension: str,
) -> dict[str, Any]:
    q = _apply_filters(db.query(Requirement), filters)

    dim_col = _dimension_col(dimension)
    if dim_col is None:
        return {"error": f"Unknown dimension: {dimension}"}

    measure_expr = _measure_expr(measure)
    if measure_expr is None:
        return {"error": f"Unknown measure: {measure}"}

    rows = (
        q.with_entities(dim_col, measure_expr)
        .filter(dim_col.isnot(None))
        .filter(dim_col != "")
        .group_by(dim_col)
        .order_by(measure_expr.desc())
        .limit(20)
        .all()
    )
    labels = [str(r[0]) for r in rows]
    values = [float(r[1] or 0) for r in rows]
    return {"labels": labels, "values": values, "measure": measure, "dimension": dimension}


def _dimension_col(dim: str):
    mapping = {
        "skill": Requirement.skill_consolidated,
        "customer": Requirement.group_customer_name,
        "account": Requirement.account_name,
        "service_practice": Requirement.service_practice,
        "country": Requirement.country,
        "iou": Requirement.iou,
        "fulfillment_channel": Requirement.fulfillment_channel,
        "delivery_manager": Requirement.delivery_manager,
        "fulfillment_status": Requirement.fulfillment_status,
        "requirement_month": Requirement.requirement_month,
        "it_bps": Requirement.it_bps,
    }
    return mapping.get(dim)


def _measure_expr(measure: str):
    mapping = {
        "revenue_impact": func.coalesce(func.sum(Requirement.revenue_impact), 0),
        "requirement_count": func.count(Requirement.requirement_id),
        "fulfillment_count": func.count(
            case((Requirement.fulfillment_status.in_(list(FULFILLED_STATUSES)), 1))
        ),
        "evaluation_count": func.count(
            case((Requirement.evaluation_status.isnot(None), 1))
        ),
    }
    return mapping.get(measure)


def get_filter_options(db: Session) -> FilterOptions:
    def distinct(col):
        return [
            r[0] for r in db.query(col).filter(col.isnot(None)).filter(col != "").distinct().order_by(col).all()
        ]

    return FilterOptions(
        fulfillment_statuses=distinct(Requirement.fulfillment_status),
        ious=distinct(Requirement.iou),
        sub_ious=distinct(Requirement.sub_iou),
        service_practices=distinct(Requirement.service_practice),
        delivery_managers=distinct(Requirement.delivery_manager),
        customers=distinct(Requirement.group_customer_name),
        accounts=distinct(Requirement.account_name),
        domains=distinct(Requirement.domain),
        countries=distinct(Requirement.country),
        branches=distinct(Requirement.branch),
        onsite_offshore_options=distinct(Requirement.onsite_offshore),
        skills=distinct(Requirement.skill_consolidated),
        competencies=distinct(Requirement.competency),
        experience_ranges=distinct(Requirement.experience_range),
        requirement_months=distinct(Requirement.requirement_month),
        fulfillment_channels=distinct(Requirement.fulfillment_channel),
        fulfillment_perspectives=distinct(Requirement.fulfillment_perspective),
        it_bps_options=distinct(Requirement.it_bps),
    )


def generate_alerts(db: Session) -> list[Alert]:
    from datetime import date as dt_date
    existing_ids = {a.requirement_id + a.alert_type for a in db.query(Alert).all()}
    new_alerts: list[Alert] = []

    reqs = db.query(Requirement).filter(Requirement.is_deleted == False).all()
    for req in reqs:
        try:
            age = int(req.requirement_ageing_calendar_days or 0)
        except (ValueError, TypeError):
            age = 0

        key30 = req.requirement_id + "aging_30"
        if age > 30 and key30 not in existing_ids:
            new_alerts.append(Alert(
                requirement_id=req.requirement_id,
                alert_type="aging_30",
                message=f"Requirement {req.requirement_id} has been open for {age} days (>30 days).",
                severity="warning",
            ))

        key60 = req.requirement_id + "aging_60"
        if age > 60 and key60 not in existing_ids:
            new_alerts.append(Alert(
                requirement_id=req.requirement_id,
                alert_type="aging_60",
                message=f"Requirement {req.requirement_id} has been open for {age} days (>60 days).",
                severity="danger",
            ))

        if req.revenue_at_risk and req.revenue_at_risk > 100000:
            key_rev = req.requirement_id + "revenue_at_risk"
            if key_rev not in existing_ids:
                new_alerts.append(Alert(
                    requirement_id=req.requirement_id,
                    alert_type="revenue_at_risk",
                    message=f"High revenue at risk: ${req.revenue_at_risk:,.0f} for {req.requirement_id}.",
                    severity="danger",
                ))

    for a in new_alerts:
        db.add(a)
    if new_alerts:
        db.commit()
    return new_alerts
