#!/bin/bash

# Build script for API Lambda function
set -e

echo "Building API Lambda deployment package..."

# Clean up previous builds
rm -rf api_build
rm -f api_lambda.zip

# Create build directory
mkdir api_build

# Copy API handler code
cp api_code/api_handler_simple.py api_build/

# No dependencies needed for API handler (uses boto3 which is in Lambda runtime)

# Create deployment package
echo "Creating deployment package..."
cd api_build
zip -r ../api_lambda.zip .
cd ..

# Clean up build directory
rm -rf api_build

echo "API Lambda deployment package created: api_lambda.zip"
echo "Package size: $(du -h api_lambda.zip | cut -f1)"