#!/bin/bash

# Deploy API Lambda updates to Development Environment
# This script builds and deploys API changes safely to dev environment

set -e  # Exit on error

echo "🔧 Deploying to Development Environment..."

# Ensure we're in the development workspace
if [[ $(terraform workspace show) != "development" ]]; then
    echo "🌿 Switching to development workspace..."
    terraform workspace select development
fi

# Build the API Lambda
echo "📦 Building API Lambda..."
./build_api_lambda.sh

# Get the development API Lambda function name
DEV_API_FUNCTION_NAME=$(terraform output -raw api_lambda_function_name 2>/dev/null || echo "")

if [ -z "$DEV_API_FUNCTION_NAME" ]; then
    echo "❌ Error: Could not get development API function name."
    echo "   Make sure development environment is deployed first."
    echo "   Run: ./setup-dev-env.sh"
    exit 1
fi

# Update the development Lambda function
echo "🚀 Deploying API Lambda to development ($DEV_API_FUNCTION_NAME)..."
aws lambda update-function-code \
    --function-name "$DEV_API_FUNCTION_NAME" \
    --zip-file fileb://api_lambda.zip \
    --query 'LastUpdateStatus' \
    --output text

# Wait for update to complete
echo "⏳ Waiting for function update to complete..."
aws lambda wait function-updated --function-name "$DEV_API_FUNCTION_NAME"

echo "✅ API Lambda deployed to development environment!"
echo ""
echo "🧪 Testing endpoints:"
DEV_API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
if [ -n "$DEV_API_URL" ]; then
    echo "Development API URL: $DEV_API_URL"
    echo ""
    echo "Test with:"
    echo "curl $DEV_API_URL/health"
fi

echo ""
echo "📊 View logs:"
echo "aws logs tail /aws/lambda/$DEV_API_FUNCTION_NAME --follow"