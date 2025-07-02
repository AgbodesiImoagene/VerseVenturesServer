# VerseVentures Server

A comprehensive server architecture for the VerseVentures application, providing semantic search capabilities for Bible verses with live audio transcription and subscription management.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │    │ Subscription     │    │  Semantic       │    │   AWS Services  │
│                 │    │ Server           │    │  Search API     │    │                 │
│ - User Auth     │◄──►│ - User Mgmt      │    │ - Verse Search  │    │ - Transcribe    │
│ - Payments      │    │ - Stripe         │    │ - Embeddings    │    │ - STS           │
│ - API Calls     │    │ - Credentials    │    │ - pgvector      │    │ - IAM           │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌──────────────────┐    ┌──────────────────┐
                       │   PostgreSQL     │    │   PostgreSQL     │
                       │   Subscriptions  │    │   Bible Data     │
                       │ - Users          │    │ - Verses         │
                       │ - Subscriptions  │    │ - Embeddings     │
                       │ - API Keys       │    │ - Metadata       │
                       │ - Usage Logs     │    └──────────────────┘
                       └──────────────────┘
```

## Services

### 1. Subscription Server (`subscription_server/`)

**Purpose**: Handles user authentication, subscription management, and AWS credential generation.

**Features**:

- User registration and authentication with JWT tokens
- Google OAuth integration for one-click sign-in
- Email verification system with token-based validation
- Stripe integration for payment processing
- AWS STS credential generation for Transcribe access
- API key management for semantic search authentication
- Usage tracking and rate limiting
- Webhook handling for subscription events

**Key Endpoints**:

- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `GET /auth/google/url` - Get Google OAuth URL
- `POST /auth/google/callback` - Google OAuth callback
- `POST /aws/credentials` - Generate AWS credentials
- `POST /api-keys/regenerate` - Regenerate API keys
- `GET /profile` - User profile and usage stats

### 2. Semantic Search API (`semantic_search_api/`)

**Purpose**: Provides semantic search capabilities for Bible verses using embeddings.

**Features**:

- Semantic search using sentence transformers
- Support for multiple Bible versions (KJV, ASV, NET, WEB)
- WebSocket and HTTP endpoints
- pgvector integration for efficient similarity search
- Configurable similarity thresholds

**Key Endpoints**:

- `POST /semantic-search` - HTTP search endpoint
- `WebSocket /ws/semantic-search` - Real-time search

### 3. Semantic Search Lambda (`semantic_search_lambda/`)

**Purpose**: Serverless version of semantic search for AWS Lambda deployment.

**Features**:

- Lambda-optimized semantic search with full feature parity to the API
- Support for multiple Bible versions (KJV, ASV, NET, WEB)
- Configurable parameters (threshold, max_results, bible_version)
- CORS support for web client integration
- Comprehensive error handling and logging
- Health check and supported versions endpoints
- Designed for serverless architectures with auto-scaling

**Key Endpoints**:

- `POST /semantic-search` - HTTP search endpoint
- `GET /supported-bible-versions` - Get supported Bible versions
- `GET /health` - Health check endpoint

**Deployment**: Use the provided `deploy.sh` script for easy AWS Lambda deployment

## Quick Start

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database
- Stripe account (for subscriptions)
- AWS account with IAM roles configured

### 1. Clone and Setup

```bash
git clone <repository-url>
cd VerseVenturesServer
```

### 2. Configure Environment

```bash
# Copy environment files
cp subscription_server/env.example subscription_server/.env
cp semantic_search_api/.env.example semantic_search_api/.env

# Edit configuration files with your actual values
```

### 3. Start Services

#### Option A: Full Stack (Recommended)

```bash
cd subscription_server
./scripts/deploy.sh
```

#### Option B: Individual Services

```bash
# Start subscription server
cd subscription_server
docker-compose up -d

# Start semantic search API
cd ../semantic_search_api
docker-compose up -d
```

### 4. Access Services

- **Subscription Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Semantic Search API**: http://localhost:8001
- **Health Checks**:
  - http://localhost:8000/health
  - http://localhost:8001/health

## API Integration Flow

### 1. User Registration and Authentication

```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Login to get JWT token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword"
  }'
```

### 2. Get AWS Credentials for Transcribe

```bash
curl -X POST http://localhost:8000/aws/credentials \
  -H "Authorization: Bearer <jwt_token>"
```

### 3. Use Semantic Search API

```bash
# Get API key from subscription server
curl -X POST http://localhost:8000/api-keys/regenerate \
  -H "Authorization: Bearer <jwt_token>"

# Use API key for semantic search
curl -X POST http://localhost:8001/semantic-search \
  -H "X-API-Key: <api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "love your neighbor",
    "threshold": 0.7,
    "bible_version": "kjv"
  }'
```

## Database Setup

### Subscription Database

```bash
# The deployment script automatically sets up the subscription database
# Manual setup if needed:
cd subscription_server
docker-compose exec postgres psql -U postgres -d verseventures_subscriptions -f /app/scripts/setup_database.sql
```

### Bible Data Database

The semantic search API requires a PostgreSQL database with pgvector extension and Bible verse data with embeddings.

## AWS Configuration

### 1. IAM Roles

Create an IAM role for Transcribe access:

```bash
# Create trust policy
cat > trust-policy.json << EOF
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
EOF

# Create role
aws iam create-role --role-name TranscribeRole --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam put-role-policy --role-name TranscribeRole --policy-name TranscribePolicy --policy-document file://subscription_server/aws_iam_policy.json
```

### 2. Environment Variables

Set the role ARN in your environment:

```bash
TRANSCRIBE_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT_ID:role/TranscribeRole
```

## Stripe Configuration

### 1. Create Products and Prices

In your Stripe dashboard, create subscription products:

- Basic Plan: $9.99/month
- Pro Plan: $19.99/month
- Enterprise Plan: $49.99/month

### 2. Configure Webhooks

Set up webhooks pointing to your subscription server:

```
https://yourdomain.com/webhooks/stripe
```

Events to listen for:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## Development

### Running Tests

```bash
# Subscription server tests
cd subscription_server
pytest

# Semantic search API tests
cd ../semantic_search_api
pytest
```

### Code Formatting

```bash
pip install black isort
black .
isort .
```

## Production Deployment

### Security Considerations

- Use strong, unique JWT secrets
- Configure production Stripe keys
- Set up production databases
- Enable HTTPS
- Configure CORS properly
- Implement rate limiting
- Set up monitoring and logging

### Scaling

- Use connection pooling for databases
- Implement caching (Redis)
- Consider using AWS RDS for databases
- Set up load balancing
- Use AWS ECS/EKS for container orchestration

## Monitoring and Logging

All services include comprehensive logging for:

- User authentication events
- Subscription changes
- API usage patterns
- Error tracking
- Performance metrics

## Support

For issues and questions:

1. Check the API documentation at `/docs`
2. Review service logs
3. Verify environment configuration
4. Test with the provided examples
5. Check the individual service README files

## License

[Add your license information here]
