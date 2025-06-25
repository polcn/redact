# Redact System Test Plan

## Overview
This comprehensive test plan covers all aspects of the Redact document processing system, including frontend UI, backend processing, pattern detection, and integrations.

## Test Environment
- **Frontend URL**: https://redact.9thcube.com
- **API Endpoint**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production
- **Test Email Domains**: gmail.com, outlook.com, yahoo.com, 9thcube.com

## 1. Frontend UI Tests

### 1.1 Authentication Flow
- [ ] Sign up with allowed email domain
- [ ] Sign up with disallowed domain (should fail)
- [ ] Login with valid credentials
- [ ] Logout functionality
- [ ] Password reset flow
- [ ] Session persistence (refresh page)

### 1.2 Home Page
- [ ] Hero section displays correctly
- [ ] Configuration section loads on home page
- [ ] Navigation buttons work (Upload Documents)
- [ ] Responsive design on mobile/tablet/desktop

### 1.3 Configuration Management
- [ ] Load existing configuration
- [ ] Add new redaction rules
- [ ] Edit existing rules
- [ ] Delete rules
- [ ] Add example rules button
- [ ] Case sensitivity toggle
- [ ] Save configuration successfully
- [ ] Error handling for invalid config

### 1.4 Pattern Detection Checkboxes (FIXED)
- [ ] SSN checkbox toggles correctly
- [ ] Credit card checkbox toggles correctly
- [ ] Phone number checkbox toggles correctly
- [ ] Email checkbox toggles correctly
- [ ] IP address checkbox toggles correctly
- [ ] Driver's license checkbox toggles correctly
- [ ] Changes persist after save
- [ ] Checkboxes maintain state on page reload

### 1.5 Document Upload
- [ ] Single file upload
- [ ] Multiple file upload
- [ ] Drag and drop functionality
- [ ] File type validation (TXT, PDF, DOCX, XLSX)
- [ ] File size validation (50MB limit)
- [ ] Upload progress indicators
- [ ] Error handling for failed uploads

### 1.6 File Management
- [ ] View all uploaded files
- [ ] Real-time status updates
- [ ] Download completed files
- [ ] Delete single file
- [ ] Select multiple files (checkboxes)
- [ ] Batch delete operation
- [ ] Batch download operation
- [ ] Select all functionality

## 2. Backend Processing Tests

### 2.1 API Endpoints
- [ ] GET /health - Health check
- [ ] POST /documents/upload - File upload
- [ ] GET /documents/status/{id} - Status check
- [ ] DELETE /documents/{id} - File deletion
- [ ] GET /user/files - List user files
- [ ] GET /api/config - Get configuration
- [ ] PUT /api/config - Update configuration

### 2.2 Document Processing
- [ ] TXT file processing
- [ ] PDF file processing
- [ ] DOCX file processing
- [ ] XLSX file processing
- [ ] Large file handling (near 50MB)
- [ ] Concurrent file processing
- [ ] Error quarantine for malformed files

### 2.3 User Isolation
- [ ] User A cannot see User B's files
- [ ] User A cannot access User B's config
- [ ] S3 paths properly isolated by user ID
- [ ] API responses filtered by user context

## 3. Pattern Detection Tests

### 3.1 Test Document Content
Create a test document with the following content:

```text
Test Document for Pattern Detection

Personal Information:
Name: John Doe
SSN: 123-45-6789
Alternative SSN: 987 65 4321
Compact SSN: 111223333

Financial Information:
Credit Card (Visa): 4532-1234-5678-9012
Credit Card (MC): 5412-3456-7890-1234
Credit Card (Amex): 3782-822463-10005

Contact Information:
Phone: (555) 123-4567
Alt Phone: 555.987.6543
International: +1-415-555-0123
Email: john.doe@example.com
Work Email: jdoe@company.org

Network Information:
IP Address: 192.168.1.100
IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334

Government IDs:
Driver's License (CA): D1234567
Driver's License (NY): 123-456-789

Custom Rules Test:
Company Name: ACME Corporation
Project: Confidential Project Alpha
Client: Jane Smith at jane@client.com
```

### 3.2 Pattern Detection Verification
Test each pattern individually:

- [ ] **SSN Pattern**: Enable only SSN, verify all formats are redacted
- [ ] **Credit Card**: Enable only credit cards, verify all formats are redacted
- [ ] **Phone Numbers**: Enable only phones, verify all formats are redacted
- [ ] **Email Addresses**: Enable only emails, verify all are redacted
- [ ] **IP Addresses**: Enable only IPs, verify IPv4/IPv6 are redacted
- [ ] **Driver's License**: Enable only DL, verify various formats are redacted

### 3.3 Combined Pattern Tests
- [ ] Enable all patterns, verify comprehensive redaction
- [ ] Disable all patterns, verify only custom rules apply
- [ ] Mix of patterns and custom rules

### 3.4 Custom Rules Tests
- [ ] Case-sensitive matching
- [ ] Case-insensitive matching
- [ ] Multiple word phrases
- [ ] Special characters in find/replace

## 4. Integration Tests

### 4.1 End-to-End Workflows
- [ ] New user signup → config → upload → download
- [ ] Existing user login → modify config → upload → verify redaction
- [ ] Batch upload → monitor status → batch download
- [ ] Config change → immediate effect on next upload

### 4.2 Performance Tests
- [ ] Upload 10 files simultaneously
- [ ] Process 50MB file
- [ ] 100 redaction rules performance
- [ ] API response times < 2 seconds

### 4.3 Error Scenarios
- [ ] Network disconnection during upload
- [ ] Invalid file format upload
- [ ] Corrupted file upload
- [ ] API rate limiting
- [ ] S3 bucket unavailable (simulated)

## 5. Security Tests

### 5.1 Authentication & Authorization
- [ ] JWT token validation
- [ ] Expired token handling
- [ ] Invalid token rejection
- [ ] CORS policy enforcement
- [ ] SQL injection attempts (config)
- [ ] XSS attempts (rule names)

### 5.2 Data Protection
- [ ] HTTPS enforcement
- [ ] S3 encryption verification
- [ ] No sensitive data in logs
- [ ] Secure file URLs (presigned, time-limited)

## 6. Browser Compatibility
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

## 7. Accessibility Tests
- [ ] Keyboard navigation
- [ ] Screen reader compatibility
- [ ] Color contrast ratios
- [ ] Focus indicators
- [ ] Alt text for images
- [ ] Form labels

## 8. Automated Testing with Puppeteer

### 8.1 Setup Puppeteer Test
```javascript
const puppeteer = require('puppeteer');

async function testPatternCheckboxes() {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  // Navigate to the app
  await page.goto('https://redact.9thcube.com');
  
  // Login (implement login flow)
  // ...
  
  // Navigate to config
  await page.waitForSelector('.pattern-checkboxes');
  
  // Test SSN checkbox
  const ssnCheckbox = await page.$('input[type="checkbox"][name="ssn"]');
  await ssnCheckbox.click();
  
  // Verify state
  const isChecked = await page.$eval('input[type="checkbox"][name="ssn"]', el => el.checked);
  console.assert(isChecked === true, 'SSN checkbox should be checked');
  
  // Save configuration
  await page.click('button:contains("Save Configuration")');
  
  // Reload and verify persistence
  await page.reload();
  const isStillChecked = await page.$eval('input[type="checkbox"][name="ssn"]', el => el.checked);
  console.assert(isStillChecked === true, 'SSN checkbox should remain checked after reload');
  
  await browser.close();
}
```

## 9. MCP Server Verification

### 9.1 AWS MCP Servers
- [ ] AWS Documentation server accessible
- [ ] AWS CDK server functional
- [ ] AWS Core operations working
- [ ] AWS Serverless utilities available

### 9.2 Other MCP Servers
- [ ] Puppeteer server operational
- [ ] Bright Data API key valid and working

## 10. Monitoring & Logging
- [ ] CloudWatch logs capturing all events
- [ ] Error tracking in place
- [ ] Performance metrics collection
- [ ] Budget alerts configured

## Test Execution Schedule

1. **Daily**: Authentication, basic upload/download
2. **Weekly**: Full UI testing, pattern detection
3. **Monthly**: Performance, security, compatibility
4. **Release**: Complete test suite

## Test Data Management

### Test Users
- test1@gmail.com / TestPass123!
- test2@outlook.com / TestPass123!
- test3@yahoo.com / TestPass123!

### Test Files
- small_text.txt (1KB)
- medium_pdf.pdf (5MB)
- large_docx.docx (45MB)
- pattern_test.txt (with all PII patterns)
- malformed.pdf (for error testing)

## Success Criteria
- All critical path tests pass
- Pattern detection accuracy > 99%
- UI responsiveness < 200ms
- API response time < 2s
- Zero security vulnerabilities
- Cross-browser compatibility confirmed

## Issue Tracking
Document all failures in GitHub Issues with:
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/videos
- Browser/environment details
- Severity level (Critical/High/Medium/Low)