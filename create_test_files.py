#!/usr/bin/env python3
"""
Create various test files to verify .log extension output
"""

import os
from datetime import datetime

# Create test directory
os.makedirs("test_files", exist_ok=True)

# Test 1: Simple text file
with open("test_files/simple.txt", "w") as f:
    f.write("This is a simple test file.\nIt should output as simple.log")

# Test 2: PDF content simulation (text that would come from PDF)
with open("test_files/pdf_content.txt", "w") as f:
    f.write("""--- Page 1 ---
PDF Document Title

This simulates content extracted from a PDF file.
It should output as pdf_content.log

--- Page 2 ---
More content here.
The file extension should be .log, not .txt
""")

# Test 3: Excel content simulation
with open("test_files/excel_content.txt", "w") as f:
    f.write("""Sheet: Data
Name\tEmail\tPhone
John Smith\tjohn@example.com\t555-1234
Jane Doe\tjane@example.com\t555-5678

This simulates content from an Excel file.
Output should be excel_content.log
""")

# Test 4: DOCX content simulation  
with open("test_files/docx_content.txt", "w") as f:
    f.write("""Document Title

This simulates content extracted from a Word document.
Output filename should be docx_content.log

Paragraph 2
More content here.
""")

# Test 5: Special characters for ChatGPT compatibility test
with open("test_files/chatgpt_test.txt", "w") as f:
    f.write("""ChatGPT Upload Test File
========================

This file tests compatibility with ChatGPT's file upload.

Special characters that should be normalized:
- Smart quotes: "Hello" and 'World'
- Em dash: Text—more text
- Bullet: • Point 1
- Non-breaking space: Hello World

PII to redact:
- SSN: 123-45-6789
- Email: test@example.com
- Phone: (555) 123-4567

Expected output: chatgpt_test.log (not .txt)
""")

print("Created test files:")
print("=" * 50)

for filename in os.listdir("test_files"):
    if filename.endswith(".txt"):
        filepath = os.path.join("test_files", filename)
        size = os.path.getsize(filepath)
        print(f"✓ {filename:<20} ({size} bytes)")

print("\nInstructions:")
print("1. Go to https://redact.9thcube.com")
print("2. Log in with your test account")
print("3. Upload these test files")
print("4. After processing, verify:")
print("   - All output files have .log extension")
print("   - Files can be uploaded to ChatGPT successfully")
print("   - Special characters are normalized to ASCII")
print("\nTimestamp:", datetime.now().isoformat())