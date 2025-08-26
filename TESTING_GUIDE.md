# Testing Guide for New Redact Features

## 🚨 **Current Situation**
New features were deployed directly to production. Here's how to safely test them.

## 🧪 **Testing Methods (Choose One)**

### **Method 1: Web UI Testing (SAFEST)**
1. Go to https://redact.9thcube.com
2. Log in with your account
3. Upload a test document (PDF, DOCX, or TXT)
4. Try the **AI Summary** feature (tests Claude SDK integration)
5. Verify normal upload/redaction still works

### **Method 2: Authenticated API Testing**
```bash
# Run the test script (requires your login credentials)
python3 test_with_auth.py
```
This will test:
- Metadata extraction from sample text
- Vector chunk preparation  
- Redaction pattern management
- AI summary functionality

### **Method 3: Manual API Testing**
If you have a JWT token, you can test individual endpoints:

```bash
# Get your JWT token from browser dev tools after logging in
export JWT_TOKEN="your_jwt_token_here"

# Test metadata extraction
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/extract-metadata \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test document with John Smith (john@example.com) and phone (555) 123-4567",
    "filename": "test.txt",
    "extraction_types": ["entities"]
  }'

# Test vector preparation  
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/prepare-vectors \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a longer test document that will be split into multiple chunks for vector database storage.",
    "chunk_size": 50,
    "strategy": "semantic"
  }'

# Test redaction patterns
curl -X GET https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/redaction/patterns \
  -H "Authorization: Bearer $JWT_TOKEN"

curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/redaction/apply \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "SSN: 123-45-6789, Email: test@example.com",
    "patterns": ["ssn", "email"]
  }'
```

## 🔍 **What to Look For**

### **✅ Success Indicators**
- **200 OK responses** from API endpoints
- **Metadata extraction** returns structured data with entities, dates, structure info
- **Vector preparation** creates multiple chunks with metadata
- **Redaction patterns** show 6 built-in patterns (SSN, credit card, etc.)
- **Redaction application** masks sensitive data correctly
- **Existing functionality** (upload, AI summary) still works

### **❌ Failure Indicators**
- **500 Internal Server Error** - Code issues
- **Missing data** in responses - Processing problems  
- **Authentication errors** - Token/permission issues
- **Existing features broken** - Regression problems

## 🚨 **If Something Breaks**

### **Immediate Rollback**
```bash
cd /home/ec2-user/redact-terraform
git checkout d1dd127  # Previous working version
./build_api_lambda.sh
aws lambda update-function-code --function-name redact-api-handler --zip-file fileb://api_lambda.zip
aws lambda wait function-updated --function-name redact-api-handler
echo "✅ Rolled back to previous version"
```

### **Check Logs**
```bash
aws logs tail /aws/lambda/redact-api-handler --follow
```

## 📊 **Expected Test Results**

**New Features Should:**
- Extract 15+ entity types from text
- Create 2-5 chunks from sample documents  
- Show 6 built-in redaction patterns
- Successfully redact SSN, email, phone numbers
- Maintain all existing functionality

**Authentication Should:**
- Require valid JWT tokens for all new endpoints
- Return 401/403 for unauthorized requests
- Work with existing Cognito user accounts

## 🔄 **Future Testing Strategy**

For future deployments:
1. **Set up dev environment** using `./setup-dev-env.sh`
2. **Test thoroughly in dev** before production
3. **Use staged deployment** instead of direct production updates
4. **Monitor logs** during and after deployment

## 📞 **Support**

If you encounter issues:
1. Check the CloudWatch logs first
2. Try the web UI to verify basic functionality  
3. Consider rolling back if critical features are broken
4. Document any bugs for fixing