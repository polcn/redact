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

def lambda_handler(event, context):
    """
    API Gateway Lambda handler for document redaction REST API
    """
    try:
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
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
        
        if path == '/health' and method == 'GET':
            return handle_health_check(headers)
        elif path == '/documents/upload' and method == 'POST':
            return handle_document_upload(event, headers, context)
        elif path.startswith('/documents/status') and method == 'GET':
            return handle_status_check(event, headers, context)
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
    """
    Handle GET /health endpoint
    """
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

def handle_document_upload(event, headers, context):
    """
    Handle POST /documents/upload endpoint
    """
    try:
        # Parse request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body)
        
        # Parse multipart form data or JSON
        content_type = event.get('headers', {}).get('Content-Type', '')
        
        if 'multipart/form-data' in content_type:
            return handle_multipart_upload(body, headers, context)
        elif 'application/json' in content_type:
            return handle_json_upload(body, headers, context)
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Unsupported content type'})
            }
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Upload failed'})
        }

def handle_json_upload(body, headers, context):
    """
    Handle JSON-based document upload (base64 encoded content)
    """
    try:
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
        
        # Generate unique key
        unique_id = str(uuid.uuid4())
        s3_key = f"{unique_id}_{filename}"
        
        # Upload to S3
        s3.put_object(
            Bucket=INPUT_BUCKET,
            Key=s3_key,
            Body=file_content,
            ServerSideEncryption='AES256',
            Metadata={
                'upload-method': 'api',
                'original-filename': filename,
                'request-id': context.aws_request_id
            }
        )
        
        logger.info(json.dumps({
            'event': 'DOCUMENT_UPLOADED',
            'key': s3_key,
            'size': len(file_content),
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

def handle_multipart_upload(body, headers, context):
    """
    Handle multipart form data upload (for future implementation)
    """
    return {
        'statusCode': 501,
        'headers': headers,
        'body': json.dumps({'error': 'Multipart upload not yet implemented'})
    }

def handle_status_check(event, headers, context):
    """
    Handle GET /documents/status/{id} endpoint
    """
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
        
        # Search for documents with this ID prefix
        status_info = check_document_status(document_id)
        
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

def check_document_status(document_id):
    """
    Check the processing status of a document
    """
    try:
        # Check input bucket (still processing)
        try:
            input_response = s3.list_objects_v2(
                Bucket=INPUT_BUCKET,
                Prefix=document_id
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
                Prefix=f"processed/{document_id}"
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
                Prefix=f"quarantine/{document_id}"
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

def generate_presigned_url(bucket, key, expiration=3600):
    """
    Generate a presigned URL for downloading processed documents
    """
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