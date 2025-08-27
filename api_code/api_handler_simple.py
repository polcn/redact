import json
import boto3
import base64
import os
import uuid
import time
from urllib.parse import unquote_plus
import logging
from botocore.exceptions import ClientError
import zipfile
import io
from datetime import datetime
import sys
import importlib.util
import re
import hashlib
from collections import defaultdict

# Import Claude SDK
try:
    from anthropic import AnthropicBedrock
except ImportError:
    AnthropicBedrock = None
    logger = logging.getLogger()
    logger.warning("anthropic package not available - falling back to direct Bedrock calls")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(message)s'
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
ssm = boto3.client('ssm')

# Environment variables
INPUT_BUCKET = os.environ['INPUT_BUCKET']
PROCESSED_BUCKET = os.environ['PROCESSED_BUCKET']
QUARANTINE_BUCKET = os.environ['QUARANTINE_BUCKET']
CONFIG_BUCKET = os.environ['CONFIG_BUCKET']

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'xlsx', 'xls', 'csv', 'pptx', 'ppt'}

# MIME type mapping for content validation
MIME_TYPE_MAPPING = {
    'pdf': [b'%PDF'],  # PDF magic bytes
    'docx': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],  # ZIP-based Office format
    'xlsx': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],  # ZIP-based Office format
    'xls': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # Old Excel format
    'pptx': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],  # ZIP-based Office format
    'ppt': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # Old PowerPoint format
    'txt': [b'', None],  # Text files don't have specific magic bytes
    'csv': [b'', None]   # CSV files don't have specific magic bytes
}

def get_content_type_from_filename(filename):
    """Get MIME content type from filename extension"""
    if not filename:
        return 'application/octet-stream'
    
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    content_types = {
        'txt': 'text/plain',
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        'csv': 'text/csv',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'ppt': 'application/vnd.ms-powerpoint',
        'md': 'text/markdown'
    }
    
    return content_types.get(ext, 'application/octet-stream')

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal attacks"""
    # Check for path traversal attempts BEFORE modifying
    if '..' in filename or filename.startswith('/') or '\\' in filename or ':' in filename:
        raise ValueError("Invalid filename detected - possible path traversal attempt")
    
    # Remove any directory components
    filename = os.path.basename(filename)
    # Remove dangerous characters but keep dots for extensions
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Double-check after sanitization
    if not filename or filename.startswith('.'):
        raise ValueError("Invalid filename after sanitization")
    
    # Limit filename length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        max_name_length = 255 - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename

def validate_file_content(file_content, claimed_extension):
    """Validate file content matches the claimed extension"""
    if not file_content:
        raise ValueError("Empty file content")
    
    # Get expected magic bytes for the extension
    expected_magic = MIME_TYPE_MAPPING.get(claimed_extension.lower(), [])
    
    # For text-based files, we allow any content
    if claimed_extension.lower() in ['txt', 'csv']:
        return True
    
    # Check if file starts with expected magic bytes
    file_header = file_content[:16]  # Read first 16 bytes
    
    valid = False
    for magic_bytes in expected_magic:
        if magic_bytes and file_header.startswith(magic_bytes):
            valid = True
            break
    
    if not valid and expected_magic:
        logger.warning(f"File content validation failed for extension {claimed_extension}")
        raise ValueError(f"File content doesn't match declared file type: {claimed_extension}")
    
    return True

def get_user_context(event):
    """Extract user context from API Gateway authorizer"""
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    
    if authorizer and 'claims' in authorizer:
        # Cognito authorizer adds claims
        claims = authorizer['claims']
        return {
            'user_id': claims.get('sub', 'anonymous'),
            'email': claims.get('email', ''),
            'role': claims.get('custom:role', 'user')
        }
    
    # Fallback for endpoints that might not have auth (like health checks)
    # or when API Gateway hasn't passed auth context
    logger.info("No Cognito claims found, using anonymous context")
    return {
        'user_id': 'anonymous',
        'email': 'anonymous@example.com',
        'role': 'user'
    }

def get_user_s3_prefix(user_id):
    """Get S3 prefix for user isolation"""
    return f"users/{user_id}"

def lambda_handler(event, context):
    """
    API Gateway Lambda handler for document redaction REST API
    """
    try:
        # Log every request for debugging
        log_data = {
            'event': 'LAMBDA_INVOKED',
            'path': event.get('path', ''),
            'method': event.get('httpMethod', ''),
            'headers': list(event.get('headers', {}).keys()),
            'has_body': bool(event.get('body')),
            'request_id': context.aws_request_id
        }
        print(f"INFO: {json.dumps(log_data)}")
        logger.info(json.dumps(log_data))
        
        # CORS headers - always use production domain for consistency
        # This matches what's configured in API Gateway OPTIONS methods
        headers = {
            'Access-Control-Allow-Origin': 'https://redact.9thcube.com',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,PUT,DELETE',
            'Content-Type': 'application/json'
        }
        
        # Handle preflight OPTIONS requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Route requests based on path and method
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        
        logger.info(json.dumps({
            'event': 'API_REQUEST',
            'path': path,
            'method': method,
            'request_id': context.aws_request_id,
            'headers': list(event.get('headers', {}).keys()),
            'has_auth': 'Authorization' in event.get('headers', {})
        }))
        
        # Public endpoints
        if path == '/health' and method == 'GET':
            return handle_health_check(headers)
        
        # String.com integration endpoint (uses API key auth, not Cognito)
        logger.info(f"Checking String.com endpoint: path='{path}' method='{method}' match={path == '/api/string/redact' and method == 'POST'}")
        if path == '/api/string/redact' and method == 'POST':
            logger.info("Calling handle_string_redact")
            return handle_string_redact(event, headers, context)
        
        # Get user context
        user_context = get_user_context(event)
        
        # Note: API Gateway handles authentication via Cognito authorizer
        # If we reach here on protected endpoints, user is already authenticated
        # The authorizer configuration at API Gateway level ensures this
        
        if path == '/documents/upload' and method == 'POST':
            return handle_document_upload(event, headers, context, user_context)
        
        elif path == '/documents/upload-url' and method == 'POST':
            return handle_get_upload_url(event, headers, context, user_context)
            
        elif path.startswith('/documents/status') and method == 'GET':
            return handle_status_check(event, headers, context, user_context)
            
        elif path == '/user/files' and method == 'GET':
            return handle_list_user_files(event, headers, context, user_context)
            
        elif path == '/api/config' and method == 'GET':
            return handle_get_config(headers, user_context)
            
        elif path == '/api/config' and method == 'PUT':
            return handle_update_config(event, headers, user_context)
            
        elif path == '/api/ai-config' and method == 'GET':
            return handle_get_ai_config(headers, user_context)
            
        elif path == '/api/ai-config' and method == 'PUT':
            return handle_update_ai_config(event, headers, user_context)
            
        elif path.startswith('/documents/') and method == 'DELETE':
            return handle_document_delete(event, headers, context, user_context)
            
        elif path == '/documents/batch-download' and method == 'POST':
            return handle_batch_download(event, headers, context, user_context)
            
        elif path == '/documents/combine' and method == 'POST':
            logger.info(f"Handling combine request for path: {path}")
            return handle_combine_documents(event, headers, context, user_context)
            
        elif path == '/documents/ai-summary' and method == 'POST':
            logger.info(f"Handling AI summary request for path: {path}")
            return handle_ai_summary(event, headers, context, user_context)
            
        elif path == '/documents/extract-metadata' and method == 'POST':
            logger.info(f"Handling metadata extraction request for path: {path}")
            return handle_extract_metadata(event, headers, context, user_context)
            
        elif path == '/documents/prepare-vectors' and method == 'POST':
            logger.info(f"Handling vector preparation request for path: {path}")
            return handle_prepare_vectors(event, headers, context, user_context)
            
        elif path == '/redaction/patterns' and method == 'GET':
            logger.info(f"Handling get redaction patterns request for path: {path}")
            return handle_get_redaction_patterns(event, headers, context, user_context)
            
        elif path == '/redaction/patterns' and method == 'POST':
            logger.info(f"Handling create redaction pattern request for path: {path}")
            return handle_create_redaction_pattern(event, headers, context, user_context)
            
        elif path == '/redaction/apply' and method == 'POST':
            logger.info(f"Handling apply redaction patterns request for path: {path}")
            return handle_apply_redaction(event, headers, context, user_context)
            
        # Quarantine file management
        elif path == '/quarantine/files' and method == 'GET':
            logger.info(f"Handling list quarantine files request for path: {path}")
            return handle_list_quarantine_files(event, headers, context, user_context)
            
        elif path.startswith('/quarantine/') and method == 'DELETE':
            logger.info(f"Handling delete quarantine file request for path: {path}")
            return handle_delete_quarantine_file(event, headers, context, user_context)
            
        elif path == '/quarantine/delete-all' and method == 'POST':
            logger.info(f"Handling delete all quarantine files request for path: {path}")
            return handle_delete_all_quarantine_files(event, headers, context, user_context)
            
        # Test redaction endpoint
        elif path == '/api/test-redaction' and method == 'POST':
            return handle_test_redaction(event, headers, context, user_context)
            
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        logger.error(json.dumps({
            'event': 'API_ERROR',
            'error': str(e),
            'request_id': context.aws_request_id
        }))
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def handle_health_check(headers):
    """Handle GET /health endpoint"""
    try:
        # Check S3 bucket accessibility
        s3.head_bucket(Bucket=INPUT_BUCKET)
        s3.head_bucket(Bucket=PROCESSED_BUCKET)
        s3.head_bucket(Bucket=CONFIG_BUCKET)
        
        health_status = {
            'status': 'healthy',
            'timestamp': int(time.time()),
            'services': {
                's3': 'operational',
                'lambda': 'operational'
            }
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(health_status)
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        
        health_status = {
            'status': 'unhealthy',
            'timestamp': int(time.time()),
            'error': str(e)
        }
        
        return {
            'statusCode': 503,
            'headers': headers,
            'body': json.dumps(health_status)
        }

def handle_get_upload_url(event, headers, context, user_context):
    """Generate a presigned URL for direct S3 upload"""
    try:
        logger.info(f"Upload URL handler called - User: {user_context.get('email', 'unknown')}")
        
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body)
        
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        
        data = json.loads(body)
        
        # Validate request
        if 'filename' not in data:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing filename'})
            }
        
        filename = data['filename']
        
        # Sanitize filename to prevent path traversal
        try:
            filename = sanitize_filename(filename)
        except ValueError as e:
            logger.warning(f"Filename sanitization failed: {str(e)} - User: {user_context['email']}")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid filename'})
            }
        
        # Validate file extension
        file_ext = filename.lower().split('.')[-1]
        if file_ext not in ALLOWED_EXTENSIONS:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Unsupported file type: {file_ext}',
                    'allowed_types': list(ALLOWED_EXTENSIONS)
                })
            }
        
        # Generate unique key with user prefix
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        
        # Generate unique filename using timestamp
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Add timestamp to filename to ensure uniqueness
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            s3_key = f"{user_prefix}/{name}_{timestamp}.{ext}"
        else:
            s3_key = f"{user_prefix}/{filename}_{timestamp}"
        
        # Generate presigned POST URL for upload
        presigned_post = s3.generate_presigned_post(
            Bucket=INPUT_BUCKET,
            Key=s3_key,
            Fields={
                'x-amz-server-side-encryption': 'AES256',
                'x-amz-meta-upload-method': 'presigned-url',
                'x-amz-meta-original-filename': filename,
                'x-amz-meta-user-id': user_context['user_id'],
                'x-amz-meta-user-email': user_context['email']
            },
            Conditions=[
                ['content-length-range', 0, MAX_FILE_SIZE],
                {'x-amz-server-side-encryption': 'AES256'},
                {'x-amz-meta-upload-method': 'presigned-url'},
                {'x-amz-meta-original-filename': filename},
                {'x-amz-meta-user-id': user_context['user_id']},
                {'x-amz-meta-user-email': user_context['email']}
            ],
            ExpiresIn=3600  # URL valid for 1 hour
        )
        
        # Generate a document ID for status tracking
        from urllib.parse import quote
        document_id = quote(s3_key, safe='')
        
        logger.info(json.dumps({
            'event': 'PRESIGNED_URL_GENERATED',
            'key': s3_key,
            'user_id': user_context['user_id'],
            'filename': filename
        }))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'upload_url': presigned_post['url'],
                'fields': presigned_post['fields'],
                'document_id': document_id,
                's3_key': s3_key,
                'filename': filename
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to generate upload URL'})
        }

def handle_document_upload(event, headers, context, user_context):
    """Handle POST /documents/upload endpoint with user isolation"""
    try:
        logger.info(f"Upload handler called - User: {user_context.get('email', 'unknown')}")
        
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body)
        
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        
        data = json.loads(body)
        
        # Validate request
        if 'filename' not in data or 'content' not in data:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing filename or content'})
            }
        
        filename = data['filename']
        content = data['content']
        
        # Sanitize filename to prevent path traversal
        try:
            filename = sanitize_filename(filename)
        except ValueError as e:
            logger.warning(f"Filename sanitization failed: {str(e)} - User: {user_context['email']}")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid filename'})
            }
        
        # Log the upload attempt
        logger.info(f"Upload attempt - Filename: {filename}, User: {user_context['email']}")
        
        # Validate file extension
        file_ext = filename.lower().split('.')[-1]
        logger.info(f"Extracted extension: '{file_ext}' from filename: '{filename}'")
        logger.info(f"Allowed extensions: {ALLOWED_EXTENSIONS}")
        
        if file_ext not in ALLOWED_EXTENSIONS:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Unsupported file type: {file_ext}',
                    'allowed_types': list(ALLOWED_EXTENSIONS)
                })
            }
        
        # Decode base64 content
        try:
            file_content = base64.b64decode(content)
        except Exception:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid base64 content'})
            }
        
        # Validate file content matches extension - warn but don't block
        try:
            validate_file_content(file_content, file_ext)
            logger.info(f"File content validation passed for {file_ext}")
        except ValueError as e:
            # Log warning but allow upload to proceed
            logger.warning(f"File content validation warning: {str(e)} - User: {user_context['email']} - File: {filename}")
            # Continue with upload despite validation warning
        
        # Validate file size
        if len(file_content) > MAX_FILE_SIZE:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': f'File too large: {len(file_content)} bytes',
                    'max_size': MAX_FILE_SIZE
                })
            }
        
        # Generate unique key with user prefix
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        
        # Generate unique filename using timestamp to avoid collision checks
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Add timestamp to filename to ensure uniqueness
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            s3_key = f"{user_prefix}/{name}_{timestamp}.{ext}"
        else:
            s3_key = f"{user_prefix}/{filename}_{timestamp}"
        
        # Upload to S3
        s3.put_object(
            Bucket=INPUT_BUCKET,
            Key=s3_key,
            Body=file_content,
            ServerSideEncryption='AES256',
            Metadata={
                'upload-method': 'api',
                'original-filename': filename,
                'request-id': context.aws_request_id,
                'user-id': user_context['user_id'],
                'user-email': user_context['email']
            }
        )
        
        logger.info(json.dumps({
            'event': 'DOCUMENT_UPLOADED',
            'key': s3_key,
            'size': len(file_content),
            'user_id': user_context['user_id'],
            'request_id': context.aws_request_id
        }))
        
        # Generate a document ID for status tracking
        # Use the S3 key as the document ID (URL encoded)
        from urllib.parse import quote
        document_id = quote(s3_key, safe='')
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Document uploaded successfully',
                'document_id': document_id,
                'filename': filename,
                'status': 'processing',
                'status_url': f'/documents/status/{document_id}'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON'})
        }

def handle_status_check(event, headers, context, user_context):
    """Handle GET /documents/status/{id} endpoint with user validation"""
    try:
        # Extract document ID from path
        path_params = event.get('pathParameters', {})
        document_id = path_params.get('id') if path_params else None
        
        if not document_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Document ID required'})
            }
        
        # Search for documents with this ID prefix (only in user's folder)
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        status_info = check_document_status(document_id, user_prefix)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(status_info)
        }
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Status check failed'})
        }

def check_document_status(document_id, user_prefix):
    """Check the processing status of a document with user isolation"""
    try:
        # Check input bucket (still processing)
        try:
            input_response = s3.list_objects_v2(
                Bucket=INPUT_BUCKET,
                Prefix=f"{user_prefix}/{document_id}"
            )
            if input_response.get('Contents'):
                return {
                    'document_id': document_id,
                    'status': 'processing',
                    'message': 'Document is being processed'
                }
        except ClientError:
            pass
        
        # Check processed bucket (completed)
        try:
            processed_response = s3.list_objects_v2(
                Bucket=PROCESSED_BUCKET,
                Prefix=f"processed/{user_prefix}/{document_id}"
            )
            if processed_response.get('Contents'):
                processed_files = [obj['Key'] for obj in processed_response['Contents']]
                return {
                    'document_id': document_id,
                    'status': 'completed',
                    'message': 'Document processing completed',
                    'processed_files': processed_files,
                    'download_urls': [
                        generate_presigned_url(PROCESSED_BUCKET, key)
                        for key in processed_files
                    ]
                }
        except ClientError:
            pass
        
        # Check quarantine bucket (failed/quarantined)
        try:
            quarantine_response = s3.list_objects_v2(
                Bucket=QUARANTINE_BUCKET,
                Prefix=f"quarantine/{user_prefix}/{document_id}"
            )
            if quarantine_response.get('Contents'):
                quarantine_obj = quarantine_response['Contents'][0]
                # Get metadata to find quarantine reason
                obj_metadata = s3.head_object(
                    Bucket=QUARANTINE_BUCKET,
                    Key=quarantine_obj['Key']
                )
                reason = obj_metadata.get('Metadata', {}).get('quarantine-reason', 'Unknown')
                
                return {
                    'document_id': document_id,
                    'status': 'quarantined',
                    'message': 'Document was quarantined',
                    'reason': reason
                }
        except ClientError:
            pass
        
        # Document not found
        return {
            'document_id': document_id,
            'status': 'not_found',
            'message': 'Document not found or expired'
        }
        
    except Exception as e:
        logger.error(f"Error checking document status: {str(e)}")
        return {
            'document_id': document_id,
            'status': 'error',
            'message': 'Status check failed'
        }

def handle_list_user_files(event, headers, context, user_context):
    """Handle GET /user/files endpoint to list user's files"""
    try:
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        files = []
        
        # List files in processed bucket
        try:
            processed_response = s3.list_objects_v2(
                Bucket=PROCESSED_BUCKET,
                Prefix=f"processed/{user_prefix}/"
            )
            
            for obj in processed_response.get('Contents', []):
                # Parse filename from key
                filename = obj['Key'].split('/')[-1]
                # Use the full S3 key as the document ID (URL encoded)
                from urllib.parse import quote
                doc_id = quote(obj['Key'], safe='')
                
                files.append({
                    'id': doc_id,
                    'filename': filename,
                    'status': 'completed',
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'download_url': generate_presigned_url(PROCESSED_BUCKET, obj['Key'], force_download=True)
                })
        except ClientError:
            pass
        
        # List files in input bucket (still processing)
        try:
            input_response = s3.list_objects_v2(
                Bucket=INPUT_BUCKET,
                Prefix=f"{user_prefix}/"
            )
            
            for obj in input_response.get('Contents', []):
                filename = obj['Key'].split('/')[-1]
                # Use the full S3 key as the document ID (URL encoded)
                from urllib.parse import quote
                doc_id = quote(obj['Key'], safe='')
                
                # Check if already in processed list
                if not any(f['id'] == doc_id for f in files):
                    files.append({
                        'id': doc_id,
                        'filename': filename,
                        'status': 'processing',
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
        except ClientError:
            pass
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'files': files,
                'count': len(files)
            })
        }
        
    except Exception as e:
        logger.error(f"Error listing user files: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to list files'})
        }

def handle_document_delete(event, headers, context, user_context):
    """Handle DELETE /documents/{id} endpoint"""
    try:
        # Extract document ID from path parameters
        path_params = event.get('pathParameters', {})
        document_id = path_params.get('id') if path_params else None
        
        if not document_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Document ID required'})
            }
        
        # Decode the document ID to get the S3 key
        from urllib.parse import unquote
        # Document ID from URL path is URL-encoded - decode it to get S3 key
        s3_key = unquote(document_id)
        
        # Log the decoding for debugging
        logger.info(f"Delete request - Document ID from path: {document_id}, Decoded S3 key: {s3_key}, User: {user_context['user_id']}")
        
        # Security check: ensure the key belongs to the user
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        
        # Check if this is a processed file or input file that belongs to the user
        valid_prefixes = [
            f"processed/{user_prefix}/",  # processed/users/{user_id}/
            f"{user_prefix}/"              # users/{user_id}/
        ]
        
        is_authorized = any(s3_key.startswith(prefix) for prefix in valid_prefixes)
        
        if not is_authorized:
            logger.warning(f"Access denied - Key: {s3_key}, User prefix: {user_prefix}, Valid prefixes: {valid_prefixes}")
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({'error': 'Access denied - you can only delete your own files'})
            }
        
        deleted_files = []
        errors = []
        
        # If it's a processed file, also delete the source file
        if s3_key.startswith("processed/"):
            # Extract the filename from the processed key
            filename = s3_key.split('/')[-1]
            
            # Delete from processed bucket
            try:
                s3.delete_object(Bucket=PROCESSED_BUCKET, Key=s3_key)
                deleted_files.append(f"processed/{s3_key}")
                logger.info(f"Successfully deleted from processed bucket: {s3_key}")
            except Exception as e:
                logger.error(f"Failed to delete from processed bucket - Key: {s3_key}, Error: {str(e)}")
                errors.append(f"Failed to delete {s3_key}: {str(e)}")
            
            # Also delete from input bucket if exists
            input_key = f"{user_prefix}/{filename}"
            try:
                s3.head_object(Bucket=INPUT_BUCKET, Key=input_key)
                s3.delete_object(Bucket=INPUT_BUCKET, Key=input_key)
                deleted_files.append(f"input/{input_key}")
            except ClientError:
                pass
        else:
            # It's an input file, delete it
            try:
                s3.delete_object(Bucket=INPUT_BUCKET, Key=s3_key)
                deleted_files.append(f"input/{s3_key}")
                logger.info(f"Successfully deleted from input bucket: {s3_key}")
            except Exception as e:
                logger.error(f"Failed to delete from input bucket - Key: {s3_key}, Error: {str(e)}")
                errors.append(f"Failed to delete {s3_key}: {str(e)}")
        
        if not deleted_files and not errors:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Document not found'})
            }
        
        if errors:
            logger.error(f"Errors during deletion: {errors}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Document deleted',
                'document_id': document_id,
                'deleted_files': deleted_files,
                'errors': errors if errors else None
            })
        }
        
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to delete document'})
        }

def handle_get_config(headers, user_context):
    """Handle GET /api/config endpoint with user-specific configuration"""
    try:
        user_id = user_context.get('user_id', 'anonymous')
        
        # Try to get user-specific config first
        user_config_key = f'configs/users/{user_id}/config.json'
        
        try:
            response = s3.get_object(
                Bucket=CONFIG_BUCKET,
                Key=user_config_key
            )
            config = json.loads(response['Body'].read())
            logger.info(f"Loaded user-specific config for user {user_id}")
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(config)
            }
        except s3.exceptions.NoSuchKey:
            # No user config exists yet - this is expected for new users
            logger.info(f"No config found for user {user_id}, will create default")
        
        # Return default config if nothing found
        default_config = {
            'replacements': [],
            'case_sensitive': False,
            'patterns': {
                'ssn': False,
                'credit_card': False,
                'phone': False,
                'email': False,
                'ip_address': False,
                'drivers_license': False
            }
        }
        
        # Save default config for user
        s3.put_object(
            Bucket=CONFIG_BUCKET,
            Key=user_config_key,
            Body=json.dumps(default_config, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Created default config for user {user_id}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(default_config)
        }
        
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get configuration'})
        }

def handle_update_config(event, headers, user_context):
    """Handle PUT /api/config endpoint with user-specific configuration"""
    try:
        user_id = user_context.get('user_id', 'anonymous')
        
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        config = json.loads(body)
        
        # Validate config structure
        if 'replacements' not in config or not isinstance(config['replacements'], list):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid config format'})
            }
        
        # Validate patterns if present
        if 'patterns' in config:
            if not isinstance(config['patterns'], dict):
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid config format: patterns must be a dictionary'})
                }
            # Validate pattern values are boolean
            for pattern_name, enabled in config['patterns'].items():
                if not isinstance(enabled, bool):
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': f'Pattern {pattern_name} must be true or false'})
                    }
        
        # Save user-specific config to S3
        user_config_key = f'configs/users/{user_id}/config.json'
        s3.put_object(
            Bucket=CONFIG_BUCKET,
            Key=user_config_key,
            Body=json.dumps(config, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256',
            Metadata={
                'user-id': user_id,
                'user-email': user_context.get('email', ''),
                'updated-at': str(int(time.time()))
            }
        )
        
        logger.info(json.dumps({
            'event': 'USER_CONFIG_UPDATED',
            'user_id': user_context['user_id'],
            'user_email': user_context['email'],
            'config_key': user_config_key
        }))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Configuration updated successfully',
                'config': config
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to update configuration'})
        }

def generate_presigned_url(bucket, key, expiration=3600, force_download=True):
    """Generate a presigned URL for accessing processed documents
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiration: URL expiration time in seconds
        force_download: If True, adds Content-Disposition to force download
    """
    try:
        params = {
            'Bucket': bucket, 
            'Key': key
        }
        
        # Only add disposition header if we want to force download
        if force_download:
            filename = key.split('/')[-1]
            # Ensure filename is properly escaped for HTTP headers
            # Replace quotes and control characters
            safe_filename = filename.replace('"', '').replace('\n', '').replace('\r', '')
            params['ResponseContentDisposition'] = f'attachment; filename="{safe_filename}"'
        
        url = s3.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        return None

def handle_batch_download(event, headers, context, user_context):
    """Handle POST /documents/batch-download endpoint to download multiple files as ZIP"""
    try:
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Get list of document IDs
        document_ids = body.get('document_ids', [])
        if not document_ids:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No document IDs provided'})
            }
        
        # Limit batch size to prevent timeout
        max_batch_size = 50
        if len(document_ids) > max_batch_size:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Maximum batch size is {max_batch_size} files'})
            }
        
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            files_added = 0
            errors = []
            
            for doc_id in document_ids:
                try:
                    # Document IDs from frontend are URL-encoded S3 keys - need to decode them
                    from urllib.parse import unquote
                    s3_key = unquote(doc_id)
                    
                    # Log for debugging
                    logger.info(f"Batch download - Document ID: {doc_id}, Decoded S3 key: {s3_key}")
                    
                    # Security check: ensure the key belongs to the user
                    valid_prefixes = [
                        f"processed/{user_prefix}/",  # processed/users/{user_id}/
                        f"{user_prefix}/"              # users/{user_id}/
                    ]
                    
                    is_authorized = any(s3_key.startswith(prefix) for prefix in valid_prefixes)
                    
                    if not is_authorized:
                        logger.warning(f"Unauthorized access attempt to {s3_key} by user {user_context['user_id']}, valid prefixes: {valid_prefixes}")
                        errors.append({'id': doc_id, 'error': 'Unauthorized'})
                        continue
                    
                    # Get the file from S3 - determine which bucket based on key
                    try:
                        if s3_key.startswith("processed/"):
                            response = s3.get_object(Bucket=PROCESSED_BUCKET, Key=s3_key)
                        else:
                            response = s3.get_object(Bucket=INPUT_BUCKET, Key=s3_key)
                        file_content = response['Body'].read()
                        
                        # Extract filename from S3 key
                        filename = s3_key.split('/')[-1]
                        
                        # Add file to ZIP
                        zip_file.writestr(filename, file_content)
                        files_added += 1
                        
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'NoSuchKey':
                            errors.append({'id': doc_id, 'error': 'File not found'})
                        else:
                            errors.append({'id': doc_id, 'error': 'Download failed'})
                            
                except Exception as e:
                    logger.error(f"Error processing document {doc_id}: {str(e)}")
                    errors.append({'id': doc_id, 'error': 'Processing error'})
            
        if files_added == 0:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'No files could be downloaded',
                    'errors': errors
                })
            }
        
        # Generate unique filename for the ZIP
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"redacted_documents_{timestamp}.zip"
        
        # Upload ZIP to a temporary location in S3
        zip_key = f"temp/{user_prefix}/{zip_filename}"
        zip_buffer.seek(0)
        
        s3.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=zip_key,
            Body=zip_buffer.getvalue(),
            ContentType='application/zip',
            Metadata={
                'files_count': str(files_added),
                'created_by': user_context['user_id']
            }
        )
        
        # Generate presigned URL for the ZIP file (valid for 1 hour)
        download_url = generate_presigned_url(PROCESSED_BUCKET, zip_key, expiration=3600)
        
        # Schedule deletion of the temporary ZIP file after 1 hour
        # Note: In production, you might want to use S3 lifecycle policies or a cleanup Lambda
        
        response_data = {
            'download_url': download_url,
            'filename': zip_filename,
            'files_count': files_added,
            'expires_in': 3600
        }
        
        if errors:
            response_data['errors'] = errors
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(f"Error in batch download: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Batch download failed'})
        }

def handle_combine_documents(event, headers, context, user_context):
    """Handle POST /documents/combine endpoint to combine multiple files into one"""
    try:
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid request body'})
            }
        
        document_ids = body.get('document_ids', [])
        base_filename = body.get('output_filename', 'combined_document')
        separator = body.get('separator', '\n\n--- Document Break ---\n\n')
        
        # Generate timestamp for unique naming
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Clean the base filename and ensure proper extension
        if base_filename.endswith(('.txt', '.md')):
            name_parts = os.path.splitext(base_filename)
            output_filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
        else:
            output_filename = f"{base_filename}_{timestamp}.txt"
        
        if not document_ids:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No document IDs provided'})
            }
        
        # Limit batch size to prevent timeout
        max_batch_size = 20
        if len(document_ids) > max_batch_size:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Maximum batch size is {max_batch_size} files'})
            }
        
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        combined_content = []
        
        # Get files from processed bucket
        for doc_id in document_ids:
            # Clean the document ID
            clean_doc_id = unquote_plus(doc_id).strip()
            
            # Check if this is a full S3 key or just a filename
            if clean_doc_id.startswith('processed/'):
                # Full S3 key - verify it belongs to this user
                expected_prefix = f"processed/{user_prefix}/"
                if not clean_doc_id.startswith(expected_prefix):
                    logger.warning(f"Access denied to document: {clean_doc_id}")
                    continue
                # Use the key directly
                prefix = clean_doc_id
            else:
                # Just a filename - build the full prefix
                # Security check - ensure doc_id doesn't contain path traversal
                if '..' in clean_doc_id:
                    logger.warning(f"Invalid document ID: {clean_doc_id}")
                    continue
                prefix = f"processed/{user_prefix}/{clean_doc_id}"
            
            try:
                processed_file = None
                
                # If we have a full S3 key, use it directly
                if clean_doc_id.startswith('processed/'):
                    # Verify the file exists and is a valid type
                    try:
                        s3.head_object(Bucket=PROCESSED_BUCKET, Key=clean_doc_id)
                        if (clean_doc_id.endswith('.txt') or clean_doc_id.endswith('.md') or 
                            clean_doc_id.endswith('.csv')) and not clean_doc_id.endswith('.zip'):
                            processed_file = clean_doc_id
                    except ClientError:
                        logger.warning(f"File not found: {clean_doc_id}")
                        continue
                else:
                    # List objects with the prefix
                    response = s3.list_objects_v2(
                        Bucket=PROCESSED_BUCKET,
                        Prefix=prefix,
                        MaxKeys=10
                    )
                    
                    if 'Contents' not in response or len(response['Contents']) == 0:
                        logger.warning(f"No files found for document: {clean_doc_id}")
                        continue
                    
                    # Find the processed file (should end with .txt, .md, or .csv)
                    for obj in response['Contents']:
                        key = obj['Key']
                        if (key.endswith('.txt') or key.endswith('.md') or key.endswith('.csv')) and not key.endswith('.zip'):
                            processed_file = key
                            break
                
                if not processed_file:
                    logger.warning(f"No processed text file found for document: {clean_doc_id}")
                    continue
                
                # Download file content
                file_obj = s3.get_object(Bucket=PROCESSED_BUCKET, Key=processed_file)
                content = file_obj['Body'].read().decode('utf-8', errors='replace')
                
                # Add document header with metadata for better LLM parsing and vector DB indexing
                file_name = os.path.basename(processed_file)
                doc_number = len(combined_content) + 1
                
                # Create a structured header that LLMs can easily parse
                header = f"""
{'='*80}
DOCUMENT #{doc_number}: {file_name}
SOURCE: {processed_file}
{'='*80}

"""
                # Add the content with clear boundaries
                combined_content.append(f"{header}{content}")
                
            except ClientError as e:
                logger.error(f"Error accessing file {clean_doc_id}: {str(e)}")
                continue
        
        if not combined_content:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'No valid documents found to combine'})
            }
        
        # Create table of contents for easy navigation
        toc_lines = [
            "="*80,
            "TABLE OF CONTENTS",
            "="*80,
            f"Total Documents: {len(combined_content)}",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            "",
            "Documents included in this combined file:",
            ""
        ]
        
        # Extract document names from combined_content headers
        for i, content in enumerate(combined_content, 1):
            # Extract filename from the header
            lines = content.split('\n')
            for line in lines:
                if line.startswith('DOCUMENT #'):
                    doc_name = line.split(':', 1)[1].strip() if ':' in line else f"Document {i}"
                    toc_lines.append(f"{i}. {doc_name}")
                    break
        
        toc_lines.extend(["", "="*80, "", ""])
        table_of_contents = '\n'.join(toc_lines)
        
        # Join all content with enhanced separator for clear document boundaries
        enhanced_separator = f"\n\n{separator}\n{'#'*80}\n# END OF DOCUMENT\n{'#'*80}\n{separator}\n\n"
        final_content = table_of_contents + enhanced_separator.join(combined_content)
        
        # Generate unique document ID for combined file
        document_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        # Save combined file to processed bucket
        combined_key = f"processed/{user_prefix}/{document_id}/{output_filename}"
        
        s3.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=combined_key,
            Body=final_content.encode('utf-8'),
            ContentType='text/plain',
            Metadata={
                'user_id': user_context['user_id'],
                'document_id': document_id,
                'combined_from': json.dumps(document_ids[:10]),  # Store first 10 IDs
                'file_count': str(len(combined_content)),
                'timestamp': str(timestamp),
                'combined': 'true'
            }
        )
        
        # Generate download URL
        download_url = generate_presigned_url(
            PROCESSED_BUCKET,
            combined_key
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Documents combined successfully',
                'document_id': document_id,
                'filename': output_filename,
                'file_count': len(combined_content),
                'download_url': download_url,
                'size': len(final_content)
            })
        }
        
    except Exception as e:
        logger.error(f"Error combining documents: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to combine documents'})
        }

def validate_string_api_key(api_key):
    """Validate API key from Parameter Store (checks both current and old keys during grace period)"""
    try:
        # Check cache first (simple in-memory cache)
        cache_key = f"api_key_{api_key[:8]}"  # Use first 8 chars as cache key
        
        # Try to get from Parameter Store
        stage = os.environ.get('STAGE', 'prod')
        # Map 'production' to 'prod' for consistency
        if stage == 'production':
            stage = 'prod'
        parameter_name = f"/redact/api-keys/string-{stage}"
        
        # Check current API key
        try:
            response = ssm.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            
            stored_config = json.loads(response['Parameter']['Value'])
            
            if stored_config.get('key') == api_key:
                logger.info("API key validated successfully (current key)")
                return {
                    'user_id': stored_config.get('user_id', 'string-integration'),
                    'name': stored_config.get('name', 'String.com Integration'),
                    'permissions': stored_config.get('permissions', ['api:string:redact']),
                    'config_override': stored_config.get('config_override', {})
                }
        except ssm.exceptions.ParameterNotFound:
            logger.warning(f"API key parameter not found: {parameter_name}")
        except Exception as e:
            logger.error(f"Error validating current API key: {str(e)}")
        
        # Check old API key during grace period
        old_parameter_name = f"/redact/api-keys/string-{stage}-old"
        try:
            response = ssm.get_parameter(
                Name=old_parameter_name,
                WithDecryption=True
            )
            
            # For old keys, we just check the raw value
            if response['Parameter']['Value'] == api_key:
                logger.info("API key validated successfully (old key during grace period)")
                return {
                    'user_id': 'string-integration',
                    'name': 'String.com Integration (Grace Period)',
                    'permissions': ['api:string:redact'],
                    'config_override': {}
                }
        except ssm.exceptions.ParameterNotFound:
            # No old key exists, which is normal
            pass
        except Exception as e:
            logger.error(f"Error validating old API key: {str(e)}")
        
        return None
        
    except Exception as e:
        logger.error(f"API key validation error: {str(e)}")
        return None

def handle_string_redact(event, headers, context):
    """
    Handle String.com redaction endpoint
    POST /api/string/redact
    Note: This endpoint requires both API Gateway key (x-api-key) and Bearer token
    """
    try:
        # Check for API Gateway key (handled by API Gateway, but we can log it)
        api_gateway_key = event.get('headers', {}).get('x-api-key', '')
        if api_gateway_key:
            logger.info("Request includes API Gateway key for rate limiting")
        
        # Extract bearer token
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing or invalid authorization header',
                    'error_code': 'AUTH_REQUIRED'
                })
            }
        
        api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Validate API key
        api_context = validate_string_api_key(api_key)
        if not api_context:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': 'Invalid API key',
                    'error_code': 'INVALID_API_KEY'
                })
            }
        
        # Parse request body
        try:
            body = event.get('body', '')
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(body).decode('utf-8')
            
            data = json.loads(body)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': 'Invalid JSON in request body',
                    'error_code': 'INVALID_JSON'
                })
            }
        
        # Get text to redact
        text = data.get('text', '')
        if not text:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': 'No text provided',
                    'error_code': 'MISSING_TEXT'
                })
            }
        
        # Check text size (1MB limit)
        if len(text.encode('utf-8')) > 1024 * 1024:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': 'Text exceeds 1MB limit',
                    'error_code': 'TEXT_TOO_LARGE'
                })
            }
        
        # Get configuration
        inline_config = data.get('config', None)
        if inline_config:
            config = inline_config
        else:
            # Load user's saved configuration
            user_id = api_context['user_id']
            user_config_key = f'configs/users/{user_id}/config.json'
            
            try:
                response = s3.get_object(
                    Bucket=CONFIG_BUCKET,
                    Key=user_config_key
                )
                config = json.loads(response['Body'].read())
            except s3.exceptions.NoSuchKey:
                # Use default String.com config
                config = {
                    "conditional_rules": [
                        {
                            "name": "Choice Hotels",
                            "enabled": True,
                            "trigger": {
                                "contains": ["Choice Hotels", "Choice"],
                                "case_sensitive": False
                            },
                            "replacements": [
                                {"find": "Choice Hotels", "replace": "CH"},
                                {"find": "Choice", "replace": "CH"}
                            ]
                        },
                        {
                            "name": "Cronos",
                            "enabled": True,
                            "trigger": {
                                "contains": ["Cronos"],
                                "case_sensitive": False
                            },
                            "replacements": [
                                {"find": "Cronos", "replace": "CR"}
                            ]
                        }
                    ],
                    "replacements": [],
                    "case_sensitive": False,
                    "patterns": {}
                }
        
        # Apply config override from API key if present
        if api_context.get('config_override'):
            config.update(api_context['config_override'])
        
        # Import and use the Lambda processor's redaction function
        start_time = time.time()
        
        # Since we can't directly import from Lambda, we'll replicate the logic here
        # In production, you might want to share code via a Lambda layer
        redacted_text, replacement_count = apply_redaction_for_api(text, config)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log the redaction for monitoring
        logger.info(json.dumps({
            'event': 'STRING_REDACTION',
            'user_id': api_context['user_id'],
            'text_length': len(text),
            'replacements_made': replacement_count,
            'processing_time_ms': processing_time
        }))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'redacted_text': redacted_text,
                'replacements_made': replacement_count,
                'processing_time_ms': processing_time
            })
        }
        
    except Exception as e:
        logger.error(f"String redaction error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error',
                'error_code': 'INTERNAL_ERROR'
            })
        }

def handle_test_redaction(event, headers, context, user_context):
    """Handle POST /api/test-redaction endpoint for UI testing"""
    try:
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        data = json.loads(body)
        text = data.get('text', '')
        config = data.get('config', {})
        
        # Apply redaction
        redacted_text, replacement_count = apply_redaction_for_api(text, config)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'redacted_text': redacted_text,
                'replacements_made': replacement_count
            })
        }
        
    except Exception as e:
        logger.error(f"Test redaction error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Test redaction failed'})
        }

def apply_redaction_for_api(text, config):
    """
    Apply redaction rules to text (simplified version for API)
    This replicates the Lambda processor logic
    """
    import re
    
    if not config:
        return text, 0
    
    processed_text = text
    replacement_count = 0
    case_sensitive = config.get('case_sensitive', False)
    
    # Apply conditional rules first
    conditional_rules = config.get('conditional_rules', [])
    for rule in conditional_rules:
        if not rule.get('enabled', True):
            continue
            
        trigger = rule.get('trigger', {})
        trigger_contains = trigger.get('contains', [])
        trigger_case_sensitive = trigger.get('case_sensitive', False)
        
        # Check if any trigger words exist
        trigger_matched = False
        for trigger_word in trigger_contains:
            if not trigger_word:
                continue
                
            if trigger_case_sensitive:
                if trigger_word in text:
                    trigger_matched = True
                    break
            else:
                if trigger_word.lower() in text.lower():
                    trigger_matched = True
                    break
        
        # Apply rule's replacements if triggered
        if trigger_matched:
            rule_replacements = rule.get('replacements', [])
            for replacement in rule_replacements:
                find_text = replacement.get('find', '')
                replace_text = replacement.get('replace', '[REDACTED]')
                
                if not find_text:
                    continue
                
                # Create pattern
                rule_case_sensitive = replacement.get('case_sensitive', trigger_case_sensitive)
                if rule_case_sensitive:
                    pattern = re.escape(find_text)
                else:
                    pattern = f"(?i){re.escape(find_text)}"
                
                # Count and apply replacements
                matches = list(re.finditer(pattern, processed_text))
                if matches:
                    replacement_count += len(matches)
                    processed_text = re.sub(pattern, replace_text, processed_text)
    
    # Apply global replacements
    replacements = config.get('replacements', [])
    for replacement in replacements:
        find_text = replacement.get('find', '')
        replace_text = replacement.get('replace', '[REDACTED]')
        
        if not find_text:
            continue
        
        # Create pattern
        if case_sensitive:
            pattern = re.escape(find_text)
        else:
            pattern = f"(?i){re.escape(find_text)}"
        
        # Count and apply replacements
        matches = list(re.finditer(pattern, processed_text))
        if matches:
            replacement_count += len(matches)
            processed_text = re.sub(pattern, replace_text, processed_text)
    
    # Apply PII patterns if enabled
    patterns = config.get('patterns', {})
    if patterns:
        # Common PII patterns
        PII_PATTERNS = {
            "ssn": {
                "pattern": r"\b(?:\d{3}-\d{2}-\d{4}|\d{3}\s\d{2}\s\d{4}|\d{9})\b",
                "replace": "[SSN]"
            },
            "credit_card": {
                "pattern": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
                "replace": "[CREDIT_CARD]"
            },
            "phone": {
                "pattern": r"\b(?:\+?1[\s\-\.]?)?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b",
                "replace": "[PHONE]"
            },
            "email": {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "replace": "[EMAIL]"
            },
            "ip_address": {
                "pattern": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
                "replace": "[IP_ADDRESS]"
            },
            "drivers_license": {
                "pattern": r"\b[A-Z][0-9]{4,8}\b",
                "replace": "[DL]"
            }
        }
        
        for pattern_name, enabled in patterns.items():
            if enabled and pattern_name in PII_PATTERNS:
                pii_config = PII_PATTERNS[pattern_name]
                pattern = pii_config['pattern']
                replace = pii_config['replace']
                
                matches = list(re.finditer(pattern, processed_text))
                if matches:
                    replacement_count += len(matches)
                    processed_text = re.sub(pattern, replace, processed_text)
    
    return processed_text, replacement_count

# AI Summary Helper Functions
anthropic_client = None
bedrock_runtime = None

def get_claude_client():
    """Get or create AnthropicBedrock client (preferred) or fallback to direct Bedrock"""
    global anthropic_client, bedrock_runtime
    
    if AnthropicBedrock and not anthropic_client:
        logger.info("Creating new AnthropicBedrock client")
        try:
            anthropic_client = AnthropicBedrock(
                aws_region=os.environ.get('AWS_REGION', 'us-east-1')
            )
            logger.info("AnthropicBedrock client created successfully")
        except Exception as e:
            logger.error(f"Error creating AnthropicBedrock client: {str(e)}")
            anthropic_client = None
    
    # Fallback to direct Bedrock client
    if not anthropic_client and not bedrock_runtime:
        logger.info("Creating fallback Bedrock runtime client")
        try:
            bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
            logger.info("Bedrock runtime client created successfully")
        except Exception as e:
            logger.error(f"Error creating Bedrock client: {str(e)}")
            raise
    
    return anthropic_client or bedrock_runtime

def get_ai_config():
    """Get AI configuration from SSM Parameter Store"""
    try:
        param_name = os.environ.get('AI_CONFIG_PARAM', '/redact/ai-config')
        response = ssm.get_parameter(Name=param_name)
        return json.loads(response['Parameter']['Value'])
    except Exception as e:
        logger.error(f"Error loading AI config: {str(e)}")
        return {
            'enabled': False,
            'error': f'Failed to load AI config: {str(e)}'
        }

def generate_ai_summary_internal(text, summary_type='standard', user_role='user', model_override=None):
    """Generate AI summary for document text using Claude SDK or AWS Bedrock"""
    global anthropic_client, bedrock_runtime
    
    try:
        ai_config = get_ai_config()
        
        if not ai_config.get('enabled', False):
            raise ValueError("AI summaries are not enabled")
        
        # Select model based on priority: model_override > admin override > default
        if model_override:
            model_id = model_override
        elif user_role == 'admin' and ai_config.get('admin_override_model'):
            model_id = ai_config['admin_override_model']
        else:
            model_id = ai_config.get('default_model', 'anthropic.claude-3-haiku-20240307-v1:0')
        
        # Map direct foundation model IDs to inference profile IDs for Claude 4 models
        model_mapping = {
            'anthropic.claude-opus-4-20250514-v1:0': 'us.anthropic.claude-opus-4-20250514-v1:0',
            'anthropic.claude-sonnet-4-20250514-v1:0': 'us.anthropic.claude-sonnet-4-20250514-v1:0',
            'anthropic.claude-opus-4-1-20250805-v1:0': 'us.anthropic.claude-opus-4-1-20250805-v1:0'
        }
        
        original_model_id = model_id
        if model_id in model_mapping:
            model_id = model_mapping[model_id]
            logger.info(f"AI Summary: Mapped {original_model_id} -> {model_id}")
        else:
            logger.info(f"AI Summary: Using model_id = {model_id}")
        
        # Get summary configuration
        summary_configs = ai_config.get('summary_types', {})
        summary_config = summary_configs.get(summary_type, summary_configs.get('standard', {}))
        
        max_tokens = summary_config.get('max_tokens', 500)
        temperature = summary_config.get('temperature', 0.5)
        instruction = summary_config.get('instruction', 'Summarize this document.')
        
        # Get the Claude client (SDK or fallback to Bedrock)
        client = get_claude_client()
        
        # Use Claude SDK if available
        if client == anthropic_client and anthropic_client:
            logger.info(f"Using Claude SDK with model: {model_id}")
            try:
                message = anthropic_client.messages.create(
                    model=model_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{instruction}\n\nDocument content:\n{text[:10000]}\n\nPlease provide a clear, well-structured summary."
                        }
                    ]
                )
                summary = message.content[0].text.strip()
                logger.info(f"Claude SDK response received, length: {len(summary)}")
                
            except Exception as sdk_error:
                logger.error(f"Claude SDK error: {str(sdk_error)}")
                # Fall through to Bedrock fallback
                if not bedrock_runtime:
                    bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
                client = bedrock_runtime
        
        # Use direct Bedrock if Claude SDK unavailable or failed
        if client == bedrock_runtime or not anthropic_client:
            logger.info(f"Using direct Bedrock with model: {model_id}")
            
            # Format request based on model type
            if any(x in model_id for x in ["claude-3", "claude-4", "opus-4", "sonnet-4"]):
                # Use Messages API for Claude 3+ models
                request_body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{instruction}\nDocument content:\n{text[:10000]}\nPlease provide a clear, well-structured summary."
                        }
                    ]
                })
            else:
                # Legacy format for older models
                request_body = json.dumps({
                    "prompt": f"""Human: {instruction}\n\nDocument content:\n{text[:10000]}\n\nPlease provide a clear, well-structured summary.\n\nAssistant:""",
                    "max_tokens_to_sample": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "stop_sequences": ["\n\nHuman:"]
                })
            
            # Invoke the model  
            logger.info(f"BEDROCK INVOCATION DEBUG:")
            logger.info(f"  model_id: {model_id}")
            logger.info(f"  client region: {client._client_config.region_name}")
            logger.info(f"  request_body size: {len(request_body)}")
            
            response = client.invoke_model(
                modelId=model_id,
                contentType='application/json',
                accept='application/json',
                body=request_body
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            logger.info(f"Bedrock response: {json.dumps(response_body)[:200]}...")
            
            if any(x in model_id for x in ["claude-3", "claude-4", "opus-4", "sonnet-4"]):
                # Claude 3+ uses Messages API response format
                content = response_body.get('content', [])
                if content and isinstance(content, list) and len(content) > 0:
                    summary = content[0].get('text', '').strip()
                else:
                    summary = ''
            else:
                summary = response_body.get('completion', '').strip()
        
        logger.info(f"Extracted summary type: {type(summary)}, value: {str(summary)[:200]}...")  # Log summary type
        
        # Ensure summary is a string
        if not isinstance(summary, str):
            logger.warning(f"Summary is not a string, converting from {type(summary)}")
            summary = str(summary)
        
        # Create metadata
        metadata = {
            'model': model_id,
            'summary_type': summary_type,
            'generated_at': datetime.utcnow().isoformat(),
            'user_role': user_role,
            'max_tokens': str(max_tokens),
            'temperature': str(temperature)
        }
        
        return summary, metadata
        
    except Exception as e:
        logger.error(f"Error generating AI summary: {str(e)}")
        raise

# Enhanced Metadata Extraction Functions
def extract_document_metadata(content, filename, file_size=None):
    """
    Extract comprehensive metadata from document content
    Based on the core design document requirements
    """
    try:
        logger.info(f"Extracting metadata for document: {filename}")
        
        metadata = {
            'document_properties': extract_document_properties(filename, file_size),
            'extracted_entities': extract_entities(content),
            'document_structure': analyze_document_structure(content),
            'temporal_data': extract_temporal_data(content),
            'topics_and_keywords': extract_topics_and_keywords(content)
        }
        
        logger.info(f"Metadata extraction complete: {len(metadata)} categories")
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        return {
            'error': str(e),
            'extraction_timestamp': datetime.utcnow().isoformat()
        }

def extract_document_properties(filename, file_size):
    """Extract basic document properties"""
    file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    # Infer document type from filename and extension
    doc_type = infer_document_type(filename)
    
    return {
        'filename': filename,
        'file_extension': file_ext,
        'inferred_type': doc_type,
        'file_size': file_size,
        'processed_at': datetime.utcnow().isoformat()
    }

def infer_document_type(filename):
    """Infer document type from filename patterns"""
    filename_lower = filename.lower()
    
    # Policy and procedure patterns
    if any(word in filename_lower for word in ['policy', 'policies', 'procedure', 'standard']):
        return 'policy'
    
    # Evidence and report patterns
    if any(word in filename_lower for word in ['report', 'evidence', 'audit', 'log', 'access']):
        return 'evidence'
    
    # Configuration and technical patterns
    if any(word in filename_lower for word in ['config', 'settings', 'technical', 'system']):
        return 'technical'
    
    # Financial and business patterns
    if any(word in filename_lower for word in ['financial', 'budget', 'invoice', 'contract']):
        return 'financial'
    
    return 'document'

def extract_entities(content):
    """Extract named entities from document content"""
    entities = {
        'people': extract_people_names(content),
        'organizations': extract_organizations(content),
        'locations': extract_locations(content),
        'monetary_values': extract_monetary_values(content),
        'percentages': extract_percentages(content),
        'email_addresses': extract_emails(content),
        'phone_numbers': extract_phone_numbers(content),
        'ip_addresses': extract_ip_addresses(content)
    }
    
    # Remove empty lists
    return {k: v for k, v in entities.items() if v}

def extract_people_names(content):
    """Extract potential people names (basic pattern matching)"""
    # Pattern for common name formats (First Last, First Middle Last)
    name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b'
    names = re.findall(name_pattern, content)
    
    # Filter out common false positives
    false_positives = {'New York', 'Los Angeles', 'San Francisco', 'United States', 'North America'}
    names = [name for name in set(names) if name not in false_positives]
    
    return names[:10]  # Limit to first 10 unique names

def extract_organizations(content):
    """Extract organization names"""
    # Patterns for common organization formats
    org_patterns = [
        r'\b[A-Z][A-Za-z\s&]+ (?:Inc|LLC|Corp|Corporation|Company|Ltd|Limited)\b',
        r'\b[A-Z][A-Za-z\s&]+ (?:Group|Associates|Partners|Solutions)\b',
        r'\b[A-Z]{2,}(?:\s[A-Z]{2,})*\b',  # Acronyms
    ]
    
    orgs = []
    for pattern in org_patterns:
        orgs.extend(re.findall(pattern, content))
    
    return list(set(orgs))[:10]  # Unique organizations, limit 10

def extract_locations(content):
    """Extract location names"""
    # Basic patterns for locations
    location_patterns = [
        r'\b[A-Z][a-z]+ (?:City|County|State|Province)\b',
        r'\b[A-Z][a-z]+, [A-Z]{2}\b',  # City, State format
        r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:, [A-Z]{2})?\b'  # City State format
    ]
    
    locations = []
    for pattern in location_patterns:
        locations.extend(re.findall(pattern, content))
    
    return list(set(locations))[:10]

def extract_monetary_values(content):
    """Extract monetary values"""
    money_pattern = r'\$[\d,]+(?:\.\d{2})?(?:[KMB])?|\$[\d.]+[KMB]'
    money_values = re.findall(money_pattern, content)
    return list(set(money_values))[:20]

def extract_percentages(content):
    """Extract percentage values"""
    percent_pattern = r'\d+(?:\.\d+)?%'
    percentages = re.findall(percent_pattern, content)
    return list(set(percentages))[:10]

def extract_emails(content):
    """Extract email addresses (redacted pattern)"""
    # Look for [EMAIL] redacted patterns and original emails if present
    email_patterns = [
        r'\[EMAIL\]',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ]
    
    emails = []
    for pattern in email_patterns:
        emails.extend(re.findall(pattern, content))
    
    return list(set(emails))

def extract_phone_numbers(content):
    """Extract phone numbers (including redacted patterns)"""
    phone_patterns = [
        r'\[PHONE\]',
        r'\(\d{3}\)\s?\d{3}-\d{4}',
        r'\d{3}-\d{3}-\d{4}',
        r'\d{3}\.\d{3}\.\d{4}'
    ]
    
    phones = []
    for pattern in phone_patterns:
        phones.extend(re.findall(pattern, content))
    
    return list(set(phones))

def extract_ip_addresses(content):
    """Extract IP addresses (including redacted patterns)"""
    ip_patterns = [
        r'\[IP_ADDRESS\]',
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ]
    
    ips = []
    for pattern in ip_patterns:
        ips.extend(re.findall(pattern, content))
    
    return list(set(ips))

def analyze_document_structure(content):
    """Analyze document structure (sections, tables, lists)"""
    structure = {
        'total_length': len(content),
        'word_count': len(content.split()),
        'line_count': len(content.split('\n')),
        'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
    }
    
    # Count markdown-style headers
    headers = len(re.findall(r'^#+\s', content, re.MULTILINE))
    if headers > 0:
        structure['headers'] = headers
    
    # Count table-like structures
    tables = len(re.findall(r'\|.*\|', content))
    if tables > 2:  # At least header + 1 data row
        structure['tables'] = tables // 2
    
    # Count list items
    lists = len(re.findall(r'^\s*[-*+]\s', content, re.MULTILINE))
    numbered_lists = len(re.findall(r'^\s*\d+\.\s', content, re.MULTILINE))
    if lists > 0:
        structure['bullet_lists'] = lists
    if numbered_lists > 0:
        structure['numbered_lists'] = numbered_lists
    
    return structure

def extract_temporal_data(content):
    """Extract dates and time-related information"""
    temporal = {}
    
    # Date patterns
    date_patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
        r'\b\d{4}-\d{2}-\d{2}\b',      # YYYY-MM-DD
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
        r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b'     # DD Month YYYY
    ]
    
    dates = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, content, re.IGNORECASE))
    
    if dates:
        temporal['dates_found'] = list(set(dates))[:10]
    
    # Time periods and quarters
    periods = re.findall(r'\b(?:Q[1-4]|Quarter [1-4])\s+\d{4}\b', content, re.IGNORECASE)
    if periods:
        temporal['periods'] = list(set(periods))
    
    # Year references
    years = re.findall(r'\b20\d{2}\b', content)
    if years:
        temporal['years'] = sorted(list(set(years)))
    
    return temporal

def extract_topics_and_keywords(content):
    """Extract key topics and important keywords"""
    # Common business/technical keywords
    business_keywords = [
        'audit', 'compliance', 'security', 'risk', 'control', 'policy', 'procedure',
        'approval', 'review', 'access', 'authentication', 'authorization', 'encryption',
        'backup', 'monitoring', 'incident', 'vulnerability', 'assessment', 'testing'
    ]
    
    found_keywords = []
    content_lower = content.lower()
    
    for keyword in business_keywords:
        if keyword in content_lower:
            count = content_lower.count(keyword)
            found_keywords.append({'keyword': keyword, 'frequency': count})
    
    # Sort by frequency
    found_keywords.sort(key=lambda x: x['frequency'], reverse=True)
    
    # Extract potential topics (capitalized phrases)
    topic_pattern = r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b'
    topics = re.findall(topic_pattern, content)
    topic_counts = defaultdict(int)
    for topic in topics:
        if len(topic.split()) > 1 and len(topic) > 10:  # Multi-word, longer topics
            topic_counts[topic] += 1
    
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'keywords': found_keywords[:15],
        'topics': [{'topic': topic, 'frequency': freq} for topic, freq in top_topics]
    }

# Vector-Ready Chunk Preparation Functions
def prepare_document_for_vectors(content, filename, chunk_size=512, overlap=50, strategy='semantic'):
    """
    Prepare document content for vector database ingestion
    Based on the core design document vector preparation requirements
    """
    try:
        logger.info(f"Preparing document for vectors: {filename} (strategy: {strategy})")
        
        # Choose chunking strategy
        if strategy == 'semantic':
            chunks = semantic_chunking(content, chunk_size, overlap)
        elif strategy == 'structure':
            chunks = structure_based_chunking(content, chunk_size, overlap)
        else:
            chunks = size_based_chunking(content, chunk_size, overlap)
        
        # Process each chunk
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunk = {
                'chunk_index': i,
                'text': chunk['text'],
                'metadata': {
                    'source_filename': filename,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_size': len(chunk['text']),
                    'word_count': len(chunk['text'].split()),
                    'strategy': strategy,
                    **chunk.get('metadata', {})
                }
            }
            processed_chunks.append(processed_chunk)
        
        # Prepare response
        vector_ready_data = {
            'chunks': processed_chunks,
            'total_chunks': len(processed_chunks),
            'chunking_strategy': strategy,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'embedding_ready': True,
            'recommended_embedding_model': 'text-embedding-ada-002',
            'preparation_timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Vector preparation complete: {len(processed_chunks)} chunks created")
        return vector_ready_data
        
    except Exception as e:
        logger.error(f"Error preparing document for vectors: {str(e)}")
        return {
            'error': str(e),
            'preparation_timestamp': datetime.utcnow().isoformat()
        }

def semantic_chunking(content, target_size, overlap):
    """Semantic chunking that tries to preserve meaning by splitting on sentences/paragraphs"""
    chunks = []
    
    # Split by paragraphs first
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    current_chunk = ""
    current_metadata = {'start_paragraph': 0}
    
    for i, paragraph in enumerate(paragraphs):
        # If adding this paragraph would exceed target size, finalize current chunk
        if current_chunk and len(current_chunk) + len(paragraph) > target_size:
            chunks.append({
                'text': current_chunk.strip(),
                'metadata': {
                    **current_metadata,
                    'end_paragraph': i - 1,
                    'paragraph_count': i - current_metadata['start_paragraph']
                }
            })
            
            # Start new chunk with overlap
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + "\n\n" + paragraph
            else:
                current_chunk = paragraph
            
            current_metadata = {'start_paragraph': i}
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add final chunk
    if current_chunk:
        chunks.append({
            'text': current_chunk.strip(),
            'metadata': {
                **current_metadata,
                'end_paragraph': len(paragraphs) - 1,
                'paragraph_count': len(paragraphs) - current_metadata['start_paragraph']
            }
        })
    
    return chunks

def structure_based_chunking(content, target_size, overlap):
    """Structure-based chunking that splits on headers, sections, and structural elements"""
    chunks = []
    
    # Split by headers first (markdown style)
    header_pattern = r'^(#{1,6}\s.+)$'
    lines = content.split('\n')
    
    current_chunk = ""
    current_section = "Introduction"
    section_start = 0
    
    for i, line in enumerate(lines):
        # Check for header
        header_match = re.match(header_pattern, line)
        if header_match:
            # Finalize previous chunk if it exists and is large enough
            if current_chunk and len(current_chunk) > 100:
                chunks.append({
                    'text': current_chunk.strip(),
                    'metadata': {
                        'section': current_section,
                        'section_start_line': section_start,
                        'section_end_line': i - 1
                    }
                })
            
            # Start new chunk
            current_section = header_match.group(1)
            section_start = i
            
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + "\n" + line
            else:
                current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line
        
        # If chunk is getting too large, split it
        if len(current_chunk) > target_size:
            chunk_text = current_chunk[:target_size]
            # Try to end at a sentence boundary
            last_period = chunk_text.rfind('.')
            if last_period > target_size * 0.7:  # At least 70% of target size
                chunk_text = chunk_text[:last_period + 1]
                remaining = current_chunk[last_period + 1:]
            else:
                remaining = current_chunk[target_size:]
            
            chunks.append({
                'text': chunk_text.strip(),
                'metadata': {
                    'section': current_section,
                    'section_start_line': section_start,
                    'partial_section': True
                }
            })
            
            current_chunk = remaining.strip()
    
    # Add final chunk
    if current_chunk:
        chunks.append({
            'text': current_chunk.strip(),
            'metadata': {
                'section': current_section,
                'section_start_line': section_start,
                'section_end_line': len(lines) - 1
            }
        })
    
    return chunks

def size_based_chunking(content, target_size, overlap):
    """Simple size-based chunking with optional overlap"""
    chunks = []
    
    # Split content into words for better boundary control
    words = content.split()
    
    start = 0
    chunk_index = 0
    
    while start < len(words):
        # Calculate end position
        end = start + target_size
        if end > len(words):
            end = len(words)
        
        # Get chunk text
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words)
        
        chunks.append({
            'text': chunk_text,
            'metadata': {
                'start_word': start,
                'end_word': end - 1,
                'word_count': len(chunk_words),
                'chunk_method': 'size_based'
            }
        })
        
        # Calculate next start position with overlap
        if overlap > 0 and start + target_size < len(words):
            start = end - overlap
        else:
            start = end
        
        chunk_index += 1
    
    return chunks

# Custom Redaction Pattern Functions
def create_custom_pattern(pattern_name, regex_pattern, replacement_text='[REDACTED]', description=''):
    """Create a custom redaction pattern"""
    return {
        'pattern_name': pattern_name,
        'regex': regex_pattern,
        'replacement': replacement_text,
        'description': description,
        'created_at': datetime.utcnow().isoformat(),
        'enabled': True,
        'pattern_type': 'custom'
    }

def get_builtin_patterns():
    """Get built-in redaction patterns as defined in the core design"""
    return {
        'ssn': {
            'pattern_name': 'ssn',
            'regex': r'\b\d{3}-\d{2}-\d{4}\b',
            'replacement': '[SSN]',
            'description': 'Social Security Numbers',
            'pattern_type': 'builtin'
        },
        'credit_card': {
            'pattern_name': 'credit_card',
            'regex': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'replacement': '[CREDIT_CARD]',
            'description': 'Credit Card Numbers',
            'pattern_type': 'builtin'
        },
        'phone': {
            'pattern_name': 'phone',
            'regex': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            'replacement': '[PHONE]',
            'description': 'Phone Numbers',
            'pattern_type': 'builtin'
        },
        'email': {
            'pattern_name': 'email',
            'regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'replacement': '[EMAIL]',
            'description': 'Email Addresses',
            'pattern_type': 'builtin'
        },
        'ip_address': {
            'pattern_name': 'ip_address',
            'regex': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'replacement': '[IP_ADDRESS]',
            'description': 'IP Addresses',
            'pattern_type': 'builtin'
        },
        'driver_license': {
            'pattern_name': 'driver_license',
            'regex': r'\b[A-Z]{1,2}[0-9]{6,8}\b',
            'replacement': '[DRIVER_LICENSE]',
            'description': 'Driver License Numbers',
            'pattern_type': 'builtin'
        }
    }

def apply_custom_redaction_patterns(content, patterns, case_sensitive=False):
    """Apply custom redaction patterns to content"""
    try:
        processed_content = content
        total_replacements = 0
        pattern_stats = {}
        
        for pattern_name, pattern_config in patterns.items():
            if not pattern_config.get('enabled', True):
                continue
                
            regex_pattern = pattern_config['regex']
            replacement = pattern_config['replacement']
            
            # Apply pattern with proper flags
            flags = 0 if case_sensitive else re.IGNORECASE
            
            # Count matches before replacement
            matches = re.findall(regex_pattern, processed_content, flags)
            match_count = len(matches)
            
            if match_count > 0:
                # Apply replacement
                processed_content = re.sub(regex_pattern, replacement, processed_content, flags=flags)
                total_replacements += match_count
                
                pattern_stats[pattern_name] = {
                    'matches_found': match_count,
                    'replacement_text': replacement,
                    'pattern_type': pattern_config.get('pattern_type', 'custom')
                }
        
        return {
            'processed_content': processed_content,
            'total_replacements': total_replacements,
            'pattern_statistics': pattern_stats,
            'redaction_summary': {
                'patterns_applied': len(pattern_stats),
                'total_patterns_available': len(patterns),
                'total_redactions': total_replacements
            }
        }
        
    except Exception as e:
        logger.error(f"Error applying custom redaction patterns: {str(e)}")
        return {
            'error': str(e),
            'processed_content': content,  # Return original content on error
            'total_replacements': 0
        }

def validate_regex_pattern(pattern):
    """Validate that a regex pattern is safe and functional"""
    try:
        # Test if pattern compiles
        compiled_pattern = re.compile(pattern)
        
        # Test with sample text to ensure it doesn't cause catastrophic backtracking
        test_text = "This is a test string with numbers 123-45-6789 and email@example.com"
        matches = compiled_pattern.findall(test_text)
        
        return True, "Pattern is valid"
        
    except re.error as e:
        return False, f"Invalid regex pattern: {str(e)}"
    except Exception as e:
        return False, f"Pattern validation error: {str(e)}"

def handle_ai_summary(event, headers, context, user_context):
    logger.info("=== handle_ai_summary called ===")
    logger.info(f"User context: {user_context}")
    try:
        logger.info("Starting AI summary generation process")
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Get document ID
        document_id = body.get('document_id')
        if not document_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Document ID required'})
            }
        
        # Get summary type (default to standard)
        summary_type = body.get('summary_type', 'standard')
        if summary_type not in ['brief', 'standard', 'detailed']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid summary_type. Must be brief, standard, or detailed'})
            }
        
        # Get model override if provided
        model_override = body.get('model')
        logger.info(f"Model override received: '{model_override}'")
        
        # Skip validation for now - allow all inference profile models
        if model_override:
            logger.info(f"Using model override: {model_override}")
        
        # Decode document ID to get S3 key
        from urllib.parse import unquote
        s3_key = unquote(document_id)
        
        # Security check: ensure the key belongs to the user
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        if not s3_key.startswith(f"processed/{user_prefix}/"):
            logger.warning(f"Access denied - Key: {s3_key}, User prefix: {user_prefix}")
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({'error': 'Access denied - you can only summarize your own files'})
            }
        
        # Check if document already has AI summary
        if "_AI" in s3_key:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Document already has an AI summary'})
            }
        
        # Get the document content
        try:
            obj = s3.get_object(Bucket=PROCESSED_BUCKET, Key=s3_key)
            document_content = obj['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error reading document: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to read document'})
            }
        
        # Generate AI summary
        try:
            logger.info(f"Calling generate_ai_summary_internal with summary_type={summary_type}, model={model_override}")
            summary_text, summary_metadata = generate_ai_summary_internal(
                document_content,
                summary_type=summary_type,
                user_role=user_context.get('user_role', 'user'),
                model_override=model_override
            )
            logger.info("AI summary generated successfully")
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': f'Failed to generate AI summary: {str(e)}'})
            }
        
        # Create new document with AI summary
        # Ensure summary_text is a string
        if not isinstance(summary_text, str):
            logger.error(f"Summary text is not a string: {type(summary_text)}, value: {summary_text}")
            summary_text = str(summary_text) if summary_text is not None else ""
            
        ai_header = f"""# AI Summary

**Generated by:** {summary_metadata['model']}  
**Summary Type:** {summary_metadata['summary_type']}  
**Generated at:** {summary_metadata['generated_at']}

{summary_text}

---

# Original Document

"""
        
        # Combine AI summary with original document
        logger.info(f"AI header type: {type(ai_header)}, summary_text type: {type(summary_text)}")
        logger.info(f"Document content type: {type(document_content)}")
        logger.info(f"AI header value: {repr(ai_header[:100])}")
        logger.info(f"Summary text value: {repr(summary_text[:100]) if isinstance(summary_text, str) else repr(summary_text)}")
        logger.info(f"Document content value: {repr(document_content[:100])}")
        
        # Ensure all parts are strings
        if not isinstance(ai_header, str):
            logger.error(f"AI header is not a string: {type(ai_header)}")
            ai_header = str(ai_header)
        if not isinstance(document_content, str):
            logger.error(f"Document content is not a string: {type(document_content)}")
            document_content = str(document_content)
            
        # Final safety check before concatenation
        try:
            new_content = str(ai_header) + str(document_content)
        except Exception as e:
            logger.error(f"Error concatenating content: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to create AI document'})
            }
            
        logger.info(f"New content type: {type(new_content)}, length: {len(new_content)}")
        
        # Create new filename with _AI suffix
        original_filename = s3_key.split('/')[-1]
        if original_filename.endswith('.md'):
            new_filename = original_filename[:-3] + '_AI.md'
        else:
            new_filename = original_filename.rsplit('.', 1)[0] + '_AI.' + original_filename.rsplit('.', 1)[1]
        
        # Save to S3
        new_key = '/'.join(s3_key.split('/')[:-1]) + '/' + new_filename
        
        try:
            # Convert all metadata values to strings
            logger.info(f"Summary metadata before conversion: {summary_metadata}")
            safe_metadata = {
                'original_document': s3_key,
                'ai_summary': 'true'
            }
            for key, value in summary_metadata.items():
                safe_metadata[key] = str(value) if value is not None else ''
            logger.info(f"Safe metadata after conversion: {safe_metadata}")
            
            # Ensure new_content is a string and encode it
            if not isinstance(new_content, str):
                logger.error(f"new_content is not a string before encoding: {type(new_content)}")
                new_content = str(new_content)
            
            encoded_content = new_content.encode('utf-8')
            
            s3.put_object(
                Bucket=PROCESSED_BUCKET,
                Key=new_key,
                Body=encoded_content,
                ContentType='text/plain',
                Metadata=safe_metadata
            )
            
            # Generate presigned URL WITHOUT download disposition for AI summary
            # (We don't want it to auto-download, just be viewable)
            download_url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': PROCESSED_BUCKET,
                    'Key': new_key
                },
                ExpiresIn=3600
            )
            
            result = {
                'success': True,
                'filename': new_filename,
                's3_key': new_key,
                'metadata': summary_metadata,
                'download_url': download_url
            }
            
        except Exception as e:
            logger.error(f"Error saving AI document: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to save AI document'})
            }
        
        # Return success response
        # Don't include download_url to avoid potential browser navigation issues
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'AI summary added successfully',
                'document_id': document_id,
                'new_filename': result['filename'],
                # 'download_url': result['download_url'],  # Removed to prevent browser navigation
                'summary_metadata': result['metadata']
            })
        }
        
    except Exception as e:
        logger.error(f"Error in AI summary generation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'AI summary generation failed'})
        }

def handle_get_ai_config(headers, user_context):
    """Handle GET /api/ai-config endpoint to retrieve AI configuration"""
    try:
        # Check if user has admin role
        # Get AI configuration from SSM
        try:
            param_name = '/redact/ai-config'
            response = ssm.get_parameter(Name=param_name)
            ai_config = json.loads(response['Parameter']['Value'])
        except Exception as e:
            logger.error(f"Error getting AI config: {str(e)}")
            ai_config = {
                'enabled': True,
                'available_models': [],
                'available_summary_types': ['brief', 'standard', 'detailed'],
                'default_summary_type': 'standard'
            }
        
        if user_context.get('role') != 'admin':
            # Regular users get limited info but with available models
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'enabled': ai_config.get('enabled', True),
                    'available_models': ai_config.get('available_models', []),
                    'available_summary_types': list(ai_config.get('summary_types', {}).keys()) or ['brief', 'standard', 'detailed'],
                    'default_summary_type': ai_config.get('default_summary_type', 'standard'),
                    'default_model': ai_config.get('default_model')
                })
            }
        
        # Admin users get full configuration
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(ai_config)
        }
        
    except Exception as e:
        logger.error(f"Error getting AI config: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get AI configuration'})
        }

def handle_update_ai_config(event, headers, user_context):
    """Handle PUT /api/ai-config endpoint to update AI configuration (admin only)"""
    try:
        # Check if user has admin role
        if user_context.get('role') != 'admin':
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({'error': 'Admin access required'})
            }
        
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        ai_config = json.loads(body)
        
        # Validate AI configuration
        required_fields = ['enabled', 'default_model', 'available_models', 'summary_types']
        for field in required_fields:
            if field not in ai_config:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Get valid models from available_models config
        available_models = ai_config.get('available_models', [])
        if isinstance(available_models, list) and len(available_models) > 0 and isinstance(available_models[0], dict):
            # New format with model objects
            valid_models = [model['id'] for model in available_models]
        else:
            # Legacy format with simple list
            valid_models = available_models or [
                # Verified working models (tested 2025-08-26)
                'anthropic.claude-3-haiku-20240307-v1:0',
                'us.anthropic.claude-3-5-haiku-20241022-v1:0',
                'us.anthropic.claude-3-5-sonnet-20240620-v1:0',
                'us.anthropic.claude-sonnet-4-20250514-v1:0',
                'us.anthropic.claude-opus-4-20250514-v1:0'
            ]
        
        if ai_config['default_model'] not in valid_models:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid default_model'})
            }
        
        # Update SSM parameter
        param_name = '/redact/ai-config'
        ssm.put_parameter(
            Name=param_name,
            Value=json.dumps(ai_config, indent=2),
            Type='String',
            Overwrite=True
        )
        
        logger.info(json.dumps({
            'event': 'AI_CONFIG_UPDATED',
            'admin_user': user_context['email'],
            'default_model': ai_config['default_model']
        }))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'AI configuration updated successfully',
                'config': ai_config
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    except Exception as e:
        logger.error(f"Error updating AI config: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to update AI configuration'})
        }

def handle_list_quarantine_files(event, headers, context, user_context):
    """Handle GET /quarantine/files endpoint to list user's quarantined files"""
    try:
        user_id = user_context.get('user_id', 'anonymous')
        
        # List objects in the quarantine bucket for this user
        prefix = f'quarantine/users/{user_id}/'
        
        response = s3.list_objects_v2(
            Bucket=QUARANTINE_BUCKET,
            Prefix=prefix,
            MaxKeys=1000
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                # Skip the directory itself
                if obj['Key'] == prefix:
                    continue
                    
                # Extract filename from the key
                filename = obj['Key'].replace(prefix, '')
                
                # Get object metadata to find the quarantine reason
                try:
                    metadata_response = s3.head_object(
                        Bucket=QUARANTINE_BUCKET,
                        Key=obj['Key']
                    )
                    quarantine_reason = metadata_response.get('Metadata', {}).get('quarantine-reason', 'Unknown')
                    original_filename = metadata_response.get('Metadata', {}).get('original-filename', filename)
                except Exception as e:
                    logger.error(f"Error getting metadata for {obj['Key']}: {str(e)}")
                    quarantine_reason = 'Unknown'
                    original_filename = filename
                
                files.append({
                    'id': obj['Key'],
                    'filename': original_filename,
                    'quarantine_filename': filename,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'quarantine_reason': quarantine_reason
                })
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'files': files,
                'count': len(files)
            })
        }
        
    except Exception as e:
        logger.error(f"Error listing quarantine files: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to list quarantine files'})
        }

def handle_delete_quarantine_file(event, headers, context, user_context):
    """Handle DELETE /quarantine/{id} endpoint to delete a specific quarantined file"""
    try:
        user_id = user_context.get('user_id', 'anonymous')
        path = event.get('path', '')
        
        # Extract file ID from path
        if path.startswith('/quarantine/'):
            file_id = path[12:]  # Remove '/quarantine/' prefix
            file_id = unquote_plus(file_id)
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid path'})
            }
        
        # Validate that the file belongs to the user
        expected_prefix = f'quarantine/users/{user_id}/'
        if not file_id.startswith(expected_prefix):
            logger.warning(f"Unauthorized delete attempt by user {user_id} for file {file_id}")
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({'error': 'Forbidden'})
            }
        
        # Delete the file
        s3.delete_object(
            Bucket=QUARANTINE_BUCKET,
            Key=file_id
        )
        
        logger.info(f"Deleted quarantine file: {file_id} for user: {user_id}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'File deleted successfully',
                'file_id': file_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error deleting quarantine file: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to delete file'})
        }

def handle_delete_all_quarantine_files(event, headers, context, user_context):
    """Handle POST /quarantine/delete-all endpoint to delete all quarantined files for a user"""
    try:
        user_id = user_context.get('user_id', 'anonymous')
        
        # List all files for the user
        prefix = f'quarantine/users/{user_id}/'
        
        # Use paginator for large number of files
        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=QUARANTINE_BUCKET,
            Prefix=prefix
        )
        
        deleted_count = 0
        for page in page_iterator:
            if 'Contents' in page:
                # Prepare delete batch
                objects_to_delete = []
                for obj in page['Contents']:
                    if obj['Key'] != prefix:  # Skip directory
                        objects_to_delete.append({'Key': obj['Key']})
                
                # Delete in batches of up to 1000 objects
                if objects_to_delete:
                    response = s3.delete_objects(
                        Bucket=QUARANTINE_BUCKET,
                        Delete={
                            'Objects': objects_to_delete,
                            'Quiet': True
                        }
                    )
                    deleted_count += len(objects_to_delete)
        
        logger.info(f"Deleted {deleted_count} quarantine files for user: {user_id}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': f'Deleted {deleted_count} quarantine files',
                'deleted_count': deleted_count
            })
        }
        
    except Exception as e:
        logger.error(f"Error deleting all quarantine files: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to delete quarantine files'})
        }

def handle_extract_metadata(event, headers, context, user_context):
    """Handle POST /documents/extract-metadata endpoint to extract metadata from document content"""
    try:
        logger.info("Starting metadata extraction process")
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Get required parameters
        document_id = body.get('document_id')
        content = body.get('content')
        filename = body.get('filename', 'unknown.txt')
        file_size = body.get('file_size')
        extraction_types = body.get('extraction_types', ['all'])
        
        # If document_id is provided, fetch content from S3
        if document_id:
            user_id = user_context.get('user_id', 'anonymous')
            
            # The document_id is URL encoded S3 key from /user/files endpoint
            # Decode it to get the actual S3 key
            from urllib.parse import unquote
            s3_key = unquote(document_id)
            
            logger.info(f"Looking for document with S3 key: {s3_key}")
            
            # Check if document exists and get content
            try:
                response = s3.get_object(Bucket=PROCESSED_BUCKET, Key=s3_key)
                content = response['Body'].read()
                
                # If it's binary content, decode it
                if isinstance(content, bytes):
                    try:
                        content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        # For binary files like PDFs, we'll use the raw content
                        # The metadata extraction functions should handle this
                        pass
                
                # Get metadata from S3 object
                if not filename or filename == 'unknown.txt':
                    # Extract filename from the S3 key
                    filename = s3_key.split('/')[-1]
                    # Try to get original filename from metadata
                    original_filename = response.get('Metadata', {}).get('original-filename')
                    if original_filename:
                        filename = original_filename
                
                if not file_size:
                    file_size = response['ContentLength']
                    
                logger.info(f"Fetched document content for {s3_key}, size: {len(content) if isinstance(content, str) else len(content)} bytes")
                
                # Verify user owns this document by checking the S3 key path
                user_prefix = f"processed/users/{user_id}/"
                if not s3_key.startswith(user_prefix) and not s3_key.startswith("processed/") and user_id != "admin":
                    # For legacy files without user prefix, check if user is authorized
                    logger.warning(f"User {user_id} trying to access document outside their prefix: {s3_key}")
                    return {
                        'statusCode': 403,
                        'headers': headers,
                        'body': json.dumps({'error': 'Access denied - you can only extract metadata from your own files'})
                    }
                
            except ClientError as e:
                if e.response['Error']['Code'] in ['NoSuchKey', '404']:
                    logger.error(f"Document not found: {s3_key}")
                    return {
                        'statusCode': 404,
                        'headers': headers,
                        'body': json.dumps({'error': 'Document not found or access denied'})
                    }
                else:
                    logger.error(f"Error fetching document: {e}")
                    return {
                        'statusCode': 500,
                        'headers': headers,
                        'body': json.dumps({'error': 'Failed to fetch document content'})
                    }
        
        # If no content after trying to fetch, return error
        if not content:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Document content is required. Provide either content or document_id.'})
            }
        
        # Extract metadata based on requested types
        if 'all' in extraction_types:
            logger.info("Extracting all metadata types")
            metadata = extract_document_metadata(content, filename, file_size)
        else:
            logger.info(f"Extracting specific metadata types: {extraction_types}")
            metadata = {}
            
            if 'entities' in extraction_types:
                metadata['extracted_entities'] = extract_entities(content)
            
            if 'structure' in extraction_types:
                metadata['document_structure'] = analyze_document_structure(content)
            
            if 'temporal' in extraction_types:
                metadata['temporal_data'] = extract_temporal_data(content)
            
            if 'topics' in extraction_types:
                metadata['topics_and_keywords'] = extract_topics_and_keywords(content)
            
            if 'properties' in extraction_types:
                metadata['document_properties'] = extract_document_properties(filename, file_size)
        
        # Prepare response - flatten metadata to match frontend expectations
        flattened_metadata = {
            'document_id': document_id,
            'filename': filename,
            'file_size': file_size or 0,
            'content_type': get_content_type_from_filename(filename),
            'created_date': datetime.utcnow().isoformat(),
            'processing_info': {
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'processing_time_ms': 0,  # Would need to track actual time
                'method': 'document_analysis'
            }
        }
        
        # Add extracted content based on metadata structure
        if 'all' in extraction_types:
            # Flatten the nested metadata structure
            if 'extracted_entities' in metadata:
                flattened_metadata['entities'] = metadata['extracted_entities']
            
            if 'document_properties' in metadata:
                doc_props = metadata['document_properties']
                # Map document properties to expected fields
                if 'file_size' in doc_props and doc_props['file_size']:
                    flattened_metadata['file_size'] = doc_props['file_size']
                if 'processed_at' in doc_props:
                    flattened_metadata['creation_date'] = doc_props['processed_at']
            
            if 'topics_and_keywords' in metadata:
                topics = metadata['topics_and_keywords']
                if topics and 'topics' in topics:
                    flattened_metadata['content_analysis'] = {
                        'key_topics': topics['topics'][:10] if topics['topics'] else [],
                        'content_type': get_content_type_from_filename(filename),
                        'sentiment': 'neutral',  # Could be enhanced
                        'reading_level': 'standard'  # Could be enhanced
                    }
        
        response_data = {
            'success': True,
            'metadata': flattened_metadata
        }
        
        logger.info(f"Metadata extraction completed for {filename}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(f"Error in metadata extraction: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Metadata extraction failed: {str(e)}'})
        }

def handle_prepare_vectors(event, headers, context, user_context):
    """Handle POST /documents/prepare-vectors endpoint to prepare document content for vector databases"""
    try:
        logger.info("Starting vector preparation process")
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Get required parameters
        document_id = body.get('document_id')
        content = body.get('content')
        filename = body.get('filename', 'unknown.txt')
        
        # Vector preparation options
        chunk_size = body.get('chunk_size', 512)
        overlap = body.get('overlap', 50)
        strategy = body.get('strategy', 'semantic')  # semantic, structure, size
        
        if not content:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Document content is required'})
            }
        
        # Validate parameters
        if chunk_size < 100 or chunk_size > 2000:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'chunk_size must be between 100 and 2000'})
            }
        
        if overlap < 0 or overlap > chunk_size // 2:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'overlap must be between 0 and half of chunk_size'})
            }
        
        if strategy not in ['semantic', 'structure', 'size']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'strategy must be one of: semantic, structure, size'})
            }
        
        # If document_id is provided, verify user owns the document
        if document_id:
            user_id = user_context.get('user_id', 'anonymous')
            
            # Check if document exists in user's processed bucket
            try:
                processed_key = f'users/{user_id}/processed/{document_id}'
                s3.head_object(Bucket=PROCESSED_BUCKET, Key=processed_key)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey' or e.response['Error']['Code'] == '404':
                    return {
                        'statusCode': 403,
                        'headers': headers,
                        'body': json.dumps({'error': 'Access denied - you can only prepare vectors from your own files'})
                    }
                else:
                    raise
        
        # Prepare document for vector database
        vector_data = prepare_document_for_vectors(
            content=content,
            filename=filename,
            chunk_size=chunk_size,
            overlap=overlap,
            strategy=strategy
        )
        
        # Check for errors
        if 'error' in vector_data:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Vector preparation failed: {vector_data["error"]}'
                })
            }
        
        # Prepare response
        response_data = {
            'document_id': document_id,
            'filename': filename,
            'vector_ready': vector_data,
            'preparation_summary': {
                'total_chunks': vector_data['total_chunks'],
                'strategy_used': strategy,
                'avg_chunk_size': sum(chunk['metadata']['chunk_size'] for chunk in vector_data['chunks']) // len(vector_data['chunks']) if vector_data['chunks'] else 0,
                'embedding_ready': True
            }
        }
        
        logger.info(f"Vector preparation completed: {vector_data['total_chunks']} chunks for {filename}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(f"Error in vector preparation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Vector preparation failed: {str(e)}'})
        }

def handle_get_redaction_patterns(event, headers, context, user_context):
    """Handle GET /redaction/patterns endpoint to list available redaction patterns"""
    try:
        logger.info("Getting available redaction patterns")
        
        # Get built-in patterns
        builtin_patterns = get_builtin_patterns()
        
        # For now, we'll return built-in patterns
        # In a full implementation, you'd also load custom patterns from a database/S3
        all_patterns = builtin_patterns.copy()
        
        pattern_summary = {
            'total_patterns': len(all_patterns),
            'builtin_patterns': len([p for p in all_patterns.values() if p['pattern_type'] == 'builtin']),
            'custom_patterns': len([p for p in all_patterns.values() if p['pattern_type'] == 'custom'])
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'patterns': all_patterns,
                'summary': pattern_summary,
                'retrieved_at': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting redaction patterns: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to get redaction patterns: {str(e)}'})
        }

def handle_create_redaction_pattern(event, headers, context, user_context):
    """Handle POST /redaction/patterns endpoint to create custom redaction patterns"""
    try:
        logger.info("Creating custom redaction pattern")
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Get required parameters
        pattern_name = body.get('pattern_name', '').strip()
        regex_pattern = body.get('regex', '').strip()
        replacement_text = body.get('replacement', '[REDACTED]').strip()
        description = body.get('description', '').strip()
        
        # Validate parameters
        if not pattern_name:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'pattern_name is required'})
            }
        
        if not regex_pattern:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'regex pattern is required'})
            }
        
        # Validate regex pattern
        is_valid, validation_message = validate_regex_pattern(regex_pattern)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Invalid regex pattern',
                    'validation_error': validation_message
                })
            }
        
        # Create the pattern
        new_pattern = create_custom_pattern(
            pattern_name=pattern_name,
            regex_pattern=regex_pattern,
            replacement_text=replacement_text,
            description=description
        )
        
        # In a full implementation, you'd save this to a database or S3
        # For now, we'll return the created pattern
        
        logger.info(f"Created custom redaction pattern: {pattern_name}")
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'Custom redaction pattern created successfully',
                'pattern': new_pattern,
                'validation': validation_message
            })
        }
        
    except Exception as e:
        logger.error(f"Error creating custom redaction pattern: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to create redaction pattern: {str(e)}'})
        }

def handle_apply_redaction(event, headers, context, user_context):
    """Handle POST /redaction/apply endpoint to apply redaction patterns to content"""
    try:
        logger.info("Applying redaction patterns to content")
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Get required parameters
        content = body.get('content', '').strip()
        patterns_to_use = body.get('patterns', ['all'])  # Default to all patterns
        case_sensitive = body.get('case_sensitive', False)
        custom_patterns = body.get('custom_patterns', {})
        
        if not content:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'content is required'})
            }
        
        # Prepare patterns to apply
        patterns = {}
        
        if 'all' in patterns_to_use or 'builtin' in patterns_to_use:
            patterns.update(get_builtin_patterns())
        
        # Add specific builtin patterns if requested
        if 'all' not in patterns_to_use and 'builtin' not in patterns_to_use:
            builtin_patterns = get_builtin_patterns()
            for pattern_name in patterns_to_use:
                if pattern_name in builtin_patterns:
                    patterns[pattern_name] = builtin_patterns[pattern_name]
        
        # Add custom patterns
        if custom_patterns:
            # Validate custom patterns first
            for pattern_name, pattern_config in custom_patterns.items():
                regex_pattern = pattern_config.get('regex', '')
                if regex_pattern:
                    is_valid, validation_message = validate_regex_pattern(regex_pattern)
                    if is_valid:
                        patterns[pattern_name] = pattern_config
                    else:
                        logger.warning(f"Skipping invalid custom pattern '{pattern_name}': {validation_message}")
        
        if not patterns:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No valid patterns to apply'})
            }
        
        # Apply redaction
        redaction_result = apply_custom_redaction_patterns(
            content=content,
            patterns=patterns,
            case_sensitive=case_sensitive
        )
        
        # Check for errors
        if 'error' in redaction_result:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Redaction failed: {redaction_result["error"]}',
                    'original_content': content
                })
            }
        
        # Prepare response
        response_data = {
            'original_content': content,
            'redacted_content': redaction_result['processed_content'],
            'redaction_statistics': redaction_result['pattern_statistics'],
            'redaction_summary': redaction_result['redaction_summary'],
            'settings': {
                'case_sensitive': case_sensitive,
                'patterns_requested': patterns_to_use,
                'total_patterns_applied': len(patterns)
            },
            'processed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Redaction completed: {redaction_result['total_replacements']} replacements made")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(f"Error applying redaction: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Redaction failed: {str(e)}'})
        }