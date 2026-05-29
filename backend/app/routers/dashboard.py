import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, SavedChart, UserPreference
from ..schemas import (
    AlertRead,
    ChartConfig,
    DashboardFilters,
    FilterOptions,
    KPICard,
    SavedChartRead,
)
from ..services import dashboard_service

router = APIRouter()


def _parse_filters(
    iou: Optional[str] = None,
    sub_iou: Optional[str] = None,
    service_practice: Optional[str] = None,
    delivery_manager: Optional[str] = None,
    gbams_rmg_name: Optional[str] = None,
    group_customer_name: Optional[str] = None,
    account_name: Optional[str] = None,
    domain: Optional[str] = None,
    country: Optional[str] = None,
    branch: Optional[str] = None,
    onsite_offshore: Optional[str] = None,
    requirement_id: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    age_bucket: Optional[str] = None,
    pending_with: Optional[str] = None,
    skill_consolidated: Optional[str] = None,
    competency: Optional[str] = None,
    experience_range: Optional[str] = None,
    requirement_month: Optional[str] = None,
    it_bps: Optional[str] = None,
) -> DashboardFilters:
    return DashboardFilters(
        iou=iou, sub_iou=sub_iou, service_practice=service_practice,
        delivery_manager=delivery_manager, gbams_rmg_name=gbams_rmg_name,
        group_customer_name=group_customer_name, account_name=account_name,
        domain=domain, country=country, branch=branch,
        onsite_offshore=onsite_offshore, requirement_id=requirement_id,
        fulfillment_status=fulfillment_status, age_bucket=age_bucket,
        pending_with=pending_with, skill_consolidated=skill_consolidated,
        competency=competency, experience_range=experience_range,
        requirement_month=requirement_month, it_bps=it_bps,
    )


@router.get("/dashboard/home", summary="Home page tiles")
def home_tiles(db: Session = Depends(get_db)):
    return dashboard_service.get_home_tiles(db)


@router.get("/dashboard/kpis", response_model=list[KPICard], summary="KPI cards")
def get_kpis(
    filters: DashboardFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_kpis(db, filters)


@router.get("/dashboard/charts/revenue-funnel", summary="Revenue funnel chart data")
def revenue_funnel(
    filters: DashboardFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_revenue_funnel(db, filters)


@router.get("/dashboard/charts/revenue-by-status", summary="Revenue by fulfillment status")
def revenue_by_status(
    filters: DashboardFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_revenue_by_status(db, filters)


@router.get("/dashboard/charts/aging-distribution", summary="Requirement aging distribution")
def aging_distribution(
    filters: DashboardFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_aging_distribution(db, filters)


@router.get("/dashboard/charts/top-skills", summary="Top skills in demand")
def top_skills(
    top_n: int = Query(10, ge=1, le=30),
    filters: DashboardFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_top_skills(db, filters, top_n)


@router.get("/dashboard/charts/custom", summary="Custom chart data")
def custom_chart(
    measure: str = Query("requirement_count"),
    dimension: str = Query("fulfillment_status"),
    filters: DashboardFilters = Depends(_parse_filters),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_custom_chart(db, filters, measure, dimension)


@router.get("/dashboard/filter-options", response_model=FilterOptions, summary="Filter dropdown options")
def filter_options(db: Session = Depends(get_db)):
    return dashboard_service.get_filter_options(db)


@router.get("/dashboard/alerts", response_model=list[AlertRead], summary="Active alerts")
def get_alerts(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    dashboard_service.generate_alerts(db)
    q = db.query(Alert)
    if unread_only:
        q = q.filter(Alert.is_read == False)
    return q.order_by(Alert.created_at.desc()).limit(100).all()


@router.patch("/dashboard/alerts/{alert_id}/read", summary="Mark alert as read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found.")
    alert.is_read = True
    db.commit()
    return {"success": True}


@router.post("/dashboard/charts/saved", response_model=SavedChartRead, summary="Save a chart")
def save_chart(config: ChartConfig, session_id: str = Query(...), db: Session = Depends(get_db)):
    chart = SavedChart(
        session_id=session_id,
        chart_name=config.chart_name,
        chart_config=json.dumps(config.model_dump()),
    )
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return chart


@router.get("/dashboard/charts/saved", response_model=list[SavedChartRead], summary="List saved charts")
def list_saved_charts(session_id: str = Query(...), db: Session = Depends(get_db)):
    return db.query(SavedChart).filter(SavedChart.session_id == session_id).order_by(SavedChart.updated_at.desc()).all()
