from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import boto3
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Auth Service")

# In production, this should be stored securely (e.g., in AWS Secrets Manager)
API_KEY = os.environ.get("SERVICE_API_KEY", "default-dev-key")
api_key_header = APIKeyHeader(name="X-API-Key")


class CredentialsResponse(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: datetime


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )
    return api_key


@app.post("/credentials", response_model=CredentialsResponse)
async def get_temporary_credentials(api_key: str = Depends(verify_api_key)):
    try:
        # Initialize STS client
        sts_client = boto3.client("sts")

        # Generate temporary credentials
        # Default duration: 15 minutes (900 seconds)
        response = sts_client.get_session_token(DurationSeconds=900)  # 15 minutes

        credentials = response["Credentials"]

        return CredentialsResponse(
            access_key_id=credentials["AccessKeyId"],
            secret_access_key=credentials["SecretAccessKey"],
            session_token=credentials["SessionToken"],
            expiration=credentials["Expiration"],
        )

    except Exception as e:
        logger.error(f"Error generating credentials: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to generate temporary credentials"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
