# Deploy .md Extension Fix for ChatGPT Compatibility

## Summary of Changes
We've updated the Lambda function to output files with `.md` extension instead of `.csv` or `.log` to ensure reliable ChatGPT file uploads.

## What Changed
1. **lambda_code/lambda_function_v2.py**:
   - `apply_filename_redaction()` now outputs `.md` extension
   - Updated comments and docstrings to reflect the change
   - All file types (PDF, DOCX, XLSX, TXT) now output as `.md`

2. **Documentation**:
   - Updated CLAUDE.md with the new extension information
   - Created test files and recommendation report
   - Added CHATGPT_EXTENSION_FIX.md documentation

## Deployment Steps

### 1. Package and Deploy Lambda
```bash
cd /home/ec2-user/redact-terraform/lambda_code
./build_lambda.sh
```

### 2. Update Lambda Function
```bash
aws lambda update-function-code \
  --function-name document-scrubbing-processor \
  --zip-file fileb://lambda_deployment.zip
```

### 3. Verify Deployment
```bash
# Check Lambda update status
aws lambda get-function --function-name document-scrubbing-processor --query 'Configuration.LastModified'

# Monitor logs
aws logs tail /aws/lambda/document-scrubbing-processor --follow
```

## Testing

### Test the New Extension
1. Upload a test document through the web interface
2. Wait for processing to complete
3. Download the processed file - it should have `.md` extension
4. Try uploading the `.md` file to ChatGPT - it should work without errors

### Expected Results
- Input: `document.pdf`
- Output: `document.md` (plain text content, no markdown formatting)
- ChatGPT: File uploads successfully

## Benefits
- ✅ Files upload to ChatGPT without errors
- ✅ Extension is appropriate for document content
- ✅ Works with all text editors
- ✅ No user confusion (markdown viewers show plain text correctly)
- ✅ Based on extensive research and testing

## Notes
- The content remains plain text - we're only changing the extension
- Windows line endings (CRLF) are still maintained
- This fixes the ChatGPT upload bug while maintaining all existing functionality