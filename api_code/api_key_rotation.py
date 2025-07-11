import json
import boto3
import os
import secrets
import string
from datetime import datetime, timedelta
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ssm = boto3.client('ssm')
apigateway = boto3.client('apigateway')

# Configuration
API_KEY_PARAMETER = '/redact/api-keys/string-prod'
OLD_API_KEY_PARAMETER = '/redact/api-keys/string-prod-old'
API_GATEWAY_KEY_PARAMETER = '/redact/api-keys/string-api-gateway-key'
ROTATION_NOTIFICATION_PARAMETER = '/redact/api-keys/last-rotation'
GRACE_PERIOD_DAYS = 7  # Keep old key active for 7 days

def generate_api_key(prefix='sk_live_', length=48):
    """Generate a secure API key similar to String.com format"""
    characters = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(characters) for _ in range(length))
    return f"{prefix}{random_part}"

def lambda_handler(event, context):
    """
    Rotate API keys for String.com integration
    This function:
    1. Generates a new API key
    2. Stores the current key as old key (for grace period)
    3. Updates the current key parameter
    4. Updates the API Gateway key if needed
    5. Records rotation timestamp
    """
    try:
        logger.info("Starting API key rotation")
        
        # Get current API key
        try:
            current_key_response = ssm.get_parameter(
                Name=API_KEY_PARAMETER,
                WithDecryption=True
            )
            current_key = current_key_response['Parameter']['Value']
            logger.info("Retrieved current API key")
        except ssm.exceptions.ParameterNotFound:
            logger.warning("No current API key found, this might be first rotation")
            current_key = None
        
        # Generate new API key
        new_api_key = generate_api_key()
        logger.info("Generated new API key")
        
        # Store current key as old key (for grace period)
        if current_key:
            ssm.put_parameter(
                Name=OLD_API_KEY_PARAMETER,
                Value=current_key,
                Type='SecureString',
                Overwrite=True,
                Description=f'Previous String.com API key (rotated on {datetime.utcnow().isoformat()})'
            )
            logger.info("Stored current key as old key for grace period")
        
        # Update current API key
        ssm.put_parameter(
            Name=API_KEY_PARAMETER,
            Value=new_api_key,
            Type='SecureString',
            Overwrite=True,
            Description='String.com API key for redaction service'
        )
        logger.info("Updated current API key parameter")
        
        # Update API Gateway key if configured
        try:
            # Get the API Gateway key ID from tags or environment
            api_key_id = os.environ.get('API_GATEWAY_KEY_ID')
            if api_key_id:
                # Generate new API Gateway key
                new_gateway_key = generate_api_key(prefix='', length=32)
                
                # Update API Gateway key
                apigateway.update_api_key(
                    apiKey=api_key_id,
                    patchOperations=[
                        {
                            'op': 'replace',
                            'path': '/value',
                            'value': new_gateway_key
                        }
                    ]
                )
                
                # Store new API Gateway key in Parameter Store
                ssm.put_parameter(
                    Name=API_GATEWAY_KEY_PARAMETER,
                    Value=new_gateway_key,
                    Type='SecureString',
                    Overwrite=True,
                    Description='API Gateway API key for String.com rate limiting'
                )
                logger.info("Updated API Gateway key")
        except Exception as e:
            logger.warning(f"Could not update API Gateway key: {str(e)}")
        
        # Record rotation timestamp
        rotation_info = {
            'last_rotation': datetime.utcnow().isoformat(),
            'next_rotation': (datetime.utcnow() + timedelta(days=30)).isoformat(),
            'grace_period_ends': (datetime.utcnow() + timedelta(days=GRACE_PERIOD_DAYS)).isoformat()
        }
        
        ssm.put_parameter(
            Name=ROTATION_NOTIFICATION_PARAMETER,
            Value=json.dumps(rotation_info),
            Type='String',
            Overwrite=True,
            Description='API key rotation tracking information'
        )
        
        logger.info(f"API key rotation completed successfully. Grace period ends: {rotation_info['grace_period_ends']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'API key rotation completed successfully',
                'rotation_info': rotation_info
            })
        }
        
    except Exception as e:
        logger.error(f"Error during API key rotation: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'API key rotation failed',
                'message': str(e)
            })
        }

def cleanup_old_keys(event, context):
    """
    Clean up old API keys after grace period expires
    This should be run separately, e.g., 7 days after rotation
    """
    try:
        # Check if grace period has expired
        rotation_info_response = ssm.get_parameter(Name=ROTATION_NOTIFICATION_PARAMETER)
        rotation_info = json.loads(rotation_info_response['Parameter']['Value'])
        
        grace_period_ends = datetime.fromisoformat(rotation_info['grace_period_ends'].replace('Z', '+00:00'))
        
        if datetime.utcnow() >= grace_period_ends:
            # Delete old key parameter
            try:
                ssm.delete_parameter(Name=OLD_API_KEY_PARAMETER)
                logger.info("Deleted old API key after grace period")
            except ssm.exceptions.ParameterNotFound:
                logger.info("No old API key to delete")
            
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Old API key cleaned up successfully'})
            }
        else:
            remaining_days = (grace_period_ends - datetime.utcnow()).days
            logger.info(f"Grace period still active. {remaining_days} days remaining")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Grace period still active. {remaining_days} days remaining'
                })
            }
            
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Cleanup failed',
                'message': str(e)
            })
        }