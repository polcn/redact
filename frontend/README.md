# Document Redaction Frontend

A secure React frontend for the AWS Document Redaction System.

## Features

- 🔐 AWS Cognito authentication with email verification
- 📁 Drag-and-drop file upload (TXT, PDF, DOCX, XLSX)
- 📊 Real-time processing status updates
- ⬇️ Secure file downloads with presigned URLs
- ⚙️ Configuration management UI (admin only)
- 🎨 Modern UI with Tailwind CSS
- 🔒 User data isolation

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS configuration
   ```

3. **Deploy infrastructure first:**
   ```bash
   cd ..
   terraform apply
   ```

4. **Run development server:**
   ```bash
   npm start
   ```

## Deployment

1. **Build the app:**
   ```bash
   npm run build
   ```

2. **Deploy to AWS:**
   ```bash
   ./deploy.sh
   ```

The app will be available at: https://redact.9thcube.com

## Architecture

- **Authentication**: AWS Cognito with JWT tokens
- **API**: REST API Gateway with Lambda backend
- **Storage**: S3 with user isolation (users/{userId}/*)
- **Hosting**: S3 + CloudFront with custom domain
- **Security**: HTTPS only, presigned URLs for downloads

## User Roles

- **User**: Can upload/download their own files
- **Admin**: Can also manage redaction configuration

## File Processing Flow

1. User uploads file via web interface
2. File stored in S3 with user prefix
3. Lambda processes file asynchronously
4. User sees real-time status updates
5. Processed file available for download

## Configuration

Admins can configure redaction rules:
- Find/replace text patterns
- Case-sensitive matching
- Applied to both content and filenames

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### `npm test`

Launches the test runner in the interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time.