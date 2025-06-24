# Redact Project - Claude Instructions

## Project Overview
**AWS Document Scrubbing System** - Automatically detects and removes client names/logos from uploaded documents using serverless AWS infrastructure.

## Current Status
- ✅ **Enterprise Production Ready**: All features implemented and tested
- ✅ **Cost-Optimized**: Reduced from $30-40 to $0-5/month  
- ✅ **Multi-Channel Processing**: API Gateway + Direct S3 upload
- ✅ **Comprehensive Testing**: 80%+ coverage with CI/CD pipeline
- ✅ **REST API Enabled**: Upload, status checking, health monitoring
- ✅ **Batch Processing**: Multiple file handling with timeout controls
- 📋 **Enterprise Documentation**: Complete operational guides

## Quick Commands

### Deploy Complete System (Recommended)
```bash
cd redact-terraform
./deploy-improvements.sh
```

### Deploy Infrastructure Only
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

#### Option A: REST API (Recommended)
```bash
# Get API URL
API_URL=https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production

# Test health
curl -X GET "$API_URL/health"

# Upload document
echo "Confidential data from ACME Corporation" > test.txt
curl -X POST "$API_URL/documents/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.txt", "content": "'$(base64 -w0 test.txt)'"}'

# Check status (use document_id from upload response)
curl -X GET "$API_URL/documents/status/{document_id}"
```

#### Option B: Direct S3 Upload
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

# Check DLQ for failed messages
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name document-scrubbing-dlq --query QueueUrl --output text) \
  --attribute-names ApproximateNumberOfMessages
```

### Run Tests
```bash
# Run comprehensive test suite
./run-tests.sh

# Run specific tests
python -m pytest tests/test_lambda_function.py -v
python -m pytest tests/test_integration.py -v
```

### Get Resource Info
```bash
terraform output
```

## Live AWS Resources
```
Input Bucket:       redact-input-documents-32a4ee51
Processed Bucket:   redact-processed-documents-32a4ee51  
Quarantine Bucket:  redact-quarantine-documents-32a4ee51
Config Bucket:      redact-config-32a4ee51
Lambda Functions:   document-scrubbing-processor, redact-api-handler
API Gateway:        https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production
Dead Letter Queue:  document-scrubbing-dlq
```

## Architecture Summary
```
External Users → API Gateway → Lambda (Batch) → S3 Storage
                     ↓              ↓               ↓
               CORS/Auth     DLQ + Retry    Lifecycle Policies
                     ↓              ↓               ↓
               CloudWatch ← Monitoring → Budget Alerts

Alternative: Direct S3 Upload → Event Trigger → Lambda Processing
                     (AES256 encrypted)    (Multi-format + validation)
```

## File Structure
```
redact-terraform/
├── main.tf                    # Core infrastructure (S3, lifecycle policies)
├── lambda.tf                  # Document processing Lambda
├── api-gateway.tf             # REST API Gateway and API Lambda
├── variables.tf               # Configuration parameters
├── outputs.tf                 # Resource outputs and API endpoints
├── lambda_code/               # Document processing logic
│   ├── lambda_function.py     # Enhanced with batch processing
│   └── requirements.txt
├── api_code/                  # API Gateway handlers
│   └── api_handler.py         # Upload, status, health endpoints
├── tests/                     # Comprehensive test suite
│   ├── test_lambda_function.py
│   ├── test_integration.py
│   └── __init__.py
├── .github/workflows/         # CI/CD automation
│   ├── ci-cd.yml             # Main pipeline
│   └── pr-validation.yml     # PR validation
├── monitoring-dashboard.json  # CloudWatch configuration
├── budget-alert.json         # Cost control
├── run-tests.sh              # Test automation
├── deploy-improvements.sh     # Deployment automation
├── README.md                 # Project overview
├── DEPLOYMENT.md             # Setup instructions
├── STATUS.md                 # Current progress
├── IMPROVEMENTS.md           # Enhancement summary
├── NEXT_STEPS.md            # Future roadmap
└── CLAUDE.md                # This file
```

## Security Features
- 🔐 **AES256 Encryption**: All data encrypted at rest
- 🚫 **Public Access Blocked**: All S3 buckets private
- 🔒 **IAM Least Privilege**: Minimal required permissions
- 🛡️ **Input Validation**: File size/type restrictions, sanitization
- 🔄 **Retry Logic**: Exponential backoff with DLQ for failures
- 🔍 **Configuration Validation**: JSON schema checking with fallback
- 🌐 **API Authentication**: IAM-based security for REST endpoints
- 📊 **Tagged Resources**: Project=redact for cost tracking
- 💰 **Cost-Optimized**: No VPC/KMS charges, within free tier

## What It Does
1. **Upload**: Documents via REST API or direct S3 upload (.txt, .pdf, .docx, .xlsx)
2. **Validate**: File size (50MB limit), type checking, and input sanitization
3. **Process**: Batch processing with retry logic and timeout controls
4. **Config**: Lambda reads redaction rules from config.json in config bucket
5. **Redact**: Replace configured text patterns and remove images from documents
6. **Output**: Clean documents → processed bucket, errors → quarantine bucket
7. **Monitor**: Real-time status via API endpoints and CloudWatch dashboard

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

### Current Capabilities (Enterprise-Ready):
1. ✅ **Multi-format Processing**: TXT, PDF, DOCX, XLSX with image removal
2. ✅ **REST API Gateway**: Upload, status checking, health monitoring
3. ✅ **Batch Processing**: Multiple files with timeout controls
4. ✅ **Comprehensive Testing**: 80%+ coverage with CI/CD pipeline
5. ✅ **Security Hardened**: Input validation, retry logic, DLQ monitoring
6. ✅ **Production Monitoring**: CloudWatch dashboard and budget alerts
7. ✅ **Configurable Rules**: S3-based redaction config with validation
8. ✅ **Cost Optimized**: $0-5/month (down from $30-40/month)

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

This project demonstrates a production-ready, enterprise-grade serverless document processing system with comprehensive testing, monitoring, REST API integration, and cost optimization. The system is fully operational and ready for production workloads.