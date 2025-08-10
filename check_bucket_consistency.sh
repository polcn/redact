#!/bin/bash

# Script to check bucket configuration consistency across Lambda functions and IAM policies
# This helps identify configuration mismatches that can cause 500 errors

echo "==========================================="
echo "Redact Infrastructure Consistency Check"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to extract bucket suffix from bucket name
get_suffix() {
    echo "$1" | rev | cut -d'-' -f1 | rev
}

echo "1. CHECKING S3 BUCKETS"
echo "----------------------"
echo "Existing S3 buckets:"
aws s3 ls | grep -E "redact.*documents|redact-config" | sort

echo ""
echo "2. CHECKING LAMBDA CONFIGURATIONS"
echo "----------------------------------"

# Check API Handler Lambda
echo "API Handler Lambda (redact-api-handler):"
API_ENV=$(aws lambda get-function-configuration --function-name redact-api-handler --query 'Environment.Variables' --output json 2>/dev/null)
if [ $? -eq 0 ]; then
    API_INPUT=$(echo "$API_ENV" | jq -r '.INPUT_BUCKET')
    API_SUFFIX=$(get_suffix "$API_INPUT")
    echo "  INPUT_BUCKET: $API_INPUT"
    echo "  PROCESSED_BUCKET: $(echo "$API_ENV" | jq -r '.PROCESSED_BUCKET')"
    echo "  QUARANTINE_BUCKET: $(echo "$API_ENV" | jq -r '.QUARANTINE_BUCKET')"
    echo "  CONFIG_BUCKET: $(echo "$API_ENV" | jq -r '.CONFIG_BUCKET')"
    echo -e "  Bucket suffix: ${GREEN}$API_SUFFIX${NC}"
else
    echo -e "  ${RED}Error: Could not retrieve configuration${NC}"
fi

echo ""
echo "Document Processor Lambda (document-scrubbing-processor):"
PROC_ENV=$(aws lambda get-function-configuration --function-name document-scrubbing-processor --query 'Environment.Variables' --output json 2>/dev/null)
if [ $? -eq 0 ]; then
    PROC_INPUT=$(echo "$PROC_ENV" | jq -r '.INPUT_BUCKET')
    PROC_SUFFIX=$(get_suffix "$PROC_INPUT")
    echo "  INPUT_BUCKET: $PROC_INPUT"
    echo "  OUTPUT_BUCKET: $(echo "$PROC_ENV" | jq -r '.OUTPUT_BUCKET')"
    echo "  QUARANTINE_BUCKET: $(echo "$PROC_ENV" | jq -r '.QUARANTINE_BUCKET')"
    echo "  CONFIG_BUCKET: $(echo "$PROC_ENV" | jq -r '.CONFIG_BUCKET')"
    echo -e "  Bucket suffix: ${GREEN}$PROC_SUFFIX${NC}"
else
    echo -e "  ${RED}Error: Could not retrieve configuration${NC}"
fi

echo ""
echo "3. CHECKING IAM POLICIES"
echo "------------------------"
echo "API Lambda IAM Policy S3 Resources:"
aws iam get-role-policy --role-name redact-api-lambda-role --policy-name redact-api-lambda-policy --query 'PolicyDocument' --output json 2>/dev/null | \
    jq -r '.Statement[] | select(.Resource | type == "array") | .Resource[] | select(contains("s3"))' | \
    grep -E "redact.*documents|redact-config" | head -4

echo ""
echo "4. TERRAFORM STATE"
echo "------------------"
if [ -f terraform.tfstate ]; then
    TF_SUFFIX=$(terraform state show random_id.bucket_suffix 2>/dev/null | grep hex | awk '{print $3}' | tr -d '"')
    if [ -n "$TF_SUFFIX" ]; then
        echo -e "Terraform bucket suffix: ${YELLOW}$TF_SUFFIX${NC}"
    else
        echo "Could not determine Terraform bucket suffix"
    fi
else
    echo "Terraform state file not found in current directory"
fi

echo ""
echo "5. CONSISTENCY CHECK RESULTS"
echo "----------------------------"

# Compare suffixes
if [ "$API_SUFFIX" == "$PROC_SUFFIX" ]; then
    echo -e "${GREEN}✓ Lambda functions use consistent bucket suffix: $API_SUFFIX${NC}"
else
    echo -e "${RED}✗ Lambda functions use DIFFERENT bucket suffixes!${NC}"
    echo -e "  API Handler: $API_SUFFIX"
    echo -e "  Document Processor: $PROC_SUFFIX"
fi

# Check IAM policy alignment
IAM_SUFFIX=$(aws iam get-role-policy --role-name redact-api-lambda-role --policy-name redact-api-lambda-policy --query 'PolicyDocument' --output json 2>/dev/null | \
    jq -r '.Statement[] | select(.Resource | type == "array") | .Resource[] | select(contains("s3"))' | \
    grep -E "redact-input-documents" | head -1 | rev | cut -d'-' -f1 | rev)

if [ "$API_SUFFIX" == "$IAM_SUFFIX" ]; then
    echo -e "${GREEN}✓ IAM policy matches Lambda configuration${NC}"
else
    echo -e "${RED}✗ IAM policy ($IAM_SUFFIX) does NOT match Lambda configuration ($API_SUFFIX)${NC}"
fi

if [ -n "$TF_SUFFIX" ] && [ "$TF_SUFFIX" != "$API_SUFFIX" ]; then
    echo -e "${YELLOW}⚠ Warning: Terraform state ($TF_SUFFIX) differs from deployed configuration ($API_SUFFIX)${NC}"
    echo "  This suggests infrastructure was modified outside of Terraform"
fi

echo ""
echo "==========================================="
echo "Check complete!"
echo "==========================================="