#!/usr/bin/env python3
"""
Authentication utilities for testing vector integration
Handles Cognito token generation and validation for tests
"""

import os
import json
import time
import base64
import hashlib
import hmac
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import uuid

class MockCognitoAuth:
    """Mock Cognito authentication for testing"""
    
    def __init__(self, user_pool_id: str = "us-east-1_4Uv3seGwS"):
        self.user_pool_id = user_pool_id
        self.mock_users = {}
        self.mock_tokens = {}
    
    def create_test_user(self, username: str, email: str, password: str = "TestPass123!") -> Dict[str, str]:
        """Create a mock test user"""
        user_id = f"test_user_{hashlib.md5(username.encode()).hexdigest()[:8]}"
        self.mock_users[username] = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "password": password,
            "created": datetime.now().isoformat()
        }
        return self.mock_users[username]
    
    def generate_mock_token(self, username: str) -> Dict[str, str]:
        """Generate a mock JWT token for testing"""
        if username not in self.mock_users:
            raise ValueError(f"User {username} not found")
        
        user = self.mock_users[username]
        
        # Create JWT header
        header = {
            "typ": "JWT",
            "alg": "RS256",
            "kid": "test-key-id"
        }
        
        # Create JWT payload
        now = datetime.now()
        exp = now + timedelta(hours=1)
        
        payload = {
            "sub": user["user_id"],
            "aud": "test-client-id",
            "iss": f"https://cognito-idp.us-east-1.amazonaws.com/{self.user_pool_id}",
            "token_use": "id",
            "auth_time": int(now.timestamp()),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "email": user["email"],
            "email_verified": True,
            "cognito:username": user["username"]
        }
        
        # Create mock JWT (not properly signed, just for testing)
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = base64.urlsafe_b64encode(b"mock-signature").decode().rstrip('=')
        
        id_token = f"{header_b64}.{payload_b64}.{signature}"
        access_token = f"mock-access-token-{user['user_id']}"
        refresh_token = f"mock-refresh-token-{user['user_id']}"
        
        token_data = {
            "id_token": id_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 3600,
            "token_type": "Bearer",
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"]
        }
        
        self.mock_tokens[id_token] = token_data
        return token_data
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a mock token"""
        if token.startswith("Bearer "):
            token = token[7:]
        
        if token in self.mock_tokens:
            token_data = self.mock_tokens[token]
            # Check if token is expired (basic check)
            try:
                payload = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '==').decode())
                if payload['exp'] < time.time():
                    return None
            except:
                pass
            
            return token_data
        return None

class TestAuthHelper:
    """Helper class for authentication in tests"""
    
    def __init__(self):
        self.auth = MockCognitoAuth()
        self.current_user = None
        self.current_token = None
        
    def create_test_users(self) -> Dict[str, Dict]:
        """Create standard test users"""
        users = {}
        
        # Create different test users for different scenarios
        test_users_data = [
            ("testuser1", "testuser1@example.com"),
            ("testuser2", "testuser2@example.com"),
            ("admin_user", "admin@example.com"),
            ("isolated_user", "isolated@example.com")
        ]
        
        for username, email in test_users_data:
            user = self.auth.create_test_user(username, email)
            token = self.auth.generate_mock_token(username)
            users[username] = {
                "user": user,
                "token": token,
                "headers": self.get_auth_headers(token["id_token"])
            }
        
        return users
    
    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def login_as_user(self, username: str) -> Dict[str, str]:
        """Login as a specific test user and return headers"""
        if username not in self.auth.mock_users:
            self.auth.create_test_user(username, f"{username}@example.com")
        
        token_data = self.auth.generate_mock_token(username)
        self.current_user = username
        self.current_token = token_data["id_token"]
        
        return self.get_auth_headers(token_data["id_token"])
    
    def get_user_context(self, token: str) -> Dict[str, Any]:
        """Extract user context from token (simulates Lambda context)"""
        token_data = self.auth.validate_token(token)
        if not token_data:
            return {}
        
        return {
            "user_id": token_data["user_id"],
            "username": token_data["username"],
            "email": token_data["email"],
            "authenticated": True
        }
    
    def create_lambda_event(self, method: str, path: str, body: Dict = None, 
                           headers: Dict = None, query_params: Dict = None) -> Dict:
        """Create a mock Lambda API Gateway event"""
        event = {
            "httpMethod": method,
            "path": path,
            "headers": headers or {},
            "queryStringParameters": query_params or {},
            "body": json.dumps(body) if body else None,
            "requestContext": {
                "requestId": str(uuid.uuid4()),
                "stage": "test",
                "httpMethod": method,
                "path": path
            },
            "isBase64Encoded": False
        }
        
        # Add authorization context if headers contain auth
        if headers and "Authorization" in headers:
            token = headers["Authorization"].replace("Bearer ", "")
            user_context = self.get_user_context(token)
            event["requestContext"]["authorizer"] = {
                "claims": user_context
            }
        
        return event
    
    def create_lambda_context(self) -> object:
        """Create a mock Lambda context"""
        class MockContext:
            def __init__(self):
                self.function_name = "test-function"
                self.function_version = "1"
                self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
                self.memory_limit_in_mb = "128"
                self.remaining_time_in_millis = lambda: 30000
                self.aws_request_id = str(uuid.uuid4())
                self.log_group_name = "/aws/lambda/test-function"
                self.log_stream_name = "2024/01/01/[1]test-stream"
        
        return MockContext()


def setup_test_environment():
    """Set up test environment with mock AWS credentials and settings"""
    # Set mock AWS credentials
    os.environ.update({
        'AWS_ACCESS_KEY_ID': 'test-access-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
        'AWS_SESSION_TOKEN': 'test-session-token',
        'AWS_DEFAULT_REGION': 'us-east-1',
        
        # Mock S3 buckets
        'PROCESSED_BUCKET': 'redact-processed-documents-test',
        'INPUT_BUCKET': 'redact-input-documents-test',
        'QUARANTINE_BUCKET': 'redact-quarantine-documents-test',
        'CONFIG_BUCKET': 'redact-config-documents-test',
        
        # ChromaDB settings
        'CHROMADB_PERSIST_DIR': '/tmp/test_chromadb',
        'CHROMADB_COLLECTION': 'test_redact_documents',
        
        # Other settings
        'LOG_LEVEL': 'INFO',
        'ENVIRONMENT': 'test'
    })


def cleanup_test_environment():
    """Clean up test environment"""
    # Remove test ChromaDB data
    import shutil
    test_dirs = ['/tmp/test_chromadb', '/tmp/test_custom_chromadb']
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
    
    # Reset environment variables
    test_env_vars = [
        'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN',
        'PROCESSED_BUCKET', 'INPUT_BUCKET', 'QUARANTINE_BUCKET', 'CONFIG_BUCKET',
        'CHROMADB_PERSIST_DIR', 'CHROMADB_COLLECTION'
    ]
    
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


# Test the authentication utilities
if __name__ == "__main__":
    print("Testing authentication utilities...")
    
    setup_test_environment()
    
    # Test mock auth
    auth_helper = TestAuthHelper()
    users = auth_helper.create_test_users()
    
    print("Created test users:")
    for username, data in users.items():
        print(f"  {username}: {data['user']['email']}")
    
    # Test token validation
    token = users["testuser1"]["token"]["id_token"]
    user_context = auth_helper.get_user_context(token)
    print(f"\nUser context for testuser1: {user_context}")
    
    # Test Lambda event creation
    headers = auth_helper.login_as_user("testuser1")
    event = auth_helper.create_lambda_event("POST", "/vectors/store", 
                                           {"test": "data"}, headers)
    print(f"\nLambda event created successfully")
    
    cleanup_test_environment()
    print("✅ Authentication utilities test completed")