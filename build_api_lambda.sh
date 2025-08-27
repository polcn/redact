#!/bin/bash

# Build script for API Lambda function
set -e

echo "Building API Lambda deployment package..."

# Clean up previous builds
rm -rf api_build
rm -f api_lambda.zip

# Create build directory
mkdir api_build

# Copy API source code
cp api_code/*.py api_build/

# Install dependencies if requirements.txt exists
if [ -f api_code/requirements.txt ]; then
    echo "Installing Python dependencies..."
    pip install -r api_code/requirements.txt -t api_build/
else
    echo "No requirements.txt found for API, skipping dependency installation"
fi

# Create deployment package
echo "Creating deployment package..."
cd api_build
zip -r ../api_lambda.zip .
cd ..

# Clean up build directory
rm -rf api_build

echo "API Lambda deployment package created: api_lambda.zip"
echo "Package size: $(du -h api_lambda.zip | cut -f1)"
