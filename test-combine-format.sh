#!/bin/bash

# Simple test script that directly calls the API and saves the output

# Get test files
echo "Finding test files..."
FILES=$(aws s3 ls s3://redact-processed-documents-32a4ee51/processed/users/04189468-0051-7049-2bab-281bd7daa851/ | grep -E '\.(txt|md|csv)$' | grep -v '.zip' | head -2 | awk '{print $4}')

if [ -z "$FILES" ]; then
    echo "No files found for testing"
    exit 1
fi

# Build document IDs array
DOC_IDS="["
FIRST=true
for FILE in $FILES; do
    if [ "$FIRST" = true ]; then
        FIRST=false
    else
        DOC_IDS="$DOC_IDS, "
    fi
    # Use simple filename approach
    DOC_IDS="$DOC_IDS\"$FILE\""
done
DOC_IDS="$DOC_IDS]"

echo "Using files: $DOC_IDS"

# Generate timestamp for unique filename
TIMESTAMP=$(date +%s)
OUTPUT_FILE="test_delineation_${TIMESTAMP}.txt"

# Call the API directly with curl
echo "Calling combine API..."
RESPONSE=$(curl -s -X POST \
  "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/combine" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_ids\": $DOC_IDS,
    \"output_filename\": \"$OUTPUT_FILE\"
  }")

echo "Response: $RESPONSE"

# Extract download URL
DOWNLOAD_URL=$(echo "$RESPONSE" | jq -r '.download_url' 2>/dev/null)

if [ "$DOWNLOAD_URL" != "null" ] && [ -n "$DOWNLOAD_URL" ]; then
    echo "Downloading combined file..."
    curl -s "$DOWNLOAD_URL" -o "/tmp/$OUTPUT_FILE"
    
    echo "Combined file content preview:"
    echo "================================"
    head -n 50 "/tmp/$OUTPUT_FILE"
    echo "..."
    echo "(truncated - full file saved to /tmp/$OUTPUT_FILE)"
else
    echo "Failed to get download URL"
    echo "Full response: $RESPONSE"
fi