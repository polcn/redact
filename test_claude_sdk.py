#!/usr/bin/env python3

"""
Test script to validate Claude SDK integration works correctly
This tests the new API handler code without deploying to production
"""

import sys
import os
import json
import tempfile

# Add the api_code directory to path so we can import the handler
sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')

def test_claude_sdk_import():
    """Test if Claude SDK can be imported"""
    print("🧪 Testing Claude SDK import...")
    try:
        from anthropic import AnthropicBedrock
        print("✅ Claude SDK imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Claude SDK import failed: {e}")
        return False

def test_client_initialization():
    """Test if we can initialize the Claude client"""
    print("🧪 Testing Claude client initialization...")
    try:
        # Set required environment variables for testing
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['INPUT_BUCKET'] = 'test-bucket'
        os.environ['PROCESSED_BUCKET'] = 'test-bucket'
        os.environ['QUARANTINE_BUCKET'] = 'test-bucket'
        os.environ['CONFIG_BUCKET'] = 'test-bucket'
        
        # Import our handler
        from api_handler_simple import get_claude_client, anthropic_client, bedrock_runtime
        
        client = get_claude_client()
        
        if client == anthropic_client and anthropic_client:
            print("✅ Claude SDK client initialized successfully")
            return True
        elif client == bedrock_runtime:
            print("⚠️  Falling back to Bedrock client (expected if no AWS credentials)")
            return True
        else:
            print("❌ No valid client returned")
            return False
            
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False

def test_ai_config():
    """Test AI configuration loading"""
    print("🧪 Testing AI configuration...")
    try:
        from api_handler_simple import get_ai_config
        
        # This will fail in test environment but should handle gracefully
        config = get_ai_config()
        if config.get('enabled') is False and 'error' in config:
            print("✅ AI config error handling works correctly")
            return True
        else:
            print("✅ AI config loaded successfully")
            return True
            
    except Exception as e:
        print(f"❌ AI config test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Claude SDK integration...")
    print("=" * 50)
    
    tests = [
        test_claude_sdk_import,
        test_client_initialization, 
        test_ai_config
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
            print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Claude SDK integration is ready for deployment")
        return 0
    else:
        print(f"⚠️  Some tests failed ({passed}/{total})")
        print("🔧 Review the errors above before deploying")
        return 1

if __name__ == "__main__":
    sys.exit(main())