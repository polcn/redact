# GitHub Issues to Create

The following issues should be created in the GitHub repository to track remaining work:

## Issue #1: Enable CI/CD Pipeline
**Title**: Enable GitHub Actions CI/CD Pipeline  
**Labels**: `enhancement`, `infrastructure`  
**Description**:
The CI/CD pipeline workflows are currently disabled. To enable them:

1. Create required test files:
   - `requirements-test.txt`
   - `tests/test_lambda_function.py`
   - `tests/test_integration.py`
   - `monitoring-dashboard.json`

2. Configure GitHub Secrets:
   - AWS credentials for staging/production
   - Terraform variables

3. Set up GitHub Environments (staging, production)

4. Enable workflow files:
   ```bash
   mv .github/workflows/ci-cd.yml.disabled .github/workflows/ci-cd.yml
   mv .github/workflows/pr-validation.yml.disabled .github/workflows/pr-validation.yml
   ```

See `docs/CI_CD_SETUP.md` for detailed instructions.

## Issue #2: Add Unit and Integration Tests
**Title**: Add comprehensive test suite  
**Labels**: `testing`, `quality`  
**Description**:
Create unit and integration tests for:
- Lambda functions (document processing, API handler)
- Frontend components
- API endpoints
- Pattern-based redaction logic

## Issue #3: Improve Error Handling and User Feedback
**Title**: Enhance error handling and user notifications  
**Labels**: `enhancement`, `ux`  
**Description**:
- Add more descriptive error messages for common failures
- Implement toast notifications for async operations
- Better handling of network errors
- Progress indicators for long-running operations

## Issue #4: Add Support for Additional File Formats
**Title**: Expand supported file formats  
**Labels**: `enhancement`, `feature`  
**Description**:
Consider adding support for:
- RTF (Rich Text Format)
- ODT (OpenDocument Text)
- CSV files
- JSON/XML with structured data

## Issue #5: Implement User Usage Analytics
**Title**: Add usage tracking and analytics  
**Labels**: `enhancement`, `monitoring`  
**Description**:
- Track file processing statistics per user
- Monitor redaction pattern usage
- Create CloudWatch dashboard for usage metrics
- Consider implementing usage quotas

## Issue #6: Add Batch Download as ZIP
**Title**: Implement ZIP download for multiple files  
**Labels**: `enhancement`, `feature`  
**Description**:
When users select multiple files, allow downloading them as a single ZIP file instead of individual downloads.

## Issue #7: Add Dark Mode Support
**Title**: Implement dark mode theme  
**Labels**: `enhancement`, `ux`  
**Description**:
Add a dark mode toggle to the UI with appropriate color scheme adjustments.

## Issue #8: Optimize Lambda Cold Starts
**Title**: Reduce Lambda cold start times  
**Labels**: `performance`, `optimization`  
**Description**:
- Consider using Lambda SnapStart for Java runtime
- Optimize Python imports and dependencies
- Implement Lambda warmup strategy

## Issue #9: Add Export/Import for Redaction Rules
**Title**: Allow users to export/import redaction configurations  
**Labels**: `enhancement`, `feature`  
**Description**:
- Export current configuration as JSON file
- Import configuration from uploaded JSON
- Share configurations between users (with permissions)

## Issue #10: Implement Redaction History/Audit Log
**Title**: Add audit logging for redaction operations  
**Labels**: `enhancement`, `security`, `compliance`  
**Description**:
- Log all redaction operations with timestamp
- Track which rules were applied to which documents
- Allow users to view their redaction history
- Consider compliance requirements (GDPR, HIPAA)

## Issue #11: Implement Automated UI Testing Suite
**Title**: Create comprehensive automated UI tests using Puppeteer  
**Labels**: `testing`, `quality`, `automation`  
**Description**:
Build on the existing `test_pattern_checkboxes.js` to create a full UI test suite:
- Authentication flow testing
- Configuration management tests
- File upload/download verification
- Pattern detection validation
- Cross-browser compatibility tests
- Performance benchmarks
- Accessibility compliance tests

Reference `TEST_PLAN.md` for complete test scenarios.

## Issue #12: FIXED - Pattern-Based Redaction Security Vulnerability
**Title**: Regex pattern matching fails due to global config sharing  
**Labels**: `bug`, `critical`, `backend`, `security`, `fixed`  
**Status**: ✅ FIXED (2025-06-25)

**Description**:
Pattern-based redaction was not functioning because all users shared a single global configuration file, creating both a security vulnerability and functional failure.

**Root Cause:**
The system was using a GLOBAL configuration file (`config.json`) instead of user-specific configs:
1. **Security/Privacy Issue**: All users shared the same redaction configuration
2. **Functionality Issue**: Pattern detection failed due to config conflicts

**Fix Implemented:**
1. ✅ Updated `api_handler_simple.py` to use user-specific configs at `configs/users/{user_id}/config.json`
2. ✅ Modified `handle_get_config()` to load user-specific config with fallback to global
3. ✅ Modified `handle_update_config()` to save user-specific config
4. ✅ Updated `lambda_function_v2.py` to load config based on file owner's user ID
5. ✅ Added automatic migration from global to user-specific config on first access
6. ✅ Maintained backward compatibility with global config fallback

**Code Changes:**
- `api_handler_simple.py`: Lines 555-672 updated for user-specific config handling
- `lambda_function_v2.py`: Lines 153-192 and 285-325 updated for per-user config loading

**Test Verification:**
- Created `test_pattern_fix.py` to verify pattern matching with user isolation
- All PII patterns now correctly redact when enabled
- Each user has isolated configuration

**Security Impact:**
- Users can no longer see or affect each other's redaction rules
- Each user's PII patterns are private and isolated
- No shared state between users

**Priority**: CRITICAL - RESOLVED