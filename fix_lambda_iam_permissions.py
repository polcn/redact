#!/usr/bin/env python3
"""
Fix Lambda IAM permissions to use correct bucket suffixes
"""

import boto3
import json
import sys

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def update_lambda_iam_policy():
    """Update the Lambda IAM policy with correct bucket suffixes"""
    
    iam = boto3.client('iam')
    role_name = 'document-scrubbing-lambda-role'
    policy_name = 'document-scrubbing-lambda-policy'
    
    print(f"\n{BLUE}Fixing Lambda IAM Permissions{RESET}")
    print(f"Role: {role_name}")
    print(f"Policy: {policy_name}")
    
    # Correct policy with proper bucket suffix
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": [
                    "arn:aws:logs:us-east-1:028358929215:log-group:/aws/lambda/document-scrubbing-processor:*",
                    "arn:aws:logs:us-east-1:028358929215:log-group:/aws/lambda/redact-api-handler:*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:HeadObject",
                    "s3:CopyObject"
                ],
                "Resource": [
                    "arn:aws:s3:::redact-input-documents-32a4ee51/*",
                    "arn:aws:s3:::redact-processed-documents-32a4ee51/*",
                    "arn:aws:s3:::redact-quarantine-documents-32a4ee51/*",
                    "arn:aws:s3:::redact-config-32a4ee51/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                    "s3:HeadBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::redact-input-documents-32a4ee51",
                    "arn:aws:s3:::redact-processed-documents-32a4ee51",
                    "arn:aws:s3:::redact-quarantine-documents-32a4ee51",
                    "arn:aws:s3:::redact-config-32a4ee51"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "textract:DetectDocumentText",
                    "textract:AnalyzeDocument"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "rekognition:DetectText",
                    "rekognition:DetectLabels"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:SendMessage",
                    "sqs:GetQueueAttributes"
                ],
                "Resource": "arn:aws:sqs:us-east-1:028358929215:document-scrubbing-dlq"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath"
                ],
                "Resource": [
                    "arn:aws:ssm:us-east-1:028358929215:parameter/redact/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "kms:Decrypt"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "kms:ViaService": "ssm.us-east-1.amazonaws.com"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": [
                    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-instant-v1",
                    "arn:aws:bedrock:us-east-1::foundation-model/*"
                ]
            }
        ]
    }
    
    try:
        # Update the inline policy
        response = iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"{GREEN}✓ IAM policy updated successfully{RESET}")
        print(f"\nChanges made:")
        print(f"  - Fixed S3 bucket suffix from 469be391 to 32a4ee51")
        print(f"  - Updated Bedrock model ARNs to include version suffixes")
        print(f"  - Added wildcard for all Bedrock models")
        
        # Also update the API handler role
        api_role_name = 'redact-api-lambda-role'
        api_policy_name = 'redact-api-lambda-policy'
        
        print(f"\n{BLUE}Updating API Handler IAM Policy{RESET}")
        print(f"Role: {api_role_name}")
        
        # Get current policy
        try:
            current_policy = iam.get_role_policy(
                RoleName=api_role_name,
                PolicyName=api_policy_name
            )
            
            # Update bucket suffixes in the policy
            api_policy = current_policy['PolicyDocument']
            api_policy_str = json.dumps(api_policy)
            api_policy_str = api_policy_str.replace('469be391', '32a4ee51')
            api_policy = json.loads(api_policy_str)
            
            # Update the policy
            iam.put_role_policy(
                RoleName=api_role_name,
                PolicyName=api_policy_name,
                PolicyDocument=json.dumps(api_policy)
            )
            
            print(f"{GREEN}✓ API handler IAM policy updated successfully{RESET}")
            
        except Exception as e:
            print(f"{YELLOW}Could not update API handler policy: {e}{RESET}")
        
        print(f"\n{GREEN}IAM permissions fixed successfully!{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print(f"  1. Wait 1-2 minutes for IAM changes to propagate")
        print(f"  2. Run the test suite again: python3 test_redact_application.py")
        
        return True
        
    except Exception as e:
        print(f"{RED}Error updating IAM policy: {str(e)}{RESET}")
        return False

if __name__ == "__main__":
    success = update_lambda_iam_policy()
    sys.exit(0 if success else 1)