# Redact Project - Claude Instructions

## Project Overview
**AWS Document Scrubbing System** - Automatically detects and removes client names/logos from uploaded documents using serverless AWS infrastructure.

## Current Status
- ✅ **Infrastructure Deployed**: VPC, S3 buckets, KMS encryption, networking
- 🔄 **Lambda Ready**: Function code written, needs deployment
- 📋 **Fully Documented**: Complete design, architecture, and roadmap

## Quick Commands

### Deploy Lambda Function
```bash
cd redact-terraform
terraform apply -auto-approve
```

### Test Document Processing
```bash
# Upload test document
echo "Confidential data from ACME Corporation" > test.txt
aws s3 cp test.txt s3://redact-input-documents-32a4ee51/

# Check processed results (wait 30 seconds)
aws s3 ls s3://redact-processed-documents-32a4ee51/processed/
```

### Monitor Processing
```bash
# View Lambda logs
aws logs tail /aws/lambda/document-scrubbing-processor --follow

# Check for errors
aws logs filter-log-events --log-group-name /aws/lambda/document-scrubbing-processor --filter-pattern "ERROR"
```

### Get Resource Info
```bash
terraform output
```

## Live AWS Resources
```
Input Bucket:      redact-input-documents-32a4ee51
Processed Bucket:  redact-processed-documents-32a4ee51  
Quarantine Bucket: redact-quarantine-documents-32a4ee51
KMS Key:          d539a81e-b71f-4cd4-a5c3-fd7c20456614
VPC:              vpc-09b9d34d87641d465
```

## Architecture Summary
```
Upload → S3 Input → Lambda → AI Processing → S3 Output/Quarantine
         (KMS encrypted)    (Text/Logo detection)   (Redacted docs)
```

## File Structure
```
redact-terraform/
├── main.tf              # Core infrastructure (VPC, S3, KMS)
├── lambda.tf            # Lambda function and IAM roles  
├── variables.tf         # Configuration parameters
├── outputs.tf           # Resource outputs
├── lambda_code/         # Python processing logic
│   └── lambda_function.py
└── docs/
    ├── README.md        # Project overview
    ├── DESIGN.md        # System design decisions
    ├── ARCHITECTURE.md  # Technical architecture
    ├── DEPLOYMENT.md    # Setup instructions
    ├── STATUS.md        # Current progress
    └── NEXT_STEPS.md    # Implementation roadmap
```

## Security Features
- 🔐 **KMS Encryption**: All data encrypted at rest
- 🏠 **VPC Isolation**: Private networking, no internet access
- 🚫 **Public Access Blocked**: All S3 buckets private
- 🔒 **IAM Least Privilege**: Minimal required permissions
- 📊 **Tagged Resources**: Project=redact for cost tracking

## What It Does
1. **Upload**: Documents uploaded to input bucket
2. **Trigger**: S3 event automatically triggers Lambda
3. **Process**: AI services detect client names/logos
4. **Redact**: Replace sensitive content with [REDACTED]
5. **Output**: Clean documents → processed bucket, sensitive → quarantine

## Development Context for Claude

### Working with this project:
- Infrastructure is **Terraform-managed** - always use `terraform` commands for changes
- All resources are **tagged** with `Project = "redact"` for billing
- Lambda function uses **Python 3.11** runtime
- Processing logic is in `lambda_code/lambda_function.py`

### Common Tasks:
- **Add new file types**: Update `lambda_function.py` processing logic
- **Add client patterns**: Modify `CLIENT_PATTERNS` array in Lambda code
- **Scale resources**: Adjust variables in `variables.tf`
- **Monitor costs**: Filter AWS billing by `Project = "redact"` tag

### Testing Strategy:
- Upload documents with known client names (ACME Corporation, TechnoSoft LLC)
- Verify redaction by downloading processed files
- Check quarantine bucket for sensitive content
- Monitor CloudWatch logs for processing status

### Security Notes:
- All processing happens in **private VPC** - no internet access
- **VPC endpoints** provide secure access to AWS services
- **KMS customer-managed key** encrypts all data
- Lambda has **minimal IAM permissions** - only what's needed

### Cost Optimization:
- Current cost: ~$30-40/month for light usage
- Scaling cost: ~$200-500/month at 1000 documents/day
- All resources tagged for accurate cost tracking
- S3 lifecycle policies can reduce storage costs

### Next Development Phase:
1. Deploy Lambda function (terraform apply)
2. Test with various document types
3. Add PDF/image processing capabilities
4. Implement advanced AI detection
5. Add monitoring dashboards

### Emergency Procedures:
- **Stop processing**: Disable S3 bucket notifications
- **View logs**: CloudWatch Logs for debugging
- **Rollback**: `terraform destroy` removes all resources
- **Backup**: All code in git, infrastructure as code

### Key Files to Modify:
- `lambda_function.py` - Processing logic
- `variables.tf` - Configuration changes
- `main.tf` - Infrastructure changes
- Documentation files for updates

This project demonstrates secure, scalable serverless document processing with comprehensive documentation and infrastructure as code.