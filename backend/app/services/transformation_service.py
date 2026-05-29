"""Transformation engine: applies all 12 rules to requirement records."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models import (
    ParameterData,
    RGSData,
    Requirement,
    SkillConsolidatedLookup,
    TransformationAudit,
)

log = logging.getLogger(__name__)


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


class TransformationService:
    def __init__(self, db: Session):
        self.db = db
        self._rgs_cache: dict[str, RGSData] | None = None
        self._skill_cache: dict[str, SkillConsolidatedLookup] | None = None
        self._param_cache: dict[str, str] | None = None

    # ── cache helpers ────────────────────────────────────────────────────────

    def _rgs(self) -> dict[str, RGSData]:
        if self._rgs_cache is None:
            rows = self.db.query(RGSData).all()
            self._rgs_cache = {r.requirement_id: r for r in rows}
        return self._rgs_cache

    def _skills(self) -> dict[str, SkillConsolidatedLookup]:
        if self._skill_cache is None:
            rows = self.db.query(SkillConsolidatedLookup).all()
            self._skill_cache = {r.input_skill.strip().lower(): r for r in rows}
        return self._skill_cache

    def _params(self) -> dict[str, str]:
        if self._param_cache is None:
            rows = self.db.query(ParameterData).all()
            self._param_cache = {
                r.fulfillment_status: r.fulfillment_perspective or "" for r in rows
            }
        return self._param_cache

    # ── transformation rules ─────────────────────────────────────────────────

    def _rule1_observation(self, req: Requirement) -> str:
        """Rule 1: Observation – Valid/Invalid RGS."""
        rgs = self._rgs()
        return "Valid RGS" if req.requirement_id in rgs else "Invalid RGS"

    def _rule2_won_sp(self, req: Requirement) -> str:
        """Rule 2: WON SP from RGS sheet."""
        rgs = self._rgs()
        row = rgs.get(req.requirement_id)
        if row is None:
            return "Invalid RGS"
        return _safe_str(row.won_sp) or "Invalid RGS"

    def _rule3_skill_consolidated(self, req: Requirement) -> str:
        """Rule 3: Skill Consolidated."""
        skill = _safe_str(req.skill_manually_entered).lower()
        skills = self._skills()
        row = skills.get(skill)
        if row is not None:
            return _safe_str(row.consolidated_skill)
        if _safe_str(req.primary_competency_proficiency_details):
            return _safe_str(req.primary_competency_proficiency_details)
        return "Verify the Skill"

    def _rule4_skill_consolidated_second(self, req: Requirement) -> str:
        """Rule 4: Skill Consolidated Second Skill."""
        skill = _safe_str(req.skill_manually_entered).lower()
        skills = self._skills()
        row = skills.get(skill)
        if row is not None:
            return _safe_str(row.second_consolidated_skill)
        return "Verify the Skill"

    def _rule5_fulfillment_perspective(self, req: Requirement) -> str:
        """Rule 5: Fulfillment Perspective from Parameters sheet."""
        params = self._params()
        status = _safe_str(req.fulfillment_status)
        return params.get(status, status)

    def _rule6_requirement_ageing_months(self, req: Requirement) -> str:
        """Rule 6: Requirement Ageing in months."""
        rgs = self._rgs()
        row = rgs.get(req.requirement_id)
        start = req.requirement_start_date if row is None else (row.requirement_start_date or req.requirement_start_date)
        if start is None:
            return "Invalid RGS"
        today = date.today()
        delta = (today - start).days
        months = round(delta / 30)
        return str(months)

    def _rule7_pending_with(self, req: Requirement) -> str:
        """Rule 7: Pending With from RGS sheet."""
        rgs = self._rgs()
        row = rgs.get(req.requirement_id)
        if row is None:
            return "Invalid RGS"
        return _safe_str(row.requirement_pending_with) or "Invalid RGS"

    def _rule8_gbams_rmg_name(self, req: Requirement) -> str:
        """Rule 8: Gbams RMG Name from RGS sheet."""
        rgs = self._rgs()
        row = rgs.get(req.requirement_id)
        if row is None:
            return "Invalid RGS"
        return _safe_str(row.gbams_rmg_name) or "Invalid RGS"

    def _rule9_evaluator_emp_name(self, req: Requirement) -> str:
        """Rule 9: Evaluator Emp Name from RGS sheet."""
        rgs = self._rgs()
        row = rgs.get(req.requirement_id)
        if row is None:
            return "Invalid RGS"
        return _safe_str(row.evaluator_emp_name) or "Invalid RGS"

    def _rule10_requirement_month(self, req: Requirement) -> str:
        """Rule 10: Requirement Month formatted as MMM 'YY."""
        rgs = self._rgs()
        row = rgs.get(req.requirement_id)
        start = req.requirement_start_date if row is None else (row.requirement_start_date or req.requirement_start_date)
        if start is None:
            return ""
        return start.strftime("%b '%y")

    def _rule11_it_bps(self, req: Requirement) -> str:
        """Rule 11: IT/BPS based on Service Practice."""
        sp = _safe_str(req.service_practice).upper()
        return "BPS" if sp == "BPS" else "IT"

    def _rule12_ageing_calendar_days(self, req: Requirement) -> str:
        """Rule 12: Requirement Ageing in Calendar Days."""
        rgs = self._rgs()
        row = rgs.get(req.requirement_id)
        start = req.requirement_start_date if row is None else (row.requirement_start_date or req.requirement_start_date)
        if start is None:
            return "Invalid RGS"
        today = date.today()
        if start > today:
            return "Future Requirement"
        return str((today - start).days + 1)

    # ── public API ───────────────────────────────────────────────────────────

    RULES = [
        (1, "observation", "_rule1_observation"),
        (2, "won_sp", "_rule2_won_sp"),
        (3, "skill_consolidated", "_rule3_skill_consolidated"),
        (4, "skill_consolidated_second_skill", "_rule4_skill_consolidated_second"),
        (5, "fulfillment_perspective", "_rule5_fulfillment_perspective"),
        (6, "requirement_ageing_months", "_rule6_requirement_ageing_months"),
        (7, "pending_with", "_rule7_pending_with"),
        (8, "gbams_rmg_name", "_rule8_gbams_rmg_name"),
        (9, "evaluator_emp_name", "_rule9_evaluator_emp_name"),
        (10, "requirement_month", "_rule10_requirement_month"),
        (11, "it_bps", "_rule11_it_bps"),
        (12, "requirement_ageing_calendar_days", "_rule12_ageing_calendar_days"),
    ]

    def apply_all_rules(self, req: Requirement) -> dict[str, int]:
        """Apply all 12 transformation rules to a single record. Returns counts."""
        counts = {"applied": 0, "failed": 0}
        for rule_id, field, method_name in self.RULES:
            method = getattr(self, method_name)
            old_val = str(getattr(req, field) or "")
            try:
                new_val = method(req)
                setattr(req, field, new_val)
                self._log(req.requirement_id, rule_id, old_val, new_val)
                counts["applied"] += 1
            except Exception as exc:
                log.warning("Rule %d failed for %s: %s", rule_id, req.requirement_id, exc)
                self._log(req.requirement_id, rule_id, old_val, "", status="failed", error=str(exc))
                counts["failed"] += 1
        return counts

    def apply_rules_batch(self, requirements: list[Requirement]) -> dict[str, int]:
        """Apply all rules to a batch of records."""
        total = {"applied": 0, "failed": 0}
        for req in requirements:
            counts = self.apply_all_rules(req)
            total["applied"] += counts["applied"]
            total["failed"] += counts["failed"]
        return total

    def _log(
        self,
        req_id: str,
        rule_id: int,
        prev: str,
        new: str,
        status: str = "success",
        error: str = "",
    ) -> None:
        try:
            entry = TransformationAudit(
                requirement_id=req_id,
                rule_id=rule_id,
                previous_value=prev[:1000] if prev else None,
                new_value=new[:1000] if new else None,
                status=status,
                error_message=error[:500] if error else None,
            )
            self.db.add(entry)
        except Exception:
            pass  # don't let audit failures break the main flow
