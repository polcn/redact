# Upload Debugging Guide

## What's Been Fixed

### 1. Backend (Lambda) ✅
- Authentication now works correctly with API Gateway Cognito authorizer
- File validation warns but doesn't block uploads
- IAM permissions fixed for all S3 buckets
- CORS headers properly set to `https://redact.9thcube.com`
- Direct Lambda invocation confirms backend is working

### 2. API Gateway ✅
- All OPTIONS methods updated with restricted CORS origin
- Changes deployed to production stage
- Authentication properly enforced (401 for unauthorized requests)

### 3. Frontend ✅
- Enhanced debug logging added to track upload flow
- Deployed to CloudFront with cache invalidation

## How to Debug Upload Issues

### 1. Open Browser Developer Console
Press F12 or right-click → Inspect → Console tab

### 2. Try Uploading a Small Text File
Create a test.txt file with simple content

### 3. Look for These Console Messages

```javascript
// Expected flow:
"uploadFile: Starting upload for: test.txt Size: 13"
"Interceptor: Fetching auth session for request to: /documents/upload"
"Interceptor: Added auth token to request"
"Request config: {url: '/documents/upload', method: 'post', ...}"
"uploadFile: File read complete, converting to base64"
"uploadFile: Base64 length: 16"
"uploadFile: Making API call to /documents/upload"
"Response received: {url: '/documents/upload', status: 202, ...}"
"uploadFile: Success! {document_id: '...', status: 'processing'}"
```

### 4. Common Issues to Check

#### A. Network Error / CORS Issue
If you see:
```
"Network error - no response received. Possible CORS issue or network failure."
```
- Check if origin is `https://redact.9thcube.com` (not http://)
- Clear browser cache and cookies
- Try incognito/private mode

#### B. Authentication Issue
If you see:
```
"Interceptor: No ID token found in session"
```
- Log out and log back in
- Check if Cognito session expired
- Clear site data and re-authenticate

#### C. API Endpoint Issue
If requests aren't reaching the API:
- Check Network tab for failed requests
- Look for preflight OPTIONS requests
- Verify API URL is correct: `https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production`

### 5. Network Tab Analysis
1. Filter by XHR/Fetch requests
2. Look for `/documents/upload` request
3. Check:
   - Request Headers (Authorization, Origin, Content-Type)
   - Response Headers (Access-Control-Allow-Origin)
   - Response Status (202 = success, 401 = auth, 500 = server error)

### 6. Test Direct API Call
Open Console and run:
```javascript
// This will test if auth is working
fetch('https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/user/files', {
  headers: {
    'Authorization': 'Bearer ' + (await AWS.config.credentials.idToken)
  }
}).then(r => r.json()).then(console.log)
```

## Current Status
- Backend: ✅ Working (confirmed via direct Lambda test)
- API Gateway: ✅ Configured correctly
- Frontend: ✅ Debug logging deployed
- CORS: ✅ Restricted to production domain
- Auth: ✅ Enforced by API Gateway

## Next Steps
1. User needs to check browser console for specific error
2. Share console output to identify exact failure point
3. Most likely issues:
   - Browser cache needs clearing
   - Auth token expired
   - Network/firewall blocking requests