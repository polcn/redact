# Redact - AWS Document Scrubbing System

A secure, automated document processing system that removes client names and logos from uploaded documents using AWS services.

## Current Status: Cost-Optimized & Deployed ✅

- **Input Bucket**: `redact-input-documents-32a4ee51`
- **Processed Bucket**: `redact-processed-documents-32a4ee51` 
- **Quarantine Bucket**: `redact-quarantine-documents-32a4ee51`
- **Lambda Function**: `document-scrubbing-processor` (512MB, 60s timeout)
- **Encryption**: AWS-managed AES256 (cost-optimized)

## Architecture

```
Documents → S3 Input → Lambda → Text Processing → S3 Output
                     ↓
              S3 Quarantine (if sensitive)
```

## Security Features (Cost-Optimized)

- **AWS-Managed Encryption**: AES256 for all S3 data (no KMS costs)
- **IAM Security**: Lambda runs with least privilege policies
- **Public Access Blocked**: All S3 buckets private
- **S3 Lifecycle Policies**: Automatic transition to cheaper storage
- **No Network Costs**: Removed VPC to save ~$22/month

## Deployed Infrastructure

### S3 Buckets (AWS-Managed Encryption)
- `redact-input-documents-*` - Upload documents here
- `redact-processed-documents-*` - Scrubbed documents output
- `redact-quarantine-documents-*` - Sensitive content review

**Lifecycle Policies**:
- 30 days → Standard-IA
- 90 days → Glacier
- 365 days → Delete (input/processed)
- 180 days → Delete (quarantine)

### Processing (Optimized for Free Tier)
- Lambda: 512MB memory, 60s timeout
- Python 3.11 runtime
- Text files: Direct regex processing
- PDFs/Images: Quarantined (Textract/Rekognition ready)
- Automatic S3 event triggers

### Cost Savings
- **No VPC**: Saves ~$22/month
- **No KMS**: Saves $1/month
- **Optimized Lambda**: Reduced memory/timeout
- **S3 Lifecycle**: Automatic cost reduction
- **Free Tier Compatible**: $0-5/month for light usage

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

### Monthly Cost Estimate (Optimized)
- **Lambda**: $0-5 (free tier: 1M requests, 400K GB-seconds)
- **S3 Storage**: $0-2 (free tier: 5GB storage, 20K GET, 2K PUT)
- **CloudWatch**: $0 (free tier: 5GB logs)
- **Total**: **$0-5/month** for light usage

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
├── main.tf              # Core infrastructure (S3, lifecycle policies)
├── lambda.tf            # Lambda function and IAM
├── variables.tf         # Configuration variables
├── outputs.tf           # Resource outputs
├── lambda_code/         # Lambda function source
│   └── lambda_function.py
├── document_processor.zip  # Packaged Lambda code
├── terraform.tfstate    # Terraform state
├── CLAUDE.md           # AI assistant instructions
├── STATUS.md           # Current deployment status
├── README.md           # This file
└── new-test.txt        # Test file
```

## Security Patterns Detected

The system automatically detects and redacts:

- Company names with suffixes (Inc, LLC, Corp, etc.)
- Technology company patterns
- Acronym-based company names
- Logos and brand imagery

## Monitoring

- CloudWatch logs for Lambda execution (within free tier)
- S3 event notifications for processing
- Cost monitoring via resource tags

## Compliance

- Data encryption in transit and at rest
- Audit trails via CloudTrail
- IAM least privilege access controls
- S3 bucket policies for security