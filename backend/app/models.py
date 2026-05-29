from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, Date, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    # Column R – Primary Key
    requirement_id = Column(String(100), primary_key=True, nullable=False, index=True)

    # Columns A-H (manual)
    fulfillment_status = Column(String(100), index=True)
    group_customer_name = Column(String(200), index=True)
    account_name = Column(String(200), index=True)
    domain = Column(String(100))
    iou = Column(String(100))
    sub_iou = Column(String(100))
    country = Column(String(100))
    branch = Column(String(100))

    # Column I – derived (Rule 12)
    requirement_ageing_calendar_days = Column(String(50))

    # Column J – derived (Rule 1)
    observation = Column(String(100))

    # Columns K-O (manual)
    primary_competency_proficiency_details = Column(String(300))
    competency = Column(String(100))
    experience_range = Column(String(50))
    revenue_impact = Column(Float)
    onsite_offshore = Column(String(50))

    # Column P – derived (Rule 2)
    won_sp = Column(String(200))

    # Columns Q-U (manual)
    delivery_manager = Column(String(200), index=True)
    skill_manually_entered = Column(String(200))
    added_date = Column(Date)
    service_practice = Column(String(100))

    # Columns V-X – derived (Rules 3-5)
    skill_consolidated = Column(String(200))
    skill_consolidated_second_skill = Column(String(200))
    fulfillment_perspective = Column(String(100))

    # Columns Y-AD (manual)
    target_fulfillment_date = Column(Date)
    revenue_at_risk = Column(Float)
    revenue_won = Column(Float)
    requirement_start_date = Column(Date)
    candidate_name = Column(String(200))
    fulfillment_channel = Column(String(100))

    # Columns AE-AH – derived (Rules 6-9)
    requirement_ageing_months = Column(String(50))
    pending_with = Column(String(200))
    gbams_rmg_name = Column(String(200))
    evaluator_emp_name = Column(String(200))

    # Columns AI-AM (manual)
    evaluation_status = Column(String(100))
    candidate_evaluation_stage = Column(String(100))
    sub_practice = Column(String(100))
    gbams_requirement_id = Column(String(50))
    sla_breach_days = Column(Integer)

    # Columns AN-AO – derived (Rules 10-11)
    requirement_month = Column(String(20), index=True)
    it_bps = Column(String(10))

    # System metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    upload_batch_id = Column(String(50), ForeignKey("upload_batches.batch_id"), nullable=True)
    is_deleted = Column(Boolean, default=False)

    lock = relationship("RecordLock", back_populates="requirement", uselist=False)


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    batch_id = Column(String(50), primary_key=True)
    filename = Column(String(255))
    uploaded_at = Column(DateTime, server_default=func.now())
    total_rows = Column(Integer, default=0)
    rows_loaded = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    status = Column(String(50), default="processing")
    error_summary = Column(Text, nullable=True)


class RecordLock(Base):
    __tablename__ = "record_locks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String(100), ForeignKey("requirements.requirement_id"), unique=True, nullable=False)
    session_id = Column(String(100), nullable=False)
    locked_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)

    requirement = relationship("Requirement", back_populates="lock")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now())
    session_id = Column(String(100))
    record_id = Column(String(100), nullable=True)
    action_type = Column(String(50))
    details = Column(Text, nullable=True)


class TransformationAudit(Base):
    __tablename__ = "transformation_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String(100))
    rule_id = Column(Integer)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    executed_at = Column(DateTime, server_default=func.now())
    status = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)


class RGSData(Base):
    __tablename__ = "rgs_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String(100), nullable=False, index=True)
    won_sp = Column(String(200), nullable=True)
    requirement_pending_with = Column(String(200), nullable=True)
    gbams_rmg_name = Column(String(200), nullable=True)
    evaluator_emp_name = Column(String(200), nullable=True)
    requirement_start_date = Column(Date, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    batch_id = Column(String(50), nullable=True)

    __table_args__ = (UniqueConstraint("requirement_id", name="uq_rgs_req_id"),)


class SkillConsolidatedLookup(Base):
    __tablename__ = "skill_consolidated_lookup"

    id = Column(Integer, primary_key=True, autoincrement=True)
    input_skill = Column(String(200), nullable=False, index=True)
    consolidated_skill = Column(String(200), nullable=True)
    second_consolidated_skill = Column(String(200), nullable=True)
    verify_skill_flag = Column(String(5), nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())


class ParameterData(Base):
    __tablename__ = "parameter_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fulfillment_status = Column(String(100), nullable=False, index=True)
    fulfillment_perspective = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String(100), nullable=False)
    alert_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="warning")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("session_id", "preference_key", name="uq_pref"),)


class SavedChart(Base):
    __tablename__ = "saved_charts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    chart_name = Column(String(200), nullable=False)
    chart_config = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_pinned = Column(Boolean, default=False)
