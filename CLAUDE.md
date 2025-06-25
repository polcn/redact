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
- **📁 Multi-Format**: TXT, PDF, DOCX, CSV → .md | XLSX → .csv (first sheet only)
- **⚙️ Config UI**: User-configurable redaction rules integrated into home page
- **🔍 Pattern Detection**: Automatic PII detection (SSN, credit cards, phones, emails, IPs, driver's licenses)
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
  "case_sensitive": false,
  "patterns": {
    "ssn": true,
    "credit_card": false,
    "phone": true,
    "email": true,
    "ip_address": false,
    "drivers_license": false
  }
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

### ✅ CRITICAL ISSUE FIXED (2025-06-25)
**Pattern-Based Redaction** - Fixed the global configuration security vulnerability:
- **Previous Issue**: All users shared the same global `config.json` file
- **Fix Implemented**: User-specific configurations at `configs/users/{user_id}/config.json`
- **Security**: Each user now has isolated redaction rules and pattern settings
- **Backward Compatible**: Falls back to global config if user-specific not found
- **Migration**: Global config automatically copied to user-specific on first access
- See GitHub Issue #12 for detailed analysis and implementation

### ✅ Recent Updates (2025-06-25)

#### Session 9
- **Clean Filenames**: Removed UUID prefixes from uploaded files
  - Implemented Windows-style versioning: `file.txt`, `file (1).txt`, `file (2).txt`
  - Much cleaner and user-friendly file management
  - Automatic collision detection and versioning
- **CSV Support**: Added full support for CSV file uploads
  - CSV files are now accepted in upload validation
  - Processed with redaction rules like other text formats
  - Output as `.md` files for ChatGPT compatibility
- **Improved Delete**: Fixed file deletion with new document ID system
  - Document IDs now use encoded S3 keys
  - Proper security validation before deletion
  - Works with both input and processed files
- **File Type Validation**: Resolved "invalid file type" errors
  - Added CSV to allowed extensions in both frontend and backend
  - Improved error messaging for unsupported files

#### Session 8
- **Fixed XLSX Upload to ChatGPT**: Resolved issue where XLSX conversions failed to upload
  - Changed approach: XLSX files now convert to proper CSV format (first sheet only)
  - Added metadata showing sheet count and omitted sheets for multi-sheet workbooks
  - CSV format with proper escaping and quoting for reliable ChatGPT uploads
  - Updated documentation to clarify XLSX limitations

#### Session 7
- **Fixed Multi-File Upload**: Resolved Lambda dependency issues preventing PDF/DOCX/XLSX processing
  - Created `build_lambda.sh` script to properly package Python dependencies
  - Successfully deployed Lambda with pypdf, openpyxl, and python-docx libraries
  - All file types now process correctly in parallel
- **Fixed Output Format**: All files now correctly output as `.md` regardless of input format
  - Modified `apply_filename_redaction()` to always append `.md` extension
  - `document.pdf` → `document.md`, `spreadsheet.xlsx` → `spreadsheet.md`, etc.
- **Fixed ChatGPT Upload Compatibility**: Implemented best solution for ChatGPT's file upload bug
  - Changed output file extension to `.md` after testing multiple alternatives
  - Extensive research confirmed `.md` is explicitly supported by ChatGPT
  - Tested alternatives: `.txt` (fails), `.log` (fails), `.csv` (works but less appropriate)
  - Files contain plain text only - no markdown formatting added
  - Windows compatibility mode with CRLF line endings maintained
  - All processed `.md` files now upload successfully to ChatGPT

#### Session 6
- **Delete Functionality Fix**: Fixed critical issue where file deletion wasn't working
- **API Gateway Enhancement**: Added missing DELETE endpoint for `/documents/{id}`
- **CORS Configuration**: Added proper CORS support for DELETE operations
- **Infrastructure Update**: Deployed new API Gateway configuration with delete support
- **Batch Operations**: Both single file delete and batch delete now fully functional

#### Session 5
- **Pattern Redaction Fix**: Implemented user-specific configuration storage
- **Security Enhancement**: Fixed critical vulnerability where all users shared global config
- **API Updates**: Modified config endpoints to save/load user-specific configurations
- **Lambda Updates**: Updated processor to load config based on file owner's user ID
- **Test Script**: Created `test_pattern_fix.py` to verify pattern matching functionality
- **Backward Compatibility**: System falls back to global config if user-specific not found

#### Session 4
- **Fixed Pattern Checkboxes**: Resolved state management issue where pattern checkboxes weren't maintaining state
- **Enhanced UI**: Added custom checkbox styling with orange theme and visual feedback
- **Comprehensive Testing**: Created TEST_PLAN.md with full test coverage scenarios
- **Test Automation**: Added Puppeteer test script for automated UI testing
- **MCP Verification**: Confirmed all MCP servers (AWS, Cloudflare, Brightdata) are operational
- **Manual Testing**: Created MANUAL_TEST_CHECKLIST.md for quick verification
- **Critical Bug Found**: Discovered pattern redaction not working due to global config issue

#### Session 3
- **Pattern-Based Redaction**: Added automatic PII detection for SSN, credit cards, phones, emails, IPs, driver's licenses
- **Enhanced Config UI**: Updated frontend with pattern toggles for each PII type
- **Backend Support**: Confirmed Lambda already had pattern detection; frontend now exposes this feature
- **Documentation**: Created comprehensive CI/CD setup guide and TODO list
- **Branch Strategy**: Created `develop` branch for staging deployments
- **Testing**: Verified pattern detection works correctly with test documents

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

## Known Issues & Fixes

### ✅ ChatGPT File Upload Compatibility (Fixed 2025-06-25)
**Issue**: Processed files were failing to upload to ChatGPT with "unknown error occurred"

**Root Cause**: ChatGPT has a known bug since May 31, 2025, that prevents `.txt` file uploads.

**Final Solution Implemented**: 
1. **Different extensions by file type**:
   - PDF/DOCX/TXT/CSV → `.md` (markdown format, plain text)
   - XLSX → `.csv` (proper CSV format, first sheet only)
   - Each file type gets the most appropriate format that ChatGPT accepts

2. **XLSX special handling**:
   - Converts only the first worksheet to CSV format
   - Adds header comments showing total sheets and omitted sheet names
   - Proper CSV escaping for values with commas, quotes, or newlines
   - Example header: `# Workbook contains 6 sheets. Showing sheet 1 of 6: 'Sales Data'`

3. **Enhanced compatibility**:
   - Windows line endings (CRLF) by default
   - Pure ASCII text output
   - Tab characters converted to spaces
   - Special UTF-8 characters replaced with ASCII equivalents

**How it works**:
- All file types now upload successfully to ChatGPT
- XLSX limitation documented in output (first sheet only)
- Files open correctly in any text editor
- To disable Windows mode: Set Lambda environment variable `WINDOWS_MODE=false`

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

## CI/CD Pipeline

**Status**: ⚠️ Disabled - See `docs/CI_CD_IMPLEMENTATION_GUIDE.md` for setup instructions.

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