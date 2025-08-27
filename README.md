# Document Redaction Service

A serverless document redaction system that automatically removes sensitive information from uploaded documents.

## Features

- **Multi-Format Support**: PDF, DOCX, TXT, CSV, XLSX, PPTX, MD
- **Pattern Detection**: SSN, credit cards, phone numbers, emails, IP addresses, driver's licenses
- **Custom Rules**: User-defined find/replace patterns
- **AI Summaries**: Generate summaries using AWS Bedrock (Claude models)
- **Vector Database**: ChromaDB integration for semantic search and document embeddings
- **Metadata Extraction**: Comprehensive document analysis with export capabilities
- **File Management**: Combine files, batch download, quarantine handling
- **User Isolation**: Secure, isolated storage per user with vector database isolation

## Recent Updates

**2025-08-27**
- **ChromaDB Vector Integration**: Full vector database with semantic search, user isolation, and comprehensive test suite
- **Metadata Export System**: Bulk and individual metadata export with JSON/CSV formats
- **Security Enhancements**: Fixed critical authentication bypass, restricted IAM permissions
- **Claude Code Slash Commands**: `/prep`, `/prep-session`, `/prep-compact` for automated workflows

**2025-08-07**
- Added 9 specialized AI agents for enhanced development support
- Implemented comprehensive agent documentation in CLAUDE.md
- Security improvements and exposed API key removal from git history
- Fixed AI summary browser navigation and metadata encoding issues
- Enhanced download behavior with proper Content-Disposition headers

**2025-07-22**
- Enhanced document combination with LLM-optimized delineation
- Added table of contents with document listing
- Clear document headers with source paths for citation
- Structured separators for vector DB indexing
- Automatic datetime naming: filename_YYYYMMDD_HHMMSS.ext
- Fixed combine files feature - now properly handles URL-encoded document IDs

**2025-07-18**
- Added .md (Markdown) file support and file combination feature

**2025-07-13**
- Fixed file deletion (403 errors) and batch download (404 errors)

**2025-07-12**
- Removed legacy .doc support, improved error handling

## Quick Start

### Prerequisites
- AWS Account with appropriate permissions
- Node.js 18+ and npm
- Python 3.9+
- Terraform (for infrastructure deployment)

### Deployment

1. **Infrastructure Setup**
```bash
cd terraform
terraform init
terraform apply
```

2. **Frontend Deployment**
```bash
cd frontend
npm install
npm run build
./deploy.sh
```

3. **Lambda Functions**
```bash
# Deploy API handler
./build_lambda.sh api
aws lambda update-function-code --function-name redact-api-handler --zip-file fileb://api_lambda.zip

# Deploy document processor
./build_lambda.sh processor
aws lambda update-function-code --function-name document-scrubbing-processor --zip-file fileb://document_processor.zip
```

## Usage

1. Visit https://redact.9thcube.com
2. Sign up with a valid email (gmail.com, outlook.com, yahoo.com, or 9thcube.com)
3. Configure redaction rules
4. Upload documents for processing
5. Download redacted versions

## API Examples

### Upload Document
```bash
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "doc.txt", "content": "'$(base64 -w0 doc.txt)'"}'
```

### Generate AI Summary
```bash
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/ai-summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "DOCUMENT_ID", "summary_type": "standard"}'
```

## Architecture

```
User → CloudFront → S3 (React App)
         ↓
    Cognito Auth
         ↓
    API Gateway
         ↓
   Lambda Functions
         ↓
    S3 Storage (User-Isolated)
```

## Configuration

### Redaction Rules Format
```json
{
  "replacements": [
    {"find": "ACME Corp", "replace": "[COMPANY]"},
    {"find": "John Doe", "replace": "[NAME]"}
  ],
  "case_sensitive": false,
  "patterns": {
    "ssn": true,
    "credit_card": true,
    "phone": true,
    "email": true,
    "ip_address": true,
    "drivers_license": true
  }
}
```

## Security

- JWT-based authentication via AWS Cognito
- User-isolated S3 storage with prefix-based access control
- API rate limiting (10,000 requests/month)
- Automatic quarantine of suspicious files
- No data persistence beyond user sessions

## Monitoring

- CloudWatch Logs: `/aws/lambda/{function-name}`
- API Gateway metrics in CloudWatch
- S3 bucket metrics for storage usage

## Support

For issues or questions, please open an issue in this repository.

## License

Proprietary - All rights reserved