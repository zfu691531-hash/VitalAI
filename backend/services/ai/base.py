# -*- coding: utf-8 -*-
"""Common AI client helpers."""

from __future__ import annotations

import time
import asyncio
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from database.models.ai_history import AiHistory
from utils.logger import logger


class AiClient:
    """Unified wrapper for chat and embedding requests."""

    def __init__(self):
        self.base_url = settings.AI_API_BASE_URL
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL_NAME
        self.timeout = settings.AI_TIMEOUT
        self.max_retries = 3

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model_name: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> str:
        if not self.base_url or not self.api_key or not self.model:
            return "AI 服务未配置，请联系管理员检查模型参数。"

        if "api.example.com" in self.base_url:
            return "AI 服务仍在使用占位地址，请联系管理员完成模型配置。"

        payload = {
            "model": model_name or self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        retry_count = max_retries if max_retries is not None else self.max_retries
        request_timeout = timeout if timeout is not None else self.timeout
        for attempt in range(retry_count):
            try:
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                last_error = "AI 服务响应超时"
                logger.warning("AI call timeout, retry=%s", attempt + 1)
                if attempt + 1 < retry_count:
                    await asyncio.sleep(2**attempt)
            except httpx.HTTPStatusError as exc:
                last_error = f"AI 服务返回错误: {exc.response.status_code}"
                logger.error("AI HTTP error: %s %s", exc.response.status_code, exc.response.text)
                break
            except Exception as exc:  # pragma: no cover
                last_error = f"AI 服务异常: {exc}"
                logger.error("AI call error: %s", exc)
                if attempt + 1 < retry_count:
                    await asyncio.sleep(2**attempt)

        return f"AI服务繁忙，请稍后再试。{last_error or 'AI 服务异常'}"

    def embed_texts(self, texts: list[str], model_name: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        if not self.base_url or not self.api_key:
            logger.warning("embedding request skipped: AI config missing")
            return []

        model = model_name or getattr(settings, "AI_EMBEDDING_MODEL_NAME", "") or self.model
        if not model:
            logger.warning("embedding request skipped: embedding model missing")
            return []

        payload = {
            "model": model,
            "input": texts,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    rows = data.get("data") or []
                    embeddings = [item.get("embedding") or [] for item in rows]
                    if len(embeddings) == len(texts):
                        return embeddings
                    return []
            except httpx.TimeoutException:
                last_error = "embedding 请求超时"
                logger.warning("embedding timeout, retry=%s", attempt + 1)
                time.sleep(2**attempt)
            except httpx.HTTPStatusError as exc:
                last_error = f"embedding 接口错误: {exc.response.status_code}"
                logger.error("embedding HTTP error: %s %s", exc.response.status_code, exc.response.text)
                break
            except Exception as exc:  # pragma: no cover
                last_error = f"embedding 异常: {exc}"
                logger.error("embedding error: %s", exc)
                time.sleep(2**attempt)

        logger.warning("embedding request failed: %s", last_error)
        return []


ai_client = AiClient()


def save_history(
    db: Session,
    user_id: int,
    tool_type: str,
    input_params: dict,
    content: str,
    student_id: Optional[int] = None,
    class_id: Optional[int] = None,
) -> AiHistory:
    history = AiHistory(
        user_id=user_id,
        tool_type=tool_type,
        input_params=input_params,
        content=content,
        student_id=student_id,
        class_id=class_id,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    logger.info("保存 AI 历史: user=%s, tool=%s", user_id, tool_type)
    return history
