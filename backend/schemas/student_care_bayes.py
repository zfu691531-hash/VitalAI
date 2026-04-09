from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StudentCareBayesRuleUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: Optional[bool] = None
    prior: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    blend_alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    likelihood_ratio: Optional[float] = Field(default=None, gt=0.0)
    description: Optional[str] = None


class StudentCareBayesRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension: str
    evidence_key: str
    enabled: bool
    prior: Optional[float] = None
    blend_alpha: Optional[float] = None
    likelihood_ratio: Optional[float] = None
    description: Optional[str] = None
    source: str = "default"
