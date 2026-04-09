# -*- coding: utf-8 -*-
"""认证与配置相关最小回归测试。"""

from core.config import ENV_FILE, settings
from tests.conftest import auth_headers, create_client, login_as


def test_env_file_is_backend_dotenv():
    """配置应固定读取 backend/.env，而不是依赖当前工作目录。"""
    assert ENV_FILE.name == ".env"
    assert ENV_FILE.exists()
    assert settings.DB_NAME == "aistu"


def test_users_me_requires_authentication():
    """未登录访问个人信息接口应返回 401。"""
    client = create_client()
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "无法验证凭据"


def test_login_success_and_fetch_user_info():
    """登录成功后应能获取当前用户信息。"""
    client = create_client()
    token = login_as(client)

    response = client.get("/api/users/me", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["username"] == "admin"
    assert body["data"]["role"] == "admin"
