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

### 2025-07-11: Link Stripping & Security Enhancements
- **Email Verification**: Now required for new user registrations (AUTO_CONFIRM = false)
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