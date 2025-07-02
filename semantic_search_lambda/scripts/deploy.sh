#!/bin/bash

# Semantic Search Lambda Deployment Script
set -e

echo "🚀 Starting Semantic Search Lambda deployment..."

# Configuration
LAMBDA_FUNCTION_NAME="verseventures-semantic-search"
LAMBDA_RUNTIME="python3.9"
LAMBDA_HANDLER="lambda_function.handler"
LAMBDA_MEMORY="2048"
LAMBDA_TIMEOUT="30"
PACKAGE_NAME="semantic-search-lambda.zip"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials are not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✅ AWS CLI and credentials verified"

# Create deployment directory
echo "📦 Creating deployment package..."
rm -rf package
mkdir -p package

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t ./package

# Copy lambda function
cp lambda_function.py ./package/

# Create deployment package
echo "🗜️  Creating deployment package..."
cd package
zip -r ../$PACKAGE_NAME .
cd ..

echo "✅ Deployment package created: $PACKAGE_NAME"

# Check if function exists
FUNCTION_EXISTS=$(aws lambda list-functions --query "Functions[?FunctionName=='$LAMBDA_FUNCTION_NAME'].FunctionName" --output text)

if [ -z "$FUNCTION_EXISTS" ]; then
    echo "🆕 Creating new Lambda function..."
    
    # Create the function
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --runtime $LAMBDA_RUNTIME \
        --handler $LAMBDA_HANDLER \
        --memory-size $LAMBDA_MEMORY \
        --timeout $LAMBDA_TIMEOUT \
        --zip-file fileb://$PACKAGE_NAME \
        --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role
    
    echo "✅ Lambda function created successfully"
else
    echo "🔄 Updating existing Lambda function..."
    
    # Update the function code
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --zip-file fileb://$PACKAGE_NAME
    
    # Update the function configuration
    aws lambda update-function-configuration \
        --function-name $LAMBDA_FUNCTION_NAME \
        --runtime $LAMBDA_RUNTIME \
        --handler $LAMBDA_HANDLER \
        --memory-size $LAMBDA_MEMORY \
        --timeout $LAMBDA_TIMEOUT
    
    echo "✅ Lambda function updated successfully"
fi

# Set environment variables (if provided)
if [ ! -z "$DB_HOST" ] && [ ! -z "$DB_USER" ] && [ ! -z "$DB_PASSWORD" ] && [ ! -z "$DB_NAME" ]; then
    echo "🔧 Setting environment variables..."
    
    aws lambda update-function-configuration \
        --function-name $LAMBDA_FUNCTION_NAME \
        --environment Variables="{DB_HOST=$DB_HOST,DB_PORT=${DB_PORT:-5432},DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD,DB_NAME=$DB_NAME}"
    
    echo "✅ Environment variables set"
else
    echo "⚠️  Environment variables not provided. Please set them manually in the AWS Console:"
    echo "   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME"
fi

# Clean up
echo "🧹 Cleaning up..."
rm -rf package
rm -f $PACKAGE_NAME

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Function Information:"
echo "   • Function Name: $LAMBDA_FUNCTION_NAME"
echo "   • Runtime: $LAMBDA_RUNTIME"
echo "   • Memory: ${LAMBDA_MEMORY}MB"
echo "   • Timeout: ${LAMBDA_TIMEOUT}s"
echo ""
echo "🔧 Next Steps:"
echo "   1. Configure API Gateway to route requests to the Lambda function"
echo "   2. Set up environment variables if not already done"
echo "   3. Configure VPC settings if your database is in a VPC"
echo "   4. Test the function with a sample request"
echo ""
echo "📊 Useful Commands:"
echo "   • Test function: aws lambda invoke --function-name $LAMBDA_FUNCTION_NAME --payload '{\"httpMethod\":\"GET\",\"path\":\"/health\"}' response.json"
echo "   • View logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo "   • Update function: ./deploy.sh" 