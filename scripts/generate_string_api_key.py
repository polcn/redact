#!/usr/bin/env python3
"""
Generate and store API key for String.com integration
"""

import json
import secrets
import boto3
import sys
from datetime import datetime

def generate_api_key(environment='prod'):
    """Generate and store API key in Parameter Store"""
    
    # Generate secure API key
    api_key = f"sk_{'test' if environment != 'prod' else 'live'}_{secrets.token_urlsafe(32)}"
    
    # Initialize SSM client
    ssm = boto3.client('ssm')
    
    # Parameter name
    parameter_name = f"/redact/api-keys/string-{environment}"
    
    # API key configuration
    api_config = {
        "key": api_key,
        "user_id": f"string-integration-{environment}",
        "name": f"String.com Integration ({environment.upper()})",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "permissions": ["api:string:redact"],
        "rate_limit": 1000,
        "config_override": {
            "conditional_rules": [
                {
                    "name": "Choice Hotels",
                    "enabled": True,
                    "trigger": {
                        "contains": ["Choice Hotels", "Choice"],
                        "case_sensitive": False
                    },
                    "replacements": [
                        {"find": "Choice Hotels", "replace": "CH"},
                        {"find": "Choice", "replace": "CH"}
                    ]
                },
                {
                    "name": "Cronos",
                    "enabled": True,
                    "trigger": {
                        "contains": ["Cronos"],
                        "case_sensitive": False
                    },
                    "replacements": [
                        {"find": "Cronos", "replace": "CR"}
                    ]
                }
            ]
        }
    }
    
    try:
        # First try to create the parameter
        try:
            response = ssm.put_parameter(
                Name=parameter_name,
                Value=json.dumps(api_config, indent=2),
                Type='SecureString',
                Description=f'API key for String.com integration ({environment})',
                Tags=[
                    {'Key': 'Project', 'Value': 'redact'},
                    {'Key': 'Service', 'Value': 'string-integration'},
                    {'Key': 'Environment', 'Value': environment}
                ]
            )
        except ssm.exceptions.ParameterAlreadyExists:
            # If it exists, update without tags
            response = ssm.put_parameter(
                Name=parameter_name,
                Value=json.dumps(api_config, indent=2),
                Type='SecureString',
                Description=f'API key for String.com integration ({environment})',
                Overwrite=True
            )
        
        print(f"✅ API key generated and stored successfully!")
        print(f"\nParameter: {parameter_name}")
        print(f"API Key: {api_key}")
        print(f"\nShare this API key with String.com:")
        print(f"Authorization: Bearer {api_key}")
        
        # Also create user-specific config in S3
        s3 = boto3.client('s3')
        
        # Get bucket name from terraform output or environment
        try:
            # Try to get from terraform output
            import subprocess
            result = subprocess.run(['terraform', 'output', '-json', 'config_bucket_name'], 
                                  capture_output=True, text=True, cwd='/home/ec2-user/redact-terraform')
            if result.returncode == 0:
                config_bucket = json.loads(result.stdout).strip('"')
            else:
                # Fallback to environment variable
                config_bucket = os.environ.get('CONFIG_BUCKET', 'redact-config-32a4ee51')
        except:
            config_bucket = 'redact-config-32a4ee51'  # hardcoded fallback
        
        # Store default config for String.com user
        config_key = f"configs/users/{api_config['user_id']}/config.json"
        s3.put_object(
            Bucket=config_bucket,
            Key=config_key,
            Body=json.dumps({
                "version": "2.0",
                "replacements": [],
                "case_sensitive": False,
                "patterns": {
                    "ssn": False,
                    "credit_card": False,
                    "phone": False,
                    "email": False,
                    "ip_address": False,
                    "drivers_license": False
                },
                "conditional_rules": api_config['config_override']['conditional_rules']
            }, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        print(f"\n✅ Default configuration stored in S3")
        print(f"Config location: s3://{config_bucket}/{config_key}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import os
    environment = os.environ.get('ENVIRONMENT', 'prod')
    
    if len(sys.argv) > 1:
        environment = sys.argv[1]
    
    print(f"Generating API key for environment: {environment}")
    generate_api_key(environment)