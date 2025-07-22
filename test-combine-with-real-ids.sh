#!/bin/bash

# Test combine endpoint with real document IDs

# Get a real file ID from the processed bucket
echo "Finding test files..."
TEST_FILES=$(aws s3 ls s3://redact-processed-documents-32a4ee51/processed/users/04189468-0051-7049-2bab-281bd7daa851/ | grep -E '\.(txt|md|csv)$' | head -2 | awk '{print $4}')

if [ -z "$TEST_FILES" ]; then
    echo "No test files found"
    exit 1
fi

# Build document IDs array
DOC_IDS=""
for file in $TEST_FILES; do
    # Full S3 key
    FULL_KEY="processed/users/04189468-0051-7049-2bab-281bd7daa851/$file"
    # URL encode
    ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$FULL_KEY', safe=''))")
    if [ -z "$DOC_IDS" ]; then
        DOC_IDS="\\\"$ENCODED\\\""
    else
        DOC_IDS="$DOC_IDS, \\\"$ENCODED\\\""
    fi
    echo "Added file: $file (encoded as: $ENCODED)"
done

# Create test payload
cat > /tmp/test-combine.json << EOF
{
  "httpMethod": "POST",
  "path": "/documents/combine",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\\\"document_ids\\\": [$DOC_IDS], \\\"output_filename\\\": \\\"test_combined.txt\\\"}",
  "requestContext": {
    "authorizer": {
      "claims": {
        "sub": "04189468-0051-7049-2bab-281bd7daa851"
      }
    }
  }
}
EOF

echo -e "\nTest payload:"
cat /tmp/test-combine.json | jq .

# Test Lambda
echo -e "\nTesting Lambda with real document IDs..."
base64 -w0 /tmp/test-combine.json > /tmp/payload.b64
aws lambda invoke --function-name redact-api-handler --payload file:///tmp/payload.b64 /tmp/lambda-output.json

echo -e "\nLambda response:"
cat /tmp/lambda-output.json | jq .