# -*- coding: utf-8 -*-
"""Lightweight web search service for assistant live-info questions."""

from __future__ import annotations

import httpx


async def search_web(query: str, timeout: int = 12) -> dict:
    params = {
        "q": query,
        "format": "json",
        "no_redirect": "1",
        "no_html": "1",
        "skip_disambig": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get("https://api.duckduckgo.com/", params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        return {
            "summary": "我刚刚尝试联网搜索，但当前外部搜索服务暂时不可用。你可以稍后再试，或换一个不依赖实时联网的信息问题。",
            "sources": [],
        }

    abstract = (data.get("AbstractText") or "").strip()
    heading = (data.get("Heading") or "").strip()
    related_topics = data.get("RelatedTopics") or []

    sources = []
    for item in related_topics[:5]:
        if "Topics" in item:
            for sub in item.get("Topics", [])[:5]:
                text = (sub.get("Text") or "").strip()
                url = (sub.get("FirstURL") or "").strip()
                if text:
                    sources.append({"title": text.split(" - ")[0], "snippet": text, "url": url})
        else:
            text = (item.get("Text") or "").strip()
            url = (item.get("FirstURL") or "").strip()
            if text:
                sources.append({"title": text.split(" - ")[0], "snippet": text, "url": url})

    summary = abstract
    if not summary and sources:
        summary = "；".join(item["snippet"] for item in sources[:3])
    if not summary and heading:
        summary = f"我找到了与“{heading}”相关的结果，但摘要信息较少。"
    if not summary:
        summary = "我已尝试联网搜索，但当前没有拿到足够可靠的公开结果。"

    return {
        "summary": summary,
        "sources": sources[:5],
    }
