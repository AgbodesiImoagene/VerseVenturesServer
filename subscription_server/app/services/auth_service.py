"""
Authentication service for user management, JWT tokens, and OAuth.
"""

import jwt
import bcrypt
import secrets
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests

from ..core.config import settings
from ..core.database import get_db_connection

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user management and JWT operations."""

    @staticmethod
    def create_jwt_token(user_id: int, email: str) -> str:
        """Create a JWT token for user authentication."""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def verify_jwt_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure verification token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def verify_google_token(id_token_str: str) -> Optional[Dict[str, Any]]:
        """Verify Google ID token and return user info."""
        try:
            if not settings.GOOGLE_CLIENT_ID:
                logger.error("Google Client ID not configured")
                return None

            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            # Check if token is expired
            if idinfo["exp"] < datetime.now().timestamp():
                logger.error("Google token expired")
                return None

            return {
                "email": idinfo["email"],
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
                "picture": idinfo.get("picture"),
                "oauth_id": idinfo["sub"],
            }
        except Exception as e:
            logger.error(f"Error verifying Google token: {str(e)}")
            return None


class UserService:
    """Service for user management operations."""

    @staticmethod
    def create_user(
        email: str, password: str, first_name: str, last_name: str
    ) -> Dict[str, Any]:
        """Create a new user with hashed password."""
        conn = get_db_connection()
        cursor = conn.cursor()

        password_hash = AuthService.hash_password(password)

        cursor.execute(
            """
            INSERT INTO users (email, password_hash, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            RETURNING id, email, first_name, last_name, email_verified
        """,
            (email, password_hash, first_name, last_name),
        )

        user = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        return dict(user)

    @staticmethod
    def create_oauth_user(
        oauth_info: Dict[str, Any], provider: str = "google"
    ) -> Dict[str, Any]:
        """Create a new user from OAuth info."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (email, first_name, last_name, email_verified, 
                              oauth_provider, oauth_id, oauth_picture)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, email, first_name, last_name, email_verified
        """,
            (
                oauth_info["email"],
                oauth_info["first_name"],
                oauth_info["last_name"],
                True,  # OAuth emails are pre-verified
                provider,
                oauth_info["oauth_id"],
                oauth_info.get("picture"),
            ),
        )

        user = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        return dict(user)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        return dict(user) if user else None

    @staticmethod
    def get_user_by_oauth(provider: str, oauth_id: str) -> Optional[Dict[str, Any]]:
        """Get user by OAuth provider and ID."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE oauth_provider = %s AND oauth_id = %s",
            (provider, oauth_id),
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        return dict(user) if user else None

    @staticmethod
    def link_oauth_to_user(
        email: str, oauth_info: Dict[str, Any], provider: str = "google"
    ) -> Dict[str, Any]:
        """Link OAuth account to existing email account."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users 
            SET oauth_provider = %s, oauth_id = %s, oauth_picture = %s
            WHERE email = %s
            RETURNING id, email, first_name, last_name, email_verified
            """,
            (provider, oauth_info["oauth_id"], oauth_info.get("picture"), email),
        )

        user = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        return dict(user)

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password."""
        user = UserService.get_user_by_email(email)
        if not user:
            return None

        if not AuthService.verify_password(password, user["password_hash"]):
            return None

        return user
