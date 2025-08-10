# Fix Summary - August 10, 2025

## Issues Resolved Today

### 1. AI Summary Feature - FIXED ✅
**Problem**: "ValidationException: The provided model identifier is invalid"
**Root Cause**: Bedrock model IDs were missing required version suffix
**Solution**: 
- Updated SSM parameter `/redact/ai-config` with correct model IDs
- Changed `anthropic.claude-3-haiku-20240307` → `anthropic.claude-3-haiku-20240307-v1:0`
- Added support for Claude 3.5 Sonnet model

### 2. IAM Permissions - FIXED ✅
**Problem**: "AccessDeniedException: not authorized to perform: bedrock:InvokeModel"
**Root Cause**: Lambda IAM role missing Bedrock permissions
**Solution**:
- Added `bedrock:InvokeModel` permission to `redact-api-lambda-role`
- Granted access to all Claude models (Haiku, Sonnet, Opus, Instant)

### 3. Bucket Configuration Mismatch - FIXED ✅
**Problem**: 500 errors on /api/config and other endpoints
**Root Cause**: Lambda using wrong bucket suffix (469be391 vs 32a4ee51)
**Solution**:
- Updated Lambda environment variables to use correct buckets (32a4ee51)
- Fixed IAM policy to match production bucket names
- Created consistency check script

## Current Status
- ✅ API Health: Operational
- ✅ AI Summary: Working with correct model IDs
- ✅ Configuration: Loading properly
- ✅ User Files: Listing correctly
- ⚠️ File Processing: Upload works but processing status check needs investigation

## Files Created/Modified
- `/redact/ai-config` SSM parameter - Updated with correct model IDs
- `redact-api-lambda-role` IAM policy - Added Bedrock permissions
- Lambda environment variables - Fixed bucket names
- `CLAUDE.md` - Updated documentation
- Test scripts created for validation

## Commands for Future Reference
```bash
# Check Lambda logs for errors
aws logs tail /aws/lambda/redact-api-handler --since 5m --filter-pattern "ERROR"

# Update SSM parameter
aws ssm put-parameter --name "/redact/ai-config" --value '...' --type String --overwrite

# Update Lambda environment
aws lambda update-function-configuration --function-name redact-api-handler --environment Variables={...}

# Test API health
curl https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/health
```

## Outstanding Issues
1. File processing status remains "not_found" after upload
2. Duplicate bucket sets (469be391 and 32a4ee51) - needs cleanup
3. Terraform state doesn't match deployed infrastructure