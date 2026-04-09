# -*- coding: utf-8 -*-
"""Schemas for isolation Bayesian-network plugin."""

from pydantic import BaseModel, Field


class IsolationEvidenceItem(BaseModel):
    rule_id: str
    label: str
    lr: float
    signal_text: str = ""
    source: str = ""


class IsolationRootCauseItem(BaseModel):
    node: str
    label: str
    probability: float
    impact: float
    contribution: float
    description: str
    evidence: list[IsolationEvidenceItem] = Field(default_factory=list)


class IsolationPathItem(BaseModel):
    path_id: str
    nodes: list[str] = Field(default_factory=list)
    path_probability: float
    summary: str


class IsolationFactorItem(BaseModel):
    id: str
    label: str
    weight: float
    signal_text: str = ""
    source: str = ""


class StudentCareIsolationPayload(BaseModel):
    student_id: int
    scene: str
    risk_probability: float
    risk_level: str
    confidence: float
    root_causes: list[IsolationRootCauseItem] = Field(default_factory=list)
    propagation_paths: list[IsolationPathItem] = Field(default_factory=list)
    evidence_summary: dict = Field(default_factory=dict)
    network_snapshot: dict = Field(default_factory=dict)
