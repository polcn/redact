import json
import boto3
import os
import re
import logging
from urllib.parse import unquote_plus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
s3 = boto3.client('s3')

# Environment variables
INPUT_BUCKET = os.environ['INPUT_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
QUARANTINE_BUCKET = os.environ['QUARANTINE_BUCKET']
KMS_KEY_ID = os.environ['KMS_KEY_ID']

# Client patterns to scrub
CLIENT_PATTERNS = [
    r'\b[A-Z][a-z]+ [A-Z][a-z]+ (Inc|LLC|Corp|Corporation|Company|Ltd)\b',
    r'\b[A-Z][a-z]+ (Technologies|Solutions|Systems|Services)\b',
    r'\b[A-Z]{2,}[a-z]* [A-Z][a-z]+\b',
    r'\bACME\b',
    r'\bTechnoSoft\b'
]

def lambda_handler(event, context):
    """
    Main Lambda handler for document processing
    """
    try:
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing document: s3://{bucket}/{key}")
            
            # Download document
            document_content = download_document(bucket, key)
            
            # For text files, process content directly
            if key.lower().endswith('.txt'):
                processed_content = process_text_content(document_content.decode('utf-8'))
                
                if processed_content != document_content.decode('utf-8'):
                    # Content was modified, upload processed version
                    upload_processed_document(key, processed_content.encode('utf-8'))
                    logger.info(f"Successfully processed and redacted: {key}")
                else:
                    # No sensitive content found, upload as-is
                    upload_processed_document(key, document_content)
                    logger.info(f"No sensitive content found in: {key}")
            else:
                # For other file types, quarantine for manual review
                quarantine_document(bucket, key, "Unsupported file type - manual review required")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Documents processed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def download_document(bucket, key):
    """Download document from S3"""
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Error downloading {key}: {str(e)}")
        raise

def process_text_content(content):
    """Process text content to scrub client information"""
    try:
        processed_content = content
        redactions_made = []
        
        # Find and redact client patterns
        for pattern in CLIENT_PATTERNS:
            matches = re.findall(pattern, processed_content)
            if matches:
                redactions_made.extend(matches)
                processed_content = re.sub(pattern, '[REDACTED]', processed_content)
        
        if redactions_made:
            logger.info(f"Redacted the following: {redactions_made}")
        
        return processed_content
        
    except Exception as e:
        logger.error(f"Error processing text content: {str(e)}")
        return content

def upload_processed_document(key, content):
    """Upload processed document to output bucket"""
    try:
        processed_key = f"processed/{key}"
        
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=processed_key,
            Body=content,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KMS_KEY_ID,
            Metadata={
                'processing-status': 'completed',
                'original-key': key
            }
        )
        
        logger.info(f"Uploaded processed document: s3://{OUTPUT_BUCKET}/{processed_key}")
        
    except Exception as e:
        logger.error(f"Error uploading processed document: {str(e)}")
        raise

def quarantine_document(bucket, key, reason):
    """Move document to quarantine bucket"""
    try:
        # Copy to quarantine bucket
        copy_source = {'Bucket': bucket, 'Key': key}
        quarantine_key = f"quarantine/{key}"
        
        s3.copy_object(
            CopySource=copy_source,
            Bucket=QUARANTINE_BUCKET,
            Key=quarantine_key,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KMS_KEY_ID,
            Metadata={
                'quarantine-reason': reason,
                'original-bucket': bucket,
                'original-key': key
            }
        )
        
        logger.info(f"Document quarantined: s3://{QUARANTINE_BUCKET}/{quarantine_key}, reason: {reason}")
        
    except Exception as e:
        logger.error(f"Error quarantining document: {str(e)}")
        raise