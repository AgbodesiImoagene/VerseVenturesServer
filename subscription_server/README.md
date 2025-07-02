# VerseVentures Subscription Server

A comprehensive subscription management server for the VerseVentures application, handling user authentication, payment processing, and AWS credential generation for Transcribe access.

## Features

- **User Management**: Registration, authentication, and profile management
- **Email Verification**: Secure email verification system with token-based validation
- **Google OAuth**: One-click sign-in with Google accounts
- **Subscription Management**: Stripe integration for payment processing
- **AWS Credentials**: Temporary credential generation for AWS Transcribe
- **API Key Management**: Secure API key generation and management
- **Usage Tracking**: Monitor API usage and enforce limits
- **Webhook Handling**: Stripe webhook processing for subscription events

## Google OAuth Setup

The subscription server now supports Google OAuth for seamless user authentication.

### 1. Google Cloud Console Setup

1. **Create a Google Cloud Project**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google+ API**:

   - Navigate to "APIs & Services" > "Library"
   - Search for "Google+ API" and enable it

3. **Create OAuth 2.0 Credentials**:

   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application" as the application type
   - Add authorized redirect URIs:
     - `http://localhost:8000/auth/google/callback` (development)
     - `https://yourdomain.com/auth/google/callback` (production)

4. **Copy Credentials**:
   - Note down the Client ID and Client Secret
   - Add them to your `.env` file

### 2. Environment Configuration

Add these variables to your `.env` file:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### 3. Frontend Integration

#### Get OAuth URL

```javascript
// Get the Google OAuth URL
const response = await fetch("/auth/google/url");
const { auth_url } = await response.json();

// Redirect user to Google
window.location.href = auth_url;
```

#### Handle OAuth Callback

```javascript
// After Google redirects back with ID token
const idToken = "google_id_token_from_callback";

const response = await fetch("/auth/google/callback", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ id_token: idToken }),
});

const result = await response.json();
// result contains: access_token, user_id, api_key, etc.
```

### 4. OAuth Endpoints

#### Get Google OAuth URL

```http
GET /auth/google/url
```

Response:

```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

#### Google OAuth Callback

```http
POST /auth/google/callback
Content-Type: application/json

{
  "id_token": "google_id_token"
}
```

Response:

```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user_id": 1,
  "email_verified": true,
  "api_key": "vv_...",
  "is_new_user": true,
  "oauth_provider": "google"
}
```

### 5. Account Linking

The system automatically handles account linking:

- **New OAuth User**: Creates new account with OAuth info
- **Existing OAuth User**: Logs in with existing OAuth account
- **Email Match**: Links OAuth to existing email account
- **API Key Generation**: Automatically generates API key for new users

### 6. Security Features

- **Token Verification**: Validates Google ID tokens server-side
- **Email Verification**: OAuth users are automatically email-verified
- **Account Linking**: Prevents duplicate accounts
- **Secure Storage**: OAuth IDs stored securely in database

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │    │ Subscription     │    │   AWS Services  │
│                 │    │ Server           │    │                 │
│ - User Auth     │◄──►│ - User Mgmt      │    │ - Transcribe    │
│ - Payments      │    │ - Stripe         │    │ - STS           │
│ - API Calls     │    │ - Credentials    │    │ - IAM           │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   PostgreSQL     │
                       │   Database       │
                       │ - Users          │
                       │ - Subscriptions  │
                       │ - API Keys       │
                       │ - Usage Logs     │
                       │ - Email Tokens   │
                       └──────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Stripe account with API keys
- AWS account with IAM roles configured
- PostgreSQL database
- SMTP email service (Gmail, SendGrid, etc.)

### 1. Environment Setup

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your actual values:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=verseventures_subscriptions

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# AWS Configuration
AWS_REGION=us-east-1
TRANSCRIBE_ROLE_ARN=arn:aws:iam::123456789012:role/TranscribeRole

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@verseventures.com
FRONTEND_URL=http://localhost:3000

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 2. Start the Services

```bash
docker-compose up -d
```

The server will be available at `http://localhost:8000`

### 3. API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## API Endpoints

### Authentication

#### Register User

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe"
}
```

Response:

```json
{
  "message": "User registered successfully. Please check your email to verify your account.",
  "user_id": 1,
  "api_key": "vv_...",
  "email_verification_sent": true
}
```

#### Login User

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

Response:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": 1,
  "email_verified": true
}
```

#### Verify Email

```http
POST /auth/verify-email
Content-Type: application/json

{
  "token": "verification_token_from_email"
}
```

#### Resend Verification Email

```http
POST /auth/resend-verification
Content-Type: application/json

{
  "email": "user@example.com"
}
```

### Subscriptions

#### Get Available Plans

```http
GET /plans
```

#### Create Subscription

```http
POST /subscriptions/create?plan_id=price_basic_monthly
Authorization: Bearer <jwt_token>
```

### AWS Credentials

#### Get Temporary AWS Credentials

```http
POST /aws/credentials
Authorization: Bearer <jwt_token>
```

Response:

```json
{
  "access_key_id": "AKIA...",
  "secret_access_key": "...",
  "session_token": "...",
  "expiration": "2024-01-01T12:00:00Z"
}
```

### API Keys

#### Regenerate API Key

```http
POST /api-keys/regenerate
Authorization: Bearer <jwt_token>
```

### User Profile

#### Get User Profile

```http
GET /profile
Authorization: Bearer <jwt_token>
```

Response:

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "email_verified": true,
  "subscription_status": "active",
  "subscription_end_date": "2024-02-01T00:00:00Z",
  "api_calls_used": 150,
  "api_calls_limit": 1000
}
```

## Email Verification Flow

### 1. User Registration

1. User registers with email and password
2. System creates user account with `email_verified = false`
3. Verification token is generated and stored
4. Verification email is sent to user's email address
5. User receives email with verification link

### 2. Email Verification

1. User clicks verification link in email
2. Frontend extracts token from URL
3. Frontend calls `/auth/verify-email` with token
4. System validates token and marks email as verified
5. User can now login and access full features

### 3. Resend Verification

1. If user doesn't receive email, they can request a new one
2. Call `/auth/resend-verification` with email address
3. New verification token is generated and email sent
4. Old token is invalidated

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Email Verification Tokens Table

```sql
CREATE TABLE email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Subscriptions Table

```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_customer_id VARCHAR(255),
    plan_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Keys Table

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Usage Logs Table

```sql
CREATE TABLE usage_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    api_endpoint VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Email Configuration

### Gmail Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Use the generated password in `SMTP_PASSWORD`

### Other SMTP Providers

Update the SMTP settings in your `.env` file:

```bash
# SendGrid
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your_sendgrid_api_key

# AWS SES
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your_ses_smtp_username
SMTP_PASSWORD=your_ses_smtp_password
```

## AWS Setup

### 1. Create IAM Role for Transcribe

Create an IAM role with the policy from `aws_iam_policy.json`:

```bash
aws iam create-role --role-name TranscribeRole --assume-role-policy-document file://trust-policy.json
aws iam put-role-policy --role-name TranscribeRole --policy-name TranscribePolicy --policy-document file://aws_iam_policy.json
```

### 2. Trust Policy (trust-policy.json)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sts.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Stripe Setup

### 1. Create Products and Prices

In your Stripe dashboard, create products and prices for your subscription plans:

- Basic Plan: $9.99/month
- Pro Plan: $19.99/month
- Enterprise Plan: $49.99/month

### 2. Configure Webhooks

Set up webhooks in Stripe dashboard pointing to:

```
https://yourdomain.com/webhooks/stripe
```

Events to listen for:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## Integration with Semantic Search API

Update your semantic search API to use the subscription server for authentication:

```python
# In your semantic search API
async def verify_api_key(api_key: str = Depends(api_key_header)):
    # Call subscription server to verify API key
    response = await http_client.post(
        "https://subscription-server.com/verify-api-key",
        json={"api_key": api_key}
    )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return response.json()
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Formatting

```bash
pip install black isort
black .
isort .
```

## Production Deployment

### 1. Environment Variables

- Use strong, unique JWT secrets
- Configure production Stripe keys
- Set up production database
- Configure AWS IAM roles properly
- Use production SMTP settings

### 2. Security Considerations

- Enable HTTPS
- Configure CORS properly
- Use environment-specific settings
- Implement rate limiting
- Set up monitoring and logging
- Use secure email delivery services

### 3. Scaling

- Use connection pooling for database
- Implement caching (Redis)
- Consider using AWS RDS for database
- Set up load balancing
- Use AWS SES for email delivery

## Monitoring and Logging

The application includes comprehensive logging for:

- User authentication events
- Email verification events
- Subscription changes
- API usage
- Error tracking

Monitor these logs for:

- Failed authentication attempts
- Email delivery issues
- Subscription payment issues
- API usage patterns
- System errors

## Support

For issues and questions:

1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Verify environment configuration
4. Test with the provided examples
