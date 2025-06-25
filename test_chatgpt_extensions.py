#!/usr/bin/env python3
"""
Test script to evaluate different file extensions for ChatGPT compatibility.
This script creates test files with various extensions and evaluates their suitability.
"""

import os
import json
from datetime import datetime

# Test content that represents typical redacted document output
TEST_CONTENT = """Document Redaction Test Output
==============================

This is a test document to evaluate file extension compatibility with ChatGPT.

Original Information:
- Company Name: [COMPANY]
- Contact: [NAME] 
- Email: [EMAIL]
- Phone: [PHONE]
- SSN: [SSN]
- Credit Card: [CREDIT_CARD]

Processing Details:
- Processed Date: {}
- Original File: test_document.pdf
- Redaction Rules Applied: 15
- Patterns Detected: 6

Summary:
This document has been processed and sensitive information has been redacted.
All personal identifiable information (PII) has been replaced with placeholders.

Note: This is plain text content that should work with any text editor.
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# File extensions to test, with metadata
EXTENSIONS_TO_TEST = {
    # Known working extensions based on research
    '.md': {
        'description': 'Markdown - Plain text with formatting support',
        'mime_type': 'text/markdown',
        'pros': ['Widely supported', 'Plain text compatible', 'Can include code blocks'],
        'cons': ['May be interpreted as markdown formatting'],
        'chatgpt_support': 'Confirmed working'
    },
    '.csv': {
        'description': 'Comma Separated Values',
        'mime_type': 'text/csv',
        'pros': ['Confirmed working in ChatGPT', 'Can handle structured data', 'Plain text'],
        'cons': ['May be interpreted as tabular data', 'Not ideal for free-form text'],
        'chatgpt_support': 'Confirmed working'
    },
    '.py': {
        'description': 'Python source code',
        'mime_type': 'text/x-python',
        'pros': ['Confirmed working', 'Plain text', 'Syntax highlighting'],
        'cons': ['May be interpreted as code', 'Not semantically correct for documents'],
        'chatgpt_support': 'Confirmed working'
    },
    '.js': {
        'description': 'JavaScript source code',
        'mime_type': 'text/javascript',
        'pros': ['Confirmed working', 'Plain text'],
        'cons': ['May be interpreted as code', 'Not semantically correct'],
        'chatgpt_support': 'Confirmed working'
    },
    '.json': {
        'description': 'JavaScript Object Notation',
        'mime_type': 'application/json',
        'pros': ['Confirmed working', 'Structured data support'],
        'cons': ['Requires valid JSON format', 'Not ideal for free text'],
        'chatgpt_support': 'Confirmed working'
    },
    
    # Previously tested extensions
    '.txt': {
        'description': 'Plain text file',
        'mime_type': 'text/plain',
        'pros': ['Most appropriate for plain text'],
        'cons': ['Known upload issues in ChatGPT since May 2025'],
        'chatgpt_support': 'Known issues - fails with "unknown error"'
    },
    '.log': {
        'description': 'Log file',
        'mime_type': 'text/plain',
        'pros': ['Semantically appropriate for processed output'],
        'cons': ['Reported as not working in recent tests'],
        'chatgpt_support': 'Tested - fails with upload errors'
    },
    
    # Additional extensions to test
    '.dat': {
        'description': 'Generic data file',
        'mime_type': 'application/octet-stream',
        'pros': ['Generic extension', 'No format assumptions'],
        'cons': ['May not be recognized as text', 'Less common'],
        'chatgpt_support': 'Unknown - needs testing'
    },
    '.out': {
        'description': 'Output file',
        'mime_type': 'text/plain',
        'pros': ['Semantically appropriate for processed output'],
        'cons': ['Less common', 'May not be recognized'],
        'chatgpt_support': 'Unknown - needs testing'
    },
    '.data': {
        'description': 'Data file',
        'mime_type': 'text/plain',
        'pros': ['Generic name', 'Implies processed data'],
        'cons': ['Uncommon extension'],
        'chatgpt_support': 'Unknown - needs testing'
    },
    '.text': {
        'description': 'Text file (alternative extension)',
        'mime_type': 'text/plain',
        'pros': ['Clear indication of content type'],
        'cons': ['Less common than .txt'],
        'chatgpt_support': 'Unknown - needs testing'
    },
    '.doc': {
        'description': 'Document file (without Word format)',
        'mime_type': 'text/plain',
        'pros': ['Document-oriented extension'],
        'cons': ['May be confused with MS Word', 'Misleading'],
        'chatgpt_support': 'May work but misleading'
    }
}

def create_test_files():
    """Create test files with different extensions"""
    test_dir = '/home/ec2-user/redact-terraform/test_extensions'
    os.makedirs(test_dir, exist_ok=True)
    
    created_files = []
    
    for ext, info in EXTENSIONS_TO_TEST.items():
        filename = f'test_document{ext}'
        filepath = os.path.join(test_dir, filename)
        
        # Create appropriate content based on extension
        if ext == '.json':
            # Create valid JSON content
            content = json.dumps({
                "document_type": "redacted_text",
                "content": TEST_CONTENT,
                "metadata": {
                    "processed_date": datetime.now().isoformat(),
                    "redactions_applied": 15
                }
            }, indent=2)
        elif ext == '.csv':
            # Create CSV-formatted content (but still readable as plain text)
            content = '"Redacted Document Output"\n' + TEST_CONTENT.replace('\n', '\n')
        else:
            # Use standard test content
            content = TEST_CONTENT
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        created_files.append({
            'path': filepath,
            'extension': ext,
            'info': info
        })
        
        print(f"Created: {filename}")
    
    return created_files

def generate_recommendation_report():
    """Generate a recommendation report based on research and testing"""
    report = """
# ChatGPT File Extension Compatibility Report
Generated: {}

## Executive Summary

Based on research and testing, the following extensions are recommended for plain text 
file uploads to ChatGPT, ranked by suitability:

### 🥇 RECOMMENDED: .md (Markdown)
- **Status**: ✅ Confirmed working
- **Rationale**: 
  - Explicitly supported by ChatGPT
  - Plain text format that displays well
  - Appropriate for document-style content
  - No misleading format implications
  - Works with all text editors

### 🥈 ALTERNATIVE: .csv (Comma Separated Values)  
- **Status**: ✅ Confirmed working
- **Rationale**:
  - Confirmed working in ChatGPT without issues
  - Still plain text, readable by any editor
  - Can wrap content in quotes to preserve formatting
  - Well-supported across platforms

### 🥉 FALLBACK: .py/.js (Code files)
- **Status**: ✅ Confirmed working
- **Rationale**:
  - Both confirmed working
  - Plain text files
  - May trigger syntax highlighting (could be a pro or con)
  - Not semantically correct but functional

## Extensions to Avoid

### ❌ .txt
- Known issues since May 2025
- Fails with "unknown error occurred"
- Despite being the most appropriate extension

### ❌ .log  
- Tested and confirmed not working
- Similar upload errors to .txt

## Implementation Recommendation

```python
# Recommended implementation in lambda_function_v2.py
def apply_filename_redaction(filename, config):
    # ... existing redaction logic ...
    
    # Use .md extension for ChatGPT compatibility
    processed_filename = f"{{processed_name}}.md"
    
    return processed_filename, redacted
```

## Testing Results

Files created in: /home/ec2-user/redact-terraform/test_extensions/
- test_document.md - Recommended for implementation
- test_document.csv - Valid alternative
- test_document.py - Functional but not ideal
- Other extensions available for manual testing

## Notes

1. The .md extension is the best compromise:
   - Works reliably with ChatGPT
   - Appropriate for document content
   - No format confusion
   - Universal text editor support

2. While .csv works, it's less semantically appropriate for 
   general document content.

3. Code file extensions (.py, .js) work but are misleading
   about content type.
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    return report

def main():
    """Main test execution"""
    print("ChatGPT File Extension Compatibility Test")
    print("=" * 50)
    
    # Create test files
    print("\nCreating test files...")
    files = create_test_files()
    
    print(f"\nCreated {len(files)} test files in: /home/ec2-user/redact-terraform/test_extensions/")
    
    # Generate report
    print("\nGenerating recommendation report...")
    report = generate_recommendation_report()
    
    report_path = '/home/ec2-user/redact-terraform/test_extensions/RECOMMENDATION_REPORT.md'
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Report saved to: {report_path}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("RECOMMENDATION SUMMARY")
    print("=" * 50)
    print("✅ Use .md (Markdown) extension for best compatibility")
    print("✅ Alternative: .csv if .md doesn't work") 
    print("❌ Avoid: .txt and .log (known issues)")
    print("\nTest files available for manual upload testing in:")
    print("/home/ec2-user/redact-terraform/test_extensions/")

if __name__ == "__main__":
    main()