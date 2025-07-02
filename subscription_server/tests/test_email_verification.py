import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import bcrypt
from main import app

client = TestClient(app)


@pytest.fixture
def mock_db_connection():
    with patch("main.get_db_connection") as mock:
        yield mock


@pytest.fixture
def mock_email_send():
    with patch("main.send_verification_email") as mock:
        yield mock


def test_register_user_with_email_verification(mock_db_connection, mock_email_send):
    """Test user registration sends verification email"""
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

    # Mock Stripe customer creation
    with patch("stripe.Customer.create") as mock_stripe_customer:
        mock_stripe_customer.return_value = MagicMock(id="cus_test123")

        # Mock email sending
        mock_email_send.return_value = True

        user_data = {
            "email": "test@example.com",
            "password": "securepassword",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert (
            data["message"]
            == "User registered successfully. Please check your email to verify your account."
        )
        assert data["email_verification_sent"] == True
        assert "api_key" in data

        # Verify email was sent
        mock_email_send.assert_called_once()


def test_verify_email_success(mock_db_connection):
    """Test successful email verification"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock token verification - token is valid
    mock_cursor.fetchone.return_value = {"user_id": 1}
    mock_db_connection.return_value = mock_conn

    verification_data = {"token": "valid_verification_token"}

    response = client.post("/auth/verify-email", json=verification_data)

    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully"


def test_verify_email_invalid_token(mock_db_connection):
    """Test email verification with invalid token"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock token verification - token is invalid
    mock_cursor.fetchone.return_value = None
    mock_db_connection.return_value = mock_conn

    verification_data = {"token": "invalid_verification_token"}

    response = client.post("/auth/verify-email", json=verification_data)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification token"


def test_resend_verification_email(mock_db_connection, mock_email_send):
    """Test resending verification email"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock user exists but email not verified
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "email_verified": False,
    }
    mock_db_connection.return_value = mock_conn

    # Mock email sending
    mock_email_send.return_value = True

    request_data = {"email": "test@example.com"}

    response = client.post("/auth/resend-verification", json=request_data)

    assert response.status_code == 200
    assert response.json()["message"] == "Verification email sent successfully"

    # Verify email was sent
    mock_email_send.assert_called_once()


def test_resend_verification_user_not_found(mock_db_connection):
    """Test resending verification email for non-existent user"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock user doesn't exist
    mock_cursor.fetchone.return_value = None
    mock_db_connection.return_value = mock_conn

    request_data = {"email": "nonexistent@example.com"}

    response = client.post("/auth/resend-verification", json=request_data)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_resend_verification_already_verified(mock_db_connection):
    """Test resending verification email for already verified user"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock user exists and email is already verified
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "email_verified": True,
    }
    mock_db_connection.return_value = mock_conn

    request_data = {"email": "test@example.com"}

    response = client.post("/auth/resend-verification", json=request_data)

    assert response.status_code == 400
    assert response.json()["detail"] == "Email is already verified"


def test_login_unverified_email(mock_db_connection):
    """Test login with unverified email"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock user with unverified email
    password_hash = bcrypt.hashpw(
        "securepassword".encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "email": "test@example.com",
        "password_hash": password_hash,
        "first_name": "John",
        "last_name": "Doe",
        "email_verified": False,
    }
    mock_db_connection.return_value = mock_conn

    login_data = {"email": "test@example.com", "password": "securepassword"}

    response = client.post("/auth/login", json=login_data)

    assert response.status_code == 401
    assert "Please verify your email address" in response.json()["detail"]


def test_login_verified_email(mock_db_connection):
    """Test login with verified email"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock user with verified email
    password_hash = bcrypt.hashpw(
        "securepassword".encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "email": "test@example.com",
        "password_hash": password_hash,
        "first_name": "John",
        "last_name": "Doe",
        "email_verified": True,
    }
    mock_db_connection.return_value = mock_conn

    login_data = {"email": "test@example.com", "password": "securepassword"}

    response = client.post("/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["email_verified"] == True


def test_user_profile_includes_email_verification_status(mock_db_connection):
    """Test that user profile includes email verification status"""
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock user and subscription data
    mock_cursor.fetchone.side_effect = [
        {
            "id": 1,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "email_verified": True,
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
    assert data["email_verified"] == True
    assert data["email"] == "test@example.com"
