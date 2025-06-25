#!/bin/bash

# Build script for Lambda function with dependencies
set -e

echo "Building Lambda deployment package..."

# Clean up previous builds
rm -rf lambda_build
rm -f document_processor.zip

# Create build directory
mkdir lambda_build

# Copy source code
cp lambda_code/*.py lambda_build/

# Install dependencies if requirements.txt exists
if [ -f lambda_code/requirements.txt ]; then
    echo "Installing Python dependencies..."
    pip install -r lambda_code/requirements.txt -t lambda_build/
else
    echo "No requirements.txt found, skipping dependency installation"
fi

# Create deployment package
echo "Creating deployment package..."
cd lambda_build
zip -r ../document_processor.zip .
cd ..

# Clean up build directory
rm -rf lambda_build

echo "Lambda deployment package created: document_processor.zip"
echo "Package size: $(du -h document_processor.zip | cut -f1)"