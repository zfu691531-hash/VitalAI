# -*- coding: utf-8 -*-
"""Student update regression tests."""

from .conftest import auth_headers, create_client, login_as


def test_update_student_can_clear_tags_and_refresh_care_profile():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    seed_resp = client.put(
        "/api/students/17",
        headers=headers,
        json={"tags": "待分班"},
    )
    assert seed_resp.status_code == 200

    clear_resp = client.put(
        "/api/students/17",
        headers=headers,
        json={"tags": None},
    )
    assert clear_resp.status_code == 200

    list_resp = client.get(
        "/api/students",
        headers=headers,
        params={"page": 1, "page_size": 50},
    )
    assert list_resp.status_code == 200
    student_row = next(item for item in list_resp.json()["data"]["list"] if item["id"] == 17)
    assert student_row["tags"] is None

    profile_resp = client.get("/api/student-care/profile/17", headers=headers)
    assert profile_resp.status_code == 200
    payload = profile_resp.json()["data"]
    assert payload is not None
    assert payload["student"]["tags"] is None
    assert all(item["signal_type"] != "tag_social" for item in payload["signals"])
