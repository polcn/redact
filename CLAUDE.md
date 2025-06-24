# Redact Project - Quick Reference

## Overview
**AWS Document Redaction System** - Enterprise-grade document scrubbing with React frontend.
- **Frontend**: https://redact.9thcube.com
- **Status**: ✅ Production Complete with UI
- **Cost**: $0-5/month
- **API**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production

## Quick Commands

### Frontend Deployment
```bash
cd frontend
npm install
cp .env.example .env          # Update with Terraform outputs
npm run build
./deploy.sh
```

### Infrastructure
```bash
terraform init
terraform apply               # Deploy all infrastructure
terraform output -json        # Get outputs for frontend config
```

### Testing
```bash
# Frontend local dev
cd frontend && npm start

# Backend logs
aws logs tail /aws/lambda/document-scrubbing-processor --follow
aws logs tail /aws/lambda/redact-api-handler --follow
```

## Architecture
```
React Frontend → Cognito Auth → API Gateway → Lambda
                                      ↓
                              S3 (User Isolated)
                                      ↓
                            Document Processing
```

## Key Features
- **🌐 Web UI**: Drag-drop upload, real-time status, secure downloads
- **🔐 Authentication**: AWS Cognito with invite-only registration  
- **👤 User Isolation**: Each user only sees their files (users/{userId}/*)
- **📁 Multi-Format**: TXT, PDF, DOCX, XLSX → redacted .txt
- **⚙️ Config UI**: Admin panel for redaction rules
- **🔄 Real-time**: Status updates via polling

## Live Resources
```
Frontend:    redact.9thcube.com (CloudFront: EOG2DS78ES8MD)
API:         https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production
Cognito:     us-east-1_4Uv3seGwS (allowed domains: gmail.com, outlook.com, yahoo.com, 9thcube.com)
Buckets:     redact-{input,processed,quarantine,config}-32a4ee51
Lambdas:     document-scrubbing-processor, redact-api-handler, redact-cognito-pre-signup
Frontend S3: redact-frontend-9thcube-12476920
```

## User Flows

### Regular User
1. Sign up at redact.9thcube.com (use allowed email domains)
2. Upload documents via drag-drop
3. View processing status in real-time
4. Download redacted .txt files

**Note**: Email verification temporarily bypassed. For manual user confirmation:
```bash
aws cognito-idp admin-confirm-sign-up --user-pool-id us-east-1_4Uv3seGwS --username EMAIL
aws cognito-idp admin-set-user-password --user-pool-id us-east-1_4Uv3seGwS --username EMAIL --password PASSWORD --permanent
```

### Admin User
1. Access /config page
2. Manage redaction rules
3. Set case sensitivity
4. Changes apply immediately

## Config Format
```json
{
  "replacements": [
    {"find": "ACME Corp", "replace": "[COMPANY]"},
    {"find": "John Smith", "replace": "[NAME]"}
  ],
  "case_sensitive": false
}
```

## Development

### Frontend Environment
```bash
REACT_APP_USER_POOL_ID=us-east-1_4Uv3seGwS
REACT_APP_CLIENT_ID=130fh2g7iqc04oa6d2p55sf61o
REACT_APP_AWS_REGION=us-east-1
REACT_APP_API_URL=https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production
REACT_APP_DOMAIN=redact.9thcube.com
```

### Key Files
- `frontend/src/App.tsx` - Main app router
- `frontend/src/contexts/AuthContext.tsx` - Authentication
- `frontend/src/services/api.ts` - API client
- `api_code/api_handler_v2.py` - Enhanced API with user context
- `lambda_code/lambda_function_v2.py` - Processor with user isolation

## Current Issues & Workarounds

### 🔴 File Upload Failing
The web UI authentication works but file uploads fail. Use direct S3 upload:
```bash
aws s3 cp file.txt s3://redact-input-documents-32a4ee51/
```

### 🟡 Email Verification
Auto-confirm not working. Manually confirm users:
```bash
aws cognito-idp admin-confirm-sign-up --user-pool-id us-east-1_4Uv3seGwS --username EMAIL
```

## Troubleshooting

### Frontend Issues
```bash
# Check CloudFront distribution
aws cloudfront get-distribution --id EOG2DS78ES8MD

# Invalidate cache
aws cloudfront create-invalidation --distribution-id EOG2DS78ES8MD --paths "/*"

# Check frontend deployment
aws s3 ls s3://redact-frontend-9thcube-12476920/
```

### Auth Issues
```bash
# Check Cognito user pool
aws cognito-idp list-users --user-pool-id us-east-1_4Uv3seGwS

# Manually confirm user
aws cognito-idp admin-confirm-sign-up --user-pool-id us-east-1_4Uv3seGwS --username EMAIL

# Set permanent password
aws cognito-idp admin-set-user-password --user-pool-id us-east-1_4Uv3seGwS --username EMAIL --password PASSWORD --permanent

# Check pre-signup Lambda logs
aws logs tail /aws/lambda/redact-cognito-pre-signup --follow
```

### Processing Issues
```bash
# Check specific file
aws s3 ls s3://redact-input-documents-32a4ee51/users/USER_ID/
aws s3 ls s3://redact-processed-documents-32a4ee51/processed/users/USER_ID/
```

## Emergency Commands
```bash
terraform destroy             # Remove all infrastructure
aws s3 rm s3://BUCKET --recursive  # Clear bucket before destroy
```