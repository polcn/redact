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

## Issue #12: CRITICAL - Pattern-Based Redaction Not Working
**Title**: Regex pattern matching fails for all PII types  
**Labels**: `bug`, `critical`, `backend`, `security`  
**Description**:
Pattern-based redaction is not functioning despite checkboxes being enabled. Testing shows that none of the PII patterns are being detected or redacted.

**Root Cause Identified:**
The system is using a GLOBAL configuration file (`config.json`) instead of user-specific configs. This creates two critical issues:
1. **Security/Privacy Issue**: All users share the same redaction configuration
2. **Functionality Issue**: Pattern detection may not work correctly due to config conflicts

**Code Analysis:**
- `api_handler_simple.py` saves/loads config from global `config.json` (lines 559-639)
- `lambda_function_v2.py` loads config from global `config.json` (lines 153-169)
- No user isolation for configurations

**Failed patterns tested:**
- SSN (various formats)
- Phone numbers (multiple formats)
- Email addresses
- Driver's license numbers

**Required Fix:**
1. Implement user-specific configuration storage (e.g., `configs/users/{userId}/config.json`)
2. Update API handler to save/load user-specific configs
3. Update Lambda function to load config based on file owner's user ID
4. Ensure proper user isolation for security

**Test case:**
```
Input text:
SSN: 123-45-6789
Phone: (555) 123-4567
Email: test@example.com
DL: D1234567

Expected: All should be redacted when patterns enabled
Actual: None are redacted
```

**Priority**: CRITICAL - Core feature not working + security vulnerability