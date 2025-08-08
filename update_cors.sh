#!/bin/bash

API_ID="101pi5aiv5"
ORIGIN="https://redact.9thcube.com"

echo "Updating CORS configuration for all OPTIONS methods..."

# List of resource IDs with OPTIONS methods
RESOURCES=(
  "u7cn09"  # /documents/upload
  "0j5sld"  # /documents/combine
  "3yojl1"  # /api/test-redaction
  "7ho12g"  # /documents/status/{id}
  "bjzsmn"  # /api/external-ai-keys
  "cs5xt3"  # /quarantine/files
  "cx8spi"  # /api/string/redact
  "dqctfb"  # /quarantine/delete-all
  "hw5nrk"  # /quarantine/{id}
  "k3wrbu"  # /documents/ai-summary
  "mvc58p"  # /documents/{id}
  "o4txc9"  # /user/files
  "pa8y8a"  # /api/config
  "pq4lja"  # /documents/batch-download
  "s0oi6g"  # /health
  "ykgzq8"  # /api/ai-config
)

for RESOURCE_ID in "${RESOURCES[@]}"; do
  echo "Updating resource: $RESOURCE_ID"
  
  aws apigateway put-integration-response \
    --rest-api-id "$API_ID" \
    --resource-id "$RESOURCE_ID" \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters "{\"method.response.header.Access-Control-Allow-Headers\":\"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'\",\"method.response.header.Access-Control-Allow-Methods\":\"'GET,OPTIONS,POST,PUT,DELETE'\",\"method.response.header.Access-Control-Allow-Origin\":\"'$ORIGIN'\"}" \
    --output text \
    --query 'statusCode' || echo "Failed to update $RESOURCE_ID"
done

echo "Deploying API Gateway changes..."
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name production \
  --description "Update CORS to restrict origin to $ORIGIN"

echo "CORS update complete!"