#!/usr/bin/env python3

"""
Safe deployment script for Claude SDK integration
Creates a test Lambda function to validate the changes before updating production
"""

import boto3
import json
import zipfile
import os
import time
import sys

def create_test_lambda():
    """Create a test Lambda function with the new Claude SDK code"""
    print("🧪 Creating test Lambda function...")
    
    lambda_client = boto3.client('lambda')
    iam_client = boto3.client('iam')
    
    # Get the production Lambda function configuration to copy settings
    try:
        prod_function = lambda_client.get_function(FunctionName='redact-api-handler')
        prod_config = prod_function['Configuration']
        
        test_function_name = 'redact-api-handler-claude-test'
        
        # Check if test function already exists
        try:
            existing = lambda_client.get_function(FunctionName=test_function_name)
            print(f"⚠️  Test function {test_function_name} already exists. Updating...")
            
            # Update the function code
            with open('api_lambda.zip', 'rb') as f:
                lambda_client.update_function_code(
                    FunctionName=test_function_name,
                    ZipFile=f.read()
                )
            
            print("✅ Test function updated successfully")
            return test_function_name
            
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new test function
            print(f"📦 Creating new test function: {test_function_name}")
            
            with open('api_lambda.zip', 'rb') as f:
                response = lambda_client.create_function(
                    FunctionName=test_function_name,
                    Runtime=prod_config['Runtime'],
                    Role=prod_config['Role'],
                    Handler=prod_config['Handler'],
                    Code={'ZipFile': f.read()},
                    Description='Test function for Claude SDK integration',
                    Timeout=prod_config['Timeout'],
                    MemorySize=prod_config['MemorySize'],
                    Environment=prod_config.get('Environment', {}),
                    Tags={
                        'Purpose': 'Claude-SDK-Testing',
                        'Environment': 'test'
                    }
                )
            
            print("✅ Test function created successfully")
            return test_function_name
            
    except Exception as e:
        print(f"❌ Error creating test function: {e}")
        return None

def test_claude_integration(function_name):
    """Test the Claude SDK integration in the test Lambda"""
    print("🧪 Testing Claude SDK integration...")
    
    lambda_client = boto3.client('lambda')
    
    # Test event that simulates an AI summary request
    test_event = {
        "httpMethod": "POST",
        "path": "/documents/ai-summary",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "document_id": "test-doc-123",
            "content": "This is a test document for Claude SDK integration testing. It contains some sample content to verify that the Claude SDK can properly generate summaries.",
            "summary_type": "brief"
        }),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "test-user-id",
                    "email": "test@example.com"
                }
            }
        }
    }
    
    try:
        # Invoke the test function
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            print("✅ Test function invocation successful")
            
            # Check if it returns a valid response
            if 'statusCode' in result:
                print(f"📊 Response status: {result['statusCode']}")
                
                if result['statusCode'] == 200:
                    print("✅ Claude SDK integration working correctly")
                    return True
                else:
                    print(f"⚠️  Function returned error: {result.get('body', 'Unknown error')}")
                    return False
            else:
                print("⚠️  Function returned unexpected format")
                print(f"Response: {result}")
                return False
        else:
            print(f"❌ Lambda invocation failed with status: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        return False

def cleanup_test_function(function_name):
    """Clean up the test Lambda function"""
    print("🧹 Cleaning up test function...")
    
    lambda_client = boto3.client('lambda')
    
    try:
        lambda_client.delete_function(FunctionName=function_name)
        print("✅ Test function deleted successfully")
    except Exception as e:
        print(f"⚠️  Error cleaning up test function: {e}")

def deploy_to_production():
    """Deploy the Claude SDK integration to production"""
    print("🚀 Deploying Claude SDK integration to production...")
    
    lambda_client = boto3.client('lambda')
    
    try:
        with open('api_lambda.zip', 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='redact-api-handler',
                ZipFile=f.read()
            )
        
        print("✅ Production Lambda updated successfully")
        
        # Wait for update to complete
        print("⏳ Waiting for function update to complete...")
        lambda_client.get_waiter('function_updated').wait(FunctionName='redact-api-handler')
        
        print("🎉 Claude SDK integration deployed to production!")
        return True
        
    except Exception as e:
        print(f"❌ Error deploying to production: {e}")
        return False

def main():
    """Main deployment workflow"""
    print("🚀 Claude SDK Integration Deployment")
    print("=" * 50)
    
    # Check if the build package exists
    if not os.path.exists('api_lambda.zip'):
        print("❌ api_lambda.zip not found. Run ./build_api_lambda.sh first")
        return 1
    
    # Create and test in a separate function first
    test_function_name = create_test_lambda()
    if not test_function_name:
        return 1
    
    # Test the integration
    test_success = test_claude_integration(test_function_name)
    
    if test_success:
        print("\n" + "=" * 50)
        response = input("✅ Tests passed! Deploy to production? (y/N): ")
        
        if response.lower() == 'y':
            success = deploy_to_production()
            if success:
                print("\n🎉 Claude SDK integration successfully deployed!")
                
                # Optionally clean up test function
                cleanup_response = input("🧹 Clean up test function? (Y/n): ")
                if cleanup_response.lower() != 'n':
                    cleanup_test_function(test_function_name)
                
                return 0
            else:
                print("\n❌ Production deployment failed!")
                return 1
        else:
            print("⏸️  Deployment cancelled. Test function preserved for debugging.")
            return 0
    else:
        print("\n❌ Tests failed! Not deploying to production.")
        print(f"🔧 Debug using test function: {test_function_name}")
        return 1

if __name__ == "__main__":
    sys.exit(main())