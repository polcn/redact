#!/bin/bash
set -e

echo "Building API Lambda deployment package with dependencies..."

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Using temp directory: $TEMP_DIR"

# Copy Python files
cp api_code/api_handler_simple.py "$TEMP_DIR/"
cp api_code/external_ai_providers.py "$TEMP_DIR/"

# Install dependencies
pip install -r api_code/requirements.txt -t "$TEMP_DIR/" --quiet

# Create the zip file
cd "$TEMP_DIR"
zip -r api_lambda.zip . -q
mv api_lambda.zip ../
cd ..

# Clean up
rm -rf "$TEMP_DIR"

echo "API Lambda package created: api_lambda.zip"
ls -lh api_lambda.zip