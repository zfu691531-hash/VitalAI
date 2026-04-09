# -*- coding: utf-8 -*-
"""权限主干最小回归测试。"""

from tests.conftest import create_client


def test_school_rule_create_requires_login():
    """未登录用户不能直接创建校规。"""
    client = create_client()
    response = client.post(
        "/api/school-rules",
        json={"category": "测试", "title": "测试标题", "content": "测试内容"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "无法验证凭据"
