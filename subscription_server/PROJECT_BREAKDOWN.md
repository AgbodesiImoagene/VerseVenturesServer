# VerseVentures Subscription Server - Project Breakdown

## Overview

The VerseVentures Subscription Server is a comprehensive backend service designed to handle user authentication, subscription management, and AWS credential generation for the VerseVentures application. This server acts as the central authority for user management and provides secure access to AWS Transcribe services.

## Core Requirements

### 1. User Management

- **User Registration**: Secure user registration with email/password
- **User Authentication**: JWT-based authentication system
- **Email Verification**: Token-based email verification system
- **Profile Management**: User profile viewing and management
- **Password Security**: Bcrypt hashing for password storage

### 2. Email Verification System

- **Verification Tokens**: Secure, time-limited verification tokens
- **Email Sending**: SMTP-based email delivery with HTML templates
- **Token Management**: Automatic token expiration and cleanup
- **Resend Functionality**: Allow users to request new verification emails
- **Verification Status**: Track email verification status in user profiles

### 3. Subscription Management

- **Payment Processing**: Stripe integration for subscription payments
- **Plan Management**: Multiple subscription tiers (Basic, Pro, Enterprise)
- **Subscription Lifecycle**: Handle subscription creation, updates, and cancellations
- **Webhook Processing**: Real-time subscription event handling

### 4. AWS Credential Generation

- **Temporary Credentials**: Generate short-lived AWS credentials for Transcribe access
- **Role-Based Access**: Use AWS STS AssumeRole for secure credential generation
- **Permission Scoping**: Limit credentials to only Transcribe services
- **Credential Expiration**: Automatic credential expiration for security

### 5. API Key Management

- **API Key Generation**: Secure API key generation for semantic search access
- **Key Rotation**: Allow users to regenerate API keys
- **Key Validation**: Verify API keys for semantic search authentication
- **Usage Tracking**: Monitor API usage for billing and limits

### 6. Usage Tracking and Rate Limiting

- **API Usage Monitoring**: Track API calls per user
- **Usage Limits**: Enforce limits based on subscription tier
- **Usage Analytics**: Provide usage statistics to users
- **Rate Limiting**: Prevent abuse through rate limiting

## Architecture Decisions

### 1. Technology Stack

- **Framework**: FastAPI (Python) - Chosen for performance, async support, and automatic API documentation
- **Database**: PostgreSQL - Reliable, ACID-compliant database with excellent JSON support
- **Authentication**: JWT tokens - Stateless, scalable authentication
- **Email**: SMTP with Jinja2 templates - Flexible email delivery with HTML support
- **Payment Processing**: Stripe - Industry-standard payment processor with excellent webhook support
- **AWS Integration**: boto3 - Official AWS SDK for Python
- **Containerization**: Docker - Consistent deployment across environments

### 2. Database Design

- **Users Table**: Store user information, Stripe customer IDs, and email verification status
- **Email Verification Tokens Table**: Manage verification tokens with expiration
- **Subscriptions Table**: Track subscription status and billing information
- **API Keys Table**: Manage API keys with active/inactive status
- **Usage Logs Table**: Track API usage for analytics and billing
- **Indexes**: Optimized indexes for common query patterns

### 3. Security Considerations

- **Password Hashing**: Bcrypt with salt for secure password storage
- **JWT Tokens**: Short-lived tokens with secure signing
- **Email Verification**: Secure token generation and validation
- **API Key Security**: Cryptographically secure random generation
- **Input Validation**: Pydantic models for request validation
- **SQL Injection Prevention**: Parameterized queries
- **CORS Configuration**: Proper CORS setup for web clients

### 4. Email System Design

- **SMTP Configuration**: Flexible SMTP settings for different providers
- **HTML Templates**: Professional email templates with Jinja2
- **Token Security**: Cryptographically secure verification tokens
- **Expiration Management**: 24-hour token expiration with automatic cleanup
- **Background Processing**: Asynchronous email sending to avoid blocking

### 5. AWS Integration Strategy

- **IAM Role**: Dedicated role for Transcribe access
- **STS AssumeRole**: Temporary credential generation
- **Permission Scoping**: Minimal required permissions
- **Credential Expiration**: Short-lived credentials (1 hour)
- **Error Handling**: Graceful handling of AWS service errors

## Implementation Details

### 1. User Authentication Flow

```
1. User registers with email/password
2. Password is hashed with bcrypt
3. User record created in database with email_verified = false
4. Verification token generated and stored
5. Verification email sent to user
6. Stripe customer created
7. API key generated and returned
8. User can login with email/password (after verification)
9. JWT token issued for session management
```

### 2. Email Verification Flow

```
1. User receives verification email with token
2. User clicks verification link
3. Frontend extracts token from URL
4. Frontend calls /auth/verify-email with token
5. System validates token and expiration
6. User email marked as verified
7. Token deleted from database
8. User can now access full features
```

### 3. Subscription Flow

```
1. User selects subscription plan
2. Stripe checkout session created
3. User completes payment on Stripe
4. Webhook received with subscription details
5. Subscription record created/updated in database
6. User gains access to premium features
```

### 4. AWS Credential Generation Flow

```
1. User requests AWS credentials
2. JWT token validated
3. Active subscription verified
4. AWS STS AssumeRole called
5. Temporary credentials generated
6. Credentials returned to user
7. Usage logged for tracking
```

### 5. API Key Management Flow

```
1. User requests new API key
2. JWT token validated
3. Old API key deactivated
4. New API key generated
5. Key stored in database
6. New key returned to user
```

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

## API Endpoints

### Authentication Endpoints

- `POST /auth/register` - User registration with email verification
- `POST /auth/login` - User authentication (requires email verification)
- `POST /auth/verify-email` - Verify email with token
- `POST /auth/resend-verification` - Resend verification email
- `GET /profile` - Get user profile and usage stats

### Subscription Endpoints

- `GET /plans` - Get available subscription plans
- `POST /subscriptions/create` - Create new subscription
- `POST /webhooks/stripe` - Stripe webhook handler

### AWS Credentials Endpoints

- `POST /aws/credentials` - Generate temporary AWS credentials

### API Key Endpoints

- `POST /api-keys/regenerate` - Regenerate API key

### Utility Endpoints

- `GET /health` - Health check endpoint

## Email Configuration

### Supported SMTP Providers

- **Gmail**: Using App Passwords for secure authentication
- **SendGrid**: Using API keys for SMTP authentication
- **AWS SES**: Using SMTP credentials
- **Custom SMTP**: Any SMTP server with proper configuration

### Email Templates

- **Verification Email**: Professional HTML template with verification link
- **Responsive Design**: Mobile-friendly email layout
- **Branding**: VerseVentures branding and styling
- **Security**: Secure token links with expiration information

## Subscription Plans

### Basic Plan ($9.99/month)

- 1,000 API calls per month
- Basic support
- AWS Transcribe access
- Standard response times
- Email verification required

### Pro Plan ($19.99/month)

- 5,000 API calls per month
- Priority support
- Advanced analytics
- Faster response times
- AWS Transcribe access
- Email verification required

### Enterprise Plan ($49.99/month)

- Unlimited API calls
- 24/7 support
- Custom integrations
- Dedicated infrastructure
- AWS Transcribe access
- Email verification required

## Integration Points

### 1. Client Application

- User registration and login
- Email verification UI
- Subscription management UI
- AWS credential consumption
- API key management

### 2. Semantic Search API

- API key validation
- Usage tracking integration
- Subscription status verification

### 3. AWS Services

- Transcribe service access
- STS credential generation
- IAM role management

### 4. Stripe

- Payment processing
- Subscription management
- Webhook handling

### 5. Email Services

- SMTP email delivery
- Email template rendering
- Delivery tracking and logging

## Deployment Considerations

### 1. Environment Configuration

- Database connection settings
- Stripe API keys
- AWS IAM role ARNs
- JWT secret keys
- SMTP configuration
- CORS configuration

### 2. Security Hardening

- HTTPS enforcement
- Rate limiting
- Input sanitization
- Logging and monitoring
- Regular security updates
- Email security (SPF, DKIM, DMARC)

### 3. Scaling Strategy

- Database connection pooling
- Redis caching for sessions
- Load balancing
- Auto-scaling groups
- CDN for static assets
- Email queue management

### 4. Monitoring and Alerting

- Application health monitoring
- Database performance monitoring
- AWS service monitoring
- Email delivery monitoring
- Error tracking and alerting
- Usage analytics

## Testing Strategy

### 1. Unit Tests

- Individual function testing
- Mock external dependencies
- Edge case coverage
- Error handling validation
- Email template testing

### 2. Integration Tests

- API endpoint testing
- Database integration testing
- Stripe webhook testing
- AWS credential generation testing
- Email sending testing

### 3. End-to-End Tests

- Complete user flows
- Email verification flow testing
- Subscription lifecycle testing
- Error scenario testing
- Performance testing

## Future Enhancements

### 1. Additional Features

- Multi-factor authentication
- Social login integration
- Advanced analytics dashboard
- Custom subscription plans
- Usage prediction and alerts
- Email preferences management

### 2. Performance Optimizations

- Database query optimization
- Caching strategies
- CDN integration
- Microservice architecture
- Event-driven architecture
- Email queue optimization

### 3. Security Enhancements

- API rate limiting
- IP whitelisting
- Audit logging
- Compliance certifications
- Penetration testing
- Advanced email security

## Conclusion

The VerseVentures Subscription Server provides a robust, scalable foundation for user management and subscription handling with comprehensive email verification. The architecture is designed to be secure, maintainable, and extensible for future requirements. The integration with Stripe, AWS services, and email providers ensures reliable payment processing, secure credential management, and effective user communication for the VerseVentures application.
