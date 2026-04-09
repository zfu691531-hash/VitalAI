# -*- coding: utf-8 -*-
"""Tests for graph config."""

from core.graph_config import GraphSettings


def test_graph_settings_defaults():
    settings = GraphSettings()
    assert settings.neo4j_enabled is False
    assert settings.neo4j_uri == "bolt://127.0.0.1:7687"
    assert settings.neo4j_username == "neo4j"
    assert settings.neo4j_database == "neo4j"

