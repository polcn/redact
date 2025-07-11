# Redact - AWS Document Scrubbing System

Production-ready document redaction system with React frontend at https://redact.9thcube.com

## Features
- **Multi-format**: PDF/DOCX/TXT/CSV/PPTX → .md | XLSX → .csv (first sheet)
- **Pattern Detection**: SSN, credit cards, phones, emails, IPs, licenses
- **User Isolation**: Secure file storage per user
- **String.com API**: Content-based redaction rules
- **Cost**: $0-5/month serverless architecture

## Architecture
```
React → CloudFront → Cognito Auth → API Gateway → Lambda
                                              ↓
                                      S3 (User Isolated)
                                              ↓
                                    Document Processing
```

## Quick Start
```bash
# Deploy infrastructure
terraform init && terraform apply

# Deploy frontend
cd frontend && npm install && npm run build && ./deploy.sh
```

Visit https://redact.9thcube.com and sign up with allowed email domains.

## Recent Updates
- **2025-07-11**: Email verification now required for new users (security enhancement)
- **2025-07-08**: Fixed AWS Amplify v6 "already signed in" error
- **2025-07-08**: String.com API with content-based rules ("Choice Hotels"→"CH")
- **2025-06-25**: User-isolated configs, PPTX support, clean filenames
- **2025-06-25**: XLSX→CSV conversion for ChatGPT compatibility

## Infrastructure
- **S3 Buckets**: redact-{input,processed,quarantine,config}-32a4ee51
- **Lambda**: document-scrubbing-processor, redact-api-handler
- **API**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production
- **Cognito**: us-east-1_4Uv3seGwS
- **Security**: AES256 encryption, IAM least-privilege, user isolation

## API Usage
```bash
# Upload document
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "doc.txt", "content": "'$(base64 -w0 doc.txt)'"}'

# String.com API
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting with Choice Hotels"}'
```

## Configuration
```json
{
  "replacements": [
    {"find": "ACME Corp", "replace": "[COMPANY]"},
    {"find": "John Smith", "replace": "[NAME]"}
  ],
  "case_sensitive": false,
  "patterns": {
    "ssn": true,
    "credit_card": true,
    "phone": true,
    "email": true,
    "ip_address": false,
    "drivers_license": false
  }
}
```

## Troubleshooting
```bash
# CloudFront cache
aws cloudfront create-invalidation --distribution-id EOG2DS78ES8MD --paths "/*"

# Manual user confirm
aws cognito-idp admin-confirm-sign-up --user-pool-id us-east-1_4Uv3seGwS --username EMAIL

# Check logs
aws logs tail /aws/lambda/document-scrubbing-processor --follow
```

## Project Structure
- `main.tf` - Core infrastructure
- `lambda.tf` - Document processor
- `api-gateway.tf` - REST API
- `frontend.tf` - CloudFront/Route53
- `cognito.tf` - Authentication
- `lambda_code/` - Processing logic
- `api_code/` - API handlers
- `frontend/` - React app

For detailed documentation, see CLAUDE.md