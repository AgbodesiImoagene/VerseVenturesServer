"""
Subscription service for Stripe integration and subscription management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import stripe

from ..core.config import settings
from ..core.database import get_db_connection

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionService:
    """Service for subscription operations."""

    @staticmethod
    def get_subscription_plans() -> List[Dict[str, Any]]:
        """Get available subscription plans."""
        return [
            {
                "name": "Basic",
                "price_id": "price_basic_monthly",
                "price": 9.99,
                "interval": "monthly",
                "features": ["1000 API calls/month", "Basic support"],
            },
            {
                "name": "Pro",
                "price_id": "price_pro_monthly",
                "price": 19.99,
                "interval": "monthly",
                "features": [
                    "5000 API calls/month",
                    "Priority support",
                    "Advanced analytics",
                ],
            },
            {
                "name": "Enterprise",
                "price_id": "price_enterprise_monthly",
                "price": 49.99,
                "interval": "monthly",
                "features": [
                    "Unlimited API calls",
                    "24/7 support",
                    "Custom integrations",
                ],
            },
        ]

    @staticmethod
    def create_stripe_customer(email: str, name: str) -> Optional[str]:
        """Create a Stripe customer and return customer ID."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
            )
            return customer.id
        except Exception as e:
            logger.error(f"Error creating Stripe customer: {str(e)}")
            return None

    @staticmethod
    def create_checkout_session(
        user_id: int, plan_id: str, customer_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a Stripe checkout session."""
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": plan_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url="https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://yourdomain.com/cancel",
                metadata={"user_id": user_id},
            )

            return {"checkout_url": session.url, "session_id": session.id}
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return None

    @staticmethod
    def get_user_subscription(user_id: int) -> Optional[Dict[str, Any]]:
        """Get active subscription for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM subscriptions 
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """,
            (user_id,),
        )

        subscription = cursor.fetchone()
        cursor.close()
        conn.close()

        return dict(subscription) if subscription else None

    @staticmethod
    def handle_checkout_completed(session: Dict[str, Any]):
        """Handle completed checkout session."""
        user_id = session["metadata"]["user_id"]
        subscription_id = session["subscription"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO subscriptions (user_id, stripe_subscription_id, stripe_customer_id, plan_name, status)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (user_id, subscription_id, session["customer"], "Basic", "active"),
        )

        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def handle_subscription_updated(subscription: Dict[str, Any]):
        """Handle subscription update."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE subscriptions 
            SET status = %s, current_period_start = %s, current_period_end = %s
            WHERE stripe_subscription_id = %s
        """,
            (
                subscription["status"],
                datetime.fromtimestamp(subscription["current_period_start"]),
                datetime.fromtimestamp(subscription["current_period_end"]),
                subscription["id"],
            ),
        )

        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def handle_subscription_deleted(subscription: Dict[str, Any]):
        """Handle subscription deletion."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE subscriptions 
            SET status = 'canceled'
            WHERE stripe_subscription_id = %s
        """,
            (subscription["id"],),
        )

        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def update_user_stripe_customer(user_id: int, customer_id: str):
        """Update user with Stripe customer ID."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users SET stripe_customer_id = %s WHERE id = %s
        """,
            (customer_id, user_id),
        )

        conn.commit()
        cursor.close()
        conn.close()
