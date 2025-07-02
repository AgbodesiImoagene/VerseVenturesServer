"""
Pydantic models for request and response schemas.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Authentication Models
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


# Subscription Models
class SubscriptionPlan(BaseModel):
    name: str
    price_id: str
    price: float
    interval: str  # monthly or yearly
    features: List[str]


# AWS Models
class AWSCredentialsResponse(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: datetime


# API Key Models
class APIKeyResponse(BaseModel):
    api_key: str
    created_at: datetime


# User Profile Models
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


# Response Models
class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email_verified: bool


class GoogleOAuthResponse(AuthResponse):
    api_key: Optional[str] = None
    is_new_user: bool
    oauth_provider: str


class RegistrationResponse(BaseModel):
    message: str
    user_id: int
    api_key: str
    email_verification_sent: bool


class MessageResponse(BaseModel):
    message: str


class PlansResponse(BaseModel):
    plans: List[SubscriptionPlan]


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class WebhookResponse(BaseModel):
    status: str
