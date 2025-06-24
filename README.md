# Redact - AWS Document Scrubbing System

A secure, automated document processing system that removes client names and logos from uploaded documents using AWS services.

## Current Status: Production-Ready with Enhanced Security ✅

- **Input Bucket**: `redact-input-documents-32a4ee51`
- **Processed Bucket**: `redact-processed-documents-32a4ee51` 
- **Quarantine Bucket**: `redact-quarantine-documents-32a4ee51`
- **Config Bucket**: `redact-config-32a4ee51`
- **Lambda Function**: `document-scrubbing-processor` (512MB, 60s timeout)
- **Supported Formats**: TXT, PDF, DOCX, XLSX with image removal
- **Configuration**: Flexible S3-based redaction rules

## Architecture

```
Documents → S3 Input → Lambda → Multi-Format Processing → S3 Output
(.txt/.pdf/.docx/.xlsx)  ↓        (Text + Image Removal)
                    S3 Config → Redaction Rules
                         ↓
                  S3 Quarantine (if errors)
```

## Security Features (Production-Hardened)

- **AWS-Managed Encryption**: AES256 for all S3 data (no KMS costs)
- **IAM Security**: Lambda runs with least privilege policies
- **Public Access Blocked**: All S3 buckets private
- **S3 Lifecycle Policies**: Automatic transition to cheaper storage
- **Input Validation**: File size limits (50MB) and type restrictions
- **Configuration Validation**: JSON schema checking with fallback
- **Dead Letter Queue**: Captures and alerts on failed processing
- **Retry Logic**: Exponential backoff for transient failures

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

### Enhanced Processing
- Lambda: 512MB memory, 60s timeout
- Python 3.11 runtime with document processing libraries
- **Multi-Format Support**: TXT, PDF, DOCX, XLSX
- **Image Removal**: Automatic stripping from PDFs/DOCX
- **Configurable Redaction**: S3-based rules (no code changes needed)
- **Structured Logging**: JSON format to CloudWatch
- **Error Handling**: Retry logic with exponential backoff
- **Monitoring**: CloudWatch dashboard and budget alerts
- Automatic S3 event triggers

### Cost Savings
- **No VPC**: Saves ~$22/month
- **No KMS**: Saves $1/month
- **Optimized Lambda**: Reduced memory/timeout
- **S3 Lifecycle**: Automatic cost reduction
- **Free Tier Compatible**: $0-5/month for light usage

## Usage

1. **Configure redaction rules** (optional - defaults provided):
   ```bash
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
   aws s3 cp config.json s3://redact-config-32a4ee51/
   ```

2. **Upload documents** (supports TXT, PDF, DOCX, XLSX):
   ```bash
   aws s3 cp document.pdf s3://redact-input-documents-32a4ee51/
   ```

3. **Check results** (processing triggers automatically):
   ```bash
   # Clean documents
   aws s3 ls s3://redact-processed-documents-32a4ee51/processed/
   
   # Error quarantine
   aws s3 ls s3://redact-quarantine-documents-32a4ee51/quarantine/
   ```

## Cost Management

### Monthly Cost Estimate (Optimized)
- **Lambda**: $0-5 (free tier: 1M requests, 400K GB-seconds)
- **S3 Storage**: $0-2 (free tier: 5GB storage, 20K GET, 2K PUT)
- **CloudWatch**: $0 (free tier: 5GB logs)
- **Total**: **$0-5/month** for light usage

All resources tagged with `Project = "redact"` for billing tracking.

## Deployment

### Quick Deploy (Recommended)
```bash
cd /home/ec2-user/redact-terraform
./deploy-improvements.sh
```

### Manual Deploy
```bash
terraform init
terraform plan
terraform apply

# Set up monitoring
aws cloudwatch put-dashboard \
  --dashboard-name "DocumentRedactionSystem" \
  --dashboard-body file://monitoring-dashboard.json

# Configure budget alerts (update email first)
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget-alert.json \
  --notifications-with-subscribers file://budget-notifications.json
```

## File Structure

```
redact-terraform/
├── main.tf                    # Core infrastructure (S3, lifecycle policies)
├── lambda.tf                  # Lambda function, IAM, and DLQ
├── variables.tf               # Configuration variables
├── outputs.tf                 # Resource outputs
├── lambda_code/               # Lambda function source
│   ├── lambda_function.py     # Enhanced with validation & retry logic
│   └── requirements.txt       # Python dependencies
├── monitoring-dashboard.json  # CloudWatch dashboard config
├── budget-alert.json          # AWS Budget configuration
├── budget-notifications.json  # Budget alert settings
├── deploy-improvements.sh     # Deployment automation script
├── CLAUDE.md                  # AI assistant instructions
├── STATUS.md                  # Current deployment status
├── IMPROVEMENTS.md            # Recent enhancements summary
├── NEXT_STEPS.md             # Prioritized roadmap
└── README.md                  # This file
```

## Redaction Capabilities

The system supports configurable redaction via `config.json`:

- **Text Replacement**: Find/replace specific patterns
- **Case Control**: Sensitive or insensitive matching
- **Image Removal**: Automatic stripping from PDF/DOCX files
- **Multi-Format**: TXT, PDF, DOCX, XLSX processing
- **No Downtime**: Update rules without redeployment

## Monitoring & Alerts

- **CloudWatch Dashboard**: Real-time metrics and error tracking
- **Budget Alerts**: Notifications at 50%, 80%, 100% of $10 threshold
- **DLQ Monitoring**: Alerts on processing failures
- **Success Rate Tracking**: Target >99% processing success
- **Structured Logging**: JSON format for easy querying
- **Cost Tracking**: All resources tagged with `Project = "redact"`

## Compliance

- Data encryption in transit and at rest
- Audit trails via CloudTrail
- IAM least privilege access controls
- S3 bucket policies for security