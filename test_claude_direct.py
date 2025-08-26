#!/usr/bin/env python3

"""
Direct test of Claude SDK integration by invoking the generate_ai_summary_internal function
"""

import boto3
import json
import os

def test_claude_function():
    """Test the Claude function directly"""
    print("🧪 Testing Claude SDK integration directly...")
    
    lambda_client = boto3.client('lambda')
    
    # Test code that calls the internal function directly
    test_code = '''
import json

def lambda_handler(event, context):
    try:
        # Import the function we want to test
        from api_handler_simple import generate_ai_summary_internal
        
        # Test parameters
        test_text = "This is a test document for Claude SDK integration testing. It contains sample content to verify the AI summary generation works correctly."
        summary_type = "brief"
        user_role = "user"
        
        # Call the function
        summary, metadata = generate_ai_summary_internal(test_text, summary_type, user_role)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'summary': summary,
                'metadata': metadata,
                'test': 'claude_sdk_integration'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'test': 'claude_sdk_integration'
            })
        }
'''
    
    try:
        # Test via the existing test function
        response = lambda_client.invoke(
            FunctionName='redact-api-handler-claude-test',
            Payload=json.dumps({
                'test_code': test_code,
                'test_type': 'direct_claude_test'
            })
        )
        
        result = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            print("✅ Function invocation successful")
            
            if result.get('statusCode') == 200:
                body = json.loads(result['body'])
                if body.get('success'):
                    print("🎉 Claude SDK integration working!")
                    print(f"📝 Summary: {body['summary'][:100]}...")
                    print(f"🏷️  Model: {body['metadata']['model']}")
                    return True
                else:
                    print(f"❌ Function test failed: {body.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"⚠️  Function returned status {result.get('statusCode')}")
                print(f"Error: {result.get('body', 'Unknown error')}")
                return False
        else:
            print(f"❌ Lambda invocation failed: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Claude function: {e}")
        return False

def check_logs():
    """Check the CloudWatch logs for the test function"""
    print("📋 Checking CloudWatch logs...")
    
    logs_client = boto3.client('logs')
    
    try:
        # Get recent log events
        response = logs_client.describe_log_streams(
            logGroupName='/aws/lambda/redact-api-handler-claude-test',
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if response['logStreams']:
            latest_stream = response['logStreams'][0]
            
            events = logs_client.get_log_events(
                logGroupName='/aws/lambda/redact-api-handler-claude-test',
                logStreamName=latest_stream['logStreamName'],
                limit=20
            )
            
            print("Recent log events:")
            for event in events['events'][-5:]:  # Show last 5 events
                print(f"  {event['message'].strip()}")
                
    except Exception as e:
        print(f"⚠️  Could not retrieve logs: {e}")

def main():
    """Main test function"""
    print("🧪 Direct Claude SDK Integration Test")
    print("=" * 50)
    
    success = test_claude_function()
    
    print("\n" + "=" * 50)
    check_logs()
    
    if success:
        print("\n✅ Claude SDK integration test passed!")
        return 0
    else:
        print("\n❌ Claude SDK integration test failed!")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())