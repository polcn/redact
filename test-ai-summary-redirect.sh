#\!/bin/bash

# Test AI summary generation to see if there's a redirect happening

echo "Testing AI summary generation behavior..."

# Get a test file ID from the list
TEST_FILE_ID=$(aws s3 ls s3://redact-processed-32a4ee51/processed/ --recursive | grep -v "_AI" | head -1 | awk '{print $4}' | sed 's|^|processed%2F|' | sed 's|/|%2F|g')

if [ -z "$TEST_FILE_ID" ]; then
    echo "No test files found"
    exit 1
fi

echo "Using test file ID: $TEST_FILE_ID"

# Call the AI summary endpoint
RESPONSE=$(curl -s -X POST \
  "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/ai-summary" \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$TEST_FILE_ID\", \"summary_type\": \"brief\"}")

echo "Response: $RESPONSE"

# Check if response contains a download_url
if echo "$RESPONSE" | grep -q "download_url"; then
    URL=$(echo "$RESPONSE" | grep -o '"download_url":"[^"]*"' | cut -d'"' -f4)
    echo "Download URL found: $URL"
    
    # Test if the URL returns a redirect
    echo "Testing URL response headers..."
    curl -I "$URL" | head -10
fi
