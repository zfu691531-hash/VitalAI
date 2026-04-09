# -*- coding: utf-8 -*-
"""Schemas for student care data inputs/outputs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AttendanceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int = Field(..., description="Student id")
    date: date
    status: str = Field(..., description="normal/late/absent/early_leave")
    remark: str | None = None


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str | None = None
    remark: str | None = None


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    date: date
    status: str
    remark: str | None = None
    created_at: datetime | None = None


class BehaviorEventCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    event_type: str = Field(..., description="discipline/conflict/warning")
    event_level: str = Field(..., description="low/medium/high")
    event_desc: str
    occurred_at: datetime


class BehaviorEventUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str | None = None
    event_level: str | None = None
    event_desc: str | None = None
    occurred_at: datetime | None = None


class BehaviorEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    event_type: str
    event_level: str
    event_desc: str
    occurred_at: datetime
    created_at: datetime | None = None


class CareObservationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    dimension: str = Field(..., description="emotion/social/safety/family/study/behavior")
    observation_type: str = Field(..., description="care_talk/emotion/social/safety/study/behavior/follow_up")
    observation_level: str = Field(..., description="low/medium/high")
    observed_at: datetime
    summary: str


class CareObservationUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension: str | None = None
    observation_type: str | None = None
    observation_level: str | None = None
    observed_at: datetime | None = None
    summary: str | None = None


class CareObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    dimension: str
    observation_type: str
    observation_level: str
    observed_at: datetime
    summary: str
    created_at: datetime | None = None


class FamilyContactCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    contact_type: str = Field(..., description="phone/meeting/home_visit")
    summary: str


class FamilyContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    contact_type: str
    summary: str
    created_at: datetime | None = None


class AssistantSummaryCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    summary_text: str
    signals_json: dict[str, Any] | None = None


class AssistantSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    summary_text: str
    signals_json: dict[str, Any] | None = None
    created_at: datetime | None = None


class GraphRelationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    target_type: str = Field(..., description="student/event")
    target_student_id: int | None = None
    relation_type: str
    dimension: str = Field(..., description="emotion/social/safety/family/study/behavior")
    relation_level: str = Field(..., description="low/medium/high")
    summary: str
    event_title: str | None = None
    occurred_at: datetime | None = None


class GraphRelationUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_type: str | None = None
    target_student_id: int | None = None
    relation_type: str | None = None
    dimension: str | None = None
    relation_level: str | None = None
    summary: str | None = None
    event_title: str | None = None
    occurred_at: datetime | None = None


class GraphRelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    target_type: str
    target_student_id: int | None = None
    target_student_name: str | None = None
    target_student_no: str | None = None
    relation_type: str
    dimension: str
    relation_level: str
    summary: str
    event_title: str | None = None
    occurred_at: datetime | None = None
    created_at: datetime | None = None
