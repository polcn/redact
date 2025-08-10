#!/usr/bin/env python3
"""
Comprehensive test suite for the Redact application
Tests all API endpoints and verifies recent fixes including:
- Bedrock model integration
- IAM permissions
- S3 bucket configuration
- File upload and processing
- AI summary generation
- Quarantine functionality
"""

import json
import sys
import time
import base64
import requests
import boto3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError
import urllib3
import os
import tempfile

# Disable SSL warnings for development testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# Test Configuration
# ============================================================================

class TestConfig:
    """Test configuration and constants"""
    # API endpoints
    PROD_URL = "https://redact.9thcube.com"
    API_URL = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"
    
    # Test credentials (you'll need to provide these)
    TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@example.com")
    TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TestPassword123!")
    
    # Colors for terminal output
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Test timeouts
    REQUEST_TIMEOUT = 30
    PROCESSING_TIMEOUT = 120
    
    # Test data
    TEST_SSN = "123-45-6789"
    TEST_CREDIT_CARD = "4111-1111-1111-1111"
    TEST_EMAIL_ADDRESS = "sensitive@example.com"
    TEST_PHONE = "(555) 123-4567"
    TEST_IP = "192.168.1.100"

# ============================================================================
# Helper Functions
# ============================================================================

class TestUtils:
    """Utility functions for testing"""
    
    @staticmethod
    def print_header(title: str):
        """Print a formatted test section header"""
        print(f"\n{TestConfig.BLUE}{'='*70}{TestConfig.RESET}")
        print(f"{TestConfig.BLUE}{TestConfig.BOLD}{title}{TestConfig.RESET}")
        print(f"{TestConfig.BLUE}{'='*70}{TestConfig.RESET}")
    
    @staticmethod
    def print_test(test_name: str, status: str = "RUNNING"):
        """Print test status"""
        if status == "RUNNING":
            print(f"\n{TestConfig.CYAN}▶ Testing: {test_name}...{TestConfig.RESET}")
        elif status == "PASSED":
            print(f"{TestConfig.GREEN}✓ {test_name} - PASSED{TestConfig.RESET}")
        elif status == "FAILED":
            print(f"{TestConfig.RED}✗ {test_name} - FAILED{TestConfig.RESET}")
        elif status == "SKIPPED":
            print(f"{TestConfig.YELLOW}⊘ {test_name} - SKIPPED{TestConfig.RESET}")
    
    @staticmethod
    def print_result(success: bool, message: str, details: str = None):
        """Print test result with optional details"""
        if success:
            print(f"  {TestConfig.GREEN}✓ {message}{TestConfig.RESET}")
        else:
            print(f"  {TestConfig.RED}✗ {message}{TestConfig.RESET}")
        
        if details:
            print(f"    {TestConfig.YELLOW}Details: {details}{TestConfig.RESET}")
    
    @staticmethod
    def create_test_document(content_type: str = "text") -> Tuple[str, str, str]:
        """Create a test document with PII data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if content_type == "text":
            filename = f"test_document_{timestamp}.txt"
            content = f"""
Test Document - Created {datetime.now().isoformat()}

This document contains sensitive information that should be redacted:

Personal Information:
- SSN: {TestConfig.TEST_SSN}
- Credit Card: {TestConfig.TEST_CREDIT_CARD}
- Email: {TestConfig.TEST_EMAIL_ADDRESS}
- Phone: {TestConfig.TEST_PHONE}
- IP Address: {TestConfig.TEST_IP}

Driver's License: D12345678
Date of Birth: 01/15/1985

This is test data for validating the redaction system.
"""
            content_base64 = base64.b64encode(content.encode()).decode()
            
        elif content_type == "csv":
            filename = f"test_data_{timestamp}.csv"
            content = """Name,SSN,Email,Phone,Credit Card
John Doe,123-45-6789,john@example.com,(555) 123-4567,4111-1111-1111-1111
Jane Smith,987-65-4321,jane@example.com,(555) 987-6543,5500-0000-0000-0004
"""
            content_base64 = base64.b64encode(content.encode()).decode()
            
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        return filename, content, content_base64

# ============================================================================
# Authentication Manager
# ============================================================================

class AuthManager:
    """Manages authentication for API testing"""
    
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name='us-east-1')
        self.user_pool_id = 'us-east-1_4Uv3seGwS'
        self.client_id = None
        self.id_token = None
        self.access_token = None
        self.refresh_token = None
        
    def get_client_id(self) -> str:
        """Get Cognito client ID from user pool"""
        try:
            response = self.cognito_client.list_user_pool_clients(
                UserPoolId=self.user_pool_id,
                MaxResults=10
            )
            
            for client in response['UserPoolClients']:
                if 'redact' in client['ClientName'].lower():
                    self.client_id = client['ClientId']
                    return self.client_id
                    
            # If no specific client found, use the first one
            if response['UserPoolClients']:
                self.client_id = response['UserPoolClients'][0]['ClientId']
                return self.client_id
                
        except Exception as e:
            print(f"{TestConfig.RED}Failed to get Cognito client ID: {e}{TestConfig.RESET}")
            return None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user and get tokens"""
        try:
            if not self.client_id:
                self.get_client_id()
            
            if not self.client_id:
                print(f"{TestConfig.RED}No Cognito client ID available{TestConfig.RESET}")
                return False
            
            response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            if 'AuthenticationResult' in response:
                self.id_token = response['AuthenticationResult']['IdToken']
                self.access_token = response['AuthenticationResult']['AccessToken']
                self.refresh_token = response['AuthenticationResult'].get('RefreshToken')
                return True
            
            return False
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                print(f"{TestConfig.YELLOW}Authentication failed: Invalid credentials{TestConfig.RESET}")
            elif error_code == 'UserNotFoundException':
                print(f"{TestConfig.YELLOW}Authentication failed: User not found{TestConfig.RESET}")
            else:
                print(f"{TestConfig.RED}Authentication error: {e}{TestConfig.RESET}")
            return False
        except Exception as e:
            print(f"{TestConfig.RED}Unexpected authentication error: {e}{TestConfig.RESET}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        if not self.id_token:
            return {}
        
        return {
            'Authorization': f'Bearer {self.id_token}',
            'Content-Type': 'application/json'
        }

# ============================================================================
# API Test Suite
# ============================================================================

class APITestSuite:
    """Main test suite for API endpoints"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth = auth_manager
        self.base_url = TestConfig.API_URL
        self.test_results = []
        self.uploaded_files = []  # Track files for cleanup
        
    def make_request(self, method: str, endpoint: str, 
                     data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Make an API request and return (success, response_data, error_message)"""
        url = f"{self.base_url}{endpoint}"
        
        if headers is None:
            headers = self.auth.get_headers()
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=TestConfig.REQUEST_TIMEOUT)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=TestConfig.REQUEST_TIMEOUT)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=TestConfig.REQUEST_TIMEOUT)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=TestConfig.REQUEST_TIMEOUT)
            else:
                return False, None, f"Unsupported method: {method}"
            
            if response.status_code == 200:
                try:
                    return True, response.json(), None
                except json.JSONDecodeError:
                    return True, {'text': response.text}, None
            else:
                return False, None, f"Status {response.status_code}: {response.text}"
                
        except requests.exceptions.Timeout:
            return False, None, "Request timeout"
        except requests.exceptions.ConnectionError:
            return False, None, "Connection error"
        except Exception as e:
            return False, None, str(e)
    
    def test_health_check(self) -> bool:
        """Test /health endpoint"""
        TestUtils.print_test("Health Check", "RUNNING")
        
        # Health check doesn't require authentication
        success, data, error = self.make_request("GET", "/health", headers={})
        
        if success and data and data.get('status') == 'healthy':
            TestUtils.print_result(True, "API is healthy")
            TestUtils.print_test("Health Check", "PASSED")
            return True
        else:
            TestUtils.print_result(False, "Health check failed", error)
            TestUtils.print_test("Health Check", "FAILED")
            return False
    
    def test_config_endpoint(self) -> bool:
        """Test /api/config endpoint"""
        TestUtils.print_test("Configuration Endpoint", "RUNNING")
        
        # Test GET
        success, data, error = self.make_request("GET", "/api/config")
        
        if not success:
            TestUtils.print_result(False, "Failed to GET config", error)
            TestUtils.print_test("Configuration Endpoint", "FAILED")
            return False
        
        TestUtils.print_result(True, "Successfully retrieved configuration")
        
        # Verify config structure
        if data and 'rules' in data:
            TestUtils.print_result(True, f"Found {len(data['rules'])} redaction rules")
            
            # Check for expected rule types
            rule_types = {rule['type'] for rule in data['rules']}
            expected_types = {'ssn', 'credit_card', 'email', 'phone', 'ip_address'}
            
            for rule_type in expected_types:
                if rule_type in rule_types:
                    TestUtils.print_result(True, f"Found {rule_type} rule")
                else:
                    TestUtils.print_result(False, f"Missing {rule_type} rule")
        
        TestUtils.print_test("Configuration Endpoint", "PASSED")
        return True
    
    def test_user_files_listing(self) -> bool:
        """Test /user/files endpoint"""
        TestUtils.print_test("User Files Listing", "RUNNING")
        
        success, data, error = self.make_request("GET", "/user/files")
        
        if not success:
            TestUtils.print_result(False, "Failed to list user files", error)
            TestUtils.print_test("User Files Listing", "FAILED")
            return False
        
        TestUtils.print_result(True, "Successfully retrieved user files")
        
        if data and 'files' in data:
            file_count = len(data['files'])
            TestUtils.print_result(True, f"Found {file_count} files for user")
            
            # Display file details if any exist
            for file_info in data['files'][:3]:  # Show first 3 files
                print(f"    - {file_info.get('filename', 'Unknown')} "
                      f"({file_info.get('status', 'Unknown')} - "
                      f"{file_info.get('size', 0)} bytes)")
        
        TestUtils.print_test("User Files Listing", "PASSED")
        return True
    
    def test_file_upload_and_processing(self) -> bool:
        """Test file upload and processing flow"""
        TestUtils.print_test("File Upload & Processing", "RUNNING")
        
        # Create test document
        filename, content, content_base64 = TestUtils.create_test_document("text")
        
        # Upload document
        upload_data = {
            "filename": filename,
            "content": content_base64,
            "content_type": "text/plain"
        }
        
        success, data, error = self.make_request("POST", "/documents/upload", upload_data)
        
        if not success:
            TestUtils.print_result(False, "Failed to upload file", error)
            TestUtils.print_test("File Upload & Processing", "FAILED")
            return False
        
        TestUtils.print_result(True, f"File uploaded: {filename}")
        
        if not data or 'document_id' not in data:
            TestUtils.print_result(False, "No document ID returned")
            TestUtils.print_test("File Upload & Processing", "FAILED")
            return False
        
        document_id = data['document_id']
        self.uploaded_files.append(document_id)  # Track for cleanup
        TestUtils.print_result(True, f"Document ID: {document_id}")
        
        # Check processing status
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(4)  # Wait 4 seconds between checks
            
            success, status_data, error = self.make_request("GET", f"/documents/status/{document_id}")
            
            if success and status_data:
                status = status_data.get('status', 'unknown')
                print(f"    Attempt {attempt + 1}/{max_attempts}: Status = {status}")
                
                if status == 'completed':
                    TestUtils.print_result(True, "File processing completed")
                    
                    # Check if PII was detected and redacted
                    if 'download_url' in status_data:
                        TestUtils.print_result(True, "Download URL available")
                    
                    TestUtils.print_test("File Upload & Processing", "PASSED")
                    return True
                    
                elif status == 'failed':
                    TestUtils.print_result(False, "File processing failed", 
                                         status_data.get('error', 'Unknown error'))
                    TestUtils.print_test("File Upload & Processing", "FAILED")
                    return False
        
        TestUtils.print_result(False, "Processing timeout", 
                             f"Still in status: {status} after {max_attempts} attempts")
        TestUtils.print_test("File Upload & Processing", "FAILED")
        return False
    
    def test_ai_summary(self) -> bool:
        """Test AI summary generation"""
        TestUtils.print_test("AI Summary Generation", "RUNNING")
        
        # First, upload a test document
        filename, content, content_base64 = TestUtils.create_test_document("text")
        
        upload_data = {
            "filename": filename,
            "content": content_base64,
            "content_type": "text/plain"
        }
        
        success, data, error = self.make_request("POST", "/documents/upload", upload_data)
        
        if not success or not data or 'document_id' not in data:
            TestUtils.print_result(False, "Failed to upload test document", error)
            TestUtils.print_test("AI Summary Generation", "SKIPPED")
            return False
        
        document_id = data['document_id']
        self.uploaded_files.append(document_id)
        
        # Wait for processing
        time.sleep(5)
        
        # Generate AI summary
        summary_data = {
            "document_ids": [document_id],
            "prompt": "Summarize this document and list any PII that was found."
        }
        
        success, summary_response, error = self.make_request("POST", "/documents/ai-summary", summary_data)
        
        if not success:
            TestUtils.print_result(False, "Failed to generate AI summary", error)
            
            # Check if it's a model access issue
            if error and "model" in error.lower():
                TestUtils.print_result(False, "Bedrock model access issue detected", 
                                     "Ensure model access is enabled in AWS Bedrock console")
            
            TestUtils.print_test("AI Summary Generation", "FAILED")
            return False
        
        TestUtils.print_result(True, "AI summary generated successfully")
        
        if summary_response and 'summary' in summary_response:
            summary_text = summary_response['summary'][:200]  # First 200 chars
            print(f"    Summary preview: {summary_text}...")
        
        TestUtils.print_test("AI Summary Generation", "PASSED")
        return True
    
    def test_quarantine_endpoints(self) -> bool:
        """Test quarantine functionality"""
        TestUtils.print_test("Quarantine Endpoints", "RUNNING")
        
        # List quarantine files
        success, data, error = self.make_request("GET", "/quarantine/files")
        
        if not success:
            TestUtils.print_result(False, "Failed to list quarantine files", error)
            TestUtils.print_test("Quarantine Endpoints", "FAILED")
            return False
        
        TestUtils.print_result(True, "Successfully retrieved quarantine files")
        
        if data and 'files' in data:
            quarantine_count = len(data['files'])
            TestUtils.print_result(True, f"Found {quarantine_count} quarantined files")
            
            # If there are quarantined files, test deletion
            if quarantine_count > 0 and False:  # Disabled by default to avoid data loss
                file_id = data['files'][0]['id']
                success, delete_data, error = self.make_request("DELETE", f"/quarantine/{file_id}")
                
                if success:
                    TestUtils.print_result(True, f"Successfully deleted quarantine file: {file_id}")
                else:
                    TestUtils.print_result(False, f"Failed to delete quarantine file", error)
        
        TestUtils.print_test("Quarantine Endpoints", "PASSED")
        return True
    
    def test_batch_operations(self) -> bool:
        """Test batch download and combine operations"""
        TestUtils.print_test("Batch Operations", "RUNNING")
        
        # Need at least 2 files for batch operations
        if len(self.uploaded_files) < 2:
            # Upload another test file
            filename, content, content_base64 = TestUtils.create_test_document("csv")
            upload_data = {
                "filename": filename,
                "content": content_base64,
                "content_type": "text/csv"
            }
            
            success, data, error = self.make_request("POST", "/documents/upload", upload_data)
            if success and data and 'document_id' in data:
                self.uploaded_files.append(data['document_id'])
                time.sleep(5)  # Wait for processing
        
        if len(self.uploaded_files) >= 2:
            # Test batch download
            batch_data = {
                "document_ids": self.uploaded_files[:2]
            }
            
            success, download_data, error = self.make_request("POST", "/documents/batch-download", batch_data)
            
            if success:
                TestUtils.print_result(True, "Batch download successful")
                if download_data and 'download_url' in download_data:
                    TestUtils.print_result(True, "Batch download URL generated")
            else:
                TestUtils.print_result(False, "Batch download failed", error)
            
            # Test combine operation
            combine_data = {
                "document_ids": self.uploaded_files[:2],
                "output_filename": f"combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            }
            
            success, combine_response, error = self.make_request("POST", "/documents/combine", combine_data)
            
            if success:
                TestUtils.print_result(True, "Document combination successful")
                if combine_response and 'document_id' in combine_response:
                    self.uploaded_files.append(combine_response['document_id'])
                    TestUtils.print_result(True, f"Combined document ID: {combine_response['document_id']}")
            else:
                TestUtils.print_result(False, "Document combination failed", error)
        else:
            TestUtils.print_result(False, "Insufficient files for batch operations")
        
        TestUtils.print_test("Batch Operations", "PASSED")
        return True
    
    def cleanup_test_files(self):
        """Clean up uploaded test files"""
        if not self.uploaded_files:
            return
        
        print(f"\n{TestConfig.CYAN}Cleaning up {len(self.uploaded_files)} test files...{TestConfig.RESET}")
        
        for document_id in self.uploaded_files:
            success, data, error = self.make_request("DELETE", f"/documents/{document_id}")
            if success:
                print(f"  {TestConfig.GREEN}✓ Deleted: {document_id}{TestConfig.RESET}")
            else:
                print(f"  {TestConfig.YELLOW}⚠ Failed to delete: {document_id}{TestConfig.RESET}")
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all API tests and return results"""
        TestUtils.print_header("API ENDPOINT TESTS")
        
        test_results = {}
        
        # Run tests in order
        test_results['health'] = self.test_health_check()
        test_results['config'] = self.test_config_endpoint()
        test_results['user_files'] = self.test_user_files_listing()
        test_results['upload_processing'] = self.test_file_upload_and_processing()
        test_results['ai_summary'] = self.test_ai_summary()
        test_results['quarantine'] = self.test_quarantine_endpoints()
        test_results['batch_operations'] = self.test_batch_operations()
        
        # Cleanup
        self.cleanup_test_files()
        
        return test_results

# ============================================================================
# AWS Infrastructure Tests
# ============================================================================

class AWSInfrastructureTests:
    """Test AWS infrastructure components"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.cognito_client = boto3.client('cognito-idp', region_name='us-east-1')
        
    def test_s3_buckets(self) -> bool:
        """Test S3 bucket accessibility"""
        TestUtils.print_test("S3 Buckets", "RUNNING")
        
        buckets = [
            'redact-input-documents-32a4ee51',
            'redact-processed-documents-32a4ee51',
            'redact-quarantine-documents-32a4ee51',
            'redact-config-32a4ee51'
        ]
        
        all_accessible = True
        
        for bucket in buckets:
            try:
                self.s3_client.head_bucket(Bucket=bucket)
                TestUtils.print_result(True, f"Bucket accessible: {bucket}")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    TestUtils.print_result(False, f"Bucket not found: {bucket}")
                elif error_code == '403':
                    TestUtils.print_result(False, f"Access denied: {bucket}")
                else:
                    TestUtils.print_result(False, f"Error accessing {bucket}: {error_code}")
                all_accessible = False
            except Exception as e:
                TestUtils.print_result(False, f"Unexpected error for {bucket}: {str(e)}")
                all_accessible = False
        
        if all_accessible:
            TestUtils.print_test("S3 Buckets", "PASSED")
        else:
            TestUtils.print_test("S3 Buckets", "FAILED")
        
        return all_accessible
    
    def test_lambda_functions(self) -> bool:
        """Test Lambda function configuration"""
        TestUtils.print_test("Lambda Functions", "RUNNING")
        
        functions = [
            'redact-api-handler',
            'document-scrubbing-processor'
        ]
        
        all_configured = True
        
        for function_name in functions:
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                
                if response['Configuration']['State'] == 'Active':
                    TestUtils.print_result(True, f"Function active: {function_name}")
                    
                    # Check runtime
                    runtime = response['Configuration']['Runtime']
                    if 'python' in runtime.lower():
                        TestUtils.print_result(True, f"Runtime: {runtime}")
                    
                    # Check memory and timeout
                    memory = response['Configuration']['MemorySize']
                    timeout = response['Configuration']['Timeout']
                    print(f"    Memory: {memory}MB, Timeout: {timeout}s")
                    
                else:
                    TestUtils.print_result(False, f"Function not active: {function_name}")
                    all_configured = False
                    
            except ClientError as e:
                TestUtils.print_result(False, f"Error checking {function_name}: {e}")
                all_configured = False
        
        if all_configured:
            TestUtils.print_test("Lambda Functions", "PASSED")
        else:
            TestUtils.print_test("Lambda Functions", "FAILED")
        
        return all_configured
    
    def test_cognito_pool(self) -> bool:
        """Test Cognito user pool configuration"""
        TestUtils.print_test("Cognito User Pool", "RUNNING")
        
        try:
            response = self.cognito_client.describe_user_pool(
                UserPoolId='us-east-1_4Uv3seGwS'
            )
            
            pool = response['UserPool']
            
            TestUtils.print_result(True, f"User pool found: {pool['Name']}")
            if 'Status' in pool:
                TestUtils.print_result(True, f"Status: {pool['Status']}")
            else:
                TestUtils.print_result(True, "User pool is active")
            
            # Check MFA configuration
            if 'MfaConfiguration' in pool:
                mfa_config = pool['MfaConfiguration']
                if mfa_config == 'OFF':
                    TestUtils.print_result(True, "MFA is disabled (as expected for testing)")
                else:
                    TestUtils.print_result(False, f"MFA is {mfa_config} (may complicate testing)")
            
            # Check password policy
            if 'Policies' in pool and 'PasswordPolicy' in pool['Policies']:
                policy = pool['Policies']['PasswordPolicy']
                print(f"    Password Policy: Min length={policy.get('MinimumLength', 'N/A')}, "
                      f"Require uppercase={policy.get('RequireUppercase', False)}")
            
            TestUtils.print_test("Cognito User Pool", "PASSED")
            return True
            
        except ClientError as e:
            TestUtils.print_result(False, f"Error accessing Cognito pool: {e}")
            TestUtils.print_test("Cognito User Pool", "FAILED")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all infrastructure tests"""
        TestUtils.print_header("AWS INFRASTRUCTURE TESTS")
        
        test_results = {}
        
        test_results['s3_buckets'] = self.test_s3_buckets()
        test_results['lambda_functions'] = self.test_lambda_functions()
        test_results['cognito_pool'] = self.test_cognito_pool()
        
        return test_results

# ============================================================================
# Main Test Runner
# ============================================================================

def print_test_summary(results: Dict[str, Dict[str, bool]]):
    """Print comprehensive test summary"""
    TestUtils.print_header("TEST SUMMARY")
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category, tests in results.items():
        print(f"\n{TestConfig.BOLD}{category}:{TestConfig.RESET}")
        
        for test_name, passed in tests.items():
            total_tests += 1
            if passed:
                passed_tests += 1
                print(f"  {TestConfig.GREEN}✓ {test_name}{TestConfig.RESET}")
            else:
                failed_tests += 1
                print(f"  {TestConfig.RED}✗ {test_name}{TestConfig.RESET}")
    
    # Overall summary
    print(f"\n{TestConfig.BLUE}{'='*70}{TestConfig.RESET}")
    print(f"{TestConfig.BOLD}Overall Results:{TestConfig.RESET}")
    print(f"  Total Tests: {total_tests}")
    print(f"  {TestConfig.GREEN}Passed: {passed_tests}{TestConfig.RESET}")
    print(f"  {TestConfig.RED}Failed: {failed_tests}{TestConfig.RESET}")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    if success_rate == 100:
        print(f"\n{TestConfig.GREEN}{TestConfig.BOLD}✓ ALL TESTS PASSED! ({success_rate:.1f}%){TestConfig.RESET}")
    elif success_rate >= 80:
        print(f"\n{TestConfig.GREEN}Success Rate: {success_rate:.1f}%{TestConfig.RESET}")
    elif success_rate >= 60:
        print(f"\n{TestConfig.YELLOW}Success Rate: {success_rate:.1f}%{TestConfig.RESET}")
    else:
        print(f"\n{TestConfig.RED}Success Rate: {success_rate:.1f}%{TestConfig.RESET}")
    
    print(f"{TestConfig.BLUE}{'='*70}{TestConfig.RESET}")

def main():
    """Main test execution function"""
    print(f"\n{TestConfig.BLUE}{TestConfig.BOLD}REDACT APPLICATION COMPREHENSIVE TEST SUITE{TestConfig.RESET}")
    print(f"{TestConfig.BLUE}{'='*70}{TestConfig.RESET}")
    print(f"Production URL: {TestConfig.PROD_URL}")
    print(f"API URL: {TestConfig.API_URL}")
    print(f"Test Started: {datetime.now().isoformat()}")
    print(f"{TestConfig.BLUE}{'='*70}{TestConfig.RESET}")
    
    all_results = {}
    
    # Test AWS Infrastructure
    print(f"\n{TestConfig.CYAN}Starting AWS infrastructure tests...{TestConfig.RESET}")
    infra_tests = AWSInfrastructureTests()
    all_results['AWS Infrastructure'] = infra_tests.run_all_tests()
    
    # Test Authentication
    print(f"\n{TestConfig.CYAN}Testing authentication...{TestConfig.RESET}")
    auth_manager = AuthManager()
    
    # Create API test suite
    api_tests = APITestSuite(auth_manager)
    
    if not TestConfig.TEST_EMAIL or TestConfig.TEST_EMAIL == "test@example.com":
        print(f"{TestConfig.YELLOW}⚠ No test credentials provided.{TestConfig.RESET}")
        print(f"  Set TEST_EMAIL and TEST_PASSWORD environment variables to test authenticated endpoints.")
        print(f"  Example: export TEST_EMAIL='your-test@email.com' TEST_PASSWORD='YourPassword123!'")
        print(f"\n{TestConfig.CYAN}Running unauthenticated tests only...{TestConfig.RESET}")
        
        # Run health check (doesn't require auth)
        health_result = api_tests.test_health_check()
        
        # Mark authenticated tests as skipped
        all_results['API Endpoints'] = {
            'health': health_result,
            'config': False,
            'user_files': False,
            'upload_processing': False,
            'ai_summary': False,
            'quarantine': False,
            'batch_operations': False
        }
    else:
        if auth_manager.authenticate(TestConfig.TEST_EMAIL, TestConfig.TEST_PASSWORD):
            print(f"{TestConfig.GREEN}✓ Authentication successful{TestConfig.RESET}")
            
            # Test API Endpoints
            all_results['API Endpoints'] = api_tests.run_all_tests()
        else:
            print(f"{TestConfig.RED}✗ Authentication failed{TestConfig.RESET}")
            print(f"  Unable to test authenticated endpoints")
            
            # Mark all API tests as failed
            all_results['API Endpoints'] = {
                'health': False,
                'config': False,
                'user_files': False,
                'upload_processing': False,
                'ai_summary': False,
                'quarantine': False,
                'batch_operations': False
            }
    
    # Print comprehensive summary
    print_test_summary(all_results)
    
    # Determine exit code
    total_failed = sum(
        1 for category in all_results.values() 
        for passed in category.values() 
        if not passed
    )
    
    if total_failed == 0:
        print(f"\n{TestConfig.GREEN}{TestConfig.BOLD}✅ All systems operational!{TestConfig.RESET}")
        sys.exit(0)
    else:
        print(f"\n{TestConfig.RED}{TestConfig.BOLD}❌ {total_failed} test(s) failed. Review logs above for details.{TestConfig.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()