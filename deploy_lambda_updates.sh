#!/bin/bash
set -e

echo "Deploying Lambda function updates..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Deploy API Handler
echo -e "${YELLOW}Updating API Handler Lambda...${NC}"
cd api_code
zip -r ../api_handler.zip api_handler_simple.py
cd ..
aws lambda update-function-code \
    --function-name redact-api-handler \
    --zip-file fileb://api_handler.zip \
    --region us-east-1
rm api_handler.zip
echo -e "${GREEN}✓ API Handler updated${NC}"

# Deploy Document Processor
echo -e "${YELLOW}Updating Document Processor Lambda...${NC}"
cd lambda_code
zip -r ../lambda_processor.zip lambda_function_v2.py requirements.txt
cd ..
aws lambda update-function-code \
    --function-name document-scrubbing-processor \
    --zip-file fileb://lambda_processor.zip \
    --region us-east-1
rm lambda_processor.zip
echo -e "${GREEN}✓ Document Processor updated${NC}"

# Wait for functions to be active
echo -e "${YELLOW}Waiting for functions to be active...${NC}"
aws lambda wait function-active --function-name redact-api-handler --region us-east-1
aws lambda wait function-active --function-name document-scrubbing-processor --region us-east-1
echo -e "${GREEN}✓ Functions are active${NC}"

echo -e "${GREEN}Deployment complete!${NC}"
echo "You can now test the pattern matching functionality."