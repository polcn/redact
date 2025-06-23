# Deployment Guide

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0 installed
- IAM permissions for:
  - S3 bucket creation and management
  - KMS key creation and management
  - Lambda function deployment
  - VPC and networking resources
  - IAM role and policy creation

## Quick Deploy

```bash
# Clone or navigate to project
cd redact-terraform

# Initialize Terraform
terraform init

# Review deployment plan
terraform plan

# Deploy infrastructure
terraform apply -auto-approve
```

## Post-Deployment

1. **Get bucket names:**
   ```bash
   terraform output
   ```

2. **Test the system:**
   ```bash
   # Upload a test document
   echo "ACME Corporation confidential data" > test.txt
   aws s3 cp test.txt s3://$(terraform output -raw input_bucket_name)/
   
   # Check processing results (wait ~30 seconds)
   aws s3 ls s3://$(terraform output -raw processed_bucket_name)/processed/
   ```

3. **Monitor processing:**
   ```bash
   # View Lambda logs
   aws logs tail /aws/lambda/document-scrubbing-processor --follow
   ```

## Costs

Estimated monthly costs (light usage):
- S3 storage: $1-5
- Lambda execution: $1-3  
- KMS operations: $1-2
- VPC/Networking: $20-30
- **Total: ~$25-40/month**

## Security Verification

```bash
# Verify bucket encryption
aws s3api get-bucket-encryption --bucket $(terraform output -raw input_bucket_name)

# Check VPC isolation
aws ec2 describe-vpcs --vpc-ids $(terraform output -raw vpc_id)

# Verify KMS key
aws kms describe-key --key-id $(terraform output -raw kms_key_id)
```

## Cleanup

```bash
# Remove all resources
terraform destroy -auto-approve
```

**Warning:** This will permanently delete all data and resources.