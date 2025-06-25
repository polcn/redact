import json
import boto3
import os
import re
import logging
from urllib.parse import unquote_plus
import tempfile
from io import BytesIO
import time
from botocore.exceptions import ClientError

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Document processing libraries with better error handling
try:
    from docx import Document
    from docx.shared import Inches
    DOCX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"DOCX import failed: {str(e)}")
    Document = None
    DOCX_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError as e:
    logger.warning(f"pypdf import failed: {str(e)}")
    pypdf = None
    PYPDF_AVAILABLE = False

try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"openpyxl import failed: {str(e)}")
    load_workbook = None
    OPENPYXL_AVAILABLE = False

# Initialize AWS clients
s3 = boto3.client('s3')

# Configuration constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
MAX_CONFIG_SIZE = 1 * 1024 * 1024  # 1MB limit for config
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'xlsx', 'xls'}
MAX_REPLACEMENTS = 100  # Maximum number of replacement rules
BATCH_SIZE = 5  # Maximum files to process in one batch
BATCH_TIMEOUT = 45  # Maximum seconds for batch processing

# Retry configuration
MAX_RETRIES = 3
BASE_BACKOFF = 1  # seconds
MAX_BACKOFF = 30  # seconds

# Environment variables
INPUT_BUCKET = os.environ['INPUT_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
QUARANTINE_BUCKET = os.environ['QUARANTINE_BUCKET']
CONFIG_BUCKET = os.environ['CONFIG_BUCKET']

# Windows compatibility mode (for ChatGPT compatibility)
WINDOWS_MODE = os.environ.get('WINDOWS_MODE', 'true').lower() == 'true'

# Global cache for config
_config_cache = None
_config_last_modified = None

# Default fallback patterns if config not available
DEFAULT_REPLACEMENTS = [
    {"find": "REPLACE_CLIENT_NAME", "replace": "Company X"},
    {"find": "ACME Corporation", "replace": "[REDACTED]"},
    {"find": "TechnoSoft", "replace": "[REDACTED]"}
]

# Common PII regex patterns
PII_PATTERNS = {
    "ssn": {
        "pattern": r"\b(?:\d{3}-\d{2}-\d{4}|\d{3}\s\d{2}\s\d{4}|\d{9})\b",
        "replace": "[SSN]",
        "description": "Social Security Number"
    },
    "credit_card": {
        "pattern": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
        "replace": "[CREDIT_CARD]",
        "description": "Credit Card Number"
    },
    "phone": {
        "pattern": r"\b(?:\+?1[\s\-\.]?)?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b",
        "replace": "[PHONE]",
        "description": "Phone Number (US/Canada)"
    },
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "replace": "[EMAIL]",
        "description": "Email Address"
    },
    "ip_address": {
        "pattern": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "replace": "[IP_ADDRESS]",
        "description": "IPv4 Address"
    },
    "drivers_license": {
        "pattern": r"\b[A-Z]{1,2}\d{5,8}\b",
        "replace": "[DRIVERS_LICENSE]",
        "description": "Driver's License (various states)"
    }
}

def get_user_info_from_key(key):
    """Extract user info from S3 key if it follows user prefix pattern"""
    # Check if key follows pattern: users/{user_id}/...
    if key.startswith('users/'):
        parts = key.split('/', 2)
        if len(parts) >= 3:
            return {
                'user_id': parts[1],
                'file_path': parts[2]
            }
    return None

def validate_file(bucket, key):
    """
    Validate file before processing
    """
    try:
        # Check file extension
        file_path = key
        user_info = get_user_info_from_key(key)
        if user_info:
            file_path = user_info['file_path']
            
        file_ext = file_path.lower().split('.')[-1]
        if file_ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {file_ext}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")
        
        # Check file size
        response = s3.head_object(Bucket=bucket, Key=key)
        file_size = response['ContentLength']
        
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size} bytes. Maximum allowed: {MAX_FILE_SIZE} bytes")
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        return True
    except s3.exceptions.NoSuchKey:
        raise ValueError(f"File not found: {key}")
    except Exception as e:
        logger.error(f"File validation error: {str(e)}")
        raise

def get_redaction_config(user_id=None):
    """Load user-specific configuration from S3 bucket with caching"""
    global _config_cache, _config_last_modified
    
    # Determine config key
    if user_id:
        config_key = f'configs/users/{user_id}/config.json'
    else:
        config_key = 'config.json'  # Fallback to global config
    
    try:
        # Try user-specific config first
        if user_id:
            try:
                response = s3.head_object(Bucket=CONFIG_BUCKET, Key=config_key)
                last_modified = response['LastModified']
                
                # Use cached config if available and not modified
                cache_key = f"user_{user_id}"
                if isinstance(_config_cache, dict) and cache_key in _config_cache:
                    if _config_last_modified and _config_last_modified.get(cache_key) == last_modified:
                        logger.info(f"Using cached configuration for user {user_id}")
                        return _config_cache[cache_key]
                
                # Load fresh user config
                response = s3.get_object(Bucket=CONFIG_BUCKET, Key=config_key)
                config_content = response['Body'].read()
                
                # Validate size
                if len(config_content) > MAX_CONFIG_SIZE:
                    raise ValueError(f"Configuration file too large: {len(config_content)} bytes")
                
                config = json.loads(config_content)
                
                # Update cache
                if not isinstance(_config_cache, dict):
                    _config_cache = {}
                if not isinstance(_config_last_modified, dict):
                    _config_last_modified = {}
                
                _config_cache[cache_key] = config
                _config_last_modified[cache_key] = last_modified
                
                logger.info(f"Loaded user-specific configuration for {user_id} with {len(config.get('replacements', []))} rules")
                return config
                
            except s3.exceptions.NoSuchKey:
                logger.info(f"No user-specific config for {user_id}, trying global config")
                # Fall through to try global config
        
        # Try global config as fallback
        try:
            response = s3.head_object(Bucket=CONFIG_BUCKET, Key='config.json')
            last_modified = response['LastModified']
            
            # Check global cache
            cache_key = "global"
            if isinstance(_config_cache, dict) and cache_key in _config_cache:
                if _config_last_modified and _config_last_modified.get(cache_key) == last_modified:
                    logger.info("Using cached global configuration")
                    return _config_cache[cache_key]
            
            # Load fresh global config
            response = s3.get_object(Bucket=CONFIG_BUCKET, Key='config.json')
            config_content = response['Body'].read()
            
            if len(config_content) > MAX_CONFIG_SIZE:
                raise ValueError(f"Configuration file too large: {len(config_content)} bytes")
            
            config = json.loads(config_content)
            
            # Update cache
            if not isinstance(_config_cache, dict):
                _config_cache = {}
            if not isinstance(_config_last_modified, dict):
                _config_last_modified = {}
                
            _config_cache[cache_key] = config
            _config_last_modified[cache_key] = last_modified
            
            logger.info(f"Loaded global configuration with {len(config.get('replacements', []))} rules")
            return config
            
        except s3.exceptions.NoSuchKey:
            pass
        
        # No config found, use defaults
        logger.warning("No configuration found, using defaults")
        default_config = {
            "replacements": DEFAULT_REPLACEMENTS, 
            "case_sensitive": False,
            "patterns": {
                "ssn": False,
                "credit_card": False,
                "phone": False,
                "email": False,
                "ip_address": False,
                "drivers_license": False
            }
        }
        return default_config
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration: {str(e)}")
        return {"replacements": DEFAULT_REPLACEMENTS, "case_sensitive": False}
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return {"replacements": DEFAULT_REPLACEMENTS, "case_sensitive": False}

def lambda_handler(event, context):
    """
    Main Lambda handler for document processing with batch support and user isolation
    """
    results = []
    start_time = time.time()
    
    try:
        # Get files to process
        files_to_process = []
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            files_to_process.append((bucket, key))
        
        # Log batch start
        logger.info(json.dumps({
            'event': 'BATCH_START',
            'batch_size': len(files_to_process),
            'request_id': context.aws_request_id
        }))
        
        # Process files in batches
        processed_count = 0
        for i in range(0, len(files_to_process), BATCH_SIZE):
            batch = files_to_process[i:i + BATCH_SIZE]
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > BATCH_TIMEOUT:
                logger.warning(json.dumps({
                    'event': 'BATCH_TIMEOUT',
                    'processed': processed_count,
                    'remaining': len(files_to_process) - processed_count,
                    'elapsed': elapsed
                }))
                break
            
            # Process batch (config will be loaded per user)
            batch_results = process_file_batch(batch, None, context)
            results.extend(batch_results)
            processed_count += len(batch_results)
        
        # Log batch completion
        logger.info(json.dumps({
            'event': 'BATCH_COMPLETE',
            'processed': processed_count,
            'total': len(files_to_process),
            'duration': time.time() - start_time,
            'request_id': context.aws_request_id
        }))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {processed_count} files',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'BATCH_ERROR',
            'error': str(e),
            'type': type(e).__name__,
            'request_id': context.aws_request_id
        }))
        
        # If any files were processed, return partial success
        if results:
            return {
                'statusCode': 207,  # Multi-status
                'body': json.dumps({
                    'message': f'Partial batch processing: {len(results)} succeeded',
                    'error': str(e),
                    'results': results
                })
            }
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }

def process_file_batch(batch, config, context):
    """Process a batch of files with error isolation and user-specific configs"""
    results = []
    
    for bucket, key in batch:
        try:
            # Extract user info from key
            user_info = get_user_info_from_key(key)
            
            # Load user-specific config for this file
            if user_info:
                user_config = get_redaction_config(user_info['user_id'])
            else:
                # Fall back to global config for non-user files
                user_config = get_redaction_config()
            
            # Validate config
            validate_config(user_config)
            
            # Process individual file with user-specific config
            result = process_single_file(bucket, key, user_config)
            results.append({
                'key': key,
                'status': 'success',
                'result': result,
                'user_id': user_info['user_id'] if user_info else 'global'
            })
            
        except Exception as e:
            error_msg = str(e)
            logger.error(json.dumps({
                'event': 'FILE_ERROR',
                'file': key,
                'error': error_msg,
                'type': type(e).__name__,
                'request_id': context.aws_request_id
            }))
            
            # Try to quarantine the file
            try:
                quarantine_document(bucket, key, error_msg)
                results.append({
                    'key': key,
                    'status': 'quarantined',
                    'error': error_msg
                })
            except Exception as q_error:
                results.append({
                    'key': key,
                    'status': 'failed',
                    'error': error_msg,
                    'quarantine_error': str(q_error)
                })
    
    return results

def process_single_file(bucket, key, config):
    """Process a single file with user isolation support"""
    logger.info(f"Processing file: s3://{bucket}/{key}")
    
    # Extract user info if present
    user_info = get_user_info_from_key(key)
    
    # Validate file
    validate_file(bucket, key)
    
    # Get file extension
    file_path = user_info['file_path'] if user_info else key
    file_ext = file_path.lower().split('.')[-1]
    
    # Process based on file type
    if file_ext == 'txt':
        process_text_file(bucket, key, config, user_info)
    elif file_ext == 'pdf':
        process_pdf_file(bucket, key, config, user_info)
    elif file_ext in ['docx', 'doc']:
        process_docx_file(bucket, key, config, user_info)
    elif file_ext in ['xlsx', 'xls']:
        process_xlsx_file(bucket, key, config, user_info)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    # Delete original file from input bucket after successful processing
    delete_processed_file(bucket, key)
    
    return {'processed': True, 'file_type': file_ext}

def apply_redaction_rules(text, config):
    """Apply redaction rules to text content including pattern-based PII detection"""
    if not config:
        return text, False
    
    redacted = False
    processed_text = text
    case_sensitive = config.get('case_sensitive', False)
    
    # Apply text-based replacements
    replacements = config.get('replacements', [])
    for replacement in replacements:
        find_text = replacement.get('find', '')
        replace_text = replacement.get('replace', '[REDACTED]')
        
        if not find_text:
            continue
        
        # Create pattern based on case sensitivity
        if case_sensitive:
            pattern = re.escape(find_text)
        else:
            pattern = re.escape(find_text)
            pattern = f"(?i){pattern}"
        
        # Check if pattern exists in text
        if re.search(pattern, processed_text):
            redacted = True
            processed_text = re.sub(pattern, replace_text, processed_text)
            logger.info(f"Applied redaction: '{find_text}' -> '{replace_text}'")
    
    # Apply pattern-based PII detection if enabled
    patterns = config.get('patterns', {})
    if patterns:
        for pattern_name, enabled in patterns.items():
            if enabled and pattern_name in PII_PATTERNS:
                pii_config = PII_PATTERNS[pattern_name]
                pattern = pii_config['pattern']
                replace = pii_config['replace']
                
                # Check if pattern exists in text
                if re.search(pattern, processed_text):
                    redacted = True
                    processed_text = re.sub(pattern, replace, processed_text)
                    logger.info(f"Applied PII pattern '{pattern_name}': {pii_config['description']}")
    
    # Normalize text output for better compatibility
    processed_text = normalize_text_output(processed_text)
    
    return processed_text, redacted

def normalize_text_output(text, windows_mode=None):
    """Normalize text for Markdown format compatibility with ChatGPT
    
    This function:
    1. Converts line endings based on mode (Unix or Windows)
    2. Replaces special UTF-8 characters with ASCII equivalents
    3. Ensures consistent encoding for plain text output
    4. Outputs clean text that works with ChatGPT's file upload
    
    Note: Files are saved as .md extension but contain plain text (no markdown formatting)
    This is a workaround for ChatGPT's .txt/.log file upload issues
    """
    if not text:
        return text
    
    # Use global setting if not specified
    if windows_mode is None:
        windows_mode = WINDOWS_MODE
    
    # Log that normalization is running
    logger.info("Running text normalization - input length: %d, windows_mode: %s", len(text), windows_mode)
    
    # First normalize to Unix line endings
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    # Remove BOM if present
    if text.startswith('\ufeff'):
        text = text[1:]
        logger.info("Removed BOM from text")
    
    # Replace common special characters that cause issues
    replacements = {
        # Curly quotes to straight quotes
        '\u2018': "'",  # Left single quotation mark
        '\u2019': "'",  # Right single quotation mark
        '\u201C': '"',  # Left double quotation mark
        '\u201D': '"',  # Right double quotation mark
        
        # Dashes and hyphens
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2015': '--', # Horizontal bar
        
        # Other common problematic characters
        '\u2026': '...', # Horizontal ellipsis
        '\u00A0': ' ',   # Non-breaking space
        '\u2022': '*',   # Bullet point
        '\u2023': '>',   # Triangular bullet
        '\u25CF': '*',   # Black circle
        '\u25CB': 'o',   # White circle
        '\u2192': '->',  # Rightwards arrow
        '\u2190': '<-',  # Leftwards arrow
        '\u2194': '<->', # Left right arrow
        
        # Mathematical symbols
        '\u00D7': 'x',   # Multiplication sign
        '\u00F7': '/',   # Division sign
        '\u00B1': '+/-', # Plus-minus sign
        '\u2264': '<=',  # Less than or equal to
        '\u2265': '>=',  # Greater than or equal to
        '\u2260': '!=',  # Not equal to
        
        # Other quotation marks
        '\u00AB': '<<',  # Left-pointing double angle quotation mark
        '\u00BB': '>>',  # Right-pointing double angle quotation mark
        '\u201A': ',',   # Single low-9 quotation mark
        '\u201E': ',,',  # Double low-9 quotation mark
        
        # Additional spaces and special characters
        '\u202F': ' ',   # Narrow no-break space
        '\u2009': ' ',   # Thin space
        '\u200A': ' ',   # Hair space
        '\u2008': ' ',   # Punctuation space
        '\u205F': ' ',   # Medium mathematical space
        '\u3000': ' ',   # Ideographic space
        '\u00AD': '',    # Soft hyphen
        '\u2011': '-',   # Non-breaking hyphen
        '\u2212': '-',   # Minus sign
        '\uFEFF': '',    # Zero-width no-break space (BOM)
    }
    
    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)
    
    # Remove any remaining non-printable characters (except newlines and tabs)
    # This preserves ASCII 32-126, plus newline (10) and tab (9)
    cleaned_text = ''.join(
        char if (32 <= ord(char) <= 126) or char in '\n\t' 
        else ' ' if ord(char) > 126 else ''
        for char in text
    )
    
    # Final pass: ensure absolutely no non-ASCII characters remain
    # Use 'ignore' instead of 'replace' to avoid question marks
    final_text = cleaned_text.encode('ascii', 'ignore').decode('ascii')
    
    # Clean up multiple spaces
    import re
    final_text = re.sub(r' +', ' ', final_text)
    final_text = re.sub(r'\n +', '\n', final_text)
    final_text = re.sub(r' +\n', '\n', final_text)
    
    # Convert to Windows line endings if requested
    if windows_mode:
        final_text = final_text.replace('\n', '\r\n')
        # Optionally add UTF-8 BOM for Windows compatibility
        # Note: BOM is not ASCII, so only add if specifically needed
        # final_text = '\ufeff' + final_text
    
    # Log completion
    logger.info("Text normalization complete - output length: %d, is ASCII: %s, line_ending: %s", 
                len(final_text), 
                all(ord(c) < 128 for c in final_text),
                "CRLF" if windows_mode else "LF")
    
    return final_text

def apply_filename_redaction(filename, config):
    """Apply redaction rules to file names and ensure .md extension for ChatGPT compatibility"""
    try:
        # Extract base name (remove extension)
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Apply redaction to base name only
        processed_name, redacted = apply_redaction_rules(base_name, config)
        
        # Always output as .md file (confirmed working with ChatGPT uploads)
        # Markdown files upload reliably while .txt and .log files have issues
        # .md is plain text and works with all text editors
        processed_filename = f"{processed_name}.md"
            
        if redacted:
            logger.info(f"Applied filename redaction: {filename} -> {processed_filename}")
            
        return processed_filename, redacted
        
    except Exception as e:
        logger.error(f"Error applying filename redaction: {str(e)}")
        return filename, False

def validate_config(config):
    """Validate configuration structure and limits"""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")
    
    # Validate replacements
    replacements = config.get('replacements', [])
    if not isinstance(replacements, list):
        raise ValueError("Replacements must be a list")
    
    if len(replacements) > MAX_REPLACEMENTS:
        raise ValueError(f"Too many replacement rules: {len(replacements)} (max: {MAX_REPLACEMENTS})")
    
    for i, replacement in enumerate(replacements):
        if not isinstance(replacement, dict):
            raise ValueError(f"Replacement {i} must be a dictionary")
        if 'find' not in replacement:
            raise ValueError(f"Replacement {i} missing 'find' field")
        if not replacement['find']:
            raise ValueError(f"Replacement {i} has empty 'find' field")
    
    # Validate patterns if present
    patterns = config.get('patterns', {})
    if patterns and not isinstance(patterns, dict):
        raise ValueError("Patterns must be a dictionary")
    
    # Validate pattern names
    for pattern_name in patterns:
        if pattern_name not in PII_PATTERNS:
            logger.warning(f"Unknown pattern name: {pattern_name}")

def exponential_backoff_retry(func):
    """Execute function with exponential backoff retry"""
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] in ['RequestTimeout', 'ServiceUnavailable', 'ThrottlingException']:
                last_exception = e
                backoff = min(BASE_BACKOFF * (2 ** attempt), MAX_BACKOFF)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {backoff}s: {str(e)}")
                time.sleep(backoff)
            else:
                raise
        except Exception as e:
            raise
    
    raise last_exception

def upload_processed_document(key, content, metadata=None, config=None, user_info=None):
    """Upload processed document to output bucket with retry logic and user isolation"""
    # Extract filename from key
    if user_info:
        # Remove user prefix from key for processing
        filename = user_info['file_path']
    else:
        filename = key
    
    # Apply filename redaction if config provided
    if config:
        redacted_filename, filename_redacted = apply_filename_redaction(filename, config)
        if metadata is None:
            metadata = {}
        metadata['filename_redacted'] = str(filename_redacted)
    else:
        redacted_filename = filename
    
    # Construct the output key with user prefix if needed
    if user_info:
        processed_key = f"processed/users/{user_info['user_id']}/{redacted_filename}"
    else:
        processed_key = f"processed/{redacted_filename}"
    
    base_metadata = {
        'processing-status': 'completed',
        'original-key': key
    }
    
    if user_info:
        base_metadata['user-id'] = user_info['user_id']
    
    if metadata:
        base_metadata.update(metadata)
    
    # Handle both bytes and file-like objects
    if hasattr(content, 'read'):
        body = content.read()
    else:
        body = content
    
    def _upload():
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=processed_key,
            Body=body,
            ServerSideEncryption='AES256',
            Metadata=base_metadata
        )
    
    try:
        exponential_backoff_retry(_upload)
        logger.info(f"Uploaded processed document: s3://{OUTPUT_BUCKET}/{processed_key}")
        return True
    except Exception as e:
        logger.error(f"Error uploading processed document after {MAX_RETRIES} attempts: {str(e)}")
        raise

def process_text_file(bucket, key, config, user_info=None):
    """Process text files with comprehensive error handling"""
    try:
        # Download file with retry
        def _download():
            return s3.get_object(Bucket=bucket, Key=key)
        
        response = exponential_backoff_retry(_download)
        content = response['Body'].read().decode('utf-8', errors='replace')
        
        # Apply redaction rules
        processed_content, redacted = apply_redaction_rules(content, config)
        
        # Upload processed document
        upload_processed_document(key, processed_content.encode('utf-8'), 
                                {'redacted': str(redacted)}, config, user_info)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing text file {key}: {str(e)}")
        raise

def process_pdf_file(bucket, key, config, user_info=None):
    """Process PDF files by extracting text and redacting"""
    if not PYPDF_AVAILABLE:
        raise ImportError("pypdf library not available for PDF processing")
    
    try:
        # Download file
        def _download():
            return s3.get_object(Bucket=bucket, Key=key)
        
        response = exponential_backoff_retry(_download)
        pdf_content = response['Body'].read()
        
        # Extract text from PDF
        pdf_file = BytesIO(pdf_content)
        reader = pypdf.PdfReader(pdf_file)
        
        all_text = []
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text.strip():
                    all_text.append(f"--- Page {page_num + 1} ---\n{text}")
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                all_text.append(f"--- Page {page_num + 1} ---\n[Error extracting text]")
        
        # Combine all text
        full_text = '\n\n'.join(all_text)
        
        if not full_text.strip():
            raise ValueError("No text content found in PDF")
        
        # Apply redaction rules
        processed_text, redacted = apply_redaction_rules(full_text, config)
        
        # Save as markdown file (change extension to .md for ChatGPT compatibility)
        file_path = user_info['file_path'] if user_info else key
        text_key = file_path.rsplit('.', 1)[0] + '.md'
        if user_info:
            text_key = f"users/{user_info['user_id']}/{text_key}"
        
        # Upload processed document as text
        upload_processed_document(text_key, processed_text.encode('utf-8'), 
                                {'redacted': str(redacted), 'converted_from': 'pdf'}, config, user_info)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing PDF file {key}: {str(e)}")
        raise

def process_docx_file(bucket, key, config, user_info=None):
    """Process DOCX files with fallback methods"""
    try:
        # Download file
        def _download():
            return s3.get_object(Bucket=bucket, Key=key)
        
        response = exponential_backoff_retry(_download)
        docx_content = response['Body'].read()
        
        # Try ZIP-based extraction first (doesn't require lxml)
        text_content = extract_docx_text_zip(docx_content)
        
        if not text_content and DOCX_AVAILABLE:
            # Fallback to python-docx if available
            text_content = extract_docx_text_library(docx_content)
        
        if not text_content:
            raise ValueError("No text content found in DOCX")
        
        # Apply redaction rules
        processed_text, redacted = apply_redaction_rules(text_content, config)
        
        # Save as markdown file
        file_path = user_info['file_path'] if user_info else key
        text_key = file_path.rsplit('.', 1)[0] + '.md'
        if user_info:
            text_key = f"users/{user_info['user_id']}/{text_key}"
        
        # Upload processed document
        upload_processed_document(text_key, processed_text.encode('utf-8'), 
                                {'redacted': str(redacted), 'converted_from': 'docx'}, config, user_info)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing DOCX file {key}: {str(e)}")
        raise

def extract_docx_text_zip(docx_content):
    """Extract text from DOCX using ZIP method (no dependencies)"""
    import zipfile
    import xml.etree.ElementTree as ET
    
    try:
        with zipfile.ZipFile(BytesIO(docx_content)) as zip_file:
            # Extract document.xml
            with zip_file.open('word/document.xml') as doc_xml:
                tree = ET.parse(doc_xml)
                root = tree.getroot()
                
                # Extract all text elements
                namespaces = {
                    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                }
                
                paragraphs = []
                for paragraph in root.findall('.//w:p', namespaces):
                    texts = []
                    for text_elem in paragraph.findall('.//w:t', namespaces):
                        if text_elem.text:
                            texts.append(text_elem.text)
                    if texts:
                        paragraphs.append(''.join(texts))
                
                return '\n'.join(paragraphs)
                
    except Exception as e:
        logger.warning(f"ZIP extraction failed: {str(e)}")
        return None

def extract_docx_text_library(docx_content):
    """Extract text from DOCX using python-docx library"""
    if not DOCX_AVAILABLE:
        return None
        
    try:
        doc = Document(BytesIO(docx_content))
        paragraphs = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)
        
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip())
                if row_text:
                    paragraphs.append('\t'.join(row_text))
        
        return '\n'.join(paragraphs)
        
    except Exception as e:
        logger.warning(f"python-docx extraction failed: {str(e)}")
        return None

def process_xlsx_file(bucket, key, config, user_info=None):
    """Process XLSX files by extracting all text content"""
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl library not available for XLSX processing")
    
    try:
        # Download file
        def _download():
            return s3.get_object(Bucket=bucket, Key=key)
        
        response = exponential_backoff_retry(_download)
        xlsx_content = response['Body'].read()
        
        # Load workbook
        workbook = load_workbook(BytesIO(xlsx_content), read_only=True, data_only=True)
        
        all_text = []
        
        # Process all worksheets
        for sheet in workbook.worksheets:
            sheet_text = [f"Sheet: {sheet.title}"]
            for row in sheet.iter_rows():
                row_values = []
                for cell in row:
                    if cell.value is not None:
                        row_values.append(str(cell.value))
                if row_values:
                    sheet_text.append('\t'.join(row_values))
            if len(sheet_text) > 1:  # Has content beyond title
                all_text.append('\n'.join(sheet_text))
        
        # Combine all text
        full_text = '\n\n'.join(all_text)
        
        # Apply redaction rules
        processed_text, redacted = apply_redaction_rules(full_text, config)
        
        # Save as markdown file
        file_path = user_info['file_path'] if user_info else key
        text_key = file_path.rsplit('.', 1)[0] + '.md'
        if user_info:
            text_key = f"users/{user_info['user_id']}/{text_key}"
        
        # Upload processed document as text
        upload_processed_document(text_key, processed_text.encode('utf-8'), 
                                {'redacted': str(redacted), 'converted_from': 'xlsx'}, config, user_info)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing XLSX file {key}: {str(e)}")
        raise

def quarantine_document(bucket, key, reason):
    """Move document to quarantine bucket with retry logic and user isolation"""
    copy_source = {'Bucket': bucket, 'Key': key}
    
    # Check for user prefix
    user_info = get_user_info_from_key(key)
    if user_info:
        quarantine_key = f"quarantine/users/{user_info['user_id']}/{user_info['file_path']}"
    else:
        quarantine_key = f"quarantine/{key}"
    
    def _quarantine():
        s3.copy_object(
            CopySource=copy_source,
            Bucket=QUARANTINE_BUCKET,
            Key=quarantine_key,
            ServerSideEncryption='AES256',
            Metadata={
                'quarantine-reason': reason[:255],  # S3 metadata value limit
                'original-bucket': bucket,
                'original-key': key,
                'user-id': user_info['user_id'] if user_info else 'none'
            }
        )
    
    try:
        exponential_backoff_retry(_quarantine)
        logger.info(f"Document quarantined: s3://{QUARANTINE_BUCKET}/{quarantine_key}, reason: {reason}")
    except Exception as e:
        logger.error(f"Error quarantining document after {MAX_RETRIES} attempts: {str(e)}")
        raise

def delete_processed_file(bucket, key):
    """Delete file from input bucket after successful processing"""
    try:
        def _delete():
            s3.delete_object(Bucket=bucket, Key=key)
        
        exponential_backoff_retry(_delete)
        logger.info(f"Deleted processed file: s3://{bucket}/{key}")
    except Exception as e:
        logger.error(f"Error deleting processed file: {str(e)}")
        # Don't raise exception as file was processed successfully
        
def create_success_marker(bucket, key):
    """Create a success marker file (optional for tracking)"""
    try:
        marker_key = f"_success/{key}.done"
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=marker_key,
            Body=json.dumps({
                'processed_at': time.time(),
                'original_bucket': bucket,
                'original_key': key
            }),
            ServerSideEncryption='AES256'
        )
    except Exception as e:
        logger.warning(f"Failed to create success marker: {str(e)}")
        # Don't fail the processing for marker creation