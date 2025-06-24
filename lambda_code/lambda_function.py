import json
import boto3
import os
import re
import logging
from urllib.parse import unquote_plus
import tempfile
from io import BytesIO

# Document processing libraries
try:
    from docx import Document
    from docx.shared import Inches
except ImportError:
    Document = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
s3 = boto3.client('s3')

# Environment variables
INPUT_BUCKET = os.environ['INPUT_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
QUARANTINE_BUCKET = os.environ['QUARANTINE_BUCKET']
CONFIG_BUCKET = os.environ['CONFIG_BUCKET']

# Global cache for config
_config_cache = None
_config_last_modified = None

# Default fallback patterns if config not available
DEFAULT_REPLACEMENTS = [
    {"find": "REPLACE_CLIENT_NAME", "replace": "Company X"},
    {"find": "ACME Corporation", "replace": "[REDACTED]"},
    {"find": "TechnoSoft", "replace": "[REDACTED]"}
]

def lambda_handler(event, context):
    """
    Main Lambda handler for document processing
    """
    results = []
    
    try:
        # Load configuration
        config = get_redaction_config()
        
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            result = {
                'file': key,
                'status': 'PROCESSING',
                'timestamp': context.aws_request_id
            }
            
            try:
                logger.info(json.dumps({
                    'event': 'PROCESSING_START',
                    'file': key,
                    'bucket': bucket,
                    'request_id': context.aws_request_id
                }))
                
                # Process document based on file type
                file_ext = key.lower().split('.')[-1]
                
                if file_ext == 'txt':
                    success = process_text_file(bucket, key, config)
                elif file_ext == 'pdf':
                    success = process_pdf_file(bucket, key, config)
                elif file_ext in ['docx', 'doc']:
                    success = process_docx_file(bucket, key, config)
                elif file_ext in ['xlsx', 'xls']:
                    success = process_xlsx_file(bucket, key, config)
                else:
                    quarantine_document(bucket, key, f"Unsupported file type: {file_ext}")
                    success = False
                
                result['status'] = 'SUCCESS' if success else 'QUARANTINED'
                
                logger.info(json.dumps({
                    'event': 'PROCESSING_COMPLETE',
                    'file': key,
                    'status': result['status'],
                    'request_id': context.aws_request_id
                }))
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'PROCESSING_ERROR',
                    'file': key,
                    'error': str(e),
                    'request_id': context.aws_request_id
                }))
                
                # Move to quarantine on error
                try:
                    quarantine_document(bucket, key, f"Processing error: {str(e)}")
                except Exception as qe:
                    logger.error(f"Failed to quarantine {key}: {str(qe)}")
                
                result['status'] = 'ERROR'
                result['error'] = str(e)
            
            results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing completed',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'HANDLER_ERROR',
            'error': str(e),
            'request_id': context.aws_request_id
        }))
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'results': results
            })
        }

def download_document(bucket, key):
    """Download document from S3"""
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Error downloading {key}: {str(e)}")
        raise

def get_redaction_config():
    """Load redaction configuration from S3 with caching"""
    global _config_cache, _config_last_modified
    
    try:
        # Check if config file exists and get last modified time
        response = s3.head_object(Bucket=CONFIG_BUCKET, Key='config.json')
        last_modified = response['LastModified']
        
        # Return cached config if it's still current
        if _config_cache and _config_last_modified and last_modified <= _config_last_modified:
            return _config_cache
        
        # Download and parse config
        config_response = s3.get_object(Bucket=CONFIG_BUCKET, Key='config.json')
        config_data = json.loads(config_response['Body'].read())
        
        # Cache the config
        _config_cache = config_data
        _config_last_modified = last_modified
        
        logger.info(f"Loaded redaction config with {len(config_data.get('replacements', []))} rules")
        return config_data
        
    except s3.exceptions.NoSuchKey:
        logger.warning("No config.json found, using default replacements")
        return {'replacements': DEFAULT_REPLACEMENTS, 'case_sensitive': False}
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}, using defaults")
        return {'replacements': DEFAULT_REPLACEMENTS, 'case_sensitive': False}

def apply_redaction_rules(content, config):
    """Apply redaction rules to text content"""
    try:
        processed_content = content
        redactions_made = []
        
        replacements = config.get('replacements', DEFAULT_REPLACEMENTS)
        case_sensitive = config.get('case_sensitive', False)
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for rule in replacements:
            find_text = rule.get('find', '')
            replace_text = rule.get('replace', '[REDACTED]')
            
            if not find_text:
                continue
                
            # Count matches before replacement
            matches = re.findall(re.escape(find_text), processed_content, flags=flags)
            if matches:
                redactions_made.extend([(find_text, len(matches))])
                processed_content = re.sub(re.escape(find_text), replace_text, processed_content, flags=flags)
        
        if redactions_made:
            logger.info(f"Applied redactions: {redactions_made}")
        
        return processed_content, len(redactions_made) > 0
        
    except Exception as e:
        logger.error(f"Error applying redaction rules: {str(e)}")
        return content, False

def upload_processed_document(key, content, metadata=None):
    """Upload processed document to output bucket"""
    try:
        processed_key = f"processed/{key}"
        
        base_metadata = {
            'processing-status': 'completed',
            'original-key': key
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        # Handle both bytes and file-like objects
        if hasattr(content, 'read'):
            body = content.read()
        else:
            body = content
        
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=processed_key,
            Body=body,
            ServerSideEncryption='AES256',
            Metadata=base_metadata
        )
        
        logger.info(f"Uploaded processed document: s3://{OUTPUT_BUCKET}/{processed_key}")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading processed document: {str(e)}")
        raise

def process_text_file(bucket, key, config):
    """Process text files"""
    try:
        # Download document
        document_content = download_document(bucket, key)
        text_content = document_content.decode('utf-8')
        
        # Apply redaction rules
        processed_content, redacted = apply_redaction_rules(text_content, config)
        
        # Upload processed document
        upload_processed_document(key, processed_content.encode('utf-8'), 
                                {'redacted': str(redacted)})
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing text file {key}: {str(e)}")
        raise

def process_pdf_file(bucket, key, config):
    """Process PDF files - remove images and redact text"""
    if not pypdf:
        raise ImportError("pypdf library not available")
    
    try:
        # Download document
        document_content = download_document(bucket, key)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_file:
            temp_file.write(document_content)
            temp_file.flush()
            
            # Read PDF
            reader = pypdf.PdfReader(temp_file.name)
            writer = pypdf.PdfWriter()
            
            redacted = False
            
            for page in reader.pages:
                # Extract text from page
                text = page.extract_text()
                
                # Apply redaction rules to text
                processed_text, page_redacted = apply_redaction_rules(text, config)
                redacted = redacted or page_redacted
                
                # Remove images (simplified - removes all image objects)
                if '/XObject' in page['/Resources']:
                    x_objects = page['/Resources']['/XObject'].get_object()
                    to_remove = []
                    for obj_name in x_objects:
                        if x_objects[obj_name]['/Subtype'] == '/Image':
                            to_remove.append(obj_name)
                    for obj_name in to_remove:
                        del x_objects[obj_name]
                
                writer.add_page(page)
            
            # Save processed PDF
            output_buffer = BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)
            
            upload_processed_document(key, output_buffer, 
                                    {'redacted': str(redacted), 'images_removed': 'true'})
            
            return True
            
    except Exception as e:
        logger.error(f"Error processing PDF file {key}: {str(e)}")
        raise

def process_docx_file(bucket, key, config):
    """Process DOCX files - remove images and redact text"""
    if not Document:
        raise ImportError("python-docx library not available")
    
    try:
        # Download document
        document_content = download_document(bucket, key)
        
        with tempfile.NamedTemporaryFile(suffix='.docx') as temp_file:
            temp_file.write(document_content)
            temp_file.flush()
            
            # Open document
            doc = Document(temp_file.name)
            
            redacted = False
            
            # Process paragraphs
            for paragraph in doc.paragraphs:
                original_text = paragraph.text
                processed_text, para_redacted = apply_redaction_rules(original_text, config)
                
                if para_redacted:
                    paragraph.text = processed_text
                    redacted = True
            
            # Remove all images
            for shape in doc.inline_shapes:
                if shape.type == 3:  # PICTURE type
                    shape._element.getparent().remove(shape._element)
            
            # Save processed document
            output_buffer = BytesIO()
            doc.save(output_buffer)
            output_buffer.seek(0)
            
            upload_processed_document(key, output_buffer, 
                                    {'redacted': str(redacted), 'images_removed': 'true'})
            
            return True
            
    except Exception as e:
        logger.error(f"Error processing DOCX file {key}: {str(e)}")
        raise

def process_xlsx_file(bucket, key, config):
    """Process XLSX files - redact text content"""
    if not load_workbook:
        raise ImportError("openpyxl library not available")
    
    try:
        # Download document
        document_content = download_document(bucket, key)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx') as temp_file:
            temp_file.write(document_content)
            temp_file.flush()
            
            # Open workbook
            workbook = load_workbook(temp_file.name)
            
            redacted = False
            
            # Process all worksheets
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value and isinstance(cell.value, str):
                            processed_value, cell_redacted = apply_redaction_rules(cell.value, config)
                            if cell_redacted:
                                cell.value = processed_value
                                redacted = True
            
            # Save processed workbook
            output_buffer = BytesIO()
            workbook.save(output_buffer)
            output_buffer.seek(0)
            
            upload_processed_document(key, output_buffer, 
                                    {'redacted': str(redacted)})
            
            return True
            
    except Exception as e:
        logger.error(f"Error processing XLSX file {key}: {str(e)}")
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
            ServerSideEncryption='AES256',
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