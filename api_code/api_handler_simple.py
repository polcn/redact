import json
import boto3
import base64
import os
import uuid
import time
from urllib.parse import unquote_plus
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
s3 = boto3.client('s3')

# Environment variables
INPUT_BUCKET = os.environ['INPUT_BUCKET']
PROCESSED_BUCKET = os.environ['PROCESSED_BUCKET']
QUARANTINE_BUCKET = os.environ['QUARANTINE_BUCKET']
CONFIG_BUCKET = os.environ['CONFIG_BUCKET']

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'xlsx', 'xls'}

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
            'request_id': context.aws_request_id
        }))
        
        # Public endpoints
        if path == '/health' and method == 'GET':
            return handle_health_check(headers)
        
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
        unique_id = str(uuid.uuid4())
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        s3_key = f"{user_prefix}/{unique_id}_{filename}"
        
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
        
        return {
            'statusCode': 202,
            'headers': headers,
            'body': json.dumps({
                'message': 'Document uploaded successfully',
                'document_id': unique_id,
                'filename': filename,
                'status': 'processing',
                'status_url': f'/documents/status/{unique_id}'
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
                doc_id = filename.split('_')[0] if '_' in filename else filename
                
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
                doc_id = filename.split('_')[0] if '_' in filename else filename
                
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
        # Extract document ID from path
        path_parts = event['path'].split('/')
        if len(path_parts) < 3:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Document ID required'})
            }
        
        document_id = path_parts[2]
        user_prefix = get_user_s3_prefix(user_context['user_id'])
        
        deleted_files = []
        errors = []
        
        # Delete from input bucket
        try:
            input_response = s3.list_objects_v2(
                Bucket=INPUT_BUCKET,
                Prefix=f"{user_prefix}/{document_id}"
            )
            
            for obj in input_response.get('Contents', []):
                try:
                    s3.delete_object(Bucket=INPUT_BUCKET, Key=obj['Key'])
                    deleted_files.append(f"input/{obj['Key']}")
                except Exception as e:
                    errors.append(f"Failed to delete {obj['Key']} from input: {str(e)}")
        except ClientError:
            pass
        
        # Delete from processed bucket
        try:
            processed_response = s3.list_objects_v2(
                Bucket=PROCESSED_BUCKET,
                Prefix=f"processed/{user_prefix}/{document_id}"
            )
            
            for obj in processed_response.get('Contents', []):
                try:
                    s3.delete_object(Bucket=PROCESSED_BUCKET, Key=obj['Key'])
                    deleted_files.append(f"processed/{obj['Key']}")
                except Exception as e:
                    errors.append(f"Failed to delete {obj['Key']} from processed: {str(e)}")
        except ClientError:
            pass
        
        # Delete from quarantine bucket
        try:
            quarantine_response = s3.list_objects_v2(
                Bucket=QUARANTINE_BUCKET,
                Prefix=f"quarantine/{user_prefix}/{document_id}"
            )
            
            for obj in quarantine_response.get('Contents', []):
                try:
                    s3.delete_object(Bucket=QUARANTINE_BUCKET, Key=obj['Key'])
                    deleted_files.append(f"quarantine/{obj['Key']}")
                except Exception as e:
                    errors.append(f"Failed to delete {obj['Key']} from quarantine: {str(e)}")
        except ClientError:
            pass
        
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
            # Try global config as fallback
            try:
                response = s3.get_object(
                    Bucket=CONFIG_BUCKET,
                    Key='config.json'
                )
                config = json.loads(response['Body'].read())
                logger.info(f"Using global config for user {user_id} (no user-specific config found)")
                
                # Copy global config to user-specific location for future use
                s3.put_object(
                    Bucket=CONFIG_BUCKET,
                    Key=user_config_key,
                    Body=json.dumps(config, indent=2),
                    ContentType='application/json',
                    ServerSideEncryption='AES256'
                )
                logger.info(f"Copied global config to user-specific location for user {user_id}")
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(config)
                }
            except s3.exceptions.NoSuchKey:
                pass
        
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