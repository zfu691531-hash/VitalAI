# -*- coding: utf-8 -*-
"""Graph database settings for student care."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class GraphSettings(BaseSettings):
    """Dedicated graph settings wrapper."""

    neo4j_enabled: bool = False
    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

