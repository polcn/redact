# Issues Log - Redact Application

## 2025-08-10: Production Outage - CloudFront Access Denied

### Issue
- **Time**: ~15:00 UTC
- **Impact**: Complete production outage - site returned 403 Forbidden
- **Symptoms**: XML error page with `<Error><Code>AccessDenied</Code>`

### Root Cause
CloudFront Origin Access Identity (OAI) mismatch:
- CloudFront was configured with OAI: `E3TN4DWQ63CI8F`
- S3 bucket policy was configured for OAI: `E1C02P22RP16HQ`

### Resolution
1. Updated S3 bucket policy to use correct OAI
2. Deleted duplicate/unused OAI
3. Invalidated CloudFront cache
4. Verified site accessibility

### Lessons Learned
- Always use Terraform for infrastructure changes to prevent drift
- Set up CloudWatch alarms for high 4xx error rates
- Regular infrastructure audits needed

---

## 2025-08-10: Security Vulnerabilities Fixed

### Issues Identified (via security-auditor agent)
1. **CRITICAL**: CloudWatch logs permissions too broad (wildcard)
2. **CRITICAL**: Missing s3:HeadBucket permission breaking health checks
3. **HIGH**: Poor frontend error handling

### Fixes Applied
1. Restricted CloudWatch logs to specific log groups
2. Added s3:HeadBucket permission to Lambda IAM policies
3. Enhanced frontend error handling with user feedback

---

## 2025-08-09: Upload Pipeline Broken

### Issue
Files uploaded but never processed, stuck in "processing" state

### Root Causes
1. Missing S3 CORS configuration on input bucket
2. Incorrect Lambda IAM permissions (wrong bucket suffix)
3. Wrong environment variables in processor Lambda
4. FormData Content-Type header issues

### Resolution
Complete pipeline fix including CORS, IAM, environment variables, and frontend fixes

---

## 2025-08-08: Authentication Bypass

### Issue
Production API allowed unauthenticated access

### Resolution
- Fixed CORS to restrict to production domain
- Re-enabled authentication on all endpoints
- Added file content validation

---

## 2025-08-07: AI Summary Navigation Issue

### Issue
Browser navigation broken after AI summary generation

### Resolution
- Fixed API response handling
- Corrected Bedrock model IDs
- Updated IAM permissions

---

## Agent Effectiveness Analysis

### Successful Agent Usage (2025-08-10)
- **aws-infrastructure-expert**: Immediately diagnosed and fixed CloudFront OAI issue
- **security-auditor**: Found 11 security issues including 2 critical ones missed manually
- **devops-automation**: Successfully deployed all fixes with proper verification

### Key Learning
Agents should be used proactively for:
- Infrastructure issues → aws-infrastructure-expert
- Security reviews → security-auditor  
- Deployments → devops-automation
- Cost analysis → cost-optimizer

Manual debugging often misses issues that specialized agents catch immediately.