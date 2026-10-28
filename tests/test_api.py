import pytest

def test_api_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["mode"] == "offline-first"
    assert data["capabilities"]["sqlite_storage"] is True

def test_api_dashboard_summary(client):
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert "metrics" in data
    assert "total_registered_students" in data["metrics"]

def test_api_create_and_list_students(client):
    # Valid student
    res = client.post("/api/v1/students", json={
        "student_id": "TEST_ROLL_101",
        "name": "Jordan Lee",
        "email": "jordan@example.edu",
        "batch": "CS-2026",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["student"]["student_id"] == "TEST_ROLL_101"

    # List
    res_list = client.get("/api/v1/students?search=Jordan")
    assert res_list.status_code == 200
    assert len(res_list.get_json()["students"]) == 1

    # Duplicate check
    res_dup = client.post("/api/v1/students", json={
        "student_id": "TEST_ROLL_101",
        "name": "Jordan Duplicate",
    })
    assert res_dup.status_code == 409

    # Validation failure (missing name)
    res_bad = client.post("/api/v1/students", json={"student_id": "BAD"})
    assert res_bad.status_code == 400

def test_api_create_and_retrieve_session(client):
    res = client.post("/api/v1/sessions", json={
        "title": "Machine Learning Lab 1",
        "expected_duration_minutes": 90,
        "input_source_type": "synthetic",
    })
    assert res.status_code == 201
    s_id = res.get_json()["session"]["id"]

    res_get = client.get(f"/api/v1/sessions/{s_id}")
    assert res_get.status_code == 200
    assert res_get.get_json()["session"]["title"] == "Machine Learning Lab 1"

def test_api_privacy_settings(client):
    # GET settings
    res = client.get("/api/v1/settings/privacy")
    assert res.status_code == 200
    assert res.get_json()["settings"]["retain_raw_video"] is False

    # POST update settings
    res_up = client.post("/api/v1/settings/privacy", json={
        "data_retention_days": 60,
        "consent_required": True,
    })
    assert res_up.status_code == 200
    assert res_up.get_json()["settings"]["data_retention_days"] == 60
