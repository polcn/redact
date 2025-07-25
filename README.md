# Redact - AWS Document Scrubbing System

Production-ready document redaction system with React frontend at https://redact.9thcube.com

## Features
- **Multi-format**: PDF/DOCX/TXT/CSV/PPTX/MD → .md | XLSX → .csv (first sheet)
- **Pattern Detection**: SSN, credit cards, phones, emails, IPs, licenses
- **Link Stripping**: Removes URLs while preserving link text for redaction
- **User Isolation**: Secure file storage per user
- **AI Summaries**: On-demand AI-powered document summaries using AWS Bedrock, OpenAI, or Google Gemini
- **External AI Support**: Web UI for managing OpenAI and Google Gemini API keys
- **File Combination**: Combine multiple processed files into one document
- **Batch Operations**: Download multiple files as ZIP or delete in bulk
- **String.com API**: Content-based redaction rules with rate limiting
- **API Management**: Automated key rotation, usage quotas, monitoring
- **Cost**: $0-5/month serverless architecture (AI summaries extra)

## Architecture
```
React → CloudFront → Cognito Auth → API Gateway → Lambda
                                              ↓
                                      S3 (User Isolated)
                                              ↓
                                    Document Processing
                                              ↓
                              AI Services (Bedrock/OpenAI/Gemini)
```

See [architecture-diagram.mmd](architecture-diagram.mmd) for the complete system diagram and [architecture-diagram-detailed.mmd](architecture-diagram-detailed.mmd) for detailed component interactions.

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate credentials
- Terraform installed
- Node.js and npm installed
- Domain configured in Route 53

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd redact-terraform

# Install dependencies (required after fresh clone)
npm install
cd frontend && npm install && cd ..

# Deploy infrastructure
terraform init
terraform apply

# Deploy frontend
cd frontend
npm run build
./deploy.sh
```

### Build Artifacts
The following files are generated during deployment and not stored in version control:
- `node_modules/` - NPM dependencies
- `frontend/node_modules/` - Frontend dependencies
- `.terraform/` - Terraform providers
- `*.zip` - Lambda deployment packages
- `frontend/build/` - React build output
- `terraform.tfstate*` - Terraform state files (store remotely)
- `.env` files - Environment configurations

Visit https://redact.9thcube.com and sign up with allowed email domains.

## Recent Updates
- **2025-07-22**: Enhanced document combination with LLM-optimized delineation
  - Added table of contents with document listing
  - Clear document headers with source paths for citation
  - Structured separators for vector DB indexing
  - Automatic datetime naming: `filename_YYYYMMDD_HHMMSS.ext`
- **2025-07-22**: Fixed combine files feature - now properly handles URL-encoded document IDs
- **2025-07-18**: Added .md (Markdown) file support and file combination feature
- **2025-07-13**: Fixed file deletion (403 errors) and batch download (404 errors)
- **2025-07-12**: Removed legacy .doc support, improved error handling
- **2025-07-11**: Fixed user isolation - new users no longer see other users' filters
- **2025-07-11**: API rate limiting (10k/month) and automated key rotation (30-day cycle)
- **2025-07-11**: Link stripping - removes URLs while preserving text for redaction
- **2025-07-11**: Email verification now required for new users (security enhancement)
- **2025-07-08**: Fixed AWS Amplify v6 "already signed in" error
- **2025-07-08**: String.com API with content-based rules ("Choice Hotels"→"CH")
- **2025-06-25**: User-isolated configs, PPTX support, clean filenames
- **2025-06-25**: XLSX→CSV conversion for ChatGPT compatibility

## Infrastructure
- **S3 Buckets**: redact-{input,processed,quarantine,config}-32a4ee51
- **Lambda**: document-scrubbing-processor, redact-api-handler, api-key-rotation
- **API**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production
- **Cognito**: us-east-1_4Uv3seGwS
- **Security**: AES256 encryption, IAM least-privilege, user isolation
- **Monitoring**: CloudWatch alarms for API quotas, throttling, and rotation failures

## API Usage
```bash
# Upload document
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "doc.txt", "content": "'$(base64 -w0 doc.txt)'"}'

# String.com API
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact \
  -H "Authorization: Bearer sk_live_SM7WYKBXiEApBTqgOQzPJW03ItzwVCzc3RLWn4JLluw" \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting with Choice Hotels"}'

# Combine multiple files
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/combine \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_ids": ["file1.txt", "file2.txt"], "output_filename": "report"}'
# Returns: {"filename": "report_20250722_163245.txt", "download_url": "..."}

# Generate AI summary
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/ai-summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "processed/users/123/document.md", "summary_type": "standard"}'
# Returns: {"new_filename": "document_AI.md", "download_url": "..."}
```

## Configuration

### Redaction Configuration
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

### AI Summary Feature
- **Models**: 
  - AWS Bedrock: Claude 3/3.5 (Haiku, Sonnet, Opus), Amazon Nova, Meta Llama, Mistral, DeepSeek
  - External AI (with API keys): OpenAI GPT-4/3.5, Google Gemini 1.5/1.0
- **Summary Types**: 
  - Brief: 2-3 sentence summary
  - Standard: Comprehensive summary
  - Detailed: In-depth analysis
- **File Naming**: AI-enhanced files get "_AI" suffix (e.g., `report.md` → `report_AI.md`)
- **Admin Controls**: Change default model via `/api/ai-config` endpoint
- **Cost**: Pay-per-use based on provider pricing

### External AI Providers
- **Web UI**: Config page → External AI Providers section (admin only)
- **Supported Providers**:
  - OpenAI: GPT-4o, GPT-4o Mini, GPT-4 Turbo, GPT-3.5 Turbo
  - Google Gemini: 1.5 Pro, 1.5 Flash, 1.0 Pro
- **Security**: API keys stored encrypted in AWS Systems Manager
- **Setup**: Get API keys from [OpenAI Platform](https://platform.openai.com/api-keys) or [Google AI Studio](https://makersuite.google.com/app/apikey)

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
- `api-rate-limiting.tf` - Usage plans and quotas
- `api-key-rotation.tf` - Automated key management
- `frontend.tf` - CloudFront/Route53
- `cognito.tf` - Authentication
- `lambda_code/` - Processing logic
- `api_code/` - API handlers and rotation
- `frontend/` - React app

For detailed documentation, see CLAUDE.md