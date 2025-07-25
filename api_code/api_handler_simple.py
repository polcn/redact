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

# Import external AI providers
from external_ai_providers import get_external_ai_provider

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

def get_unique_filename(bucket, prefix, base_filename):
    """
    Generate a unique filename by adding (1), (2), etc. if the file already exists
    Similar to Windows naming convention
    
    Args:
        bucket: S3 bucket name
        prefix: S3 prefix/directory path
        base_filename: Original filename
        
    Returns:
        Unique filename that doesn't exist in S3
    """
    # Split filename and extension
    if '.' in base_filename:
        name_part, extension = base_filename.rsplit('.', 1)
        extension = '.' + extension
    else:
        name_part = base_filename
        extension = ''
    
    # Check if original filename exists
    original_key = f"{prefix}/{base_filename}"
    try:
        s3.head_object(Bucket=bucket, Key=original_key)
        # File exists, need to find a unique name
        counter = 1
        while counter < 1000:  # Reasonable limit
            new_filename = f"{name_part} ({counter}){extension}"
            new_key = f"{prefix}/{new_filename}"
            try:
                s3.head_object(Bucket=bucket, Key=new_key)
                # This name also exists, try next
                counter += 1
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # File doesn't exist, we can use this name
                    return new_filename
                else:
                    raise
        # If we get here, too many duplicates
        raise ValueError(f"Too many duplicates of {base_filename}")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # Original file doesn't exist, can use original name
            return base_filename
        else:
            raise

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
            
        elif path == '/api/ai-config' and method == 'GET':
            return handle_get_ai_config(headers, user_context)
            
        elif path == '/api/ai-config' and method == 'PUT':
            return handle_update_ai_config(event, headers, user_context)
            
        elif path == '/api/external-ai-keys' and method == 'GET':
            return handle_get_external_ai_keys(headers, user_context)
            
        elif path == '/api/external-ai-keys' and method == 'PUT':
            return handle_update_external_ai_keys(event, headers, user_context)
            
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
        
        # Use smart naming function to get unique filename
        unique_filename = get_unique_filename(INPUT_BUCKET, user_prefix, filename)
        s3_key = f"{user_prefix}/{unique_filename}"
        
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
                'filename': unique_filename,
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
        
        # Log the bucket and prefix we're using
        logger.info(f"Listing files for user {user_context['user_id']} in bucket {PROCESSED_BUCKET} with prefix: processed/{user_prefix}/")
        
        # List files in processed bucket
        try:
            processed_response = s3.list_objects_v2(
                Bucket=PROCESSED_BUCKET,
                Prefix=f"processed/{user_prefix}/"
            )
            
            logger.info(f"S3 response: Found {len(processed_response.get('Contents', []))} files in processed bucket")
            
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
        except ClientError as e:
            logger.error(f"Error listing processed files: {str(e)}")
        
        # List files in input bucket (still processing)
        try:
            logger.info(f"Listing input files in bucket {INPUT_BUCKET} with prefix: {user_prefix}/")
            
            input_response = s3.list_objects_v2(
                Bucket=INPUT_BUCKET,
                Prefix=f"{user_prefix}/"
            )
            
            logger.info(f"S3 response: Found {len(input_response.get('Contents', []))} files in input bucket")
            
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
        except ClientError as e:
            logger.error(f"Error listing input files: {str(e)}")
        
        # Sort by last modified date, most recent first
        files.sort(key=lambda x: x['last_modified'], reverse=True)
        
        logger.info(f"Returning {len(files)} total files for user {user_context['user_id']}")
        
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
        # Extract filename from key for Content-Disposition header
        filename = key.split('/')[-1]
        
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket, 
                'Key': key,
                'ResponseContentDisposition': f'attachment; filename="{filename}"'
            },
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
        
        # Get unique filename using our smart naming function
        prefix = f"processed/{user_prefix}/{document_id}"
        unique_filename = get_unique_filename(PROCESSED_BUCKET, prefix, output_filename)
        
        # Save combined file to processed bucket
        combined_key = f"{prefix}/{unique_filename}"
        
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
        
        logger.info(f"Combine documents response - NOT including download_url, s3_key: {combined_key}")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Documents combined successfully',
                'document_id': document_id,
                'filename': unique_filename,
                'file_count': len(combined_content),
                's3_key': combined_key,
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
bedrock_runtime = None

def get_bedrock_client():
    """Get or create Bedrock runtime client"""
    global bedrock_runtime
    if not bedrock_runtime:
        logger.info("Creating new Bedrock runtime client")
        try:
            bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
            logger.info("Bedrock client created successfully")
        except Exception as e:
            logger.error(f"Error creating Bedrock client: {str(e)}")
            raise
    return bedrock_runtime

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

def generate_ai_summary_internal(text, summary_type='standard', user_role='user', selected_model=None):
    """Generate AI summary for document text using AWS Bedrock"""
    try:
        ai_config = get_ai_config()
        
        if not ai_config.get('enabled', False):
            raise ValueError("AI summaries are not enabled")
        
        # Model selection priority:
        # 1. User-selected model (if provided and allowed)
        # 2. Admin override model (if user is admin)
        # 3. Default model
        available_models = [
            # Claude models
            'anthropic.claude-3-haiku-20240307-v1:0',
            'anthropic.claude-3-sonnet-20240229-v1:0',
            'anthropic.claude-3-opus-20240229-v1:0',
            'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'anthropic.claude-3-5-haiku-20241022-v1:0',
            # Amazon Nova models (free tier)
            'amazon.nova-micro-v1:0',
            'amazon.nova-lite-v1:0',
            'amazon.nova-pro-v1:0',
            # Meta Llama models
            'meta.llama3-2-1b-instruct-v1:0',
            'meta.llama3-2-3b-instruct-v1:0',
            'meta.llama3-8b-instruct-v1:0',
            # Mistral models
            'mistral.mistral-7b-instruct-v0:2',
            'mistral.mistral-small-2402-v1:0',
            # DeepSeek models
            'deepseek.r1-v1:0',
            # OpenAI models
            'openai.gpt-4o',
            'openai.gpt-4o-mini',
            'openai.gpt-4-turbo',
            'openai.gpt-3.5-turbo',
            # Google Gemini models
            'gemini.gemini-1.5-pro',
            'gemini.gemini-1.5-flash',
            'gemini.gemini-1.0-pro'
        ]
        
        if selected_model and selected_model in available_models:
            model_id = selected_model
        elif user_role == 'admin' and ai_config.get('admin_override_model'):
            model_id = ai_config['admin_override_model']
        else:
            model_id = ai_config.get('default_model', 'anthropic.claude-3-haiku-20240307-v1:0')
        
        logger.info(f"Using model_id: {model_id}")
        logger.info(f"Selected model from frontend: {selected_model}")
        logger.info(f"User role: {user_role}")
        
        # Get summary configuration
        summary_configs = ai_config.get('summary_types', {})
        summary_config = summary_configs.get(summary_type, summary_configs.get('standard', {}))
        
        max_tokens = summary_config.get('max_tokens', 500)
        temperature = summary_config.get('temperature', 0.5)
        instruction = summary_config.get('instruction', 'Summarize this document.')
        
        # Prepare the prompt
        prompt = f"""Human: {instruction}

Document content:
{text[:10000]}

Please provide a clear, well-structured summary."""
        
        # Check if this is an external provider model
        if model_id.startswith('openai.'):
            # Use OpenAI provider
            provider = get_external_ai_provider('openai')
            if not provider:
                raise ValueError("OpenAI provider not available. Please configure API key.")
            
            # Extract model name from model_id
            model_name = model_id.replace('openai.', '')
            summary, provider_metadata = provider.generate_summary(
                text=text,
                summary_type=summary_type,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model_name
            )
            
            # Create metadata
            metadata = {
                'model': model_id,
                'summary_type': summary_type,
                'generated_at': datetime.utcnow().isoformat(),
                'user_role': user_role,
                'max_tokens': str(max_tokens),
                'temperature': str(temperature),
                'provider': 'openai',
                **provider_metadata
            }
            
            return summary, metadata
            
        elif model_id.startswith('gemini.'):
            # Use Gemini provider
            provider = get_external_ai_provider('gemini')
            if not provider:
                raise ValueError("Gemini provider not available. Please configure API key.")
            
            # Extract model name from model_id
            model_name = model_id.replace('gemini.', '')
            summary, provider_metadata = provider.generate_summary(
                text=text,
                summary_type=summary_type,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model_name
            )
            
            # Create metadata
            metadata = {
                'model': model_id,
                'summary_type': summary_type,
                'generated_at': datetime.utcnow().isoformat(),
                'user_role': user_role,
                'max_tokens': str(max_tokens),
                'temperature': str(temperature),
                'provider': 'gemini',
                **provider_metadata
            }
            
            return summary, metadata
        
        # Otherwise, use Bedrock for AWS models
        # Prepare request for Bedrock
        bedrock = get_bedrock_client()
        
        # Format request based on model type
        if "claude-3" in model_id or "claude-3-5" in model_id:
            # Use Messages API for Claude 3/3.5 models
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
        elif "nova" in model_id:
            # Amazon Nova models
            request_body = json.dumps({
                "messages": [
                    {
                        "role": "user", 
                        "content": [{"text": f"{instruction}\nDocument content:\n{text[:10000]}\nPlease provide a clear, well-structured summary."}]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "topP": 0.9
                }
            })
        elif "llama" in model_id:
            # Meta Llama models
            request_body = json.dumps({
                "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{instruction}\nDocument content:\n{text[:10000]}\nPlease provide a clear, well-structured summary.<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                "max_gen_len": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            })
        elif "mistral" in model_id:
            # Mistral models
            request_body = json.dumps({
                "prompt": f"<s>[INST] {instruction}\nDocument content:\n{text[:10000]}\nPlease provide a clear, well-structured summary. [/INST]",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            })
        elif "deepseek" in model_id:
            # DeepSeek models
            request_body = json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": f"{instruction}\nDocument content:\n{text[:10000]}\nPlease provide a clear, well-structured summary."
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            })
        else:
            # Default to Claude format for backwards compatibility
            request_body = json.dumps({
                "prompt": prompt,
                "max_tokens_to_sample": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "stop_sequences": ["\n\nHuman:"]
            })
        
        # Invoke the model
        bedrock = get_bedrock_client()
        logger.info(f"About to invoke model with modelId: {model_id}")
        logger.info(f"Request body length: {len(request_body)}")
        response = bedrock.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=request_body
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        logger.info(f"Bedrock response: {json.dumps(response_body)[:500]}...")  # Log first 500 chars
        
        if "claude-3" in model_id or "claude-3-5" in model_id:
            # Claude 3 uses Messages API response format
            content = response_body.get('content', [])
            if content and isinstance(content, list) and len(content) > 0:
                summary = content[0].get('text', '').strip()
            else:
                summary = ''
        elif "nova" in model_id:
            # Amazon Nova response format
            output = response_body.get('output', {})
            message = output.get('message', {})
            content = message.get('content', [])
            if content and isinstance(content, list) and len(content) > 0:
                summary = content[0].get('text', '').strip()
            else:
                summary = ''
        elif "llama" in model_id:
            # Meta Llama response format
            summary = response_body.get('generation', '').strip()
        elif "mistral" in model_id:
            # Mistral response format
            outputs = response_body.get('outputs', [])
            if outputs and len(outputs) > 0:
                summary = outputs[0].get('text', '').strip()
            else:
                summary = ''
        elif "deepseek" in model_id:
            # DeepSeek response format
            choices = response_body.get('choices', [])
            if choices and len(choices) > 0:
                message = choices[0].get('message', {})
                summary = message.get('content', '').strip()
            else:
                summary = ''
        elif "claude" in model_id:
            summary = response_body.get('completion', '').strip()
        else:
            summary = response_body.get('text', '').strip()
        
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
        
        # Get model selection (optional)
        selected_model = body.get('model')  # Will be None if not provided
        logger.info(f"Model from request body: {selected_model}")
        
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
            logger.info(f"Calling generate_ai_summary_internal with summary_type={summary_type}")
            summary_text, summary_metadata = generate_ai_summary_internal(
                document_content,
                summary_type=summary_type,
                user_role=user_context.get('role', 'user'),
                selected_model=selected_model
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
            
        new_content = ai_header + document_content
        logger.info(f"New content type: {type(new_content)}, length: {len(new_content)}")
        
        # Create new filename with _AI suffix
        original_filename = s3_key.split('/')[-1]
        if original_filename.endswith('.md'):
            base_new_filename = original_filename[:-3] + '_AI.md'
        else:
            base_new_filename = original_filename.rsplit('.', 1)[0] + '_AI.' + original_filename.rsplit('.', 1)[1]
        
        # Get unique filename
        prefix = '/'.join(s3_key.split('/')[:-1])
        new_filename = get_unique_filename(PROCESSED_BUCKET, prefix, base_new_filename)
        
        # Save to S3
        new_key = prefix + '/' + new_filename
        
        try:
            s3.put_object(
                Bucket=PROCESSED_BUCKET,
                Key=new_key,
                Body=new_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'original_document': s3_key,
                    'ai_summary': 'true',
                    **summary_metadata
                }
            )
            
            # Generate presigned URL with download disposition
            download_url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': PROCESSED_BUCKET,
                    'Key': new_key,
                    'ResponseContentDisposition': f'attachment; filename="{new_filename}"'
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
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'AI summary added successfully',
                'document_id': document_id,
                'new_filename': result['filename'],
                's3_key': result['s3_key'],
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
        if user_context.get('role') != 'admin':
            # Regular users get limited info
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'enabled': True,
                    'available_summary_types': ['brief', 'standard', 'detailed'],
                    'default_summary_type': 'standard'
                })
            }
        
        # Admin users get full configuration
        try:
            param_name = '/redact/ai-config'
            response = ssm.get_parameter(Name=param_name)
            ai_config = json.loads(response['Parameter']['Value'])
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(ai_config)
            }
        except ssm.exceptions.ParameterNotFound:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'AI configuration not found'})
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
        
        # Validate model IDs
        valid_models = [
            'anthropic.claude-3-haiku-20240307',
            'anthropic.claude-3-sonnet-20240229',
            'anthropic.claude-instant-v1'
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

def handle_get_external_ai_keys(headers, user_context):
    """Get external AI key status (doesn't return actual keys)"""
    try:
        # Check if keys are configured (without returning the actual keys)
        key_status = {
            'openai': {'configured': False, 'last_updated': None},
            'gemini': {'configured': False, 'last_updated': None}
        }
        
        # Check OpenAI key
        try:
            response = ssm.get_parameter(Name='/redact/api-keys/openai-api-key', WithDecryption=False)
            key_status['openai']['configured'] = response['Parameter']['Value'] != 'placeholder-will-be-updated-manually'
            key_status['openai']['last_updated'] = response['Parameter']['LastModifiedDate'].isoformat()
        except ssm.exceptions.ParameterNotFound:
            pass
        except Exception as e:
            logger.warning(f"Error checking OpenAI key: {str(e)}")
        
        # Check Gemini key
        try:
            response = ssm.get_parameter(Name='/redact/api-keys/gemini-api-key', WithDecryption=False)
            key_status['gemini']['configured'] = response['Parameter']['Value'] != 'placeholder-will-be-updated-manually'
            key_status['gemini']['last_updated'] = response['Parameter']['LastModifiedDate'].isoformat()
        except ssm.exceptions.ParameterNotFound:
            pass
        except Exception as e:
            logger.warning(f"Error checking Gemini key: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'key_status': key_status,
                'user_role': user_context.get('role', 'user')
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting external AI key status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get API key status'})
        }

def handle_update_external_ai_keys(event, headers, user_context):
    """Update external AI API keys (admin only)"""
    if user_context.get('role') != 'admin':
        return {
            'statusCode': 403,
            'headers': headers,
            'body': json.dumps({'error': 'Admin access required to manage API keys'})
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        updated_keys = []
        
        # Update OpenAI key if provided
        if 'openai_key' in body and body['openai_key']:
            try:
                ssm.put_parameter(
                    Name='/redact/api-keys/openai-api-key',
                    Value=body['openai_key'],
                    Type='SecureString',
                    Overwrite=True
                )
                updated_keys.append('openai')
                logger.info("OpenAI API key updated successfully")
            except Exception as e:
                logger.error(f"Error updating OpenAI key: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({'error': f'Failed to update OpenAI key: {str(e)}'})
                }
        
        # Update Gemini key if provided
        if 'gemini_key' in body and body['gemini_key']:
            try:
                ssm.put_parameter(
                    Name='/redact/api-keys/gemini-api-key',
                    Value=body['gemini_key'],
                    Type='SecureString',
                    Overwrite=True
                )
                updated_keys.append('gemini')
                logger.info("Gemini API key updated successfully")
            except Exception as e:
                logger.error(f"Error updating Gemini key: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({'error': f'Failed to update Gemini key: {str(e)}'})
                }
        
        if not updated_keys:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No API keys provided to update'})
            }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': f'Successfully updated API keys: {", ".join(updated_keys)}',
                'updated_keys': updated_keys
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        logger.error(f"Error updating external AI keys: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to update API keys'})
        }