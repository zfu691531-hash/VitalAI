# -*- coding: utf-8 -*-
"""Manage Bayesian config overrides for student care."""

from __future__ import annotations

from copy import deepcopy

from sqlalchemy.orm import Session

from core.response import error_response, success_response
from core.student_care_bayes_config import STUDENT_CARE_BAYES_CONFIG
from database.models.student_care_bayes_rule import StudentCareBayesRule
from services.student_care_schema_guard import ensure_student_care_schema


BASE_EVIDENCE_KEY = "__base__"


def _clone_default_config() -> dict:
    return deepcopy(STUDENT_CARE_BAYES_CONFIG)


def _flatten_config(config: dict, source_map: dict[tuple[str, str], str] | None = None) -> list[dict]:
    rows: list[dict] = []
    source_map = source_map or {}
    for dimension, item in config.items():
        rows.append(
            {
                "dimension": dimension,
                "evidence_key": BASE_EVIDENCE_KEY,
                "enabled": bool(item.get("enabled", False)),
                "prior": item.get("prior"),
                "blend_alpha": item.get("blend_alpha"),
                "likelihood_ratio": None,
                "description": None,
                "source": source_map.get((dimension, BASE_EVIDENCE_KEY), "default"),
            }
        )
        for evidence_key, likelihood_ratio in sorted((item.get("evidence_rules") or {}).items()):
            rows.append(
                {
                    "dimension": dimension,
                    "evidence_key": evidence_key,
                    "enabled": bool(item.get("enabled", False)),
                    "prior": None,
                    "blend_alpha": None,
                    "likelihood_ratio": round(float(likelihood_ratio), 4),
                    "description": None,
                    "source": source_map.get((dimension, evidence_key), "default"),
                }
            )
    return rows


def get_effective_bayes_config(db: Session) -> dict:
    ensure_student_care_schema()
    config = _clone_default_config()
    rows = db.query(StudentCareBayesRule).all()
    for row in rows:
        dimension_config = config.setdefault(
            row.dimension,
            {"enabled": True, "prior": 0.0, "blend_alpha": 0.7, "evidence_rules": {}},
        )
        if row.evidence_key == BASE_EVIDENCE_KEY:
            if row.enabled is not None:
                dimension_config["enabled"] = bool(row.enabled)
            if row.prior is not None:
                dimension_config["prior"] = float(row.prior)
            if row.blend_alpha is not None:
                dimension_config["blend_alpha"] = float(row.blend_alpha)
            continue

        if row.likelihood_ratio is not None:
            dimension_config.setdefault("evidence_rules", {})[row.evidence_key] = float(row.likelihood_ratio)
    return config


def list_bayes_rules(db: Session) -> dict:
    ensure_student_care_schema()
    config = _clone_default_config()
    source_map: dict[tuple[str, str], str] = {}
    db_rows = db.query(StudentCareBayesRule).order_by(StudentCareBayesRule.dimension, StudentCareBayesRule.evidence_key).all()
    for row in db_rows:
        dimension_config = config.setdefault(
            row.dimension,
            {"enabled": True, "prior": 0.0, "blend_alpha": 0.7, "evidence_rules": {}},
        )
        source_map[(row.dimension, row.evidence_key)] = "database"
        if row.evidence_key == BASE_EVIDENCE_KEY:
            if row.enabled is not None:
                dimension_config["enabled"] = bool(row.enabled)
            if row.prior is not None:
                dimension_config["prior"] = float(row.prior)
            if row.blend_alpha is not None:
                dimension_config["blend_alpha"] = float(row.blend_alpha)
        elif row.likelihood_ratio is not None:
            dimension_config.setdefault("evidence_rules", {})[row.evidence_key] = float(row.likelihood_ratio)

    return success_response(
        data={
            "dimensions": sorted(config.keys()),
            "rules": _flatten_config(config, source_map),
        }
    )


def update_bayes_rule(
    db: Session,
    current_user,
    dimension: str,
    evidence_key: str,
    payload: dict,
) -> dict:
    ensure_student_care_schema()
    dimension = (dimension or "").strip()
    evidence_key = (evidence_key or "").strip()
    if not dimension:
        return error_response(code=400, msg="dimension 不能为空")
    if not evidence_key:
        return error_response(code=400, msg="evidence_key 不能为空")

    rule = (
        db.query(StudentCareBayesRule)
        .filter(
            StudentCareBayesRule.dimension == dimension,
            StudentCareBayesRule.evidence_key == evidence_key,
        )
        .first()
    )
    if not rule:
        rule = StudentCareBayesRule(dimension=dimension, evidence_key=evidence_key)
        db.add(rule)

    data = {key: value for key, value in (payload or {}).items() if value is not None}
    if evidence_key == BASE_EVIDENCE_KEY:
        if "prior" in data:
            rule.prior = float(data["prior"])
        if "blend_alpha" in data:
            rule.blend_alpha = float(data["blend_alpha"])
        if "enabled" in data:
            rule.enabled = bool(data["enabled"])
        rule.likelihood_ratio = None
    else:
        if "likelihood_ratio" in data:
            rule.likelihood_ratio = float(data["likelihood_ratio"])
        if "enabled" in data:
            rule.enabled = bool(data["enabled"])
        rule.prior = None
        rule.blend_alpha = None

    if "description" in data:
        rule.description = data["description"]
    rule.updated_by = getattr(current_user, "id", None)

    db.commit()
    db.refresh(rule)

    return success_response(
        data={
            "dimension": rule.dimension,
            "evidence_key": rule.evidence_key,
            "enabled": rule.enabled,
            "prior": rule.prior,
            "blend_alpha": rule.blend_alpha,
            "likelihood_ratio": rule.likelihood_ratio,
            "description": rule.description,
            "source": "database",
        }
    )
