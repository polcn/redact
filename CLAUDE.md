# Redact Project - Quick Reference

**Production URL**: https://redact.9thcube.com | **API**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production

## Quick Deploy
```bash
# Infrastructure
terraform init && terraform apply

# Frontend  
cd frontend && npm install && npm run build && ./deploy.sh
```

## Architecture
```
React → Cognito → API Gateway → Lambda → S3 (User Isolated)
```

## Key Features
- Multi-format support: PDF/DOCX/TXT/CSV/PPTX → .md | XLSX → .csv (first sheet)
- User-isolated file storage with real-time processing
- Pattern detection: SSN, credit cards, phones, emails, IPs, licenses
- String.com API: `POST /api/string/redact` with Bearer auth
- Cost: $0-5/month serverless

## Resources
- **Cognito**: us-east-1_4Uv3seGwS (gmail.com, outlook.com, yahoo.com, 9thcube.com)
- **Buckets**: redact-{input,processed,quarantine,config}-32a4ee51
- **CloudFront**: EOG2DS78ES8MD

## Config Format
```json
{
  "replacements": [{"find": "ACME", "replace": "[COMPANY]"}],
  "case_sensitive": false,
  "patterns": {"ssn": true, "credit_card": true}
}
```

## Recent Updates

### 2025-07-12: Bug Fixes & File Support Updates  
- **CORS Issues**: Fixed CORS preflight requests for DELETE and POST operations
  - API Gateway CORS configuration properly deployed
  - Browser no longer blocks delete and batch download requests
- **File Operations**: Partial fixes for delete and batch download functionality
  - Resolved URL encoding issues between frontend and backend
  - Enhanced logging for troubleshooting
  - ⚠️ Delete and ZIP download still experiencing issues - requires further investigation
- **Legacy .doc File Handling**: Removed support for legacy .doc format
  - Moved stuck .doc files to quarantine bucket
  - Updated upload validation to reject .doc files with clear error message
  - Only .docx format supported (along with txt, pdf, xlsx, xls, csv, pptx, ppt)
- **Error Handling**: Improved error messages for unsupported file types

### 2025-07-11: Security & Infrastructure Updates
- **User Isolation Fix**: Fixed critical security issue where new users could see other users' filters
  - Removed global config fallback that was exposing data between users
  - Each user now gets a clean, empty configuration on first use
  - Deleted legacy global config files from S3
- **API Rate Limiting**: Implemented AWS API Gateway Usage Plans
  - 10,000 requests/month quota, 100 req/sec rate limit
  - CloudWatch alarms at 80% quota usage and high 4XX errors
- **API Key Rotation**: Automated monthly rotation with 7-day grace period
  - EventBridge scheduled rotation every 30 days
  - Old keys remain valid during grace period for smooth transitions
  - Rotation tracking in Parameter Store
- **Link Stripping**: URLs removed while preserving link text for redaction
  - HTML: `<a href="url">Choice Hotels</a>` → `CH`
  - Markdown: `[Choice Hotels](url)` → `CH`
  - Prevents information leakage through URLs
- **CSV Processing**: Fixed normalize_text function error

### 2025-07-08: Authentication Fix
- Fixed "There is already a signed in user" error with AWS Amplify v6
- Auto-signs out existing users before new sign-in
- Maintains concurrent login support from multiple devices

### 2025-06-25: Security & Features
- **Security Fix**: User-isolated configs at `configs/users/{user_id}/config.json`
- **String.com API**: Content-based rules ("Choice Hotels"→"CH", "Cronos"→"CR")
- **File Support**: Added PPTX, fixed XLSX→CSV conversion for ChatGPT
- **UI**: Clean filenames with Windows-style versioning

## API Endpoints
- `POST /documents/upload` - Upload file (base64)
- `GET /documents/status/{id}` - Check processing
- `DELETE /documents/{id}` - Delete file
- `GET /user/files` - List user files
- `GET/PUT /api/config` - Manage redaction rules
- `POST /api/string/redact` - String.com API (Bearer auth)

## String.com API
```bash
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting with Choice Hotels and Cronos"}'
# Returns: {"redacted_text": "Meeting with CH and CR", "replacements_made": 2}
```

## API Key Management
```bash
# View current API key (first 50 chars)
aws ssm get-parameter --name /redact/api-keys/string-prod --with-decryption --query 'Parameter.Value' --output text | head -c 50

# Manually rotate API key
aws lambda invoke --function-name redact-api-key-rotation /tmp/output.json

# Check rotation status
aws ssm get-parameter --name /redact/api-keys/last-rotation --query 'Parameter.Value' --output text | jq

# Monitor API usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=document-redaction-api Name=Stage,Value=production \
  --statistics Sum \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400
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

## Key Files
- `api_code/api_handler_simple.py` - API Lambda
- `lambda_code/lambda_function_v2.py` - Document processor
- `frontend/src/contexts/AuthContext.tsx` - Auth management