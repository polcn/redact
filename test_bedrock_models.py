#!/usr/bin/env python3
"""
Test script to verify AWS Bedrock model IDs are working correctly
"""

import boto3
import json
import sys
from botocore.exceptions import ClientError

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_model(bedrock_client, model_id):
    """Test a specific Bedrock model"""
    print(f"\n{BLUE}Testing model: {model_id}{RESET}")
    
    try:
        # Prepare test prompt based on model type
        if "claude-3" in model_id or "claude-3.5" in model_id:
            # Use Messages API for Claude 3/3.5 models
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "temperature": 0.5,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, please respond with 'Model working' if you receive this message."
                    }
                ]
            }
        elif "claude" in model_id:
            # Use legacy format for older Claude models
            request_body = {
                "prompt": "\n\nHuman: Hello, please respond with 'Model working' if you receive this message.\n\nAssistant:",
                "max_tokens_to_sample": 100,
                "temperature": 0.5,
                "top_p": 0.9,
                "stop_sequences": ["\n\nHuman:"]
            }
        else:
            print(f"{YELLOW}⚠ Unsupported model type: {model_id}{RESET}")
            return False
        
        # Invoke the model
        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract the response text based on model type
        if "claude-3" in model_id or "claude-3.5" in model_id:
            content = response_body.get('content', [])
            if content and isinstance(content, list) and len(content) > 0:
                response_text = content[0].get('text', '').strip()
            else:
                response_text = 'No response'
        elif "claude" in model_id:
            response_text = response_body.get('completion', '').strip()
        else:
            response_text = response_body.get('text', '').strip()
        
        print(f"{GREEN}✓ Model {model_id} responded successfully{RESET}")
        print(f"  Response: {response_text[:100]}...")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'ValidationException':
            print(f"{RED}✗ Invalid model ID: {model_id}{RESET}")
            print(f"  Error: {error_message}")
        elif error_code == 'AccessDeniedException':
            print(f"{RED}✗ Access denied to model: {model_id}{RESET}")
            print(f"  Error: {error_message}")
            print(f"{YELLOW}  Note: You may need to request access to this model in the AWS Console{RESET}")
        else:
            print(f"{RED}✗ Error testing model: {model_id}{RESET}")
            print(f"  Error Code: {error_code}")
            print(f"  Error Message: {error_message}")
        return False
        
    except Exception as e:
        print(f"{RED}✗ Unexpected error testing model: {model_id}{RESET}")
        print(f"  Error: {str(e)}")
        return False

def main():
    """Main test function"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}AWS Bedrock Model ID Testing{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # Initialize Bedrock client
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        print(f"{GREEN}✓ Bedrock client initialized successfully{RESET}")
    except Exception as e:
        print(f"{RED}✗ Failed to initialize Bedrock client{RESET}")
        print(f"  Error: {str(e)}")
        sys.exit(1)
    
    # Models to test (corrected IDs)
    models_to_test = [
        "anthropic.claude-3-haiku-20240307-v1:0",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "anthropic.claude-instant-v1"
    ]
    
    # Test each model
    results = {}
    for model_id in models_to_test:
        results[model_id] = test_model(bedrock, model_id)
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test Summary:{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    working_models = []
    failed_models = []
    
    for model_id, success in results.items():
        if success:
            working_models.append(model_id)
            print(f"{GREEN}✓ {model_id}{RESET}")
        else:
            failed_models.append(model_id)
            print(f"{RED}✗ {model_id}{RESET}")
    
    print(f"\n{BLUE}Results:{RESET}")
    print(f"  Working models: {len(working_models)}/{len(models_to_test)}")
    print(f"  Failed models: {len(failed_models)}/{len(models_to_test)}")
    
    if failed_models:
        print(f"\n{YELLOW}⚠ Some models failed. Common causes:{RESET}")
        print("  1. Model access not enabled in AWS Bedrock console")
        print("  2. IAM permissions missing for specific models")
        print("  3. Model not available in your region")
        print("\nTo enable model access:")
        print("  1. Go to AWS Bedrock Console")
        print("  2. Navigate to 'Model access'")
        print("  3. Request access to the failed models")
        print("  4. Wait for approval (usually instant for Claude models)")
    
    # Return exit code based on results
    if len(working_models) > 0:
        print(f"\n{GREEN}At least one model is working. The application should function.{RESET}")
        sys.exit(0)
    else:
        print(f"\n{RED}No models are working. The AI summary feature will fail.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()