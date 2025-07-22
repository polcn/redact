#!/bin/bash

# Test combine endpoint with correct field names
API_URL="https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"

# Test with correct payload structure
echo "Testing Lambda directly with correct payload..."
cat > /tmp/combine-payload.json << 'EOF'
{
  "httpMethod": "POST",
  "path": "/documents/combine",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"document_ids\": [\"test1\", \"test2\"], \"output_filename\": \"combined.txt\"}",
  "requestContext": {
    "authorizer": {
      "claims": {
        "sub": "test-user-123"
      }
    }
  }
}
EOF

# Encode and invoke
base64 -w0 /tmp/combine-payload.json > /tmp/payload.b64
aws lambda invoke --function-name redact-api-handler --payload file:///tmp/payload.b64 /tmp/lambda-output.json
echo "Lambda response:"
cat /tmp/lambda-output.json | jq .

# Check if the endpoint is properly deployed to production stage
echo -e "\n\nChecking deployment status..."
aws apigateway get-stage --rest-api-id 101pi5aiv5 --stage-name production --query '[stageName, deploymentId, lastUpdatedDate]' --output table