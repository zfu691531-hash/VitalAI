from __future__ import annotations

import logging
from typing import Any

from Base.Config.logConfig import setup_logging
from Base.Config.setting import settings

setup_logging()
logger = logging.getLogger(__name__)

_default_qwen_llm: Any | None = None
_default_qwen_llm_loaded = False


def get_default_qwen_llm() -> Any | None:
    """Lazily build the default Qwen client when it is actually needed."""
    global _default_qwen_llm
    global _default_qwen_llm_loaded

    if _default_qwen_llm_loaded:
        return _default_qwen_llm

    _default_qwen_llm_loaded = True
    try:
        from Base.Ai.llms.qwenLlm import create_qwen_llm

        _default_qwen_llm = create_qwen_llm()
    except Exception as exc:  # pragma: no cover - exercised indirectly by import tests
        logger.warning(
            "Default Qwen LLM is unavailable; continuing without eager model bootstrap: %s",
            exc,
        )
        _default_qwen_llm = None
    return _default_qwen_llm


def __getattr__(name: str) -> Any:
    """Preserve the historical module API while making heavy globals lazy."""
    if name == "default_qwen_llm":
        return get_default_qwen_llm()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["settings", "default_qwen_llm", "get_default_qwen_llm"]
