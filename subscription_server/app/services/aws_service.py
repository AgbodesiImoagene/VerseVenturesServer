"""
AWS service for credential generation and usage tracking.
"""

import logging
from typing import Optional, Dict, Any
import boto3

from ..core.config import settings
from ..core.database import get_db_connection

logger = logging.getLogger(__name__)


class AWSService:
    """Service for AWS operations."""

    @staticmethod
    def generate_temporary_credentials() -> Optional[Dict[str, Any]]:
        """Generate temporary AWS credentials."""
        try:
            # Initialize STS client
            sts_client = boto3.client("sts", region_name=settings.AWS_REGION)

            # Generate temporary credentials
            response = sts_client.get_session_token(
                DurationSeconds=settings.SESSION_DURATION
            )

            credentials = response["Credentials"]

            return {
                "access_key_id": credentials["AccessKeyId"],
                "secret_access_key": credentials["SecretAccessKey"],
                "session_token": credentials["SessionToken"],
                "expiration": credentials["Expiration"],
            }

        except Exception as e:
            logger.error(f"Error generating credentials: {str(e)}")
            return None


class UsageService:
    """Service for API usage tracking."""

    @staticmethod
    def log_api_usage(user_id: int, endpoint: str):
        """Log API usage for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO usage_logs (user_id, api_endpoint)
            VALUES (%s, %s)
        """,
            (user_id, endpoint),
        )

        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_api_usage_count(user_id: int, period_days: int = 30) -> int:
        """Get API usage count for a user in the specified period."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) as count FROM usage_logs
            WHERE user_id = %s AND timestamp >= NOW() - INTERVAL '%s days'
        """,
            (user_id, period_days),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result["count"]

    @staticmethod
    def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile with subscription and usage information."""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user info
        cursor.execute(
            """
            SELECT id, email, first_name, last_name, email_verified
            FROM users WHERE id = %s
        """,
            (user_id,),
        )

        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            return None

        # Get subscription info
        cursor.execute(
            """
            SELECT status, current_period_end
            FROM subscriptions 
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """,
            (user_id,),
        )

        subscription = cursor.fetchone()

        cursor.close()
        conn.close()

        # Get usage count
        api_calls_used = UsageService.get_api_usage_count(user_id)

        # Determine API call limit based on subscription
        api_calls_limit = 1000  # Default for free tier
        if subscription:
            if subscription["status"] == "active":
                # You can customize limits based on plan
                api_calls_limit = 5000  # Example for paid plans

        return {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "email_verified": user["email_verified"],
            "subscription_status": subscription["status"] if subscription else "none",
            "subscription_end_date": (
                subscription["current_period_end"] if subscription else None
            ),
            "api_calls_used": api_calls_used,
            "api_calls_limit": api_calls_limit,
        }
