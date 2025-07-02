from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import stripe
import boto3
import jwt
import bcrypt
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import emails
import secrets
from jinja2 import Template
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="VerseVentures Subscription Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)

# Email configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@verseventures.com")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Security
security = HTTPBearer()


# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        cursor_factory=RealDictCursor,
    )


# Pydantic models
class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    token: str


class GoogleOAuthRequest(BaseModel):
    id_token: str


class OAuthUserInfo(BaseModel):
    email: str
    first_name: str
    last_name: str
    picture: Optional[str] = None
    oauth_id: str


class SubscriptionPlan(BaseModel):
    name: str
    price_id: str
    price: float
    interval: str  # monthly or yearly
    features: List[str]


class AWSCredentialsResponse(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: datetime


class APIKeyResponse(BaseModel):
    api_key: str
    created_at: datetime


class UserProfile(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    email_verified: bool
    subscription_status: str
    subscription_end_date: Optional[datetime]
    api_calls_used: int
    api_calls_limit: int


# JWT token management
def create_jwt_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(datetime.UTC) + timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Authentication dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    return verify_jwt_token(token)


# Database initialization
def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255),
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email_verified BOOLEAN DEFAULT FALSE,
            stripe_customer_id VARCHAR(255),
            oauth_provider VARCHAR(50),
            oauth_id VARCHAR(255),
            oauth_picture VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(oauth_provider, oauth_id)
        )
    """
    )

    # Create email_verification_tokens table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create subscriptions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            stripe_subscription_id VARCHAR(255) UNIQUE,
            stripe_customer_id VARCHAR(255),
            plan_name VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            current_period_start TIMESTAMP,
            current_period_end TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create api_keys table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            api_key VARCHAR(255) UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create usage_logs table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            api_endpoint VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.commit()
    cursor.close()
    conn.close()


# User management functions
def create_user(email: str, password: str, first_name: str, last_name: str) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Hash password
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    cursor.execute(
        """
        INSERT INTO users (email, password_hash, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        RETURNING id, email, first_name, last_name, created_at
    """,
        (email, password_hash, first_name, last_name),
    )

    user = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return dict(user)


def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)


def create_verification_token(user_id: int) -> str:
    """Create and store a verification token for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete any existing tokens for this user
    cursor.execute(
        "DELETE FROM email_verification_tokens WHERE user_id = %s", (user_id,)
    )

    # Generate new token
    token = generate_verification_token()
    expires_at = datetime.now(datetime.UTC) + timedelta(hours=24)  # 24 hour expiration

    cursor.execute(
        """
        INSERT INTO email_verification_tokens (user_id, token, expires_at)
        VALUES (%s, %s, %s)
    """,
        (user_id, token, expires_at),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return token


def verify_email_token(token: str) -> Optional[int]:
    """Verify an email verification token and return user_id if valid"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT user_id FROM email_verification_tokens 
        WHERE token = %s AND expires_at > %s
    """,
        (token, datetime.now(datetime.UTC)),
    )

    result = cursor.fetchone()
    if result:
        user_id = result["user_id"]
        # Mark email as verified
        cursor.execute(
            "UPDATE users SET email_verified = TRUE WHERE id = %s", (user_id,)
        )
        # Delete the used token
        cursor.execute(
            "DELETE FROM email_verification_tokens WHERE token = %s", (token,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return user_id

    cursor.close()
    conn.close()
    return None


def send_verification_email(email: str, token: str, first_name: str):
    """Send verification email to user"""
    try:
        # Email template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Email - VerseVentures</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #4a90e2; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .button { display: inline-block; padding: 12px 24px; background: #4a90e2; color: white; text-decoration: none; border-radius: 5px; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to VerseVentures!</h1>
                </div>
                <div class="content">
                    <p>Hi {{ first_name }},</p>
                    <p>Thank you for registering with VerseVentures! To complete your registration, please verify your email address by clicking the button below:</p>
                    <p style="text-align: center;">
                        <a href="{{ verification_url }}" class="button">Verify Email Address</a>
                    </p>
                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p>{{ verification_url }}</p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't create an account with VerseVentures, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 VerseVentures. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Create verification URL
        verification_url = f"{FRONTEND_URL}/verify-email?token={token}"

        # Render template
        template = Template(html_template)
        html_content = template.render(
            first_name=first_name, verification_url=verification_url
        )

        # Send email
        message = emails.Message(
            subject="Verify Your Email - VerseVentures",
            html=html_content,
            mail_from=FROM_EMAIL,
        )

        smtp_options = {
            "host": SMTP_HOST,
            "port": SMTP_PORT,
            "user": SMTP_USERNAME,
            "password": SMTP_PASSWORD,
            "tls": True,
        }

        response = message.send(to=email, smtp=smtp_options)

        if response.status_code not in [250, 200, 201, 202]:
            logger.error(f"Failed to send verification email: {response.status_code}")
            return False

        logger.info(f"Verification email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return False


def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return dict(user) if user else None


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_api_key() -> str:
    return f"vv_{secrets.token_urlsafe(32)}"


def create_api_key(user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()

    api_key = generate_api_key()

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


def get_user_subscription(user_id: int) -> Optional[dict]:
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


def log_api_usage(user_id: int, endpoint: str):
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


def get_api_usage_count(user_id: int, period_days: int = 30) -> int:
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


# Google OAuth functions
def verify_google_token(id_token_str: str) -> Optional[dict]:
    """Verify Google ID token and return user info"""
    try:
        if not GOOGLE_CLIENT_ID:
            logger.error("Google Client ID not configured")
            return None

        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            id_token_str, requests.Request(), GOOGLE_CLIENT_ID
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


def get_user_by_oauth(provider: str, oauth_id: str) -> Optional[dict]:
    """Get user by OAuth provider and ID"""
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


def create_oauth_user(oauth_info: dict, provider: str = "google") -> dict:
    """Create a new user from OAuth info"""
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


# API Endpoints
@app.on_event("startup")
async def startup_event():
    init_database()


@app.post("/auth/register")
async def register_user(user_data: UserRegistration, background_tasks: BackgroundTasks):
    # Check if user already exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Create user
    user = create_user(
        user_data.email,
        user_data.password,
        user_data.first_name,
        user_data.last_name,
    )

    # Generate verification token
    verification_token = create_verification_token(user["id"])

    # Send verification email in background
    background_tasks.add_task(
        send_verification_email,
        user_data.email,
        verification_token,
        user_data.first_name,
    )

    # Generate API key
    api_key = create_api_key(user["id"])

    # Create Stripe customer
    try:
        customer = stripe.Customer.create(
            email=user_data.email,
            name=f"{user_data.first_name} {user_data.last_name}",
        )

        # Update user with Stripe customer ID
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users SET stripe_customer_id = %s WHERE id = %s
        """,
            (customer.id, user["id"]),
        )
        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error creating Stripe customer: {str(e)}")

    return {
        "message": "User registered successfully. Please check your email to verify your account.",
        "user_id": user["id"],
        "api_key": api_key,
        "email_verification_sent": True,
    }


@app.post("/auth/verify-email")
async def verify_email(verification_data: EmailVerificationConfirm):
    """Verify user email with token"""
    user_id = verify_email_token(verification_data.token)

    if not user_id:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        )

    return {"message": "Email verified successfully"}


@app.post("/auth/resend-verification")
async def resend_verification_email(
    request_data: EmailVerificationRequest, background_tasks: BackgroundTasks
):
    """Resend verification email"""
    user = get_user_by_email(request_data.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["email_verified"]:
        raise HTTPException(status_code=400, detail="Email is already verified")

    # Generate new verification token
    verification_token = create_verification_token(user["id"])

    # Send verification email in background
    background_tasks.add_task(
        send_verification_email,
        user["email"],
        verification_token,
        user["first_name"],
    )

    return {"message": "Verification email sent successfully"}


@app.post("/auth/login")
async def login_user(login_data: UserLogin):
    user = get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if email is verified (optional - you can remove this if you want to allow unverified users)
    if not user["email_verified"]:
        raise HTTPException(
            status_code=401,
            detail="Please verify your email address before logging in. Check your email for a verification link.",
        )

    token = create_jwt_token(user["id"], user["email"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "email_verified": user["email_verified"],
    }


@app.get("/auth/google/url")
async def get_google_oauth_url():
    """Get Google OAuth URL for frontend"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Google OAuth 2.0 authorization URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        "response_type=id_token&"
        "scope=openid email profile&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        "nonce=random_nonce"
    )

    return {"auth_url": auth_url}


@app.post("/auth/google/callback")
async def google_oauth_callback(oauth_request: GoogleOAuthRequest):
    """Handle Google OAuth callback with ID token"""
    # Verify the Google ID token
    oauth_info = verify_google_token(oauth_request.id_token)
    if not oauth_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Check if user exists by OAuth ID
    existing_user = get_user_by_oauth("google", oauth_info["oauth_id"])

    if existing_user:
        # User exists, log them in
        user = existing_user
    else:
        # Check if user exists by email (for linking accounts)
        existing_user_by_email = get_user_by_email(oauth_info["email"])

        if existing_user_by_email:
            # Link OAuth account to existing email account
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE users 
                SET oauth_provider = %s, oauth_id = %s, oauth_picture = %s
                WHERE email = %s
                RETURNING id, email, first_name, last_name, email_verified
                """,
                (
                    "google",
                    oauth_info["oauth_id"],
                    oauth_info.get("picture"),
                    oauth_info["email"],
                ),
            )

            user = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            user = dict(user)
        else:
            # Create new user
            user = create_oauth_user(oauth_info, "google")

            # Create Stripe customer for new user
            try:
                customer = stripe.Customer.create(
                    email=oauth_info["email"],
                    name=f"{oauth_info['first_name']} {oauth_info['last_name']}",
                )

                # Update user with Stripe customer ID
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users SET stripe_customer_id = %s WHERE id = %s
                """,
                    (customer.id, user["id"]),
                )
                conn.commit()
                cursor.close()
                conn.close()

            except Exception as e:
                logger.error(f"Error creating Stripe customer: {str(e)}")

    # Generate API key if user doesn't have one
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
        api_key = create_api_key(user["id"])

    # Create JWT token
    token = create_jwt_token(user["id"], user["email"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "email_verified": user["email_verified"],
        "api_key": api_key,
        "is_new_user": api_key is not None,
        "oauth_provider": "google",
    }


@app.get("/plans")
async def get_subscription_plans():
    return {
        "plans": [
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
    }


@app.post("/subscriptions/create")
async def create_subscription(
    plan_id: str, current_user: dict = Depends(get_current_user)
):
    user = get_user_by_email(current_user["email"])

    # Check if user already has an active subscription
    existing_subscription = get_user_subscription(user["id"])
    if existing_subscription:
        raise HTTPException(
            status_code=400, detail="User already has an active subscription"
        )

    try:
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            customer=user.get("stripe_customer_id"),
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
            metadata={"user_id": user["id"]},
        )

        return {"checkout_url": session.url, "session_id": session.id}

    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating subscription")


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle_checkout_completed(session)
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        handle_subscription_updated(subscription)
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        handle_subscription_deleted(subscription)

    return {"status": "success"}


def handle_checkout_completed(session):
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


def handle_subscription_updated(subscription):
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


def handle_subscription_deleted(subscription):
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


@app.post("/aws/credentials", response_model=AWSCredentialsResponse)
async def get_aws_credentials(current_user: dict = Depends(get_current_user)):
    user = get_user_by_email(current_user["email"])
    subscription = get_user_subscription(user["id"])

    if not subscription or subscription["status"] != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")

    try:
        # Initialize STS client
        sts_client = boto3.client("sts")

        # Generate temporary credentials with Transcribe permissions
        response = sts_client.assume_role(
            RoleArn=os.environ.get("TRANSCRIBE_ROLE_ARN"),
            RoleSessionName=f"user-{user['id']}-session",
            DurationSeconds=3600,  # 1 hour
            Policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "transcribe:StartStreamTranscription",
                                "transcribe:StartTranscriptionJob",
                                "transcribe:GetTranscriptionJob",
                            ],
                            "Resource": "*",
                        }
                    ],
                }
            ),
        )

        credentials = response["Credentials"]

        return AWSCredentialsResponse(
            access_key_id=credentials["AccessKeyId"],
            secret_access_key=credentials["SecretAccessKey"],
            session_token=credentials["SessionToken"],
            expiration=credentials["Expiration"],
        )

    except Exception as e:
        logger.error(f"Error generating AWS credentials: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to generate AWS credentials"
        )


@app.post("/api-keys/regenerate")
async def regenerate_api_key(current_user: dict = Depends(get_current_user)):
    user = get_user_by_email(current_user["email"])

    # Deactivate old API key
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE api_keys SET is_active = FALSE WHERE user_id = %s
    """,
        (user["id"],),
    )

    # Generate new API key
    new_api_key = create_api_key(user["id"])

    conn.commit()
    cursor.close()
    conn.close()

    return {"api_key": new_api_key}


@app.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    user = get_user_by_email(current_user["email"])
    subscription = get_user_subscription(user["id"])
    api_usage = get_api_usage_count(user["id"])

    # Determine API call limits based on subscription
    api_limit = 1000  # Default
    if subscription:
        if subscription["plan_name"] == "Pro":
            api_limit = 5000
        elif subscription["plan_name"] == "Enterprise":
            api_limit = -1  # Unlimited

    return UserProfile(
        id=user["id"],
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email_verified=user["email_verified"],
        subscription_status=subscription["status"] if subscription else "none",
        subscription_end_date=(
            subscription["current_period_end"] if subscription else None
        ),
        api_calls_used=api_usage,
        api_calls_limit=api_limit,
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Middleware to log API usage
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)

    # Log API usage for authenticated endpoints
    if request.url.path.startswith("/aws/credentials") or request.url.path.startswith(
        "/api-keys"
    ):
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                user_data = verify_jwt_token(token)
                log_api_usage(user_data["user_id"], request.url.path)
            except:
                pass

    return response
