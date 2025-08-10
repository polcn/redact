#!/usr/bin/env python3
"""Quick test for file upload and processing"""

import os
import sys
sys.path.insert(0, '.')

from test_redact_application import *

# Get credentials from environment
email = os.environ.get('TEST_EMAIL')
password = os.environ.get('TEST_PASSWORD')

if not email or not password:
    print("Please set TEST_EMAIL and TEST_PASSWORD environment variables")
    sys.exit(1)

# Authenticate
auth = AuthManager()
if not auth.authenticate(email, password):
    print("Authentication failed")
    sys.exit(1)

print("Authentication successful")

# Create API test suite
api_tests = APITestSuite(auth)

# Test file upload and processing
print("\n" + "="*50)
print("Testing File Upload and Processing")
print("="*50)

result = api_tests.test_file_upload_and_processing()

# Cleanup
api_tests.cleanup_test_files()

# Print result
print("\n" + "="*50)
if result:
    print(f"{TestConfig.GREEN}✅ FILE PROCESSING TEST PASSED!{TestConfig.RESET}")
    sys.exit(0)
else:
    print(f"{TestConfig.RED}❌ FILE PROCESSING TEST FAILED{TestConfig.RESET}")
    sys.exit(1)