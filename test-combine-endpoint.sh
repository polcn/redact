#!/bin/bash

# Test the combine endpoint directly

API_URL="https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"

# First test OPTIONS (CORS preflight)
echo "Testing OPTIONS request for CORS..."
curl -v -X OPTIONS "${API_URL}/documents/combine" \
  -H "Origin: https://redact.9thcube.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type"

echo -e "\n\nTesting POST without auth (should fail with 401)..."
curl -v -X POST "${API_URL}/documents/combine" \
  -H "Content-Type: application/json" \
  -d '{"file_ids": ["test1", "test2"], "output_filename": "test.txt"}'

echo -e "\n\nChecking API Gateway resources..."
aws apigateway get-resources --rest-api-id 101pi5aiv5 --query 'items[?path==`/documents/combine`]' 

echo -e "\n\nChecking method configuration..."
aws apigateway get-method --rest-api-id 101pi5aiv5 --resource-id $(aws apigateway get-resources --rest-api-id 101pi5aiv5 --query 'items[?path==`/documents/combine`].id' --output text) --http-method POST 2>/dev/null || echo "Method not found"