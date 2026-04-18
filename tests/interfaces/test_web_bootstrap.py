"""Tests for the lightweight web overview console."""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from VitalAI.interfaces.api.app import init_http_interfaces
from VitalAI.interfaces.web.bootstrap import init_web_interfaces


class WebBootstrapTests(unittest.TestCase):
    @staticmethod
    def build_test_client() -> TestClient:
        app = FastAPI(title="VitalAI Web Test App")
        init_web_interfaces(app)
        init_http_interfaces(app)
        return TestClient(app)

    def test_root_page_renders_overview_console(self) -> None:
        client = self.build_test_client()

        response = client.get("/")

        self.assertEqual(200, response.status_code)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("VitalAI Overview Console", response.text)
        self.assertIn("/vitalai/users/", response.text)
        self.assertIn("Load Overview", response.text)

    def test_root_page_includes_attention_and_activity_sections(self) -> None:
        client = self.build_test_client()

        response = client.get("/")

        self.assertEqual(200, response.status_code)
        self.assertIn("Recent Activity", response.text)
        self.assertIn("Attention", response.text)
        self.assertIn("attention_items", response.text)
        self.assertIn("recent_activity", response.text)


if __name__ == "__main__":
    unittest.main()
