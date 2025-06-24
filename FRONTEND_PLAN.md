# Simple React Frontend Plan - Document Redaction System

## Overview
A streamlined, secure React frontend with core functionality:
- Password-protected authentication
- File upload/download 
- User data isolation (users only see their own files)
- Configuration management interface

## Core Features

### 1. Authentication (AWS Cognito)
- Simple email/password login
- Self-registration enabled (with email verification)
- Password reset functionality
- JWT token management via AWS Amplify

### 2. File Management
**Upload Flow:**
- Drag-and-drop or click to upload
- Supported formats: TXT, PDF, DOCX, XLSX
- Max file size: 50MB
- Progress indicator during upload

**Download Flow:**
- List of user's files with status (processing/completed/failed)
- Download button for completed files
- Files automatically deleted after 7 days

**User Data Isolation:**
- Files uploaded to S3 with user ID prefix: `users/{userId}/filename.ext`
- API returns only files belonging to authenticated user
- Presigned URLs include user context

### 3. Configuration Management
**Simple Config UI:**
- Table view of redaction rules
- Add/Edit/Delete rules
- Toggle case sensitivity
- Save configuration button
- Only available to users with 'admin' role

### 4. Technical Architecture

**Frontend Stack:**
- React 18 with TypeScript
- AWS Amplify (authentication)
- Tailwind CSS (styling)
- Axios (API calls)

**Backend Updates Needed:**
- Modify Lambda to handle user-prefixed S3 keys
- Add user context to file metadata
- Update API endpoints to filter by user ID
- Add configuration endpoints

**File Structure:**
```
src/
├── components/
│   ├── Auth/
│   │   ├── Login.tsx
│   │   └── PrivateRoute.tsx
│   ├── Files/
│   │   ├── Upload.tsx
│   │   ├── FileList.tsx
│   │   └── FileItem.tsx
│   └── Config/
│       ├── ConfigEditor.tsx
│       └── RuleRow.tsx
├── pages/
│   ├── Dashboard.tsx
│   ├── Login.tsx
│   └── Config.tsx
└── App.tsx
```

## Implementation Steps

### Phase 1: Backend Modifications (Week 1)
1. **Update Lambda Functions:**
   ```python
   # Add user context to S3 keys
   def get_user_s3_key(user_id, filename):
       return f"users/{user_id}/{filename}"
   ```

2. **Add Configuration API Endpoints:**
   - `GET /api/config` - Get current config
   - `PUT /api/config` - Update config (admin only)

3. **Update S3 Processing:**
   - Maintain user folder structure through processing
   - Add user_id to file metadata

### Phase 2: Basic Frontend (Week 2)
1. **Setup & Authentication:**
   - Create React app with TypeScript
   - Configure AWS Amplify
   - Build login/register pages
   - Implement auth context

2. **Core Layout:**
   - Navigation header with logout
   - Dashboard with file upload area
   - File list component

### Phase 3: File Operations (Week 3)
1. **File Upload:**
   ```tsx
   const uploadFile = async (file: File) => {
     const user = await Auth.currentAuthenticatedUser();
     const response = await api.post('/documents/upload', {
       filename: file.name,
       content: await toBase64(file),
       userId: user.attributes.sub
     });
     return response.data;
   };
   ```

2. **File List & Download:**
   - Poll for file status
   - Generate download links
   - Show processing status

### Phase 4: Configuration UI (Week 4)
1. **Config Editor (Admin Only):**
   ```tsx
   interface Rule {
     find: string;
     replace: string;
   }
   
   const ConfigEditor = () => {
     const [rules, setRules] = useState<Rule[]>([]);
     const [caseSensitive, setCaseSensitive] = useState(false);
     
     // Add/edit/delete rule functions
     // Save configuration to API
   };
   ```

## API Endpoints

### Existing (Modified)
- `POST /documents/upload` - Add user context
- `GET /documents/status/{id}` - Filter by user

### New Endpoints
- `GET /api/user/files` - List user's files
- `GET /api/config` - Get configuration
- `PUT /api/config` - Update configuration

## Security Considerations

1. **Authentication:**
   - All API calls require valid JWT token
   - Token refresh handled by Amplify
   - 24-hour token expiration

2. **Authorization:**
   - User can only access their own files
   - Config management requires admin role
   - S3 presigned URLs include user context

3. **Data Isolation:**
   - S3 key prefixing with user ID
   - Lambda validates user ownership
   - API filters results by authenticated user

## Simplified UI Mockups

### Dashboard
```
┌─────────────────────────────────────┐
│ Document Redaction    [Config] [Logout] │
├─────────────────────────────────────┤
│                                     │
│   ┌─────────────────────────────┐   │
│   │    Drop files here or       │   │
│   │    click to upload          │   │
│   │         📁                  │   │
│   └─────────────────────────────┘   │
│                                     │
│ Your Files:                         │
│ ┌─────────────────────────────────┐ │
│ │ document.pdf    ⟳ Processing... │ │
│ ├─────────────────────────────────┤ │
│ │ report.docx     ✓ [Download]    │ │
│ ├─────────────────────────────────┤ │
│ │ data.xlsx       ✗ Failed        │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Configuration (Admin Only)
```
┌─────────────────────────────────────┐
│ Redaction Rules         [← Back]    │
├─────────────────────────────────────┤
│                                     │
│ Find          Replace      Actions  │
│ ┌─────────────────────────────────┐ │
│ │ Choice       CH          [✎][🗑] │ │
│ │ ACME Corp    [REDACTED]  [✎][🗑] │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [+ Add Rule]                        │
│                                     │
│ ☐ Case Sensitive                    │
│                                     │
│ [Save Configuration]                │
└─────────────────────────────────────┘
```

## Deployment

1. **Frontend Hosting with Custom Domain (9thcube.com):**
   - Build: `npm run build`
   - Deploy to S3: `aws s3 sync build/ s3://redact-frontend-9thcube`
   - CloudFront distribution with custom domain
   - Route 53 configuration for 9thcube.com

2. **Domain Configuration (Route 53 Hosted Zone: Z08255452MP6V2QLHWIYG):**
   ```
   # A. Create subdomain for the app
   redact.9thcube.com → CloudFront Distribution
   
   # B. API custom domain (optional)
   api.redact.9thcube.com → API Gateway Custom Domain
   ```

3. **CloudFront Setup:**
   - Origin: S3 bucket (redact-frontend-9thcube)
   - Alternate domain names: redact.9thcube.com
   - SSL Certificate: AWS Certificate Manager (ACM) for *.9thcube.com
   - Default root object: index.html
   - Error pages: 404 → /index.html (for React Router)

4. **Environment Variables:**
   ```
   REACT_APP_API_URL=https://api.redact.9thcube.com
   REACT_APP_USER_POOL_ID=us-east-1_xxxxx
   REACT_APP_CLIENT_ID=xxxxxxxxxxxxx
   REACT_APP_DOMAIN=redact.9thcube.com
   ```

## Infrastructure Updates for Custom Domain

### Terraform Updates Required:
```hcl
# ACM Certificate for CloudFront (must be in us-east-1)
resource "aws_acm_certificate" "frontend_cert" {
  provider          = aws.us-east-1
  domain_name       = "redact.9thcube.com"
  validation_method = "DNS"
  
  lifecycle {
    create_before_destroy = true
  }
}

# Route 53 Record for domain validation
resource "aws_route53_record" "cert_validation" {
  zone_id = "Z08255452MP6V2QLHWIYG"
  name    = aws_acm_certificate.frontend_cert.domain_validation_options[0].resource_record_name
  type    = aws_acm_certificate.frontend_cert.domain_validation_options[0].resource_record_type
  records = [aws_acm_certificate.frontend_cert.domain_validation_options[0].resource_record_value]
  ttl     = 60
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "frontend" {
  aliases = ["redact.9thcube.com"]
  
  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.frontend_cert.arn
    ssl_support_method  = "sni-only"
  }
}

# Route 53 A Record for CloudFront
resource "aws_route53_record" "frontend" {
  zone_id = "Z08255452MP6V2QLHWIYG"
  name    = "redact.9thcube.com"
  type    = "A"
  
  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}
```

## Cost Estimate
- Cognito: Free tier (50K users)
- S3/CloudFront: ~$1/month
- Route 53 Hosted Zone: $0.50/month (already exists)
- Additional Lambda calls: ~$1/month
- **Total: ~$2-3/month**

## Next Steps
1. Update backend Lambda functions for user isolation
2. Create ACM certificate for redact.9thcube.com
3. Create React app with authentication
4. Build file upload/download features
5. Add configuration management
6. Configure CloudFront with custom domain
7. Update Route 53 records
8. Deploy and test at redact.9thcube.com

This simplified approach provides all requested features while maintaining security and keeping implementation straightforward.