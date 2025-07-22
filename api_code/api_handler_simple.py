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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    # For testing without proper auth
    return {
        'user_id': 'test-user',
        'email': 'test@example.com',
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
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
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
        
        # Protected endpoints - check for authorization
        authorizer = event.get('requestContext', {}).get('authorizer', {})
        if not authorizer:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authentication required'})
            }
        
        if path == '/documents/upload' and method == 'POST':
            return handle_document_upload(event, headers, context, user_context)
            
        elif path.startswith('/documents/status') and method == 'GET':
            return handle_status_check(event, headers, context, user_context)
            
        elif path == '/user/files' and method == 'GET':
            return handle_list_user_files(event, headers, context, user_context)
            
        elif path == '/api/config' and method == 'GET':
            return handle_get_config(headers, user_context)
            
        elif path == '/api/config' and method == 'PUT':
            return handle_update_config(event, headers, user_context)
            
        elif path.startswith('/documents/') and method == 'DELETE':
            return handle_document_delete(event, headers, context, user_context)
            
        elif path == '/documents/batch-download' and method == 'POST':
            return handle_batch_download(event, headers, context, user_context)
            
        elif path == '/documents/combine' and method == 'POST':
            logger.info(f"Handling combine request for path: {path}")
            return handle_combine_documents(event, headers, context, user_context)
            
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

def handle_document_upload(event, headers, context, user_context):
    """Handle POST /documents/upload endpoint with user isolation"""
    try:
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
        
        # Check for existing files and add version number if needed
        base_key = f"{user_prefix}/{filename}"
        s3_key = base_key
        
        # Check if file exists and find next available version
        version = 1
        while True:
            try:
                s3.head_object(Bucket=INPUT_BUCKET, Key=s3_key)
                # File exists, try next version
                if '.' in filename:
                    name, ext = filename.rsplit('.', 1)
                    s3_key = f"{user_prefix}/{name} ({version}).{ext}"
                else:
                    s3_key = f"{user_prefix}/{filename} ({version})"
                version += 1
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # File doesn't exist, we can use this key
                    break
                else:
                    raise
        
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
            'statusCode': 202,
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
                    'download_url': generate_presigned_url(PROCESSED_BUCKET, obj['Key'])
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

def generate_presigned_url(bucket, key, expiration=3600):
    """Generate a presigned URL for downloading processed documents"""
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
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
        output_filename = body.get('output_filename', 'combined_document.txt')
        separator = body.get('separator', '\n\n--- Document Break ---\n\n')
        
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
                
                # Add document header
                file_name = os.path.basename(processed_file)
                combined_content.append(f"=== {file_name} ===\n\n{content}")
                
            except ClientError as e:
                logger.error(f"Error accessing file {clean_doc_id}: {str(e)}")
                continue
        
        if not combined_content:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'No valid documents found to combine'})
            }
        
        # Join all content with separator
        final_content = separator.join(combined_content)
        
        # Generate unique document ID for combined file
        document_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        # Ensure output filename has proper extension
        if not output_filename.endswith(('.txt', '.md')):
            output_filename = output_filename + '.txt'
        
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