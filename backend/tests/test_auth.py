import pytest


def test_register(client):
    res = client.post("/api/auth/register", json={"email": "test@example.com", "password": "password123"})
    assert res.status_code == 201
    data = res.get_json()
    assert "token" in data
    assert data["user"]["email"] == "test@example.com"


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={"email": "dup@example.com", "password": "password123"})
    res = client.post("/api/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert res.status_code == 409


def test_register_invalid_email(client):
    res = client.post("/api/auth/register", json={"email": "not-an-email", "password": "password123"})
    assert res.status_code == 400


def test_register_short_password(client):
    res = client.post("/api/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert res.status_code == 400


def test_login_success(client):
    client.post("/api/auth/register", json={"email": "login@example.com", "password": "password123"})
    res = client.post("/api/auth/login", json={"email": "login@example.com", "password": "password123"})
    assert res.status_code == 200
    assert "token" in res.get_json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "wp@example.com", "password": "password123"})
    res = client.post("/api/auth/login", json={"email": "wp@example.com", "password": "wrongpassword"})
    assert res.status_code == 401


def test_me_requires_auth(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_with_token(client):
    reg = client.post("/api/auth/register", json={"email": "me@example.com", "password": "password123"})
    token = reg.get_json()["token"]
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.get_json()["user"]["email"] == "me@example.com"
