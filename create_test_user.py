#!/usr/bin/env python3
"""
Create a test user for the Redact application
"""

import boto3
import sys
import random
import string
from botocore.exceptions import ClientError

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def generate_password():
    """Generate a strong password that meets Cognito requirements"""
    # Ensure we have at least one of each required character type
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice('!@#$%^&*()_+-=[]{}|;:,.<>?')
    
    # Generate the rest randomly
    remaining_length = 12 - 4  # We already have 4 characters
    remaining = ''.join(random.choices(
        string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?',
        k=remaining_length
    ))
    
    # Combine and shuffle
    password = uppercase + lowercase + digit + special + remaining
    password_list = list(password)
    random.shuffle(password_list)
    return ''.join(password_list)

def create_test_user():
    """Create a test user in Cognito"""
    cognito = boto3.client('cognito-idp', region_name='us-east-1')
    user_pool_id = 'us-east-1_4Uv3seGwS'
    
    # Generate test user credentials
    # Use gmail.com as it's an allowed domain
    timestamp = ''.join(random.choices(string.digits, k=6))
    username = f"testuser{timestamp}@gmail.com"
    password = generate_password()
    
    print(f"\n{BLUE}Creating test user in Cognito...{RESET}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    
    try:
        # Create user
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {'Name': 'email', 'Value': username},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            TemporaryPassword=password,
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        print(f"{GREEN}✓ User created successfully{RESET}")
        
        # Set permanent password
        print(f"\n{BLUE}Setting permanent password...{RESET}")
        
        # Get app client ID
        clients = cognito.list_user_pool_clients(
            UserPoolId=user_pool_id,
            MaxResults=10
        )
        
        client_id = None
        for client in clients['UserPoolClients']:
            if 'redact' in client['ClientName'].lower():
                client_id = client['ClientId']
                break
        
        if not client_id and clients['UserPoolClients']:
            client_id = clients['UserPoolClients'][0]['ClientId']
        
        if client_id:
            # Set permanent password
            cognito.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=username,
                Password=password,
                Permanent=True
            )
            
            print(f"{GREEN}✓ Password set as permanent{RESET}")
        
        # Save credentials to file
        with open('.test_credentials', 'w') as f:
            f.write(f"export TEST_EMAIL='{username}'\n")
            f.write(f"export TEST_PASSWORD='{password}'\n")
        
        print(f"\n{GREEN}Test user created successfully!{RESET}")
        print(f"\n{BLUE}To run tests with this user:{RESET}")
        print(f"  source .test_credentials")
        print(f"  python3 test_redact_application.py")
        print(f"\n{YELLOW}Note: Credentials saved to .test_credentials file{RESET}")
        
        return username, password
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UsernameExistsException':
            print(f"{YELLOW}User already exists: {username}{RESET}")
        else:
            print(f"{RED}Error creating user: {error_code}{RESET}")
            print(f"  {error_message}")
        
        return None, None
    
    except Exception as e:
        print(f"{RED}Unexpected error: {str(e)}{RESET}")
        return None, None

def delete_test_user(username):
    """Delete a test user from Cognito"""
    cognito = boto3.client('cognito-idp', region_name='us-east-1')
    user_pool_id = 'us-east-1_4Uv3seGwS'
    
    try:
        cognito.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        print(f"{GREEN}✓ User {username} deleted successfully{RESET}")
        return True
    except ClientError as e:
        print(f"{RED}Error deleting user: {e}{RESET}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == 'delete':
        if len(sys.argv) > 2:
            username = sys.argv[2]
            delete_test_user(username)
        else:
            print(f"{RED}Please provide username to delete{RESET}")
            print(f"Usage: {sys.argv[0]} delete <username>")
    else:
        create_test_user()

if __name__ == "__main__":
    main()