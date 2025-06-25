#!/usr/bin/env python3
"""
Test script to verify pattern matching fix with user-specific configurations
"""

import boto3
import json
import base64
import time
import requests
from datetime import datetime

# Test configuration
API_URL = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"
TEST_USER_EMAIL = "testuser@gmail.com"  # Should be an allowed domain
TEST_USER_PASSWORD = "TestPassword123!"

# Test document with various PII patterns
TEST_DOCUMENT = """
Test Document for Pattern Matching

Personal Information:
Name: John Smith
SSN: 123-45-6789
Phone: (555) 123-4567
Email: john.smith@example.com
IP Address: 192.168.1.100
Driver's License: D1234567

Credit Card: 4532-1234-5678-9012
Another SSN format: 987654321
International phone: +1-555-987-6543

Company: ACME Corporation
Project: TechnoSoft Implementation
"""

def get_auth_token():
    """Get authentication token from Cognito"""
    cognito = boto3.client('cognito-idp', region_name='us-east-1')
    
    try:
        # Try to authenticate
        response = cognito.initiate_auth(
            ClientId='130fh2g7iqc04oa6d2p55sf61o',
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': TEST_USER_EMAIL,
                'PASSWORD': TEST_USER_PASSWORD
            }
        )
        
        return response['AuthenticationResult']['IdToken']
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        print("Please ensure test user exists and is confirmed")
        return None

def test_pattern_matching():
    """Test pattern matching with user-specific config"""
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to authenticate")
        return False
    
    print("✅ Authentication successful")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 1: Enable all pattern detection
    print("\n1. Configuring pattern detection...")
    config = {
        "replacements": [
            {"find": "ACME Corporation", "replace": "[COMPANY]"},
            {"find": "TechnoSoft", "replace": "[PROJECT]"}
        ],
        "case_sensitive": False,
        "patterns": {
            "ssn": True,
            "credit_card": True,
            "phone": True,
            "email": True,
            "ip_address": True,
            "drivers_license": True
        }
    }
    
    response = requests.put(f"{API_URL}/api/config", 
                           headers=headers,
                           json=config)
    
    if response.status_code == 200:
        print("✅ Pattern detection configured")
    else:
        print(f"❌ Failed to configure: {response.text}")
        return False
    
    # Step 2: Upload test document
    print("\n2. Uploading test document...")
    upload_data = {
        "filename": "test_patterns.txt",
        "content": base64.b64encode(TEST_DOCUMENT.encode()).decode()
    }
    
    response = requests.post(f"{API_URL}/documents/upload",
                           headers=headers,
                           json=upload_data)
    
    if response.status_code == 202:
        result = response.json()
        document_id = result['document_id']
        print(f"✅ Document uploaded: {document_id}")
    else:
        print(f"❌ Upload failed: {response.text}")
        return False
    
    # Step 3: Wait for processing
    print("\n3. Waiting for processing...")
    max_attempts = 30
    for i in range(max_attempts):
        time.sleep(2)
        
        response = requests.get(f"{API_URL}/documents/status/{document_id}",
                              headers=headers)
        
        if response.status_code == 200:
            status = response.json()
            if status['status'] == 'completed':
                print("✅ Processing completed")
                break
            elif status['status'] == 'quarantined':
                print(f"❌ Document quarantined: {status.get('reason', 'Unknown')}")
                return False
        else:
            print(f"❌ Status check failed: {response.text}")
            return False
    else:
        print("❌ Processing timeout")
        return False
    
    # Step 4: Download and verify processed document
    print("\n4. Downloading processed document...")
    response = requests.get(f"{API_URL}/user/files", headers=headers)
    
    if response.status_code == 200:
        files = response.json()['files']
        processed_file = None
        
        for file in files:
            if file['id'] == document_id and file['status'] == 'completed':
                processed_file = file
                break
        
        if not processed_file:
            print("❌ Processed file not found")
            return False
        
        # Download the file content
        download_url = processed_file['download_url']
        response = requests.get(download_url)
        
        if response.status_code == 200:
            content = response.text
            print("✅ Downloaded processed document")
            
            # Verify patterns were redacted
            print("\n5. Verifying pattern redaction...")
            patterns_found = []
            patterns_redacted = []
            
            # Check each pattern
            checks = [
                ("SSN", "123-45-6789", "[SSN]"),
                ("Credit Card", "4532-1234-5678-9012", "[CREDIT_CARD]"),
                ("Phone", "(555) 123-4567", "[PHONE]"),
                ("Email", "john.smith@example.com", "[EMAIL]"),
                ("IP Address", "192.168.1.100", "[IP_ADDRESS]"),
                ("Driver's License", "D1234567", "[DRIVERS_LICENSE]"),
                ("Company", "ACME Corporation", "[COMPANY]"),
                ("Project", "TechnoSoft", "[PROJECT]")
            ]
            
            print("\nRedaction Results:")
            print("-" * 50)
            
            for name, original, replacement in checks:
                if original in content:
                    patterns_found.append(name)
                    print(f"❌ {name}: NOT redacted (found '{original}')")
                elif replacement in content:
                    patterns_redacted.append(name)
                    print(f"✅ {name}: Redacted to '{replacement}'")
                else:
                    print(f"⚠️  {name}: Neither original nor replacement found")
            
            print("-" * 50)
            print(f"Total patterns redacted: {len(patterns_redacted)}/{len(checks)}")
            
            if len(patterns_redacted) == len(checks):
                print("\n✅ All patterns successfully redacted!")
                return True
            else:
                print(f"\n❌ Pattern redaction incomplete")
                print(f"   Patterns found unredacted: {patterns_found}")
                return False
            
        else:
            print(f"❌ Download failed: {response.status_code}")
            return False
    else:
        print(f"❌ Failed to list files: {response.text}")
        return False

def main():
    """Main test function"""
    print("Pattern Matching Fix Verification Test")
    print("=" * 50)
    print(f"API URL: {API_URL}")
    print(f"Test User: {TEST_USER_EMAIL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)
    
    success = test_pattern_matching()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ PATTERN MATCHING FIX VERIFIED - All tests passed!")
    else:
        print("❌ PATTERN MATCHING FIX FAILED - Please check the implementation")
    print("=" * 50)

if __name__ == "__main__":
    main()