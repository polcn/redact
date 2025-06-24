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

1. **Frontend Hosting:**
   - Build: `npm run build`
   - Deploy to S3: `aws s3 sync build/ s3://frontend-bucket`
   - CloudFront distribution for HTTPS

2. **Environment Variables:**
   ```
   REACT_APP_API_URL=https://api-id.execute-api.region.amazonaws.com/production
   REACT_APP_USER_POOL_ID=us-east-1_xxxxx
   REACT_APP_CLIENT_ID=xxxxxxxxxxxxx
   ```

## Cost Estimate
- Cognito: Free tier (50K users)
- S3/CloudFront: ~$1/month
- Additional Lambda calls: ~$1/month
- **Total: ~$2-3/month**

## Next Steps
1. Update backend Lambda functions for user isolation
2. Create React app with authentication
3. Build file upload/download features
4. Add configuration management
5. Deploy and test

This simplified approach provides all requested features while maintaining security and keeping implementation straightforward.