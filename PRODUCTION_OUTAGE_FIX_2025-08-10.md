# Production Outage Resolution - 2025-08-10

## Issue Summary
**Impact**: Complete production outage at https://redact.9thcube.com with 403 Access Denied errors  
**Duration**: Unknown (discovered during this session)  
**Root Cause**: CloudFront Origin Access Identity (OAI) mismatch with S3 bucket policy

## Problem Details
Users were receiving XML error responses instead of the React application:
```xml
<Error>
  <Code>AccessDenied</Code>
  <Message>Access Denied</Message>
</Error>
```

## Root Cause Analysis
1. **CloudFront Configuration**: Distribution EOG2DS78ES8MD was configured to use OAI `E3TN4DWQ63CI8F`
2. **S3 Bucket Policy**: The bucket `redact-frontend-9thcube-12476920` was configured to allow access from OAI `E1C02P22RP16HQ`
3. **Result**: CloudFront could not access S3 objects due to the OAI mismatch

## Resolution Steps
1. **Identified the Issue**:
   - Checked CloudFront origin configuration
   - Reviewed S3 bucket policy
   - Found OAI mismatch between the two configurations

2. **Applied Fix**:
   - Updated S3 bucket policy to use the correct OAI (`E3TN4DWQ63CI8F`) that CloudFront was configured with
   - Removed the unused duplicate OAI (`E1C02P22RP16HQ`) to prevent future confusion

3. **Cache Invalidation**:
   - Created CloudFront invalidation (ID: I2RS04GQ7IN1F57VI0RJ1DB6Z5) to ensure all edge locations received updated content

## Verification
- Site now returns HTTP 200 status
- React application loads correctly
- HTML content is properly served

## Prevention Measures
1. **Terraform Configuration**: The `frontend.tf` file is correctly configured to create and manage OAI consistently
2. **Deployment Process**: Ensure deployments use Terraform to maintain infrastructure consistency
3. **Monitoring**: Set up CloudWatch alarms for CloudFront 4xx error rates to detect similar issues early

## Technical Details
- **CloudFront Distribution ID**: EOG2DS78ES8MD
- **S3 Bucket**: redact-frontend-9thcube-12476920
- **Correct OAI**: E3TN4DWQ63CI8F
- **Certificate**: ACM certificate for redact.9thcube.com

## Lessons Learned
- Manual infrastructure changes can lead to configuration drift
- Multiple OAIs for the same purpose create confusion
- Always use Infrastructure as Code (Terraform) for production deployments
- Regular infrastructure audits can catch configuration mismatches early