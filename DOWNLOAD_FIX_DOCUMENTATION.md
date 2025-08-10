# Presigned URL Download Issue - Root Cause and Fix

## Problem Summary
Users were experiencing "SignatureDoesNotMatch" errors when attempting to download files. Instead of downloading, the browser displayed an XML error page with signature validation failure messages.

## Root Cause Analysis

### 1. Signature Mismatch
The issue occurred due to conflicting Content-Disposition headers:

- **Backend**: Generated presigned URLs with `ResponseContentDisposition` parameter included in the signature
- **Frontend**: Added its own `response-content-disposition` parameter to the URL
- **Result**: Duplicate parameters caused AWS S3 signature validation to fail

### 2. Technical Details

#### Backend Code (api_handler_simple.py)
```python
# Original code inconsistency:
# Line 709 - Generated URL WITHOUT disposition header
generate_presigned_url(PROCESSED_BUCKET, obj['Key'], force_download=False)

# But line 637 and others - Generated WITH disposition header
generate_presigned_url(PROCESSED_BUCKET, key)  # force_download=True by default
```

#### Frontend Code (FileItem.tsx)
```javascript
// Frontend was adding its own disposition parameter
const downloadUrl = file.download_url!.includes('?') 
  ? `${file.download_url}&response-content-disposition=attachment%3B...`
  : `${file.download_url}?response-content-disposition=attachment%3B...`;
```

This created URLs with duplicate parameters:
```
https://s3.amazonaws.com/bucket/key?
  X-Amz-Algorithm=...&
  response-content-disposition=attachment%3B%20filename%3D%22file.pdf%22&  // From backend signature
  X-Amz-Signature=...&
  response-content-disposition=attachment%3B%20filename%3D%22file.pdf%22   // Added by frontend (BREAKS SIGNATURE!)
```

## Solution Implemented

### 1. Backend Changes (api_handler_simple.py)

#### Consistent URL Generation
- Changed line 709 to always use `force_download=True`
- Ensures all download URLs include Content-Disposition in the signature

#### Improved Filename Sanitization
```python
# Added safety checks for filenames in headers
safe_filename = filename.replace('"', '').replace('\n', '').replace('\r', '')
params['ResponseContentDisposition'] = f'attachment; filename="{safe_filename}"'
```

### 2. Frontend Changes (FileItem.tsx)

#### Removed Duplicate Parameter Addition
```javascript
// OLD: Adding duplicate parameter
const downloadUrl = file.download_url! + '&response-content-disposition=...'

// NEW: Use presigned URL directly
link.href = file.download_url!;  // URL already has disposition in signature
```

#### Added Fallback Method
```javascript
link.onerror = () => {
  console.error('Download failed, trying alternative method');
  window.open(file.download_url!, '_blank');  // Fallback to new tab
};
```

## Best Practices for Presigned URLs

### 1. Generation Rules
- **Include all parameters in signature**: Any query parameters that will be used must be included when generating the signature
- **Don't modify URLs client-side**: Once generated, presigned URLs should not be modified
- **Use consistent settings**: All download URLs should use the same disposition settings

### 2. Security Considerations
- **Sanitize filenames**: Remove quotes and control characters from filenames in headers
- **Set appropriate expiration**: Use reasonable expiration times (1 hour for downloads)
- **Validate access**: Ensure users can only generate URLs for their own files

### 3. Error Handling
- **Provide fallbacks**: If download fails, try opening in new tab
- **Log errors**: Track signature mismatches for debugging
- **Clear error messages**: Help users understand when downloads fail

## Testing Checklist

After deployment, verify:
- [ ] Files download with correct filename
- [ ] No XML error pages appear
- [ ] Browser shows download dialog or saves file
- [ ] Large files download successfully
- [ ] Special characters in filenames handled correctly
- [ ] CloudWatch logs show no signature errors

## Deployment Instructions

Run the deployment script:
```bash
./fix_download_issue.sh
```

This will:
1. Build and deploy the frontend
2. Update the API Lambda function
3. Clear CloudFront cache

## Monitoring

Check for issues in CloudWatch Logs:
```bash
aws logs tail /aws/lambda/redact-api-handler --follow --filter-pattern "SignatureDoesNotMatch"
```

## Rollback Plan

If issues persist:
1. Revert the code changes:
   ```bash
   git revert HEAD
   ```
2. Redeploy using the same script
3. Consider temporarily using client-side fetch with blob downloads as workaround