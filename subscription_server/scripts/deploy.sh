#!/bin/bash

# VerseVentures Subscription Server Deployment Script
set -e

echo "🚀 Starting VerseVentures Subscription Server deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy env.example to .env and configure it."
    exit 1
fi

# Load environment variables
source .env

# Check required environment variables
required_vars=("STRIPE_SECRET_KEY" "STRIPE_WEBHOOK_SECRET" "JWT_SECRET" "DB_HOST" "DB_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set in .env file"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Build and start services
echo "🔨 Building and starting services..."
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

echo "✅ Services are running"

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ Database is ready"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Database failed to start within expected time"
    exit 1
fi

# Initialize database schema
echo "🗄️  Initializing database schema..."
docker-compose exec -T postgres psql -U postgres -d verseventures_subscriptions -f /app/scripts/setup_database.sql

echo "✅ Database schema initialized"

# Check if the application is responding
echo "🔍 Checking application health..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Application is healthy"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Application failed to respond within expected time"
    echo "📋 Check logs with: docker-compose logs subscription-server"
    exit 1
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Service Information:"
echo "   • Subscription Server: http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/health"
echo ""
echo "📊 Database Information:"
echo "   • Host: localhost:5432"
echo "   • Database: verseventures_subscriptions"
echo "   • User: postgres"
echo ""
echo "🔧 Useful Commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo "   • Access database: docker-compose exec postgres psql -U postgres -d verseventures_subscriptions"
echo ""
echo "⚠️  Next Steps:"
echo "   1. Configure Stripe webhooks to point to: http://yourdomain.com/webhooks/stripe"
echo "   2. Set up AWS IAM roles for Transcribe access"
echo "   3. Update your semantic search API to use this server for authentication"
echo "   4. Test the complete flow with a sample user registration" 