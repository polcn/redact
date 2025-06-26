"""Simple PPTX handler without lxml dependency"""

import json
import zipfile
import re
from io import BytesIO

def extract_text_from_pptx(pptx_content):
    """Extract text from PPTX without using python-pptx library"""
    text_parts = []
    
    try:
        # PPTX files are ZIP archives
        with zipfile.ZipFile(BytesIO(pptx_content), 'r') as zip_file:
            # Get slide files
            slide_files = [f for f in zip_file.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
            slide_files.sort()  # Sort to maintain slide order
            
            text_parts.append(f"# PowerPoint Document ({len(slide_files)} slides)\n")
            
            for idx, slide_file in enumerate(slide_files, 1):
                text_parts.append(f"\n--- Slide {idx} ---")
                
                # Read slide XML content
                slide_content = zip_file.read(slide_file).decode('utf-8', errors='ignore')
                
                # Extract text from XML (simple regex approach)
                # Look for text between <a:t> tags
                text_matches = re.findall(r'<a:t[^>]*>([^<]+)</a:t>', slide_content)
                
                if text_matches:
                    # Clean and join text
                    slide_text = ' '.join(text_matches)
                    slide_text = re.sub(r'\s+', ' ', slide_text).strip()
                    text_parts.append(slide_text)
                
                text_parts.append("")  # Empty line between slides
            
        return '\n'.join(text_parts)
        
    except Exception as e:
        raise Exception(f"Failed to extract text from PPTX: {str(e)}")

def process_pptx_simple(pptx_content, config):
    """Process PPTX file with simple text extraction"""
    import os
    
    # Extract text
    text = extract_text_from_pptx(pptx_content)
    
    # Apply redaction rules (simplified version)
    processed_text = text
    redacted = False
    
    # Apply text replacements
    if config and 'replacements' in config:
        for replacement in config.get('replacements', []):
            find_text = replacement.get('find', '')
            replace_text = replacement.get('replace', '[REDACTED]')
            
            if find_text and find_text in processed_text:
                redacted = True
                processed_text = processed_text.replace(find_text, replace_text)
    
    # Simple PII patterns
    patterns = {
        'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
        'credit_card': (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CREDIT CARD REDACTED]'),
        'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),
        'phone': (r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', '[PHONE REDACTED]')
    }
    
    # Apply pattern-based redaction if enabled
    if config and 'patterns' in config:
        for pattern_name, (pattern, replace) in patterns.items():
            if config['patterns'].get(pattern_name, False):
                if re.search(pattern, processed_text):
                    redacted = True
                    processed_text = re.sub(pattern, replace, processed_text)
    
    # Windows line endings
    if os.environ.get('WINDOWS_MODE', 'true').lower() == 'true':
        processed_text = processed_text.replace('\n', '\r\n')
    
    return processed_text, redacted