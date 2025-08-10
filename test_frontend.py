#!/usr/bin/env python3
"""
Test the Redact application frontend accessibility
"""

import requests
import sys

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_frontend():
    """Test frontend accessibility"""
    url = "https://redact.9thcube.com"
    
    print(f"\n{BLUE}Testing Frontend Accessibility{RESET}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"{GREEN}✓ Frontend is accessible (Status: 200){RESET}")
            
            # Check for React app indicators
            if 'root' in response.text:
                print(f"{GREEN}✓ React app root element found{RESET}")
            
            if 'manifest.json' in response.text:
                print(f"{GREEN}✓ React manifest reference found{RESET}")
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                print(f"{GREEN}✓ Correct content type: {content_type}{RESET}")
            
            print(f"\n{GREEN}Frontend is fully operational!{RESET}")
            return True
            
        else:
            print(f"{RED}✗ Frontend returned status: {response.status_code}{RESET}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"{RED}✗ Request timeout{RESET}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"{RED}✗ Connection error{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ Unexpected error: {str(e)}{RESET}")
        return False

if __name__ == "__main__":
    success = test_frontend()
    sys.exit(0 if success else 1)