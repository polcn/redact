# Deployment Guide

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0 installed
- IAM permissions for:
  - S3 bucket creation and management
  - Lambda function deployment
  - SQS queue creation (for DLQ)
  - CloudWatch dashboard and alarms
  - IAM role and policy creation
  - Budget management (optional)

## Quick Deploy (Recommended)

```bash
# Navigate to project
cd /home/ec2-user/redact-terraform

# Run automated deployment script
./deploy-improvements.sh
```

This script will:
1. Deploy all infrastructure with Terraform
2. Create CloudWatch dashboard
3. Set up budget alerts (after email update)
4. Upload sample configuration
5. Run validation tests

## Manual Deployment Steps

### Phase 1: Infrastructure Deployment

```bash
# Initialize Terraform
terraform init

# Review deployment plan
terraform plan

# Deploy infrastructure
terraform apply -auto-approve
```

**Deployed Resources:**
- 4 S3 buckets (input, processed, quarantine, config)
- Lambda function with retry logic
- SQS Dead Letter Queue
- CloudWatch log groups
- IAM roles and policies

### Phase 2: Monitoring Setup

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "DocumentRedactionSystem" \
  --dashboard-body file://monitoring-dashboard.json

# Set up budget alerts (update email in budget-notifications.json first!)
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget-alert.json \
  --notifications-with-subscribers file://budget-notifications.json
```

### Phase 3: Configuration Setup

```bash
# Create redaction configuration
cat > config.json << 'EOF'
{
  "replacements": [
    {"find": "ACME Corporation", "replace": "[CLIENT NAME REDACTED]"},
    {"find": "TechnoSoft", "replace": "[CLIENT NAME REDACTED]"},
    {"find": "Confidential", "replace": "[REDACTED]"},
    {"find": "john.doe@example.com", "replace": "[EMAIL REDACTED]"},
    {"find": "555-123-4567", "replace": "[PHONE REDACTED]"}
  ],
  "case_sensitive": false
}
EOF

# Upload to config bucket
CONFIG_BUCKET=$(terraform output -raw config_bucket_name)
aws s3 cp config.json s3://$CONFIG_BUCKET/
```

## Post-Deployment Verification

### 1. Get Resource Information
```bash
terraform output
```

### 2. Test Document Processing
```bash
# Test normal file
echo "Contact ACME Corporation at john.doe@example.com" > test.txt
aws s3 cp test.txt s3://$(terraform output -raw input_bucket_name)/

# Test oversized file (should be quarantined)
dd if=/dev/zero of=large.txt bs=1M count=51
echo "ACME Corporation" >> large.txt
aws s3 cp large.txt s3://$(terraform output -raw input_bucket_name)/

# Wait 30 seconds for processing
sleep 30

# Check results
aws s3 ls s3://$(terraform output -raw processed_bucket_name)/processed/
aws s3 ls s3://$(terraform output -raw quarantine_bucket_name)/quarantine/
```

### 3. Monitor Processing
```bash
# View Lambda logs
aws logs tail /aws/lambda/document-scrubbing-processor --follow

# Check DLQ for failures
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name document-scrubbing-dlq --query QueueUrl --output text) \
  --attribute-names ApproximateNumberOfMessages

# View dashboard
echo "Dashboard URL: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=DocumentRedactionSystem"
```

## Security Features

- **File Validation**: 50MB size limit, restricted file types
- **Configuration Validation**: JSON schema checking
- **Retry Logic**: Exponential backoff for transient failures
- **Dead Letter Queue**: Captures persistent failures
- **Budget Alerts**: Cost control at $10/month
- **Encryption**: AES256 for all S3 data

## Cost Management

### Optimized Monthly Costs:
- S3 storage: $0-2 (free tier)
- Lambda execution: $0-3 (free tier)
- CloudWatch: $0 (free tier)
- SQS: $0 (free tier)
- **Total: $0-5/month** for light usage

### Cost Monitoring:
```bash
# View current costs by tag
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --filter file://cost-filter.json
```

## Troubleshooting

### Check for Errors
```bash
# Recent Lambda errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/document-scrubbing-processor \
  --filter-pattern "ERROR"

# DLQ messages
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name document-scrubbing-dlq --query QueueUrl --output text)
```

### Common Issues
1. **File not processing**: Check file size/type limits
2. **Configuration errors**: Validate config.json format
3. **Permission errors**: Verify IAM policies
4. **High costs**: Review CloudWatch dashboard metrics

## Cleanup

```bash
# Remove all resources
terraform destroy -auto-approve

# Delete CloudWatch dashboard
aws cloudwatch delete-dashboards --dashboard-names DocumentRedactionSystem

# Delete budget (optional)
aws budgets delete-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget-name DocumentRedactionSystemBudget
```

**Warning:** This will permanently delete all data and resources.

## Next Steps

1. Monitor the CloudWatch dashboard regularly
2. Review and adjust redaction rules as needed
3. Set up additional alerts based on usage patterns
4. Consider implementing batch processing for efficiency
5. Add unit tests and CI/CD pipeline