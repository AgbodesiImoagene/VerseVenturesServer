"""
AWS API routes for credential generation and user management.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime

from ..models.schemas import AWSCredentialsResponse, APIKeyResponse, UserProfile
from ..services.auth_service import AuthService, UserService
from ..services.aws_service import AWSService, UsageService
from ..services.api_key_service import APIKeyService

router = APIRouter(prefix="/aws", tags=["aws"])
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


@router.post("/credentials", response_model=AWSCredentialsResponse)
async def get_aws_credentials(current_user: dict = Depends(get_current_user)):
    """Generate temporary AWS credentials for the authenticated user."""
    # Log API usage
    UsageService.log_api_usage(current_user["user_id"], "aws_credentials")

    # Generate credentials
    credentials = AWSService.generate_temporary_credentials()
    if not credentials:
        raise HTTPException(
            status_code=500, detail="Failed to generate temporary credentials"
        )

    return AWSCredentialsResponse(**credentials)


@router.post("/api-keys/regenerate", response_model=APIKeyResponse)
async def regenerate_api_key(current_user: dict = Depends(get_current_user)):
    """Regenerate API key for the authenticated user."""
    # Log API usage
    UsageService.log_api_usage(current_user["user_id"], "regenerate_api_key")

    # Deactivate existing API keys
    user = UserService.get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get existing API keys and deactivate them
    existing_keys = APIKeyService.get_user_api_keys(user["id"])
    for key in existing_keys:
        if key["is_active"]:
            APIKeyService.deactivate_api_key(key["api_key"], user["id"])

    # Generate new API key
    api_key = APIKeyService.create_api_key(user["id"])

    return {"api_key": api_key, "created_at": datetime.now()}


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile with subscription and usage information."""
    # Log API usage
    UsageService.log_api_usage(current_user["user_id"], "get_profile")

    profile = UsageService.get_user_profile(current_user["user_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfile(**profile)
