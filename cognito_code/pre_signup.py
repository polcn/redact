import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Pre-signup Lambda trigger for Cognito
    Controls user registration based on email domain or invitation
    """
    logger.info(f"Pre-signup trigger event: {json.dumps(event)}")
    
    # Get configuration from environment
    allowed_domains = os.environ.get('ALLOWED_DOMAINS', '').split(',')
    auto_confirm = os.environ.get('AUTO_CONFIRM', 'false').lower() == 'true'
    
    logger.info(f"AUTO_CONFIRM env var: {os.environ.get('AUTO_CONFIRM', 'not set')}")
    logger.info(f"auto_confirm flag: {auto_confirm}")
    
    try:
        # Extract user attributes
        user_attributes = event['request']['userAttributes']
        email = user_attributes.get('email', '')
        
        # Check if email domain is allowed
        email_domain = email.split('@')[-1].lower()
        
        if allowed_domains and email_domain not in [d.strip().lower() for d in allowed_domains]:
            # For now, reject users not from allowed domains
            # In the future, this could check an invitation table
            raise Exception(f"Registration not allowed for domain: {email_domain}")
        
        # Auto-confirm user if configured
        if auto_confirm:
            event['response']['autoConfirmUser'] = True
            event['response']['autoVerifyEmail'] = True
            event['response']['autoVerifyPhone'] = False
        
        # Don't modify userAttributes in response - this causes issues
        # The response should only contain autoConfirm flags
        
        logger.info(f"User {email} allowed to register")
        return event
        
    except Exception as e:
        logger.error(f"Pre-signup error: {str(e)}")
        raise e