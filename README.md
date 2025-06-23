# Redact - AWS Document Scrubbing System

A secure, automated document processing system that removes client names and logos from uploaded documents using AWS services.

## Architecture

```
Documents → S3 Input → Lambda → AI Processing → S3 Output
                     ↓
              S3 Quarantine (if sensitive)
```

## Security Features

- **KMS Encryption**: All data encrypted at rest
- **Private VPC**: No internet access for processing
- **VPC Endpoints**: Secure AWS service communication
- **Public Access Blocked**: All S3 buckets private
- **IAM Least Privilege**: Minimal required permissions

## Deployed Infrastructure

### S3 Buckets (All KMS Encrypted)
- `redact-input-documents-*` - Upload documents here
- `redact-processed-documents-*` - Scrubbed documents output
- `redact-quarantine-documents-*` - Sensitive content review

### Processing
- Lambda function with Python 3.11 runtime
- AWS Textract for text extraction
- AWS Rekognition for logo detection
- Regex patterns for client name detection

### Networking
- Private VPC with isolated subnets
- VPC endpoints for S3, Textract, Rekognition
- Security groups with minimal access

## Usage

1. Upload documents to input bucket:
   ```bash
   aws s3 cp document.pdf s3://redact-input-documents-32a4ee51/
   ```

2. Processing automatically triggers on upload

3. Check results:
   ```bash
   # Clean documents
   aws s3 ls s3://redact-processed-documents-32a4ee51/
   
   # Quarantined documents
   aws s3 ls s3://redact-quarantine-documents-32a4ee51/
   ```

## Cost Management

All resources tagged with `Project = "redact"` for billing tracking.

## Deployment

```bash
terraform init
terraform plan
terraform apply
```

## File Structure

```
redact-terraform/
├── main.tf              # Core infrastructure (VPC, S3, KMS)
├── lambda.tf            # Lambda function and IAM
├── variables.tf         # Configuration variables
├── outputs.tf           # Resource outputs
├── lambda_code/         # Lambda function source
└── README.md           # This file
```

## Security Patterns Detected

The system automatically detects and redacts:

- Company names with suffixes (Inc, LLC, Corp, etc.)
- Technology company patterns
- Acronym-based company names
- Logos and brand imagery

## Monitoring

- CloudWatch logs for Lambda execution
- S3 access logging
- KMS key usage tracking

## Compliance

- Data encryption in transit and at rest
- Audit trails via CloudTrail
- Network isolation
- Access controls