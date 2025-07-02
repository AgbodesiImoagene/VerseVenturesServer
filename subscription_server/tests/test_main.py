import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from main import app

client = TestClient(app)


@pytest.fixture
def mock_db_connection():
    with patch("main.get_db_connection") as mock:
        yield mock


@pytest.fixture
def mock_stripe():
    with patch("stripe.Customer.create") as mock_customer, patch(
        "stripe.checkout.Session.create"
    ) as mock_session:
        yield {"customer": mock_customer, "session": mock_session}


@pytest.fixture
def mock_boto3():
    with patch("boto3.client") as mock_client:
        mock_sts = MagicMock()
        mock_client.return_value = mock_sts
        yield mock_sts


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_plans():
    response = client.get("/plans")
    assert response.status_code == 200
    plans = response.json()["plans"]
    assert len(plans) == 3
    assert any(plan["name"] == "Basic" for plan in plans)
    assert any(plan["name"] == "Pro" for plan in plans)
    assert any(plan["name"] == "Enterprise" for plan in plans)


def test_register_user_success(mock_db_connection):
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # No existing user
    mock_cursor.fetchone.side_effect = [
        None,
        {
            "id": 1,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "created_at": "2024-01-01T00:00:00Z",
        },
    ]
    mock_db_connection.return_value = mock_conn

    user_data = {
        "email": "test@example.com",
        "password": "securepassword",
        "first_name": "John",
        "last_name": "Doe",
    }

    with patch("stripe.Customer.create") as mock_stripe_customer:
        mock_stripe_customer.return_value = MagicMock(id="cus_test123")

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert "api_key" in data


def test_register_user_already_exists(mock_db_connection):
    # Mock existing user
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {"id": 1, "email": "test@example.com"}
    mock_db_connection.return_value = mock_conn

    user_data = {
        "email": "test@example.com",
        "password": "securepassword",
        "first_name": "John",
        "last_name": "Doe",
    }

    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "User already exists"


def test_login_user_success(mock_db_connection):
    # Mock user with hashed password
    import bcrypt

    password_hash = bcrypt.hashpw(
        "securepassword".encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "email": "test@example.com",
        "password_hash": password_hash,
        "first_name": "John",
        "last_name": "Doe",
    }
    mock_db_connection.return_value = mock_conn

    login_data = {"email": "test@example.com", "password": "securepassword"}

    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_user_invalid_credentials(mock_db_connection):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # User not found
    mock_db_connection.return_value = mock_conn

    login_data = {"email": "test@example.com", "password": "wrongpassword"}

    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_get_aws_credentials_success(mock_db_connection, mock_boto3):
    # Mock user and active subscription
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [
        {
            "id": 1,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        },
        {"id": 1, "user_id": 1, "status": "active", "plan_name": "Basic"},
    ]
    mock_db_connection.return_value = mock_conn

    # Mock AWS STS response
    mock_boto3.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIA...",
            "SecretAccessKey": "secret...",
            "SessionToken": "token...",
            "Expiration": "2024-01-01T12:00:00Z",
        }
    }

    # Create a valid JWT token
    from main import create_jwt_token

    token = create_jwt_token(1, "test@example.com")

    response = client.post(
        "/aws/credentials", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_key_id" in data
    assert "secret_access_key" in data
    assert "session_token" in data
    assert "expiration" in data


def test_get_aws_credentials_no_subscription(mock_db_connection):
    # Mock user but no active subscription
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [
        {
            "id": 1,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        },
        None,  # No active subscription
    ]
    mock_db_connection.return_value = mock_conn

    # Create a valid JWT token
    from main import create_jwt_token

    token = create_jwt_token(1, "test@example.com")

    response = client.post(
        "/aws/credentials", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Active subscription required"


def test_regenerate_api_key(mock_db_connection):
    # Mock user
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
    }
    mock_db_connection.return_value = mock_conn

    # Create a valid JWT token
    from main import create_jwt_token

    token = create_jwt_token(1, "test@example.com")

    response = client.post(
        "/api-keys/regenerate", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert data["api_key"].startswith("vv_")


def test_get_user_profile(mock_db_connection):
    # Mock user and subscription
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [
        {
            "id": 1,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        },
        {
            "id": 1,
            "user_id": 1,
            "status": "active",
            "plan_name": "Basic",
            "current_period_end": "2024-02-01T00:00:00Z",
        },
        {"count": 150},  # API usage count
    ]
    mock_db_connection.return_value = mock_conn

    # Create a valid JWT token
    from main import create_jwt_token

    token = create_jwt_token(1, "test@example.com")

    response = client.get("/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["subscription_status"] == "active"
    assert data["api_calls_used"] == 150
    assert data["api_calls_limit"] == 1000


def test_stripe_webhook_valid():
    with patch("stripe.Webhook.construct_event") as mock_webhook:
        mock_webhook.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"user_id": "1"},
                    "subscription": "sub_test123",
                    "customer": "cus_test123",
                }
            },
        }

        response = client.post(
            "/webhooks/stripe",
            headers={"stripe-signature": "test_signature"},
            content=b"test_payload",
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"


def test_stripe_webhook_invalid_signature():
    with patch("stripe.Webhook.construct_event") as mock_webhook:
        from stripe.error import SignatureVerificationError

        mock_webhook.side_effect = SignatureVerificationError(
            "Invalid signature", "sig_header"
        )

        response = client.post(
            "/webhooks/stripe",
            headers={"stripe-signature": "invalid_signature"},
            content=b"test_payload",
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid signature"
