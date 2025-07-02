"""
Authentication API routes.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.schemas import (
    UserRegistration,
    UserLogin,
    EmailVerificationRequest,
    EmailVerificationConfirm,
    GoogleOAuthRequest,
    AuthResponse,
    GoogleOAuthResponse,
    RegistrationResponse,
    MessageResponse,
)
from ..services.auth_service import AuthService, UserService
from ..services.email_service import EmailService
from ..services.api_key_service import APIKeyService
from ..services.subscription_service import SubscriptionService

router = APIRouter(prefix="/auth", tags=["authentication"])
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


@router.post("/register", response_model=RegistrationResponse)
async def register_user(user_data: UserRegistration, background_tasks: BackgroundTasks):
    """Register a new user."""
    # Check if user already exists
    existing_user = UserService.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Create user
    user = UserService.create_user(
        user_data.email,
        user_data.password,
        user_data.first_name,
        user_data.last_name,
    )

    # Generate verification token
    verification_token = EmailService.create_verification_token(user["id"])

    # Send verification email in background
    background_tasks.add_task(
        EmailService.send_verification_email,
        user_data.email,
        verification_token,
        user_data.first_name,
    )

    # Generate API key
    api_key = APIKeyService.create_api_key(user["id"])

    # Create Stripe customer
    customer_id = SubscriptionService.create_stripe_customer(
        user_data.email, f"{user_data.first_name} {user_data.last_name}"
    )

    if customer_id:
        SubscriptionService.update_user_stripe_customer(user["id"], customer_id)

    return {
        "message": "User registered successfully. Please check your email to verify your account.",
        "user_id": user["id"],
        "api_key": api_key,
        "email_verification_sent": True,
    }


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(verification_data: EmailVerificationConfirm):
    """Verify user email with token."""
    user_id = EmailService.verify_email_token(verification_data.token)
    if not user_id:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        )

    return {"message": "Email verified successfully"}


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification_email(
    request_data: EmailVerificationRequest, background_tasks: BackgroundTasks
):
    """Resend verification email."""
    user = UserService.get_user_by_email(request_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["email_verified"]:
        raise HTTPException(status_code=400, detail="Email is already verified")

    # Generate new verification token
    verification_token = EmailService.create_verification_token(user["id"])

    # Send verification email in background
    background_tasks.add_task(
        EmailService.send_verification_email,
        user["email"],
        verification_token,
        user["first_name"],
    )

    return {"message": "Verification email sent successfully"}


@router.post("/login", response_model=AuthResponse)
async def login_user(login_data: UserLogin):
    """Login user with email and password."""
    user = UserService.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if email is verified
    if not user["email_verified"]:
        raise HTTPException(
            status_code=401,
            detail="Please verify your email address before logging in. Check your email for a verification link.",
        )

    token = AuthService.create_jwt_token(user["id"], user["email"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "email_verified": user["email_verified"],
    }


@router.get("/google/url")
async def get_google_oauth_url():
    """Get Google OAuth URL for frontend."""
    from ..core.config import settings

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Google OAuth 2.0 authorization URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        "response_type=id_token&"
        "scope=openid email profile&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        "nonce=random_nonce"
    )

    return {"auth_url": auth_url}


@router.post("/google/callback", response_model=GoogleOAuthResponse)
async def google_oauth_callback(oauth_request: GoogleOAuthRequest):
    """Handle Google OAuth callback with ID token."""
    # Verify the Google ID token
    oauth_info = AuthService.verify_google_token(oauth_request.id_token)
    if not oauth_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Check if user exists by OAuth ID
    existing_user = UserService.get_user_by_oauth("google", oauth_info["oauth_id"])

    if existing_user:
        # User exists, log them in
        user = existing_user
    else:
        # Check if user exists by email (for linking accounts)
        existing_user_by_email = UserService.get_user_by_email(oauth_info["email"])

        if existing_user_by_email:
            # Link OAuth account to existing email account
            user = UserService.link_oauth_to_user(
                oauth_info["email"], oauth_info, "google"
            )
        else:
            # Create new user
            user = UserService.create_oauth_user(oauth_info, "google")

            # Create Stripe customer for new user
            customer_id = SubscriptionService.create_stripe_customer(
                oauth_info["email"],
                f"{oauth_info['first_name']} {oauth_info['last_name']}",
            )

            if customer_id:
                SubscriptionService.update_user_stripe_customer(user["id"], customer_id)

    # Generate API key if user doesn't have one
    from ..core.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as count FROM api_keys WHERE user_id = %s AND is_active = TRUE",
        (user["id"],),
    )
    api_key_count = cursor.fetchone()["count"]
    cursor.close()
    conn.close()

    api_key = None
    if api_key_count == 0:
        api_key = APIKeyService.create_api_key(user["id"])

    # Create JWT token
    token = AuthService.create_jwt_token(user["id"], user["email"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "email_verified": user["email_verified"],
        "api_key": api_key,
        "is_new_user": api_key is not None,
        "oauth_provider": "google",
    }
