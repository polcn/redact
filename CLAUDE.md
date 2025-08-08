# Redact Project - AI Assistant Context

**Production**: https://redact.9thcube.com | **API**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production

## Architecture
React → Cognito → API Gateway → Lambda → S3 (User-isolated storage)

## Core Features
- **File Processing**: PDF/DOCX/TXT/CSV/PPTX/MD → redacted output
- **Pattern Detection**: SSN, credit cards, phones, emails, IPs, licenses  
- **AI Summaries**: AWS Bedrock integration (Claude models)
- **User Isolation**: Each user's files stored separately in S3
- **Quarantine**: Failed files manageable via UI

## Key Resources
- **Cognito Pool**: us-east-1_4Uv3seGwS
- **S3 Buckets**: redact-{input,processed,quarantine,config}-documents-32a4ee51  
- **CloudFront**: EOG2DS78ES8MD
- **Lambda Functions**: document-scrubbing-processor, redact-api-handler

## Development Commands
```bash
# Deploy frontend
cd frontend && npm run build && ./deploy.sh

# Deploy API Lambda
./build_lambda.sh api && aws lambda update-function-code --function-name redact-api-handler --zip-file fileb://api_lambda.zip

# Deploy processor Lambda  
./build_lambda.sh processor && aws lambda update-function-code --function-name document-scrubbing-processor --zip-file fileb://document_processor.zip

# CloudFront cache clear
aws cloudfront create-invalidation --distribution-id EOG2DS78ES8MD --paths "/*"
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /documents/upload | Upload file (base64) |
| GET | /documents/status/{id} | Check processing status |
| DELETE | /documents/{id} | Delete file |
| POST | /documents/batch-download | Download multiple as ZIP |
| POST | /documents/combine | Combine multiple files |
| POST | /documents/ai-summary | Generate AI summary |
| GET | /user/files | List user's files |
| GET/PUT | /api/config | Manage redaction rules |
| GET | /quarantine/files | List quarantine files |
| DELETE | /quarantine/{id} | Delete quarantine file |

## Project Structure
```
/
├── api_code/               # API Lambda handler
│   └── api_handler_simple.py
├── lambda_code/            # Document processor
│   └── lambda_function_v2.py
├── frontend/               # React application
│   ├── src/
│   └── build/             # Deployed to S3
└── terraform/             # Infrastructure as code
```

## Recent Fixes (2025-08-08)
- ✅ CORS configuration restricted to production domain only
- ✅ Authentication bypass in production removed  
- ✅ File content validation with magic bytes added (warns but allows)
- ✅ Path traversal protection implemented
- ✅ IAM permissions fixed for correct bucket suffixes (32a4ee51)
- ✅ CONFIG_BUCKET environment variable corrected
- ⚠️ Frontend upload issue identified (requests not reaching Lambda)

## Recent Fixes (2025-08-07)
- ✅ AI summary browser navigation issue resolved
- ✅ Exposed API key removed from git history
- ✅ Download behavior fixed with Content-Disposition headers
- ✅ Bedrock model IDs and IAM permissions corrected

## Testing & Debugging
- Lambda logs: `/aws/lambda/{function-name}`
- Test users: Use gmail.com, outlook.com, yahoo.com, or 9thcube.com emails
- File size limit: 10MB
- Supported formats: PDF, DOCX, TXT, CSV, XLSX, PPTX, MD

## Security Notes
- User isolation enforced at S3 prefix level
- Cognito JWT required for all API calls
- API rate limiting: 10,000 req/month, 100 req/sec
- Never commit API keys or secrets to repository

## Specialized AI Agents
Use these agents for targeted assistance with specific aspects of the codebase:

### Code Quality & Review
- **`code-reviewer`**: Code review, security checks, AWS best practices, performance optimization
- **`testing-qa-specialist`**: Unit/integration/e2e testing, test coverage, mock strategies

### Security & Compliance  
- **`security-auditor`**: IAM policies, authentication, S3 isolation, vulnerability assessment

### AWS & Infrastructure
- **`aws-infrastructure-expert`**: Lambda optimization, API Gateway, S3, CloudFront, Terraform
- **`cost-optimizer`**: AWS cost analysis, resource right-sizing, savings recommendations
- **`devops-automation`**: CI/CD pipelines, GitHub Actions, deployment automation
- **`bedrock-ai-specialist`**: AWS Bedrock integration, AI model configuration, prompt engineering

### Application Development
- **`python-lambda-specialist`**: Lambda functions, document processing, PII detection
- **`frontend-ux-specialist`**: React/TypeScript, AWS Amplify, accessibility, performance

**Usage**: When working on specific areas, invoke the relevant agent for expert guidance.
Example: Use `security-auditor` before deployments, `cost-optimizer` for monthly reviews.

## Code Review Findings (2025-08-07)
See `CODE_REVIEW_FINDINGS.md` for comprehensive security audit results including:
- 4 critical security vulnerabilities requiring immediate fixes
- High priority performance and architectural improvements
- Detailed remediation code examples and action plan