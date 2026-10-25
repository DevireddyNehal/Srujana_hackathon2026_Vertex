"""
Tests for Multi-User Data Isolation, Authentication, and Session Switching.
Validates:
- Registering a new user with unique email
- Duplicate registration rejection
- Login with valid credentials and wrong credentials
- Multi-user isolation in trading journal
- Multi-user isolation in analytics/overview performance calculations
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from tradefxbook.repository import get_user_by_id


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_register_and_login_flow(client):
    # 1. Register a new custom user
    import uuid
    test_email = f"trader_{uuid.uuid4().hex[:8]}@example.com"
    reg_payload = {
        "name": "Alpha Trader",
        "email": test_email,
        "password": "SecurePassword123!",
        "starting_balance": 100000.0,
        "currency": "USD",
        "timezone": "America/New_York",
    }
    resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["user"]["email"] == test_email
    assert data["user"]["starting_balance"] == 100000.0
    user_id = data["user"]["id"]
    token = data["token"]
    assert token.startswith("token_")

    # 2. Duplicate registration must fail with 400
    resp_dup = client.post("/api/v1/auth/register", json=reg_payload)
    assert resp_dup.status_code == 400

    # 3. Login with wrong password must return 401
    resp_wrong = client.post("/api/v1/auth/login", json={"email": test_email, "password": "wrongpassword"})
    assert resp_wrong.status_code == 401

    # 4. Login with correct password must succeed
    resp_login = client.post("/api/v1/auth/login", json={"email": test_email, "password": "SecurePassword123!"})
    assert resp_login.status_code == 200
    login_data = resp_login.json()
    assert login_data["user"]["id"] == user_id
    assert login_data["token"] == token

    # 5. Access profile with token
    resp_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_me.status_code == 200
    assert resp_me.json()["id"] == user_id


def test_multi_user_journal_and_analytics_isolation(client):
    import uuid
    # Create User A and User B
    email_a = f"user_a_{uuid.uuid4().hex[:6]}@demo.test"
    email_b = f"user_b_{uuid.uuid4().hex[:6]}@demo.test"

    reg_a = client.post("/api/v1/auth/register", json={"name": "User A", "email": email_a, "password": "password123", "starting_balance": 50000}).json()
    reg_b = client.post("/api/v1/auth/register", json={"name": "User B", "email": email_b, "password": "password123", "starting_balance": 50000}).json()


    user_a_id = reg_a["user"]["id"]
    user_b_id = reg_b["user"]["id"]

    # User A creates a winning trade
    trade_a = client.post(
        "/api/v1/trades",
        headers={"X-User-Id": user_a_id},
        json={
            "symbol": "EUR/USD",
            "direction": "LONG",
            "status": "CLOSED",
            "entry_time": "2026-02-01T10:00:00Z",
            "exit_time": "2026-02-01T12:00:00Z",
            "entry_price": 1.0800,
            "exit_price": 1.0900,
            "quantity": 1.0,
            "contract_size": 100000.0,
            "strategy_or_setup": "Breakout",
            "trading_session": "London",
        },
    )
    assert trade_a.status_code == 201
    trade_a_id = trade_a.json()["id"]

    # User B lists trades: must be empty
    trades_b = client.get("/api/v1/trades", headers={"X-User-Id": user_b_id}).json()
    assert trades_b["total"] == 0
    assert len(trades_b["items"]) == 0

    # User B cannot access User A's trade directly
    resp_unauth = client.get(f"/api/v1/trades/{trade_a_id}", headers={"X-User-Id": user_b_id})
    assert resp_unauth.status_code == 404

    # User A's analytics show 1 trade and positive net P&L
    analytics_a = client.get("/api/v1/analytics/overview?range_preset=all", headers={"X-User-Id": user_a_id}).json()
    assert analytics_a["total_closed_trades"] == 1
    assert analytics_a["net_pnl"] > 0
    assert analytics_a["win_rate"] == 100.0

    # User B's analytics show 0 trades
    analytics_b = client.get("/api/v1/analytics/overview?range_preset=all", headers={"X-User-Id": user_b_id}).json()
    assert analytics_b["total_closed_trades"] == 0
    assert analytics_b["net_pnl"] == 0.0


def test_token_cryptographic_verification_and_spoofing_protection(client):
    """Verify that forged tokens, tampered signatures, and cross-user header spoofing are rejected."""
    import uuid
    email = f"secure_user_{uuid.uuid4().hex[:6]}@test.com"
    reg = client.post("/api/v1/auth/register", json={
        "name": "Secure Trader",
        "email": email,
        "password": "Password123!",
        "starting_balance": 50000.0,
    }).json()
    user_id = reg["user"]["id"]
    valid_token = reg["token"]

    # 1. Unsigned / forged token without signature must fail with 401
    resp_forged = client.get("/api/v1/trades", headers={"Authorization": f"Bearer token_{user_id}"})
    assert resp_forged.status_code == 401
    assert "signature" in resp_forged.json()["detail"].lower() or "token" in resp_forged.json()["detail"].lower()

    # 2. Tampered signature must fail with 401
    tampered = f"token_{user_id}_badbadbadbadbadbadbadbadbadbadba"
    resp_tampered = client.get("/api/v1/trades", headers={"Authorization": f"Bearer {tampered}"})
    assert resp_tampered.status_code == 401

    # 3. Using demo_token on a registered non-demo user must fail with 401
    resp_demo_fake = client.get("/api/v1/trades", headers={"Authorization": f"Bearer demo_token_{user_id}"})
    assert resp_demo_fake.status_code == 401

    # 4. Valid token with matching user succeeds
    resp_valid = client.get("/api/v1/trades", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp_valid.status_code == 200

    # 5. Spoofing: sending valid token for User A with X-User-Id for another user must be rejected with 403
    resp_spoof = client.get("/api/v1/trades", headers={
        "Authorization": f"Bearer {valid_token}",
        "X-User-Id": "demo_trader_02",
    })
    assert resp_spoof.status_code == 403
    assert "Security violation" in resp_spoof.json()["detail"]


def test_trade_review_and_csv_import_endpoints(client):
    """Verify AI checklist trade review and CSV import capabilities with user isolation."""
    # 1. Create a trade under demo_trader_01
    auth_header = {"Authorization": "Bearer demo_token_demo_trader_01"}
    trade_res = client.post("/api/v1/trades", headers=auth_header, json={
        "symbol": "GBP/USD",
        "asset_class": "Forex",
        "direction": "SHORT",
        "status": "CLOSED",
        "entry_time": "2026-03-01T08:00:00Z",
        "exit_time": "2026-03-01T10:30:00Z",
        "entry_price": 1.2850,
        "exit_price": 1.2750,
        "quantity": 1.0,
        "stop_loss_price": 1.2900,
        "strategy_or_setup": "Breakout Retest",
        "trading_session": "London",
        "notes": "Clean high-volume breakdown through key support.",
    })
    assert trade_res.status_code == 201
    trade_id = trade_res.json()["id"]

    # 2. Review the trade
    rev_res = client.post(f"/api/v1/trades/{trade_id}/review", headers=auth_header)
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["status"] == "SUCCESS"
    assert rev_data["trade_id"] == trade_id
    assert len(rev_data["observations"]) > 0
    assert len(rev_data["suggestions"]) > 0

    # 3. Another user cannot review this trade
    other_header = {"Authorization": "Bearer demo_token_demo_trader_02"}
    unauth_rev = client.post(f"/api/v1/trades/{trade_id}/review", headers=other_header)
    assert unauth_rev.status_code == 404

    # 4. Import trades via CSV
    csv_payload = (
        "symbol,direction,status,entry_time,exit_time,entry_price,exit_price,quantity,strategy_or_setup,trading_session\n"
        "EUR/USD,LONG,CLOSED,2026-04-01T09:00:00Z,2026-04-01T11:00:00Z,1.0800,1.0880,1.0,Trend Following,London\n"
        "USD/JPY,SHORT,CLOSED,2026-04-02T02:00:00Z,2026-04-02T04:00:00Z,155.00,154.20,1.0,Asian Fade,Asian\n"
    )
    import_res = client.post(
        "/api/v1/trades/import/csv",
        headers=auth_header,
        files={"file": ("test_trades.csv", csv_payload.encode("utf-8"), "text/csv")},
    )
    assert import_res.status_code == 200
    import_data = import_res.json()
    assert import_data["status"] == "SUCCESS"
    assert import_data["imported_count"] == 2
