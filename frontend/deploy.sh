#!/bin/bash

# Frontend deployment script

set -e

echo "Building React app..."
npm run build

echo "Getting CloudFront distribution ID and S3 bucket..."
# Frontend is managed outside of terraform, using hardcoded values
BUCKET_NAME="redact-frontend-9thcube-12476920"
DISTRIBUTION_ID="EOG2DS78ES8MD"

if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Could not get S3 bucket name from Terraform outputs"
    exit 1
fi

echo "Deploying to S3 bucket: $BUCKET_NAME"
aws s3 sync build/ s3://$BUCKET_NAME --delete

if [ ! -z "$DISTRIBUTION_ID" ]; then
    echo "Invalidating CloudFront cache..."
    aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"
fi

echo "Deployment complete!"
echo "Frontend URL: https://redact.9thcube.com"