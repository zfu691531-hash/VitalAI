# -*- coding: utf-8 -*-
"""Schemas for student care profile."""

from pydantic import BaseModel, Field


class StudentCareSignalResponse(BaseModel):
    id: int
    signal_type: str
    dimension: str
    signal_text: str
    signal_weight: float
    source: str
    created_at: str | None = None


class StudentCareProfileResponse(BaseModel):
    student_id: int
    class_id: int | None = None
    emotion_score: float
    emotion_linear_score: float | None = None
    emotion_bayes_posterior: float | None = None
    emotion_final_score: float | None = None
    social_score: float
    safety_score: float
    safety_linear_score: float | None = None
    safety_bayes_posterior: float | None = None
    safety_final_score: float | None = None
    family_score: float
    family_linear_score: float | None = None
    family_bayes_posterior: float | None = None
    family_final_score: float | None = None
    study_score: float
    behavior_score: float
    overall_risk: float
    risk_level: str
    trend: str
    bayes_results: dict | None = None
    updated_at: str | None = None


class StudentCareProfilePayload(BaseModel):
    student: dict
    profile: StudentCareProfileResponse
    signals: list[StudentCareSignalResponse] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class StudentCareBulkRecalculateOut(BaseModel):
    count: int
