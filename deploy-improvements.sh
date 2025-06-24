#!/bin/bash
set -e

echo "🚀 Deploying Document Redaction System Improvements"
echo "=================================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $ACCOUNT_ID"

# 1. Deploy infrastructure updates
echo ""
echo "1️⃣ Deploying infrastructure updates..."
cd /home/ec2-user/redact-terraform
terraform init -upgrade
terraform apply -auto-approve

# 2. Create CloudWatch dashboard
echo ""
echo "2️⃣ Creating CloudWatch dashboard..."
if aws cloudwatch put-dashboard \
    --dashboard-name "DocumentRedactionSystem" \
    --dashboard-body file://monitoring-dashboard.json; then
    echo "✅ Dashboard created successfully"
else
    echo "⚠️  Dashboard creation failed (may already exist)"
fi

# 3. Set up budget alerts
echo ""
echo "3️⃣ Setting up budget alerts..."
echo "⚠️  NOTE: Update the email in budget-notifications.json before running!"
read -p "Have you updated the email address in budget-notifications.json? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if aws budgets create-budget \
        --account-id $ACCOUNT_ID \
        --budget file://budget-alert.json \
        --notifications-with-subscribers file://budget-notifications.json 2>/dev/null; then
        echo "✅ Budget alerts created successfully"
    else
        echo "⚠️  Budget creation failed (may already exist)"
    fi
else
    echo "⏩ Skipping budget alerts setup"
fi

# 4. Create sample configuration
echo ""
echo "4️⃣ Creating sample configuration..."
cat > config.json << 'EOF'
{
  "replacements": [
    {"find": "ACME Corporation", "replace": "[CLIENT NAME REDACTED]"},
    {"find": "TechnoSoft", "replace": "[CLIENT NAME REDACTED]"},
    {"find": "Confidential", "replace": "[REDACTED]"},
    {"find": "Internal Use Only", "replace": "[REDACTED]"},
    {"find": "john.doe@example.com", "replace": "[EMAIL REDACTED]"},
    {"find": "555-123-4567", "replace": "[PHONE REDACTED]"}
  ],
  "case_sensitive": false
}
EOF

# Upload config to S3
CONFIG_BUCKET=$(terraform output -raw config_bucket_name 2>/dev/null || echo "redact-config-32a4ee51")
aws s3 cp config.json s3://$CONFIG_BUCKET/
echo "✅ Configuration uploaded to S3"

# 5. Test the improvements
echo ""
echo "5️⃣ Testing the improvements..."
INPUT_BUCKET=$(terraform output -raw input_bucket_name 2>/dev/null || echo "redact-input-documents-32a4ee51")

# Test file size validation
echo "Creating oversized test file..."
dd if=/dev/zero of=large-test.txt bs=1M count=51 2>/dev/null
echo "ACME Corporation data" >> large-test.txt

echo "Uploading oversized file (should be quarantined)..."
aws s3 cp large-test.txt s3://$INPUT_BUCKET/
rm large-test.txt

# Test normal processing
echo "Creating normal test file..."
cat > test-improvements.txt << 'EOF'
This document contains sensitive information about ACME Corporation.
Contact: john.doe@example.com or call 555-123-4567
Status: Confidential - Internal Use Only

TechnoSoft project details are included below.
EOF

echo "Uploading normal test file..."
aws s3 cp test-improvements.txt s3://$INPUT_BUCKET/
rm test-improvements.txt

echo ""
echo "⏳ Waiting 30 seconds for processing..."
sleep 30

# Check results
echo ""
echo "6️⃣ Checking results..."
PROCESSED_BUCKET=$(terraform output -raw processed_bucket_name 2>/dev/null || echo "redact-processed-documents-32a4ee51")
QUARANTINE_BUCKET=$(terraform output -raw quarantine_bucket_name 2>/dev/null || echo "redact-quarantine-documents-32a4ee51")

echo "Processed files:"
aws s3 ls s3://$PROCESSED_BUCKET/processed/ || echo "No processed files yet"

echo ""
echo "Quarantined files:"
aws s3 ls s3://$QUARANTINE_BUCKET/quarantine/ || echo "No quarantined files"

# Show Lambda logs
echo ""
echo "7️⃣ Recent Lambda logs:"
aws logs tail /aws/lambda/document-scrubbing-processor --since 5m | tail -20

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Monitoring Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=DocumentRedactionSystem"
echo "💰 Budget Alerts: https://console.aws.amazon.com/billing/home#/budgets"
echo "📝 Lambda Logs: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logStream:group=/aws/lambda/document-scrubbing-processor"
echo ""
echo "🔧 Next steps:"
echo "  1. Monitor the dashboard for any errors"
echo "  2. Check if the oversized file was quarantined"
echo "  3. Verify the normal file was processed correctly"
echo "  4. Review and adjust the configuration as needed"