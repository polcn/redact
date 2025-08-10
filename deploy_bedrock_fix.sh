#!/bin/bash

# Deploy Bedrock model ID fix for Redact application
# This script updates the API Lambda function with corrected Bedrock model identifiers

set -e

echo "================================================"
echo "Deploying AWS Bedrock Model ID Fix"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Build the API Lambda package
echo ""
echo "Step 1: Building API Lambda package..."
if ./build_lambda.sh api; then
    print_status "API Lambda package built successfully"
else
    print_error "Failed to build API Lambda package"
    exit 1
fi

# Step 2: Update the Lambda function code
echo ""
echo "Step 2: Updating Lambda function code..."
if aws lambda update-function-code \
    --function-name redact-api-handler \
    --zip-file fileb://api_lambda.zip \
    --region us-east-1 > /dev/null 2>&1; then
    print_status "Lambda function code updated successfully"
else
    print_error "Failed to update Lambda function code"
    exit 1
fi

# Step 3: Wait for Lambda update to complete
echo ""
echo "Step 3: Waiting for Lambda update to complete..."
sleep 5
if aws lambda wait function-updated \
    --function-name redact-api-handler \
    --region us-east-1 2>/dev/null; then
    print_status "Lambda function update completed"
else
    print_warning "Lambda update wait timed out (this is usually okay)"
fi

# Step 4: Update SSM Parameter for AI config (if Terraform is not managing it)
echo ""
echo "Step 4: Updating AI configuration in SSM..."
cat > /tmp/ai-config.json << 'EOF'
{
  "enabled": true,
  "default_model": "anthropic.claude-3-haiku-20240307-v1:0",
  "available_models": [
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic.claude-instant-v1"
  ],
  "admin_override_model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
  "summary_types": {
    "brief": {
      "max_tokens": 150,
      "temperature": 0.3,
      "instruction": "Provide a brief 2-3 sentence summary of the key points in this document."
    },
    "standard": {
      "max_tokens": 500,
      "temperature": 0.5,
      "instruction": "Provide a comprehensive summary of this document, including main topics, key findings, and important details."
    },
    "detailed": {
      "max_tokens": 1000,
      "temperature": 0.7,
      "instruction": "Provide a detailed analysis and summary of this document, including all major points, supporting details, context, and implications."
    }
  },
  "default_summary_type": "standard"
}
EOF

if aws ssm put-parameter \
    --name "/redact/ai-config" \
    --value "$(cat /tmp/ai-config.json)" \
    --type "String" \
    --overwrite \
    --region us-east-1 > /dev/null 2>&1; then
    print_status "AI configuration updated in SSM Parameter Store"
else
    print_warning "Could not update SSM parameter (may need to apply Terraform changes)"
fi

rm -f /tmp/ai-config.json

# Step 5: Test the API health endpoint
echo ""
echo "Step 5: Testing API health endpoint..."
API_URL="https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"
if curl -s "${API_URL}/health" | grep -q "healthy"; then
    print_status "API health check passed"
else
    print_warning "API health check failed or returned unexpected response"
fi

# Summary
echo ""
echo "================================================"
echo "Deployment Summary:"
echo "================================================"
print_status "API Lambda function updated with corrected Bedrock model IDs"
print_status "Model IDs fixed:"
echo "  - Claude 3 Haiku: anthropic.claude-3-haiku-20240307-v1:0"
echo "  - Claude 3 Sonnet: anthropic.claude-3-sonnet-20240229-v1:0"
echo "  - Claude 3.5 Sonnet: anthropic.claude-3-5-sonnet-20240620-v1:0"
echo "  - Claude 3 Opus: anthropic.claude-3-opus-20240229-v1:0"
echo "  - Claude Instant: anthropic.claude-instant-v1"
echo ""
print_warning "Next steps:"
echo "1. Apply Terraform changes to update IAM permissions:"
echo "   cd /home/ec2-user/redact-terraform && terraform apply"
echo "2. Test the AI summary feature in the application"
echo "3. Monitor CloudWatch logs for any errors"
echo ""
echo "CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fredact-api-handler"