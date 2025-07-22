#!/bin/bash

# Simple test with hardcoded real file IDs

# Create test payload with actual file keys
cat > /tmp/test-combine.json << 'EOF'
{
  "httpMethod": "POST",
  "path": "/documents/combine",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"document_ids\": [\"processed%2Fusers%2F04189468-0051-7049-2bab-281bd7daa851%2FAmazon%20Linux%202%20Operating%20System%20Security%20Standards.md\", \"processed%2Fusers%2F04189468-0051-7049-2bab-281bd7daa851%2FAnti-Virus%20Standard.md\"], \"output_filename\": \"test_combined.txt\"}",
  "requestContext": {
    "authorizer": {
      "claims": {
        "sub": "04189468-0051-7049-2bab-281bd7daa851"
      }
    }
  }
}
EOF

echo "Test payload:"
cat /tmp/test-combine.json | jq .

# Test Lambda
echo -e "\nTesting Lambda..."
base64 -w0 /tmp/test-combine.json > /tmp/payload.b64
aws lambda invoke --function-name redact-api-handler --payload file:///tmp/payload.b64 /tmp/lambda-output.json

echo -e "\nLambda response:"
cat /tmp/lambda-output.json | jq .