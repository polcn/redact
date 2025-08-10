# Critical Bucket Configuration Mismatch Fix
**Date**: 2025-08-10  
**Issue**: 500 Internal Server Error - Lambda IAM permission mismatch  
**Resolution**: ✅ FIXED - API Lambda environment variables updated

## Problem Summary
The Redact application was experiencing 500 errors due to a configuration mismatch:
- **API Lambda** environment variables pointed to OLD buckets (suffix: `469be391`)
- **IAM Policy** only granted access to NEW buckets (suffix: `32a4ee51`)
- **Document Processor Lambda** correctly used NEW buckets (suffix: `32a4ee51`)

This mismatch prevented the API Lambda from accessing S3 buckets, causing all API calls to fail.

## Root Cause Analysis

### Infrastructure State Discovery
1. **Two sets of S3 buckets exist**:
   - OLD: `*-469be391` (created 2025-07-18)
   - NEW: `*-32a4ee51` (created 2025-06-23)

2. **Configuration Status Before Fix**:
   | Component | Bucket Suffix | Status |
   |-----------|--------------|--------|
   | Document Processor Lambda | 32a4ee51 | ✅ Correct |
   | API Handler Lambda | 469be391 | ❌ Wrong |
   | IAM Policy | 32a4ee51 | ✅ Correct |
   | Terraform State | 469be391 | ⚠️ Out of sync |

3. **Impact**: API Lambda couldn't access S3 buckets → AccessDenied errors → 500 responses

## Solution Implemented

### 1. Updated API Lambda Environment Variables
```bash
aws lambda update-function-configuration \
  --function-name redact-api-handler \
  --environment "Variables={
    INPUT_BUCKET=redact-input-documents-32a4ee51,
    PROCESSED_BUCKET=redact-processed-documents-32a4ee51,
    QUARANTINE_BUCKET=redact-quarantine-documents-32a4ee51,
    CONFIG_BUCKET=redact-config-32a4ee51
  }"
```

### 2. Configuration After Fix
| Component | Bucket Suffix | Status |
|-----------|--------------|--------|
| Document Processor Lambda | 32a4ee51 | ✅ Correct |
| API Handler Lambda | 32a4ee51 | ✅ Fixed |
| IAM Policy | 32a4ee51 | ✅ Correct |
| Terraform State | 469be391 | ⚠️ Needs sync |

### 3. Verification
- API health endpoint: `200 OK` ✅
- Both Lambda functions now use consistent bucket configuration
- IAM policies properly aligned with Lambda configurations

## Created Monitoring Script
A new script `/home/ec2-user/redact-terraform/check_bucket_consistency.sh` was created to:
- Check S3 bucket existence
- Verify Lambda environment variables
- Validate IAM policy resources
- Compare Terraform state
- Report configuration consistency

Run it anytime with:
```bash
./check_bucket_consistency.sh
```

## Remaining Tasks

### 1. Terraform State Reconciliation
The Terraform state still references the old bucket suffix (`469be391`). Options:
- **Option A**: Import existing resources with correct suffix
- **Option B**: Update Terraform state to match reality
- **Option C**: Migrate data and destroy old buckets

### 2. Clean Up Old Buckets
Once confirmed safe, remove old buckets:
```bash
# Verify no critical data in old buckets first!
aws s3 rb s3://redact-input-documents-469be391 --force
aws s3 rb s3://redact-processed-documents-469be391 --force
aws s3 rb s3://redact-quarantine-documents-469be391 --force
aws s3 rb s3://redact-config-469be391 --force
```

### 3. Update Terraform Configuration
To prevent future drift, consider:
1. Using Terraform import to align state with reality
2. Setting up Terraform Cloud for state management
3. Implementing drift detection in CI/CD pipeline

## Lessons Learned
1. **Always verify bucket suffixes** match across all components
2. **Check IAM policies** when debugging Lambda permission errors
3. **Use configuration validation scripts** to catch mismatches early
4. **Maintain Terraform state** alignment with actual infrastructure

## Monitoring Recommendations
1. Set up CloudWatch alarms for Lambda errors
2. Implement configuration drift detection
3. Add integration tests that verify S3 access
4. Regular infrastructure consistency audits

## AWS Best Practices Applied
- ✅ Principle of least privilege in IAM policies
- ✅ Environment-specific resource naming with random suffixes
- ✅ Separation of concerns between Lambda functions
- ✅ Proper error handling and monitoring
- ⚠️ Need to improve infrastructure-as-code practices

## Cost Optimization Note
Currently maintaining duplicate bucket sets doubles storage costs. After verifying data migration, remove old buckets to optimize costs.