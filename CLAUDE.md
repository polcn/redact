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

## Known Issues
- **Failed to load settings**: Settings may fail to load on initial page visit
- **No file history**: File list shows "No file history found" despite files existing in S3


## External AI Provider Setup

### Via Web UI (Recommended)

1. Navigate to the **Config** page in the web interface
2. Look for the **External AI Providers** section
3. Click **Update API Keys** (admin access required)
4. Enter your API keys:
   - **OpenAI**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
   - **Google Gemini**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
5. Click **Update Keys** to save

### Via AWS CLI

If you prefer command-line setup:

```bash
# Set OpenAI API key:
aws ssm put-parameter --name "/redact/api-keys/openai-api-key" \
  --value "YOUR_OPENAI_API_KEY" \
  --type SecureString \
  --overwrite

# Set Google Gemini API key:
aws ssm put-parameter --name "/redact/api-keys/gemini-api-key" \
  --value "YOUR_GEMINI_API_KEY" \
  --type SecureString \
  --overwrite

# Verify API keys are set (shows first 10 characters only):
aws ssm get-parameter --name "/redact/api-keys/openai-api-key" --with-decryption --query 'Parameter.Value' --output text | head -c 10
aws ssm get-parameter --name "/redact/api-keys/gemini-api-key" --with-decryption --query 'Parameter.Value' --output text | head -c 10
```

**Implementation Details**:
- API keys are stored securely in AWS Systems Manager Parameter Store
- Keys are encrypted at rest using AWS KMS
- Lambda functions have IAM permissions to decrypt and retrieve keys
- External AI providers are automatically available when API keys are configured
- Error handling gracefully falls back to AWS Bedrock models if keys are not set
- Only admins can manage API keys through the UI

## Recent Updates

### 2025-07-25: API Key Management UI & Infrastructure Fixes
- **New Feature**: Web UI for Managing External AI API Keys
  - **Purpose**: Allow admins to configure OpenAI and Gemini API keys through the web interface
  - **Location**: Config page → External AI Providers section
  - **Security**: Keys are stored encrypted, never exposed in UI, admin-only access
  - **UI Features**:
    - Shows configuration status for all users
    - Admin-only "Update API Keys" interface
    - Direct links to OpenAI Platform and Google AI Studio
    - Real-time status updates after key changes
  - **API Endpoints**:
    - `GET /api/external-ai-keys` - Check key status
    - `PUT /api/external-ai-keys` - Update keys (admin only)
- **Fixed**: Configuration Loading Issues
  - **Root Cause**: Lambda functions were pointing to old S3 buckets from previous deployment
  - **Solution**: Updated Lambda environment variables to correct bucket names
  - **Data Migration**: Migrated all user data from old buckets to new ones
- **Infrastructure**: External AI Provider Support
  - Created Terraform configuration for API key storage in SSM
  - Added IAM policies for Lambda access to encrypted keys
  - Deployed external AI provider modules to both Lambda functions

### 2025-07-24: Smart File Naming, Download Fix, Batch AI Summary, Model Selection & UI
- **New Feature**: Smart File Naming with Duplicate Handling
  - **Purpose**: Prevent file overwrites by automatically renaming duplicates
  - **Naming Convention**: Uses Windows-style naming: `file.txt`, `file (1).txt`, `file (2).txt`
  - **Implementation**: 
    - Created `get_unique_filename()` utility function
    - Checks S3 for existing files before saving
    - Automatically appends (1), (2), etc. when duplicates found
  - **Applied To**:
    - Document uploads
    - AI summary generation (_AI files)
    - Combined documents
  - **Status**: ✅ Feature deployed and working
- **Fixed**: Download button was opening files in browser instead of downloading
  - **Root Cause**: S3 presigned URLs weren't forcing download disposition
  - **Solution**: Added `ResponseContentDisposition: attachment` header to all presigned URLs
  - **Status**: ✅ Fix deployed - all files now download properly instead of opening in browser
- **New Feature**: Batch AI Summary for multiple files
  - **Purpose**: Generate AI summaries for multiple files at once
  - **UI**: "Batch AI Summary" button appears when multiple completed files are selected
  - **Functionality**: Processes each file individually, showing progress (e.g., "3/10 files")
  - **Smart**: Skips files that already have AI summaries (_AI suffix)
  - **Status**: ✅ Feature deployed and working
- **New Feature**: AI Model Selection
  - **Purpose**: Allow users to choose which AI model to use for summaries
  - **Available Models**:
    - **Claude Models**: 3 Haiku, 3.5 Haiku, 3 Sonnet, 3.5 Sonnet, 3 Opus
    - **Amazon Nova (Free Tier)**: Nova Micro, Lite, Pro
    - **Meta Llama**: 3.2 1B/3B, 3 8B
    - **Mistral**: 7B, Small
    - **DeepSeek**: R1 (Advanced Reasoning)
    - **OpenAI** (Requires API Key): GPT-4o, GPT-4o Mini, GPT-4 Turbo, GPT-3.5 Turbo
    - **Google Gemini** (Requires API Key): Gemini 1.5 Pro, 1.5 Flash, 1.0 Pro
  - **UI Updates**: 
    - Model dropdown added to AI Summary modal
    - Model dropdown added to Batch AI Summary modal
  - **Backend**: Fixed user role checking bug (was checking 'user_role' instead of 'role' from Cognito)
  - **API**: Updated `/documents/ai-summary` to accept optional 'model' parameter
  - **UI Improvements**: Fixed batch AI summary modal styling with proper borders, spacing, and typography
  - **Status**: ✅ Feature deployed and working

### 2025-07-24: Combined Files Auto-Download Fix
- **Fixed**: Combined files were auto-downloading instead of just appearing in file list
  - **Root Cause**: Lambda function was returning `download_url` in response, causing frontend to auto-download
  - **Solution**: Updated `combine_documents` Lambda handler to NOT return `download_url` in response
  - **Frontend**: Added console logging to track combine operation flow
  - **Status**: ✅ Fix deployed - combined files now appear in list without auto-downloading

### 2025-07-23: AI Summary Feature & Fixes
- **Fixed**: AI summary was failing with "Failed to save AI document" error
  - **Root Cause**: S3 metadata values must be strings, but `max_tokens` (int) and `temperature` (float) were being passed as numeric types
  - **Solution**: Updated `generate_ai_summary_internal` to convert numeric metadata values to strings before saving to S3
  - **Status**: ✅ Fix deployed and working
- **Fixed**: AI summaries and combined documents auto-downloading instead of just appearing in file list
  - **Root Cause**: Code was automatically triggering downloads after creation
  - **Solution**: Removed automatic download behavior; files now just appear in the list
  - **Status**: ✅ Fix deployed - files appear in list without auto-downloading

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
- `GET/PUT /api/external-ai-keys` - External AI API keys (GET: all users see status, PUT: admin only)
- `POST /api/string/redact` - String.com API (Bearer auth)

## String.com API
```bash
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact \
  -H "Authorization: Bearer sk_live_SM7WYKBXiEApBTqgOQzPJW03ItzwVCzc3RLWn4JLluw" \
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

## Claude Code MCP Integration

Claude Code supports Model Context Protocol (MCP) servers to extend functionality. MCP servers provide specialized tools and capabilities.

### Currently Configured MCP Servers

#### 1. AWS Documentation Server
Provides access to AWS service documentation and examples.
- **Command**: `awslabs.aws-documentation-mcp-server`
- **Features**: Search and retrieve AWS documentation, service examples, and best practices

#### 2. AWS CDK Server
Enables AWS CDK (Cloud Development Kit) operations.
- **Command**: `awslabs.cdk-mcp-server`
- **Features**: CDK stack management, synthesis, and deployment operations

#### 3. AWS Core Services Server
Provides tools for core AWS service operations.
- **Command**: `awslabs.core-mcp-server`
- **Features**: EC2, S3, IAM, and other core AWS service interactions

#### 4. AWS Serverless Server
Specialized tools for AWS serverless services.
- **Command**: `awslabs.aws-serverless-mcp-server`
- **Features**: Lambda, API Gateway, DynamoDB, and other serverless service management

#### 5. Playwright Browser Automation
Enables browser automation and web scraping.
- **Command**: `npx @modelcontextprotocol/server-playwright`
- **Features**: Browser automation, web scraping, screenshot capture, form filling

#### 6. BrightData API Server
Provides web data collection capabilities.
- **Command**: `npx @brightdata/mcp-server`
- **Features**: Web scraping, proxy management, data collection
- **Note**: Requires API key configuration

#### 7. Jina AI MCP Tools
Provides web content extraction, search, and fact-checking capabilities.

**Installation & Configuration**:
```bash
# Install globally
npm install -g jina-mcp-tools

# Add to Claude Code with API key
claude mcp add jina npx jina-mcp-tools --env JINA_API_KEY=your-api-key-here

# Check configuration
claude mcp get jina

# Remove if needed
claude mcp remove jina -s local
```

**Features**:
- **Web Reading**: Extract and parse content from any URL
- **Web Search**: Search the internet using Jina's search API
- **Fact Checking**: Verify information against web sources

**API Key**: Get your Jina API key from [jina.ai](https://jina.ai/)

### Managing MCP Servers

```bash
# List all configured servers
claude mcp list

# Add a stdio server
claude mcp add server-name /path/to/server

# Add an SSE server
claude mcp add --transport sse server-name https://example.com/endpoint

# Add an HTTP server
claude mcp add --transport http server-name https://example.com/mcp

# Get server details
claude mcp get server-name

# Remove a server
claude mcp remove server-name
```

### Configuration Scopes
- **local**: Private to you in the current project (default)
- **project**: Shared with all users in the project
- **user**: Available in all your projects

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
IMPORTANT: When working on bug fixes or debugging issues, proceed autonomously without asking for permission. Execute all necessary commands, tests, and debugging steps directly.