"""
Subscription API routes.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import stripe

from ..models.schemas import PlansResponse, CheckoutResponse, WebhookResponse
from ..services.auth_service import AuthService, UserService
from ..services.subscription_service import SubscriptionService
from ..core.config import settings

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    try:
        return AuthService.verify_jwt_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/plans", response_model=PlansResponse)
async def get_subscription_plans():
    """Get available subscription plans."""
    plans = SubscriptionService.get_subscription_plans()
    return {"plans": plans}


@router.post("/create", response_model=CheckoutResponse)
async def create_subscription(
    plan_id: str, current_user: dict = Depends(get_current_user)
):
    """Create a new subscription checkout session."""
    user = UserService.get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user already has an active subscription
    existing_subscription = SubscriptionService.get_user_subscription(user["id"])
    if existing_subscription:
        raise HTTPException(
            status_code=400, detail="User already has an active subscription"
        )

    # Create checkout session
    result = SubscriptionService.create_checkout_session(
        user["id"], plan_id, user.get("stripe_customer_id")
    )

    if not result:
        raise HTTPException(status_code=500, detail="Error creating subscription")

    return result


@router.post("/webhooks/stripe", response_model=WebhookResponse)
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks."""
    if settings.STRIPE_WEBHOOK_SECRET is None:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not set")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        SubscriptionService.handle_checkout_completed(session)
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        SubscriptionService.handle_subscription_updated(subscription)
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        SubscriptionService.handle_subscription_deleted(subscription)

    return {"status": "success"}
