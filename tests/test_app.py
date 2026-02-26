"""Tests for ClawHealth Flask application."""
import json
import pytest
from datetime import datetime, timezone

from app import app as flask_app
from database import db as _db


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with flask_app.app_context():
        _db.create_all()
    yield flask_app
    with flask_app.app_context():
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Health Sync
# ---------------------------------------------------------------------------

def test_sync_single_record(client):
    payload = {
        "recorded_at": "2024-03-01T08:00:00",
        "steps": 8500,
        "heart_rate": 72.0,
        "calories_burned": 420,
        "active_minutes": 35,
        "sleep_hours": 7.5,
        "blood_oxygen": 98.0,
        "workout_type": "跑步",
        "workout_duration": 30,
    }
    res = client.post("/api/health/sync", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["synced"] == 1
    assert data["records"][0]["steps"] == 8500
    assert data["records"][0]["heart_rate"] == 72.0


def test_sync_multiple_records(client):
    payload = [
        {"recorded_at": "2024-03-01T08:00:00", "steps": 5000, "calories_burned": 300},
        {"recorded_at": "2024-03-02T08:00:00", "steps": 7000, "calories_burned": 400},
    ]
    res = client.post("/api/health/sync", json=payload)
    assert res.status_code == 201
    assert res.get_json()["synced"] == 2


def test_sync_invalid_json(client):
    res = client.post("/api/health/sync", data="not-json",
                      content_type="text/plain")
    assert res.status_code == 400


def test_sync_invalid_datetime(client):
    res = client.post("/api/health/sync", json={"recorded_at": "bad-date"})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Health Data & Summary
# ---------------------------------------------------------------------------

def test_get_health_data_empty(client):
    res = client.get("/api/health/data")
    assert res.status_code == 200
    assert res.get_json() == []


def test_get_health_data_with_records(client):
    client.post("/api/health/sync", json={"steps": 9000})
    res = client.get("/api/health/data")
    assert res.status_code == 200
    records = res.get_json()
    assert len(records) == 1
    assert records[0]["steps"] == 9000


def test_health_summary_empty(client):
    res = client.get("/api/health/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_records"] == 0
    assert data["avg_steps"] == 0


def test_health_summary_with_data(client):
    client.post("/api/health/sync", json={"steps": 10000, "heart_rate": 70})
    client.post("/api/health/sync", json={"steps": 8000, "heart_rate": 80})
    res = client.get("/api/health/summary?days=7")
    assert res.status_code == 200
    data = res.get_json()
    assert data["avg_steps"] == 9000.0
    assert data["avg_heart_rate"] == 75.0


def test_health_trend(client):
    client.post("/api/health/sync", json={"steps": 6000})
    res = client.get("/api/health/trend?days=7")
    assert res.status_code == 200
    trend = res.get_json()
    assert len(trend) == 7


# ---------------------------------------------------------------------------
# Food Entries
# ---------------------------------------------------------------------------

def test_add_food_entry(client):
    payload = {
        "meal_type": "lunch",
        "food_name": "米饭",
        "amount_g": 200,
        "calories": 260,
        "protein_g": 5.0,
        "carbs_g": 58.0,
        "fat_g": 1.0,
        "fiber_g": 0.5,
    }
    res = client.post("/api/food/entries", json=payload)
    assert res.status_code == 201
    entry = res.get_json()
    assert entry["food_name"] == "米饭"
    assert entry["calories"] == 260.0
    assert entry["meal_type"] == "lunch"


def test_add_food_entry_missing_name(client):
    res = client.post("/api/food/entries", json={"meal_type": "lunch"})
    assert res.status_code == 400
    assert "food_name" in res.get_json()["error"]


def test_add_food_entry_invalid_meal(client):
    res = client.post("/api/food/entries", json={"meal_type": "brunch", "food_name": "面包"})
    assert res.status_code == 400


def test_get_food_entries(client):
    client.post("/api/food/entries", json={
        "meal_type": "breakfast",
        "food_name": "鸡蛋",
        "logged_at": datetime.now(timezone.utc).date().isoformat() + "T08:00:00",
        "calories": 72,
    })
    res = client.get("/api/food/entries")
    assert res.status_code == 200
    entries = res.get_json()
    assert len(entries) == 1
    assert entries[0]["food_name"] == "鸡蛋"


def test_delete_food_entry(client):
    post_res = client.post("/api/food/entries", json={
        "meal_type": "snack",
        "food_name": "苹果",
        "calories": 52,
    })
    entry_id = post_res.get_json()["id"]

    del_res = client.delete(f"/api/food/entries/{entry_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["deleted"] == entry_id

    # Verify it's gone
    entries = client.get("/api/food/entries").get_json()
    assert all(e["id"] != entry_id for e in entries)


def test_delete_nonexistent_entry(client):
    res = client.delete("/api/food/entries/99999")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Food Analysis
# ---------------------------------------------------------------------------

def test_food_analysis_empty(client):
    res = client.get("/api/food/analysis")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_calories"] == 0.0
    assert data["total_protein_g"] == 0.0


def test_food_analysis_with_entries(client):
    today = datetime.now(timezone.utc).date().isoformat()
    client.post("/api/food/entries", json={
        "meal_type": "lunch",
        "food_name": "鸡胸肉",
        "logged_at": today + "T12:00:00",
        "calories": 165,
        "protein_g": 31.0,
        "carbs_g": 0,
        "fat_g": 3.6,
    })
    res = client.get(f"/api/food/analysis?date={today}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_calories"] == 165.0
    assert data["total_protein_g"] == 31.0


def test_food_analysis_invalid_date(client):
    res = client.get("/api/food/analysis?date=not-a-date")
    assert res.status_code == 400


def test_food_trend(client):
    res = client.get("/api/food/trend?days=7")
    assert res.status_code == 200
    assert len(res.get_json()) == 7


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

def test_get_default_goals(client):
    res = client.get("/api/goals")
    assert res.status_code == 200
    goals = res.get_json()
    assert goals["daily_steps"] == 10000
    assert goals["daily_calories_intake"] == 2000


def test_update_goals(client):
    res = client.put("/api/goals", json={
        "daily_steps": 12000,
        "sleep_hours": 7.5,
    })
    assert res.status_code == 200
    goals = res.get_json()
    assert goals["daily_steps"] == 12000
    assert goals["sleep_hours"] == 7.5


def test_update_goals_invalid_payload(client):
    res = client.put("/api/goals", data="bad", content_type="text/plain")
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Frontend route
# ---------------------------------------------------------------------------

def test_index_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"ClawHealth" in res.data
