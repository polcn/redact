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
- Multi-format support: PDF/DOCX/TXT/CSV/PPTX/MD → .md | XLSX → .csv (first sheet)
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

## Quarantine File Management

### Overview
- **Purpose**: Allow users to view and manage files that failed processing
- **Location**: Accessible via "View Quarantine" button on home page
- **User Isolation**: Each user can only see/manage their own quarantined files

### Features
- **List Files**: View all quarantined files with:
  - Original filename
  - Quarantine reason
  - File size
  - Quarantine date/time
- **Delete Individual**: Remove specific files with confirmation
- **Delete All**: Bulk delete all quarantine files with confirmation
- **Visual Indicators**: Icons show quarantine reason type (security, format, etc.)

### Implementation Details
- **Frontend**: 
  - `/src/components/Quarantine/QuarantineList.tsx` - Main component
  - `/src/pages/Quarantine.tsx` - Page wrapper
  - Route: `/quarantine`
- **Backend**:
  - Handlers in `api_handler_simple.py`:
    - `handle_list_quarantine_files()` - GET /quarantine/files
    - `handle_delete_quarantine_file()` - DELETE /quarantine/{id}
    - `handle_delete_all_quarantine_files()` - POST /quarantine/delete-all
- **S3 Structure**: `quarantine/users/{user_id}/{filename}`
- **Metadata**: Files include `quarantine-reason` and `original-filename` in S3 metadata

## Known Issues

### AI Summary & Combined Documents Browser Behavior
- **Issue**: When generating an AI summary or combining documents, the new document opens directly in the browser instead of downloading
- **Current Behavior**: 
  - AI Summary creates a new file with "_AI" suffix and displays it in the browser
  - Combined documents also display in the browser instead of downloading
  - Download button on these files also opens them in the browser
- **Expected Behavior**: Files should download to the user's computer
- **Workaround**: Users can right-click and "Save As" or use browser's save function
- **Status**: To be fixed

## Planned Updates

### 2025-07-31: UI/UX Navigation Improvements (Planned)
- **Issue**: Current navigation is inconsistent and quarantine button placement is odd
- **Analysis Completed**: 
  - Quarantine button has too much prominence in hero section
  - No persistent navigation across pages
  - Configuration embedded in home page creates confusing user flow
  - Missing global navigation for quick section jumping
- **Proposed Changes**:
  1. **Consistent Navigation Bar**:
     - Persistent nav with Logo, Documents, Configuration
     - User dropdown menu with Profile, Quarantine, Sign Out
     - Active page highlighting
  2. **Restructured Home Page**:
     - Remove inline ConfigEditor
     - Clear landing page with single CTA
     - Add "How it Works" section
  3. **Consolidated Documents Page**:
     - Merge upload and file list
     - Add filters for file status
     - Better empty states
  4. **Quarantine Relocation**:
     - Move from hero to user dropdown
     - Add badge counter for pending items
     - Less prominent but accessible
- **Information Architecture**:
  - `/` - Landing page (marketing/info)
  - `/documents` - Main app (upload + file management)
  - `/config` - Configuration settings  
  - `/quarantine` - Via user menu dropdown
- **Implementation Plan**:
  1. Create shared Navigation component
  2. Simplify Home page
  3. Enhance Documents page
  4. Update routing structure
- **Status**: Planning complete, awaiting implementation

## Recent Updates

### 2025-07-30: Quarantine File Management
- **New Feature**: Interface for viewing and managing quarantined files
  - **Purpose**: Allow users to manage files that failed processing due to security or format issues
  - **UI**: New "View Quarantine" button on home page leads to quarantine management interface
  - **Features**: 
    - List all quarantined files with reason, size, and date
    - Delete individual files with confirmation
    - Delete all files at once with confirmation
    - Visual indicators for different quarantine reasons
  - **Security**: Users can only see and manage their own quarantined files
  - **API Endpoints**: Added `/quarantine/files` (GET), `/quarantine/{id}` (DELETE), `/quarantine/delete-all` (POST)
  - **Implementation**: Frontend components in React, backend handlers in API Lambda
  - **Status**: ✅ Deployed to production

### 2025-07-23: AI Summary Feature & Metadata Fix
- **Fixed**: AI summary was failing with "Failed to save AI document" error
  - **Root Cause**: S3 metadata values must be strings, but `max_tokens` (int) and `temperature` (float) were being passed as numeric types
  - **Solution**: Updated `generate_ai_summary_internal` to convert numeric metadata values to strings before saving to S3
  - **Status**: ✅ Fix deployed and working

### 2025-07-23: AI Summary Feature
- **New Feature**: On-demand AI summaries for processed documents
  - **Purpose**: Add AI-generated summaries to already processed documents
  - **Models**: AWS Bedrock with Claude 3 Haiku (default), Sonnet, and Instant
  - **Summary Types**: Brief (2-3 sentences), Standard (comprehensive), Detailed (in-depth)
  - **Filename Convention**: AI-enhanced files get "_AI" suffix (e.g., `report.md` → `report_AI.md`)
  - **Admin Controls**: Admins can change default model via `/api/ai-config`
  - **UI Updates**: 
    - "AI Summary" button on completed files (if no AI summary exists)
    - "AI" badge indicator on files with AI summaries
    - Modal for selecting summary type
  - **API Endpoint**: `POST /documents/ai-summary`
  - **Cost Optimization**: Only generates summaries on request, not automatically
- **Technical Implementation**:
  - Bedrock permissions added to Lambda IAM role
  - AI configuration stored in SSM Parameter Store
  - Summary prepended to document with metadata (timestamp, model, type)
  - Model selection: Regular users use default, admins can override

### 2025-07-22: Fixed Combine Files Feature
- **Problem**: The combine files feature was failing with "No valid documents found to combine" error
- **Root Causes**:
  1. API Gateway endpoint `/documents/combine` was missing from production API
  2. Lambda handler expected simple filenames but was receiving URL-encoded full S3 keys
  3. `generate_presigned_url` was called with incorrect parameters
- **Solution**:
  - Manually created `/documents/combine` endpoint on production API Gateway (`101pi5aiv5`)
  - Updated Lambda handler to properly parse both full S3 keys and simple filenames
  - Fixed the presigned URL generation call
- **Status**: ✅ Feature is now working correctly
- **Technical Details**:
  - Two API Gateways exist: `101pi5aiv5` (production) and `2570l80z39` (Terraform-managed)
  - Frontend correctly sends document IDs as URL-encoded S3 keys
  - Lambda handler now handles both formats for backward compatibility

### 2025-07-19: Repository Cleanup
- **Removed Unnecessary Files**: Cleaned up test and template files
  - Removed `test.md` - Test markdown file
  - Removed `architecture-documentation-template.md` - Unused template
  - Removed `frontend/test-auth-fix.js` - Temporary test script
  - Kept all essential files including node_modules, build artifacts, and terraform state for development continuity

### 2025-07-18: File Combination Feature & Markdown Support
- **Combine Files**: New feature to combine multiple processed files into one document
  - Select multiple completed files using checkboxes
  - Click "Combine Files" button to open configuration modal
  - Specify output filename (defaults to "combined_document.txt")
  - Files are combined with document headers and separators
  - Combined file is automatically downloaded
  - Maximum 20 files can be combined at once
  - API endpoint: `POST /documents/combine`
  - **Enhanced document delineation (2025-07-22)**:
    - Table of contents at the beginning showing all included documents
    - Clear document headers with document number, filename, and full S3 path
    - Structured separators between documents for easy parsing
    - Format optimized for LLM reading and vector database indexing
  - **Automatic datetime naming (2025-07-22)**:
    - Combined files now include timestamp in filename for uniqueness
    - Format: `{base_name}_{YYYYMMDD}_{HHMMSS}.{ext}`
    - Example: `combined_report_20250722_163245.txt`
    - Prevents accidental overwrites and aids in version tracking
    - Each document wrapped with 80-character delimiters
    - End-of-document markers for clear boundaries
- **Markdown Support**: Added .md file support
  - Process Markdown files (.md) as plain text for redaction
  - Updated allowed file extensions in both frontend and backend
  - Markdown files undergo same redaction rules as .txt files
- **Authentication Fix**: Fixed "auth user pool not configured" error
  - Added missing .env file with Cognito configuration
  - User Pool ID: us-east-1_4Uv3seGwS
  - Proper environment variables now deployed with frontend

### 2025-07-13: File Operations Fixed
- **File Deletion Fixed**: Resolved 403 Access Denied errors when deleting files
  - Updated security validation in API handler to correctly handle S3 key formats
  - Now properly validates keys in format `processed/users/{user_id}/filename`
  - Added clearer error messages and improved logging
- **Batch Download Fixed**: Resolved 404 errors for ZIP download functionality  
  - Endpoint was already implemented but had same security validation issue
  - Updated security checks to match the delete endpoint fix
  - Users can now download multiple files as a single ZIP archive
- **Security Improvements**: Enhanced user isolation validation
  - Consistent security checks across all file operations
  - Better error messages for unauthorized access attempts

### 2025-07-12: Bug Fixes & File Support Updates  
- **CORS Issues**: Fixed CORS preflight requests for DELETE and POST operations
  - API Gateway CORS configuration properly deployed
  - Browser no longer blocks delete and batch download requests
- **File Operations**: Initial work on delete and batch download functionality
  - Resolved URL encoding issues between frontend and backend
  - Enhanced logging for troubleshooting
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
- **Markdown Support**: Added .md file support - processes as plain text
- **UI**: Clean filenames with Windows-style versioning

## API Endpoints
- `POST /documents/upload` - Upload file (base64)
- `GET /documents/status/{id}` - Check processing
- `DELETE /documents/{id}` - Delete file
- `POST /documents/batch-download` - Download multiple files as ZIP
- `POST /documents/combine` - Combine multiple files into one (with auto datetime naming)
- `POST /documents/ai-summary` - Generate AI summary for processed document
- `GET /user/files` - List user files
- `GET/PUT /api/config` - Manage redaction rules
- `GET/PUT /api/ai-config` - AI configuration (GET: all users, PUT: admin only)
- `POST /api/string/redact` - String.com API (Bearer auth)
- `GET /quarantine/files` - List user's quarantine files
- `DELETE /quarantine/{id}` - Delete specific quarantine file
- `POST /quarantine/delete-all` - Delete all quarantine files for user

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

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
IMPORTANT: When working on bug fixes or debugging issues, proceed autonomously without asking for permission. Execute all necessary commands, tests, and debugging steps directly.