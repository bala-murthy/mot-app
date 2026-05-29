from __future__ import annotations
from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, field_validator


# ─── Requirement ────────────────────────────────────────────────────────────

class RequirementBase(BaseModel):
    fulfillment_status: Optional[str] = None
    group_customer_name: Optional[str] = None
    account_name: Optional[str] = None
    domain: Optional[str] = None
    iou: Optional[str] = None
    sub_iou: Optional[str] = None
    country: Optional[str] = None
    branch: Optional[str] = None
    primary_competency_proficiency_details: Optional[str] = None
    competency: Optional[str] = None
    experience_range: Optional[str] = None
    revenue_impact: Optional[float] = None
    onsite_offshore: Optional[str] = None
    delivery_manager: Optional[str] = None
    skill_manually_entered: Optional[str] = None
    added_date: Optional[date] = None
    service_practice: Optional[str] = None
    target_fulfillment_date: Optional[date] = None
    revenue_at_risk: Optional[float] = None
    revenue_won: Optional[float] = None
    requirement_start_date: Optional[date] = None
    candidate_name: Optional[str] = None
    fulfillment_channel: Optional[str] = None
    evaluation_status: Optional[str] = None
    candidate_evaluation_stage: Optional[str] = None
    sub_practice: Optional[str] = None
    gbams_requirement_id: Optional[str] = None
    sla_breach_days: Optional[int] = None


class RequirementRead(RequirementBase):
    requirement_id: str
    requirement_ageing_calendar_days: Optional[str] = None
    observation: Optional[str] = None
    won_sp: Optional[str] = None
    skill_consolidated: Optional[str] = None
    skill_consolidated_second_skill: Optional[str] = None
    fulfillment_perspective: Optional[str] = None
    requirement_ageing_months: Optional[str] = None
    pending_with: Optional[str] = None
    gbams_rmg_name: Optional[str] = None
    evaluator_emp_name: Optional[str] = None
    requirement_month: Optional[str] = None
    it_bps: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    upload_batch_id: Optional[str] = None
    is_locked: Optional[bool] = False

    model_config = {"from_attributes": True}


class RequirementUpdate(RequirementBase):
    session_id: str


class RequirementListResponse(BaseModel):
    items: list[RequirementRead]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Upload ─────────────────────────────────────────────────────────────────

class UploadResult(BaseModel):
    batch_id: str
    filename: str
    total_rows: int
    rows_loaded: int
    rows_skipped: int
    rows_failed: int
    status: str
    errors: list[str] = []
    transformation_summary: dict[str, Any] = {}


# ─── Lock ────────────────────────────────────────────────────────────────────

class LockRequest(BaseModel):
    session_id: str


class LockResponse(BaseModel):
    success: bool
    message: str
    locked_by_session: Optional[str] = None
    expires_at: Optional[datetime] = None


# ─── Download ───────────────────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    fulfillment_status: Optional[str] = None
    requirement_id: Optional[str] = None
    group_customer_name: Optional[str] = None
    account_name: Optional[str] = None
    format: str = "excel"


# ─── Dashboard ──────────────────────────────────────────────────────────────

class KPICard(BaseModel):
    key: str
    label: str
    value: Any
    formatted_value: str
    change_pct: Optional[float] = None
    color: str = "primary"
    icon: str = "bi-bar-chart"


class DashboardFilters(BaseModel):
    iou: Optional[str] = None
    sub_iou: Optional[str] = None
    service_practice: Optional[str] = None
    delivery_manager: Optional[str] = None
    gbams_rmg_name: Optional[str] = None
    group_customer_name: Optional[str] = None
    account_name: Optional[str] = None
    domain: Optional[str] = None
    country: Optional[str] = None
    branch: Optional[str] = None
    onsite_offshore: Optional[str] = None
    requirement_id: Optional[str] = None
    fulfillment_status: Optional[str] = None
    age_bucket: Optional[str] = None
    pending_with: Optional[str] = None
    skill_consolidated: Optional[str] = None
    skill_consolidated_second: Optional[str] = None
    competency: Optional[str] = None
    experience_range: Optional[str] = None
    requirement_month: Optional[str] = None
    it_bps: Optional[str] = None


class FilterOptions(BaseModel):
    fulfillment_statuses: list[str]
    ious: list[str]
    sub_ious: list[str]
    service_practices: list[str]
    delivery_managers: list[str]
    customers: list[str]
    accounts: list[str]
    domains: list[str]
    countries: list[str]
    branches: list[str]
    onsite_offshore_options: list[str]
    skills: list[str]
    competencies: list[str]
    experience_ranges: list[str]
    requirement_months: list[str]
    fulfillment_channels: list[str]
    fulfillment_perspectives: list[str]
    it_bps_options: list[str]


# ─── Alerts ─────────────────────────────────────────────────────────────────

class AlertRead(BaseModel):
    id: int
    requirement_id: str
    alert_type: str
    message: str
    severity: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Chart Builder ───────────────────────────────────────────────────────────

class ChartConfig(BaseModel):
    chart_name: str
    chart_type: str
    measure: str
    dimension: str
    filters: DashboardFilters = DashboardFilters()


class SavedChartRead(BaseModel):
    id: int
    chart_name: str
    chart_config: str
    created_at: datetime
    is_pinned: bool

    model_config = {"from_attributes": True}
