#!/usr/bin/env python3
"""
Test script to verify .log extension functionality in the redact system
"""

import requests
import json
import base64
import time
import os
from datetime import datetime

# API Configuration
API_URL = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"

# Test user credentials (you'll need to update these)
USERNAME = "test@example.com"  # Update with a valid test user
PASSWORD = "TestPassword123!"  # Update with the test user's password

def get_auth_token():
    """Get authentication token from Cognito"""
    import boto3
    
    client = boto3.client('cognito-idp', region_name='us-east-1')
    
    try:
        response = client.initiate_auth(
            ClientId='130fh2g7iqc04oa6d2p55sf61o',
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': USERNAME,
                'PASSWORD': PASSWORD
            }
        )
        
        return response['AuthenticationResult']['IdToken']
    except Exception as e:
        print(f"Error getting auth token: {e}")
        print("Please update USERNAME and PASSWORD with valid test credentials")
        return None

def upload_file(file_path, auth_token):
    """Upload a file to the redact system"""
    filename = os.path.basename(file_path)
    
    # Read and encode file
    with open(file_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    
    # Prepare request
    headers = {
        'Authorization': auth_token,
        'Content-Type': 'application/json'
    }
    
    data = {
        'filename': filename,
        'content': content
    }
    
    # Upload file
    response = requests.post(
        f"{API_URL}/documents/upload",
        headers=headers,
        json=data
    )
    
    if response.status_code == 202:
        result = response.json()
        print(f"✓ Uploaded {filename}")
        print(f"  Document ID: {result['document_id']}")
        return result['document_id']
    else:
        print(f"✗ Failed to upload {filename}: {response.status_code}")
        print(f"  Response: {response.text}")
        return None

def check_status(document_id, auth_token):
    """Check processing status of a document"""
    headers = {
        'Authorization': auth_token
    }
    
    response = requests.get(
        f"{API_URL}/documents/status/{document_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error checking status: {response.status_code}")
        return None

def wait_for_processing(document_id, auth_token, max_wait=60):
    """Wait for document to be processed"""
    print(f"Waiting for processing", end="")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status = check_status(document_id, auth_token)
        
        if status:
            if status['status'] == 'completed':
                print(" ✓ Completed!")
                return status
            elif status['status'] == 'quarantined':
                print(f" ✗ Quarantined: {status.get('reason', 'Unknown')}")
                return status
            elif status['status'] == 'not_found':
                print(" ✗ Not found")
                return status
        
        print(".", end="", flush=True)
        time.sleep(2)
    
    print(" ✗ Timeout")
    return None

def download_file(url, output_path):
    """Download processed file"""
    response = requests.get(url)
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    else:
        print(f"Failed to download: {response.status_code}")
        return False

def verify_log_extension(status):
    """Verify that processed files have .log extension"""
    if status and status['status'] == 'completed':
        processed_files = status.get('processed_files', [])
        
        print("\nVerifying file extensions:")
        all_log = True
        
        for file_key in processed_files:
            filename = file_key.split('/')[-1]
            if filename.endswith('.log'):
                print(f"  ✓ {filename} - Correct .log extension")
            else:
                print(f"  ✗ {filename} - Wrong extension (expected .log)")
                all_log = False
        
        return all_log
    return False

def main():
    print("=" * 60)
    print("Redact System .log Extension Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Get auth token
    print("\n1. Getting authentication token...")
    auth_token = get_auth_token()
    
    if not auth_token:
        print("Cannot proceed without authentication")
        return
    
    print("✓ Authentication successful")
    
    # Test files
    test_files = [
        "test_files/test_document.txt",
        "test_files/test_with_special_chars.txt"
    ]
    
    results = []
    
    # Upload and process each test file
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n2. Testing {test_file}...")
            
            # Upload
            doc_id = upload_file(test_file, auth_token)
            
            if doc_id:
                # Wait for processing
                status = wait_for_processing(doc_id, auth_token)
                
                if status and status['status'] == 'completed':
                    # Verify extension
                    log_correct = verify_log_extension(status)
                    
                    # Download first processed file
                    if status.get('download_urls'):
                        url = status['download_urls'][0]
                        output_file = f"test_output/{doc_id}.log"
                        
                        os.makedirs("test_output", exist_ok=True)
                        
                        print(f"\nDownloading processed file...")
                        if download_file(url, output_file):
                            print(f"✓ Downloaded to {output_file}")
                            
                            # Check content
                            with open(output_file, 'r') as f:
                                content = f.read()
                                
                            print(f"\nFile details:")
                            print(f"  Size: {len(content)} bytes")
                            print(f"  Lines: {len(content.splitlines())}")
                            
                            # Check for Windows line endings
                            if '\r\n' in content:
                                print(f"  Line endings: CRLF (Windows compatible)")
                            else:
                                print(f"  Line endings: LF (Unix)")
                            
                            # Check for non-ASCII characters
                            non_ascii = [c for c in content if ord(c) > 127]
                            if non_ascii:
                                print(f"  ⚠️  Found {len(non_ascii)} non-ASCII characters")
                            else:
                                print(f"  ✓ All characters are ASCII")
                    
                    results.append({
                        'file': test_file,
                        'doc_id': doc_id,
                        'status': 'success',
                        'log_extension': log_correct
                    })
                else:
                    results.append({
                        'file': test_file,
                        'doc_id': doc_id,
                        'status': 'failed',
                        'reason': status.get('reason', 'Unknown') if status else 'Timeout'
                    })
        else:
            print(f"\n✗ Test file not found: {test_file}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r.get('status') == 'success')
    log_count = sum(1 for r in results if r.get('log_extension', False))
    
    print(f"Total tests: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"With .log extension: {log_count}")
    
    if log_count == len(results):
        print("\n✓ ALL FILES HAVE .LOG EXTENSION - ChatGPT compatibility confirmed!")
    else:
        print("\n✗ Some files missing .log extension")
    
    print("\nIndividual results:")
    for result in results:
        print(f"  {result['file']}: {result.get('status', 'unknown')}")
        if result.get('log_extension') is not None:
            print(f"    .log extension: {'✓' if result['log_extension'] else '✗'}")

if __name__ == "__main__":
    main()