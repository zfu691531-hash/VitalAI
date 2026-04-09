from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TagReviewApprove(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scope_type: str
    scope_value: Optional[str] = None
    polarity: str
    dimension: Optional[str] = None
    weight: Optional[float] = None
    description: Optional[str] = None
    review_note: Optional[str] = None


class TagReviewReject(BaseModel):
    model_config = ConfigDict(extra="ignore")

    review_note: Optional[str] = None


class TagReviewOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    tag_text: str
    status: str
    student_id: Optional[int]
    class_id: Optional[int]
    grade: Optional[str]
    source: Optional[str]
    suggested_scope_type: Optional[str]
    suggested_scope_value: Optional[str]
    suggested_polarity: Optional[str]
    suggested_dimension: Optional[str]
    suggested_weight: Optional[float]
    suggested_description: Optional[str]
    suggestion_note: Optional[str]
    created_by: Optional[int]
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    created_at: Optional[datetime]
