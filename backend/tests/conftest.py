# -*- coding: utf-8 -*-
"""测试基础夹具。"""

from fastapi.testclient import TestClient

from main import app


def create_client() -> TestClient:
    """创建 FastAPI TestClient。"""
    return TestClient(app)


def login_as(client: TestClient, username: str = "admin", password: str = "admin123") -> str:
    """使用现有测试账号登录并返回 bearer token。"""
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    """生成授权请求头。"""
    return {"Authorization": f"Bearer {token}"}
