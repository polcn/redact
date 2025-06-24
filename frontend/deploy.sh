#!/bin/bash

# Frontend deployment script

set -e

echo "Building React app..."
npm run build

echo "Getting CloudFront distribution ID and S3 bucket..."
BUCKET_NAME=$(cd .. && terraform output -raw frontend_bucket_name 2>/dev/null || echo "")
DISTRIBUTION_ID=$(cd .. && terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")

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