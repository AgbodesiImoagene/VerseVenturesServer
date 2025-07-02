"""
API key service for generating and managing API keys.
"""

import secrets
import logging
from typing import Optional, Dict, Any

from ..core.database import get_db_connection

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for API key operations."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"vv_{secrets.token_urlsafe(32)}"

    @staticmethod
    def create_api_key(user_id: int) -> str:
        """Create and store an API key for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        api_key = APIKeyService.generate_api_key()

        cursor.execute(
            """
            INSERT INTO api_keys (user_id, api_key)
            VALUES (%s, %s)
            RETURNING api_key, created_at
        """,
            (user_id, api_key),
        )

        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        return result["api_key"]

    @staticmethod
    def get_user_api_keys(user_id: int) -> list:
        """Get all API keys for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT api_key, is_active, created_at 
            FROM api_keys 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """,
            (user_id,),
        )

        api_keys = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(key) for key in api_keys]

    @staticmethod
    def deactivate_api_key(api_key: str, user_id: int) -> bool:
        """Deactivate an API key."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE api_keys 
            SET is_active = FALSE 
            WHERE api_key = %s AND user_id = %s
        """,
            (api_key, user_id),
        )

        success = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()

        return success

    @staticmethod
    def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return user info."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.id, u.email, u.first_name, u.last_name, u.email_verified
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE ak.api_key = %s AND ak.is_active = TRUE
        """,
            (api_key,),
        )

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        return dict(user) if user else None
