# Redact Project - Claude Instructions

## Project Overview
**AWS Document Scrubbing System** - Automatically detects and removes client names/logos from uploaded documents using serverless AWS infrastructure.

## Current Status
- ✅ **Fully Operational**: System deployed and tested
- ✅ **Cost-Optimized**: Reduced from $30-40 to $0-5/month
- ✅ **Processing Working**: Automatic redaction on file upload
- 📋 **Fully Documented**: Updated with cost optimizations

## Quick Commands

### Deploy Lambda Function
```bash
cd redact-terraform
terraform apply -auto-approve
```

### Configure Redaction Rules
```bash
# Create config file
cat > config.json << 'EOF'
{
  "replacements": [
    {"find": "REPLACE_CLIENT_NAME", "replace": "Company X"},
    {"find": "ACME Corporation", "replace": "[REDACTED]"},
    {"find": "Confidential", "replace": "[REDACTED]"}
  ],
  "case_sensitive": false
}
EOF

# Upload config to S3
aws s3 cp config.json s3://redact-config-32a4ee51/
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
Config Bucket:     redact-config-32a4ee51
Lambda Function:   document-scrubbing-processor
```

## Architecture Summary
```
Upload → S3 Input → Lambda → AI Processing → S3 Output/Quarantine
         (AES256 encrypted) (Text/Logo detection)   (Redacted docs)
```

## File Structure
```
redact-terraform/
├── main.tf              # Core infrastructure (S3, lifecycle policies)
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
- 🔐 **AES256 Encryption**: All data encrypted at rest
- 🚫 **Public Access Blocked**: All S3 buckets private
- 🔒 **IAM Least Privilege**: Minimal required permissions
- 📊 **Tagged Resources**: Project=redact for cost tracking
- 💰 **Cost-Optimized**: No VPC/KMS charges, within free tier

## What It Does
1. **Upload**: Documents (.txt, .pdf, .docx, .xlsx) uploaded to input bucket
2. **Config**: Lambda reads redaction rules from config.json in config bucket
3. **Process**: Extract text and remove images from documents
4. **Redact**: Replace configured text patterns with specified replacements
5. **Output**: Clean documents → processed bucket, errors → quarantine

## Configuration System
- **Flexible Rules**: Define find/replace patterns in config.json
- **No Code Changes**: Update redaction rules without redeploying
- **Multi-Format**: Supports text, PDF, DOCX, and XLSX files
- **Image Removal**: Automatically strips images from documents
- **Case Control**: Configure case-sensitive or case-insensitive matching

## Development Context for Claude

### Working with this project:
- Infrastructure is **Terraform-managed** - always use `terraform` commands for changes
- All resources are **tagged** with `Project = "redact"` for billing
- Lambda function uses **Python 3.11** runtime
- Processing logic is in `lambda_code/lambda_function.py`

### Common Tasks:
- **Update redaction rules**: Modify and upload `config.json` to config bucket
- **Add new file types**: Update `lambda_function.py` processing logic
- **Scale resources**: Adjust variables in `variables.tf`
- **Monitor costs**: Filter AWS billing by `Project = "redact"` tag

### Config File Format:
```json
{
  "replacements": [
    {"find": "CLIENT_NAME", "replace": "Company X"},
    {"find": "John Smith", "replace": "[NAME REDACTED]"},
    {"find": "555-123-4567", "replace": "[PHONE REDACTED]"}
  ],
  "case_sensitive": false
}
```

### Testing Strategy:
- Upload documents with known client names (ACME Corporation, TechnoSoft LLC)
- Verify redaction by downloading processed files
- Check quarantine bucket for sensitive content
- Monitor CloudWatch logs for processing status

### Security Notes:
- All data **encrypted at rest** with AWS-managed AES256
- **Public access blocked** on all S3 buckets
- Lambda has **minimal IAM permissions** - only what's needed
- **CloudWatch logging** for audit trails

### Cost Optimization:
- Current cost: **$0-5/month** for light usage (within free tier)
- Previous cost was $30-40/month before optimization
- Removed VPC infrastructure (saved ~$22/month)
- Removed customer KMS key (saved $1/month)
- S3 lifecycle policies automatically reduce storage costs

### Current Capabilities (Enhanced):
1. ✅ Multi-format processing (TXT, PDF, DOCX, XLSX)
2. ✅ Configurable redaction rules via S3 config
3. ✅ Automatic image removal from documents
4. ✅ Structured JSON logging
5. ✅ Error handling with quarantine system

### Emergency Procedures:
- **Stop processing**: Disable S3 bucket notifications
- **View logs**: CloudWatch Logs for debugging
- **Rollback**: `terraform destroy` removes all resources
- **Backup**: All code in git, infrastructure as code

### Key Files to Modify:
- `config.json` in S3 - Redaction rules (no deployment needed)
- `lambda_function.py` - Processing logic
- `variables.tf` - Configuration changes
- `main.tf` - Infrastructure changes
- Documentation files for updates

This project demonstrates secure, scalable serverless document processing with comprehensive documentation and infrastructure as code.