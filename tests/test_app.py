"""Tests for the Mergington High School Activities API."""

import copy
import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activities database before each test."""
    original = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(original)


@pytest.fixture
def client():
    return TestClient(app)


# ── GET / ────────────────────────────────────────────────────────────────────

class TestRoot:
    def test_root_redirects_to_index(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


# ── GET /activities ──────────────────────────────────────────────────────────

class TestGetActivities:
    def test_returns_all_activities(self, client):
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_activity_has_required_fields(self, client):
        response = client.get("/activities")
        data = response.json()
        for name, details in data.items():
            assert "description" in details, f"{name} missing description"
            assert "schedule" in details, f"{name} missing schedule"
            assert "max_participants" in details, f"{name} missing max_participants"
            assert "participants" in details, f"{name} missing participants"


# ── POST /activities/{name}/signup ───────────────────────────────────────────

class TestSignup:
    def test_signup_success(self, client):
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "newstudent@mergington.edu" in response.json()["message"]
        # Verify participant was actually added
        act = client.get("/activities").json()
        assert "newstudent@mergington.edu" in act["Chess Club"]["participants"]

    def test_signup_duplicate_returns_400(self, client):
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()

    def test_signup_nonexistent_activity_returns_404(self, client):
        response = client.post(
            "/activities/Nonexistent/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404

    def test_signup_missing_email_returns_422(self, client):
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422


# ── DELETE /activities/{name}/signup ─────────────────────────────────────────

class TestUnregister:
    def test_unregister_success(self, client):
        response = client.delete(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        assert "michael@mergington.edu" in response.json()["message"]
        # Verify participant was actually removed
        act = client.get("/activities").json()
        assert "michael@mergington.edu" not in act["Chess Club"]["participants"]

    def test_unregister_not_signed_up_returns_400(self, client):
        response = client.delete(
            "/activities/Chess Club/signup?email=unknown@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()

    def test_unregister_nonexistent_activity_returns_404(self, client):
        response = client.delete(
            "/activities/Nonexistent/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404

    def test_unregister_missing_email_returns_422(self, client):
        response = client.delete("/activities/Chess Club/signup")
        assert response.status_code == 422


# ── Signup + Unregister round-trip ───────────────────────────────────────────

class TestRoundTrip:
    def test_signup_then_unregister(self, client):
        email = "roundtrip@mergington.edu"
        # Sign up
        res = client.post(f"/activities/Art Club/signup?email={email}")
        assert res.status_code == 200
        # Confirm present
        act = client.get("/activities").json()
        assert email in act["Art Club"]["participants"]
        # Unregister
        res = client.delete(f"/activities/Art Club/signup?email={email}")
        assert res.status_code == 200
        # Confirm removed
        act = client.get("/activities").json()
        assert email not in act["Art Club"]["participants"]
