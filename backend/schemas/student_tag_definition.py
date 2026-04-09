from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TagDefinitionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope_type: str = Field(..., description="school/grade/class")
    scope_value: Optional[str] = None
    tag_text: str
    polarity: str = Field(..., description="positive/neutral/negative")
    dimension: Optional[str] = None
    weight: Optional[float] = None
    description: Optional[str] = None


class TagDefinitionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope_type: Optional[str] = None
    scope_value: Optional[str] = None
    tag_text: Optional[str] = None
    polarity: Optional[str] = None
    dimension: Optional[str] = None
    weight: Optional[float] = None
    description: Optional[str] = None


class TagDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope_type: str
    scope_value: Optional[str] = None
    tag_text: str
    polarity: str
    dimension: Optional[str] = None
    weight: Optional[float] = None
    description: Optional[str] = None
