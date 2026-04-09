# -*- coding: utf-8 -*-
"""Schemas for rule rag feature."""

from pydantic import BaseModel, Field


class RuleRagAskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    chat_history: list[dict] | None = Field(default=None, description="对话历史")


class RuleRagFeedbackRequest(BaseModel):
    qa_record_id: int = Field(..., description="问答记录ID")
    rating: str = Field(..., description="up/down")
    improvement_reason: str | None = Field(default=None, description="改进理由")
    suggested_answer: str | None = Field(default=None, description="建议答案")


class RuleFeedbackReviewRequest(BaseModel):
    review_note: str | None = Field(default=None, description="处理说明")
    revised_title: str | None = Field(default=None, description="修订后的标题")
    revised_category: str | None = Field(default=None, description="修订后的分类")
    revised_content: str | None = Field(default=None, description="修订后的内容")
