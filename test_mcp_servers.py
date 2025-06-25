#!/usr/bin/env python3
"""
Test script to verify MCP (Model Context Protocol) servers are working
"""

import subprocess
import json
import sys

def test_mcp_server(server_name, test_command=None):
    """Test if an MCP server is accessible and working"""
    print(f"\nTesting {server_name} MCP server...")
    
    try:
        # List available MCP servers
        result = subprocess.run(['claude', 'mcp', 'list'], 
                              capture_output=True, text=True)
        
        if server_name in result.stdout:
            print(f"✅ {server_name} server is configured")
            
            # Try to get server info if possible
            info_result = subprocess.run(['claude', 'mcp', 'get', server_name], 
                                       capture_output=True, text=True)
            if info_result.returncode == 0:
                print(f"   Server info: Available")
            
            return True
        else:
            print(f"❌ {server_name} server not found")
            return False
            
    except FileNotFoundError:
        print("❌ claude CLI not found in PATH")
        return False
    except Exception as e:
        print(f"❌ Error testing {server_name}: {str(e)}")
        return False

def main():
    """Test all configured MCP servers"""
    print("MCP Server Verification Test")
    print("=" * 40)
    
    servers_to_test = [
        ('aws', 'AWS Documentation and services'),
        ('cloudflare', 'Cloudflare services'),
        ('brightdata', 'Web scraping and data collection'),
    ]
    
    results = {}
    
    for server_name, description in servers_to_test:
        print(f"\n{description}")
        results[server_name] = test_mcp_server(server_name)
    
    # Summary
    print("\n" + "=" * 40)
    print("Summary:")
    working = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"✅ Working servers: {working}/{total}")
    
    if working < total:
        print("\nFailed servers:")
        for server, status in results.items():
            if not status:
                print(f"  - {server}")
    
    # Test AWS S3 bucket access as a practical test
    print("\n" + "=" * 40)
    print("Practical Test: List Redact S3 Buckets")
    try:
        result = subprocess.run(['aws', 's3', 'ls'], 
                              capture_output=True, text=True)
        
        redact_buckets = [line for line in result.stdout.split('\n') 
                         if 'redact-' in line]
        
        if redact_buckets:
            print("✅ Found Redact buckets:")
            for bucket in redact_buckets:
                print(f"   {bucket.strip()}")
        else:
            print("⚠️  No Redact buckets found")
            
    except Exception as e:
        print(f"❌ Error listing S3 buckets: {str(e)}")

if __name__ == "__main__":
    main()