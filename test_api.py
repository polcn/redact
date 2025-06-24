#!/usr/bin/env python3
"""
Test script for debugging API Gateway authentication issues
"""
import requests
import json
import base64
import boto3
import sys

# Configuration
API_URL = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"
USER_POOL_ID = "us-east-1_4Uv3seGwS"
CLIENT_ID = "130fh2g7iqc04oa6d2p55sf61o"

def test_health_check():
    """Test the health check endpoint (no auth required)"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{API_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

def get_cognito_token(username, password):
    """Get a Cognito JWT token"""
    print(f"\n=== Getting Cognito Token for {username} ===")
    
    cognito = boto3.client('cognito-idp', region_name='us-east-1')
    
    try:
        response = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        if 'AuthenticationResult' in response:
            id_token = response['AuthenticationResult']['IdToken']
            print("✓ Successfully obtained ID token")
            return id_token
        else:
            print("✗ No authentication result")
            return None
            
    except Exception as e:
        print(f"✗ Error getting token: {str(e)}")
        return None

def test_api_with_token(token):
    """Test API endpoints with JWT token"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: List user files
    print("\n=== Testing GET /user/files ===")
    response = requests.get(f"{API_URL}/user/files", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}...")
    
    # Test 2: Upload a test file
    print("\n=== Testing POST /documents/upload ===")
    test_content = "This is a test document with ACME Corporation information."
    payload = {
        'filename': 'test_api.txt',
        'content': base64.b64encode(test_content.encode()).decode()
    }
    
    response = requests.post(
        f"{API_URL}/documents/upload",
        headers=headers,
        json=payload
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 202:
        data = response.json()
        doc_id = data.get('document_id')
        
        # Test 3: Check status
        print(f"\n=== Testing GET /documents/status/{doc_id} ===")
        response = requests.get(
            f"{API_URL}/documents/status/{doc_id}",
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

def test_cors_preflight():
    """Test CORS preflight request"""
    print("\n=== Testing CORS Preflight ===")
    headers = {
        'Origin': 'https://redact.9thcube.com',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type'
    }
    
    response = requests.options(f"{API_URL}/documents/upload", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"CORS Headers: {dict(response.headers)}")

def main():
    print("Document Redaction API Test Suite")
    print("=================================")
    
    # Test health check
    if not test_health_check():
        print("\n✗ Health check failed. API may be down.")
        return
    
    # Test CORS
    test_cors_preflight()
    
    # Test with authentication
    if len(sys.argv) > 2:
        username = sys.argv[1]
        password = sys.argv[2]
        
        token = get_cognito_token(username, password)
        if token:
            test_api_with_token(token)
    else:
        print("\n⚠️  No credentials provided. Skipping authenticated tests.")
        print("Usage: python test_api.py <username> <password>")
        
        # Test without token to see error
        print("\n=== Testing without authentication ===")
        response = requests.get(f"{API_URL}/user/files")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    main()