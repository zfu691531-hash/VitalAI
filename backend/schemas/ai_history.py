# -*- coding: utf-8 -*-
"""AI 历史相关 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import PaginationParams


class AiHistoryQuery(PaginationParams):
    tool_type: Optional[str] = Field(None, description="工具类型")


class AiHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: str
    tool_type: str
    input_params: Optional[str]
    content: str
    student_id: Optional[int]
    student_name: Optional[str]
    class_id: Optional[int]
    class_name: Optional[str]
    created_at: datetime
