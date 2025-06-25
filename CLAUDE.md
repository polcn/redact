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
- **⚙️ Config UI**: User-configurable redaction rules integrated into home page
- **🔄 Real-time**: Status updates via polling
- **📤 Multi-File Upload**: Upload multiple files at once with progress tracking
- **🗑️ File Management**: Delete files, batch operations, multi-select

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
2. Land on Home page with welcome message and config section
3. Configure redaction rules directly on the home page
4. Click "Upload Documents" to proceed to document upload
5. Upload documents via drag-drop or file selection (supports multiple files)
6. View processing status in real-time
7. Manage files: download, delete, or batch operations
8. Download redacted .txt files individually or in batch

**Note**: Email verification temporarily bypassed. For manual user confirmation:
```bash
aws cognito-idp admin-confirm-sign-up --user-pool-id us-east-1_4Uv3seGwS --username EMAIL
aws cognito-idp admin-set-user-password --user-pool-id us-east-1_4Uv3seGwS --username EMAIL --password PASSWORD --permanent
```

### All Users
1. Home page is now the default landing page with integrated config
2. All authenticated users can manage redaction rules
3. Set case sensitivity toggle directly on home page
4. Changes apply immediately to their documents
5. Example rules button available for quick setup

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
- `frontend/src/pages/Home.tsx` - Landing page with integrated config
- `frontend/src/contexts/AuthContext.tsx` - Authentication
- `frontend/src/services/api.ts` - API client
- `api_code/api_handler_simple.py` - Current API handler (simplified for Lambda compatibility)
- `lambda_code/lambda_function_v2.py` - Processor with user isolation

## Implementation Notes

### ✅ Recent Updates (2025-06-25)

#### Session 2
- **Home Page**: Created new landing page with hero section and integrated config
- **Improved Navigation**: Updated routing to make home page the default landing
- **Better User Flow**: Home → Dashboard navigation with clear CTAs
- **Documentation**: Updated all docs to reflect new home page flow

#### Session 1
- **File Management**: Complete implementation of multi-file upload, delete, and batch operations
- **API Enhancement**: Added DELETE endpoint for file removal
- **UI Improvements**: Added checkboxes, batch selection, and progress tracking
- **Better UX**: Confirmation dialogs, real-time updates, error handling

### ✅ Previous Updates (2025-06-24)
- **Anthropic Design**: Complete UI redesign with clean, minimalist aesthetic
- **Home Page First**: New home page with hero section and integrated config
- **User Access**: All users can configure their own redaction rules
- **Improved UX**: Clear flow from config → upload with navigation buttons
- **Example Rules**: Added quick-start button with sample redaction patterns
- **File Upload**: Working - using simplified API handler
- **Email Auto-Confirm**: Working - enabled for allowed domains
- **CORS**: Fully configured for all endpoints

### Design System
- **Colors**: Clean whites (#FFFFFF, #F7F7F7) with orange accent (#CC785C)
- **Typography**: System font stack with responsive sizing using clamp()
- **Components**: Minimalist buttons, subtle borders, smooth transitions
- **Layout**: 1200px max-width container, consistent spacing scale

### API Handler
Currently using `api_handler_simple.py` for the API Lambda function. This simplified version:
- Works with Cognito authorizer without external JWT libraries
- Extracts user context from API Gateway authorizer claims
- Handles all endpoints with proper user isolation
- Compatible with Lambda Python 3.11 runtime

### Authentication Flow
- Users sign up with allowed email domains (gmail.com, outlook.com, yahoo.com, 9thcube.com)
- Auto-confirm is enabled via pre-signup Lambda
- API Gateway uses Cognito authorizer for all protected endpoints
- Frontend includes JWT token in Authorization header

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /documents/upload | Upload single file (base64) |
| GET | /documents/status/{id} | Check file processing status |
| DELETE | /documents/{id} | Delete file from all buckets |
| GET | /user/files | List all user files |
| GET | /api/config | Get redaction configuration |
| PUT | /api/config | Update redaction configuration |

## File Management Features

### Multi-File Upload
- Drag and drop or click to select multiple files
- Individual progress tracking for each file
- Validation for file type and size (50MB max)
- Sequential processing to avoid overwhelming the system

### File Operations
- **Delete**: Remove single files with confirmation
- **Batch Delete**: Select multiple files and delete at once
- **Batch Download**: Download multiple completed files
- **Select All**: Quick selection of all files

### User Interface
- Checkbox selection for batch operations
- Real-time status updates
- Confirmation dialogs for destructive actions
- Progress indicators for uploads and operations

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

## CI/CD Pipeline (Currently Disabled)

**Status**: ⚠️ GitHub Actions workflows are currently disabled to prevent failure notifications.

### Required Setup for CI/CD:
1. **Missing Files**:
   - `requirements-test.txt` - Test dependencies
   - `tests/test_lambda_function.py` - Unit tests
   - `tests/test_integration.py` - Integration tests
   - `monitoring-dashboard.json` - CloudWatch dashboard config

2. **GitHub Configuration**:
   - AWS credentials secrets (AWS_ACCESS_KEY_ID_STAGING, AWS_SECRET_ACCESS_KEY_STAGING, etc.)
   - GitHub environments (staging, production)
   - Create `develop` branch for staging deployments

3. **To Re-enable**:
   ```bash
   mv .github/workflows/ci-cd.yml.disabled .github/workflows/ci-cd.yml
   mv .github/workflows/pr-validation.yml.disabled .github/workflows/pr-validation.yml
   ```

See GitHub Issue #[TBD] for full CI/CD implementation tracking.

## MCP Servers Configuration

Claude Code has been configured with the following MCP (Model Context Protocol) servers for enhanced functionality:

### Available MCP Servers
1. **AWS Documentation** - Access AWS service documentation
2. **AWS CDK** - AWS CDK utilities and helpers
3. **AWS Core** - Core AWS operations and services
4. **AWS Serverless** - Serverless framework support
5. **Puppeteer** - Browser automation capabilities
6. **Bright Data** - Web scraping and data collection (API key configured)

### Setup
MCP servers are configured in `~/.claude/settings.json` and will start automatically with new Claude Code sessions.

To manually start Claude with MCP servers:
```bash
./start-claude-with-mcps.sh
```

### MCP Server Management
```bash
claude mcp list              # List configured MCP servers
claude mcp get <server-name> # Get details about a specific server
```