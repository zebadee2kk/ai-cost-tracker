import pytest
import uuid


def _register_and_token(client, email="acct@example.com"):
    res = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    return res.get_json()["token"]


def _seed_service(db):
    from models.service import Service
    from app import db as _db
    svc = Service(
        name=f"TestService-{uuid.uuid4().hex[:8]}",
        api_provider="Test",
        has_api=True,
        pricing_model={},
    )
    _db.session.add(svc)
    _db.session.commit()
    return svc.id


def test_create_account(client, db):
    token = _register_and_token(client, "create@example.com")
    svc_id = _seed_service(db)
    res = client.post(
        "/api/accounts",
        json={"service_id": svc_id, "account_name": "My Account", "api_key": "sk-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.get_json()["account"]
    assert data["account_name"] == "My Account"
    assert data["has_api_key"] is True


def test_list_accounts(client, db):
    token = _register_and_token(client, "list@example.com")
    svc_id = _seed_service(db)
    client.post("/api/accounts", json={"service_id": svc_id, "account_name": "A1"}, headers={"Authorization": f"Bearer {token}"})
    res = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert len(res.get_json()["accounts"]) >= 1


def test_delete_account(client, db):
    token = _register_and_token(client, "del@example.com")
    svc_id = _seed_service(db)
    create_res = client.post("/api/accounts", json={"service_id": svc_id, "account_name": "ToDelete"}, headers={"Authorization": f"Bearer {token}"})
    acct_id = create_res.get_json()["account"]["id"]
    del_res = client.delete(f"/api/accounts/{acct_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200


def test_cannot_access_other_users_account(client, db):
    token1 = _register_and_token(client, "u1@example.com")
    token2 = _register_and_token(client, "u2@example.com")
    svc_id = _seed_service(db)
    create_res = client.post("/api/accounts", json={"service_id": svc_id, "account_name": "Private"}, headers={"Authorization": f"Bearer {token1}"})
    acct_id = create_res.get_json()["account"]["id"]
    res = client.get(f"/api/accounts/{acct_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code == 404
