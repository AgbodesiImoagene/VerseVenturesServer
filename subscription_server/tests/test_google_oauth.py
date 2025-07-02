#!/usr/bin/env python3
"""
Test Google OAuth functionality
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add the parent directory to the path to import the main module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import verify_google_token, get_user_by_oauth, create_oauth_user, app
from fastapi.testclient import TestClient

client = TestClient(app)


class TestGoogleOAuth:
    """Test Google OAuth functionality"""

    def test_verify_google_token_valid(self):
        """Test valid Google token verification"""
        mock_token_info = {
            "email": "test@example.com",
            "given_name": "John",
            "family_name": "Doe",
            "picture": "https://example.com/picture.jpg",
            "sub": "google_oauth_id_123",
            "exp": (datetime.now() + timedelta(hours=1)).timestamp(),
        }

        with patch("main.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_token_info

            result = verify_google_token("valid_token")

            assert result is not None
            assert result["email"] == "test@example.com"
            assert result["first_name"] == "John"
            assert result["last_name"] == "Doe"
            assert result["oauth_id"] == "google_oauth_id_123"
            assert result["picture"] == "https://example.com/picture.jpg"

    def test_verify_google_token_expired(self):
        """Test expired Google token verification"""
        mock_token_info = {
            "email": "test@example.com",
            "given_name": "John",
            "family_name": "Doe",
            "sub": "google_oauth_id_123",
            "exp": (datetime.now() - timedelta(hours=1)).timestamp(),  # Expired
        }

        with patch("main.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_token_info

            result = verify_google_token("expired_token")

            assert result is None

    def test_verify_google_token_invalid(self):
        """Test invalid Google token verification"""
        with patch("main.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            result = verify_google_token("invalid_token")

            assert result is None

    def test_verify_google_token_no_client_id(self):
        """Test Google token verification without client ID configured"""
        with patch("main.GOOGLE_CLIENT_ID", None):
            result = verify_google_token("any_token")

            assert result is None

    @patch("main.get_db_connection")
    def test_get_user_by_oauth_existing(self, mock_db_conn):
        """Test getting existing OAuth user"""
        mock_cursor = MagicMock()
        mock_user = {
            "id": 1,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "oauth_provider": "google",
            "oauth_id": "google_oauth_id_123",
        }
        mock_cursor.fetchone.return_value = mock_user
        mock_db_conn.return_value.cursor.return_value = mock_cursor

        result = get_user_by_oauth("google", "google_oauth_id_123")

        assert result is not None
        assert result["email"] == "test@example.com"
        assert result["oauth_provider"] == "google"

    @patch("main.get_db_connection")
    def test_get_user_by_oauth_not_found(self, mock_db_conn):
        """Test getting non-existing OAuth user"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db_conn.return_value.cursor.return_value = mock_cursor

        result = get_user_by_oauth("google", "non_existing_id")

        assert result is None

    @patch("main.get_db_connection")
    def test_create_oauth_user(self, mock_db_conn):
        """Test creating new OAuth user"""
        mock_cursor = MagicMock()
        mock_user = {
            "id": 1,
            "email": "new@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "email_verified": True,
        }
        mock_cursor.fetchone.return_value = mock_user
        mock_db_conn.return_value.cursor.return_value = mock_cursor

        oauth_info = {
            "email": "new@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "oauth_id": "google_oauth_id_456",
            "picture": "https://example.com/picture2.jpg",
        }

        result = create_oauth_user(oauth_info, "google")

        assert result is not None
        assert result["email"] == "new@example.com"
        assert result["email_verified"] is True

    def test_get_google_oauth_url(self):
        """Test getting Google OAuth URL"""
        with patch("main.GOOGLE_CLIENT_ID", "test_client_id"):
            response = client.get("/auth/google/url")

            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "test_client_id" in data["auth_url"]
            assert "accounts.google.com" in data["auth_url"]

    def test_get_google_oauth_url_no_config(self):
        """Test getting Google OAuth URL without configuration"""
        with patch("main.GOOGLE_CLIENT_ID", None):
            response = client.get("/auth/google/url")

            assert response.status_code == 500
            data = response.json()
            assert "Google OAuth not configured" in data["detail"]

    @patch("main.verify_google_token")
    @patch("main.get_user_by_oauth")
    @patch("main.get_user_by_email")
    @patch("main.create_oauth_user")
    @patch("main.create_api_key")
    @patch("main.create_jwt_token")
    def test_google_oauth_callback_new_user(
        self,
        mock_jwt,
        mock_api_key,
        mock_create_user,
        mock_get_email,
        mock_get_oauth,
        mock_verify_token,
    ):
        """Test Google OAuth callback for new user"""
        # Mock token verification
        mock_verify_token.return_value = {
            "email": "new@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "oauth_id": "google_oauth_id_789",
            "picture": "https://example.com/picture3.jpg",
        }

        # Mock user lookup - not found by OAuth
        mock_get_oauth.return_value = None
        # Mock user lookup - not found by email
        mock_get_email.return_value = None

        # Mock user creation
        mock_create_user.return_value = {
            "id": 1,
            "email": "new@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "email_verified": True,
        }

        # Mock API key creation
        mock_api_key.return_value = "vv_test_api_key_123"

        # Mock JWT creation
        mock_jwt.return_value = "jwt_test_token_123"

        response = client.post(
            "/auth/google/callback", json={"id_token": "test_google_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "jwt_test_token_123"
        assert data["email_verified"] is True
        assert data["api_key"] == "vv_test_api_key_123"
        assert data["is_new_user"] is True
        assert data["oauth_provider"] == "google"

    @patch("main.verify_google_token")
    @patch("main.get_user_by_oauth")
    @patch("main.create_api_key")
    @patch("main.create_jwt_token")
    def test_google_oauth_callback_existing_user(
        self, mock_jwt, mock_api_key, mock_get_oauth, mock_verify_token
    ):
        """Test Google OAuth callback for existing user"""
        # Mock token verification
        mock_verify_token.return_value = {
            "email": "existing@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "oauth_id": "google_oauth_id_123",
            "picture": "https://example.com/picture.jpg",
        }

        # Mock existing user
        mock_get_oauth.return_value = {
            "id": 1,
            "email": "existing@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "email_verified": True,
            "oauth_provider": "google",
            "oauth_id": "google_oauth_id_123",
        }

        # Mock JWT creation
        mock_jwt.return_value = "jwt_test_token_456"

        response = client.post(
            "/auth/google/callback", json={"id_token": "test_google_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "jwt_test_token_456"
        assert data["email_verified"] is True
        assert data["is_new_user"] is False
        assert data["oauth_provider"] == "google"

    def test_google_oauth_callback_invalid_token(self):
        """Test Google OAuth callback with invalid token"""
        with patch("main.verify_google_token", return_value=None):
            response = client.post(
                "/auth/google/callback", json={"id_token": "invalid_token"}
            )

            assert response.status_code == 401
            data = response.json()
            assert "Invalid Google token" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__])
