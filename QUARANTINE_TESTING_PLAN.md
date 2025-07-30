# Quarantine File Management - Testing Plan

## Current Status
- ✅ Backend API endpoints implemented and deployed
- ✅ Frontend UI components created and deployed
- ✅ API Gateway endpoints manually configured in production (101pi5aiv5)
- ✅ Lambda function updated with quarantine handlers
- ✅ Documentation updated (README.md and CLAUDE.md)
- ✅ Code pushed to GitHub

## Remaining Tasks

### 1. Test Quarantine File Listing
- **Objective**: Verify users can see their quarantined files
- **Steps**:
  1. Login to https://redact.9thcube.com
  2. Click "View Quarantine" button on home page
  3. Verify the quarantine list loads correctly
  4. Check that file information is displayed (name, reason, size, date)
- **Expected**: Should show any quarantined files for the logged-in user

### 2. Test Individual File Deletion
- **Objective**: Verify users can delete specific quarantine files
- **Steps**:
  1. From quarantine list, click delete button on a specific file
  2. Confirm deletion in the dialog
  3. Verify file is removed from list
  4. Refresh page to ensure deletion persists
- **Expected**: File should be permanently deleted

### 3. Test Delete All Functionality
- **Objective**: Verify bulk delete works correctly
- **Steps**:
  1. Click "Delete All" button
  2. Confirm in the warning dialog
  3. Verify all files are removed
  4. Check S3 bucket to confirm deletion
- **Expected**: All user's quarantine files deleted

### 4. Test User Isolation
- **Objective**: Verify users only see their own files
- **Steps**:
  1. Create test files in quarantine bucket for different users
  2. Login as different users
  3. Verify each user only sees their own files
- **Expected**: Strict user isolation maintained

### 5. Test Error Handling
- **Objective**: Verify graceful error handling
- **Steps**:
  1. Test with network disconnected
  2. Test with expired auth token
  3. Test with malformed requests
- **Expected**: Appropriate error messages displayed

### 6. Create Test Quarantine Files
To properly test, you need quarantine files. Use this AWS CLI command:
```bash
# Create a test quarantine file
aws s3 cp test.txt s3://redact-quarantine-documents-469be391/quarantine/users/YOUR_USER_ID/test-file.txt \
  --metadata quarantine-reason="Unsupported file format",original-filename="test.txt"
```

## Known Issues to Monitor
1. CORS configuration was manually added - may need adjustment
2. Terraform state doesn't reflect manual API Gateway changes
3. Frontend may cache file lists - implement refresh if needed

## Next Session Starting Point
1. Create test quarantine files for testing
2. Run through all test scenarios
3. Fix any issues discovered
4. Consider adding:
   - File download from quarantine (if needed)
   - More detailed quarantine reasons
   - Quarantine file count on home page
   - Email notifications for quarantined files

## Technical Details for Reference
- **Quarantine Bucket**: redact-quarantine-documents-469be391
- **S3 Structure**: quarantine/users/{user_id}/{filename}
- **API Endpoints**:
  - GET https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/quarantine/files
  - DELETE https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/quarantine/{id}
  - POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/quarantine/delete-all
- **Lambda Function**: redact-api-handler
- **Frontend Route**: https://redact.9thcube.com/quarantine