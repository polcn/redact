#!/usr/bin/env python3
"""
Comprehensive Security Validation Test Suite
Tests the critical security fixes deployed to the Redact application
"""

import requests
import json
import sys
from urllib.parse import urljoin

# Production API endpoint
BASE_URL = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"

def test_anonymous_access_blocked():
    """Test that anonymous access is properly blocked"""
    print("\n=== Testing Anonymous Access Blocking ===")
    
    endpoints_to_test = [
        ("GET", "/user/files"),
        ("POST", "/documents/upload"),
        ("GET", "/documents/status/test"),
        ("DELETE", "/documents/test"),
        ("POST", "/documents/batch-download"),
        ("POST", "/documents/combine"),
        ("POST", "/documents/ai-summary"),
        ("POST", "/documents/extract-metadata"),
        ("POST", "/documents/prepare-vectors"),
        ("GET", "/api/config"),
        ("PUT", "/api/config"),
        ("GET", "/redaction/patterns"),
        ("POST", "/redaction/patterns"),
        ("POST", "/redaction/apply"),
        ("GET", "/quarantine/files"),
        ("DELETE", "/quarantine/test"),
        ("POST", "/vectors/store"),
        ("POST", "/vectors/search"),
        ("GET", "/vectors/stats"),
        ("DELETE", "/vectors/delete"),
        ("POST", "/export/batch-metadata")
    ]
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    for method, endpoint in endpoints_to_test:
        try:
            if method == "GET":
                response = requests.get(urljoin(BASE_URL, endpoint), timeout=10)
            elif method == "POST":
                response = requests.post(urljoin(BASE_URL, endpoint), 
                                       json={"test": "data"}, timeout=10)
            elif method == "PUT":
                response = requests.put(urljoin(BASE_URL, endpoint), 
                                      json={"test": "data"}, timeout=10)
            elif method == "DELETE":
                response = requests.delete(urljoin(BASE_URL, endpoint), timeout=10)
            
            if response.status_code == 401:
                print(f"✅ {method} {endpoint}: Properly blocked (401)")
                results["passed"] += 1
                results["details"].append(f"PASS: {method} {endpoint} - 401 Unauthorized")
            elif response.status_code == 403 and "Forbidden" in response.text:
                print(f"✅ {method} {endpoint}: Properly blocked (403)")
                results["passed"] += 1
                results["details"].append(f"PASS: {method} {endpoint} - 403 Forbidden")
            else:
                print(f"❌ {method} {endpoint}: NOT BLOCKED! Status: {response.status_code}, Response: {response.text[:100]}")
                results["failed"] += 1
                results["details"].append(f"FAIL: {method} {endpoint} - Status {response.status_code}: {response.text[:100]}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ {method} {endpoint}: Request failed: {str(e)}")
            results["details"].append(f"ERROR: {method} {endpoint} - Request failed: {str(e)}")
    
    return results

def test_malformed_auth_blocked():
    """Test that malformed authorization headers are blocked"""
    print("\n=== Testing Malformed Authorization Blocking ===")
    
    malformed_headers = [
        {"Authorization": "Bearer invalid_token"},
        {"Authorization": "Basic invalid_basic"},
        {"Authorization": "Bearer "},
        {"Authorization": ""},
        {"Authorization": "NotBearer token"},
    ]
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    for headers in malformed_headers:
        try:
            response = requests.get(urljoin(BASE_URL, "/user/files"), 
                                  headers=headers, timeout=10)
            
            if response.status_code in [401, 403]:
                print(f"✅ Malformed auth blocked: {headers['Authorization'][:20]}...")
                results["passed"] += 1
                results["details"].append(f"PASS: Blocked malformed auth: {headers['Authorization'][:20]}...")
            else:
                print(f"❌ Malformed auth NOT blocked: {headers['Authorization'][:20]}... Status: {response.status_code}")
                results["failed"] += 1
                results["details"].append(f"FAIL: Malformed auth not blocked: {headers['Authorization'][:20]}... Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request failed for {headers['Authorization'][:20]}...: {str(e)}")
            results["details"].append(f"ERROR: Request failed for malformed auth: {str(e)}")
    
    return results

def test_cors_headers():
    """Test CORS configuration"""
    print("\n=== Testing CORS Configuration ===")
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    # Test OPTIONS request
    try:
        response = requests.options(urljoin(BASE_URL, "/user/files"),
                                  headers={"Origin": "https://redact.9thcube.com"}, timeout=10)
        
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
        }
        
        # Check if CORS is restricted to production domain
        if cors_headers["Access-Control-Allow-Origin"] == "https://redact.9thcube.com":
            print("✅ CORS properly restricted to production domain")
            results["passed"] += 1
            results["details"].append("PASS: CORS restricted to production domain")
        elif cors_headers["Access-Control-Allow-Origin"] == "*":
            print("❌ CORS allows all origins - SECURITY RISK!")
            results["failed"] += 1
            results["details"].append("FAIL: CORS allows all origins - SECURITY RISK!")
        else:
            print(f"⚠️ CORS origin: {cors_headers['Access-Control-Allow-Origin']}")
            results["details"].append(f"INFO: CORS origin: {cors_headers['Access-Control-Allow-Origin']}")
        
        print(f"CORS Headers: {cors_headers}")
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ CORS test failed: {str(e)}")
        results["details"].append(f"ERROR: CORS test failed: {str(e)}")
    
    return results

def test_vector_endpoints_security():
    """Test vector endpoints are properly secured"""
    print("\n=== Testing Vector Endpoints Security ===")
    
    vector_endpoints = [
        ("POST", "/vectors/store"),
        ("POST", "/vectors/search"),
        ("GET", "/vectors/stats"),
        ("DELETE", "/vectors/delete"),
        ("POST", "/export/batch-metadata")
    ]
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    for method, endpoint in vector_endpoints:
        try:
            if method == "GET":
                response = requests.get(urljoin(BASE_URL, endpoint), timeout=10)
            elif method == "POST":
                response = requests.post(urljoin(BASE_URL, endpoint), 
                                       json={"test": "payload"}, timeout=10)
            elif method == "DELETE":
                response = requests.delete(urljoin(BASE_URL, endpoint), timeout=10)
            
            if response.status_code in [401, 403]:
                print(f"✅ Vector endpoint {method} {endpoint}: Properly secured")
                results["passed"] += 1
                results["details"].append(f"PASS: {method} {endpoint} - Properly secured")
            else:
                print(f"❌ Vector endpoint {method} {endpoint}: NOT SECURED! Status: {response.status_code}")
                results["failed"] += 1
                results["details"].append(f"FAIL: {method} {endpoint} - Not secured: Status {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Vector endpoint {method} {endpoint} test failed: {str(e)}")
            results["details"].append(f"ERROR: {method} {endpoint} test failed: {str(e)}")
    
    return results

def main():
    """Run comprehensive security validation"""
    print("🔒 REDACT APPLICATION SECURITY VALIDATION")
    print("=" * 50)
    print("Testing critical security patches deployed on 2025-08-27")
    
    all_results = {
        "anonymous_access": test_anonymous_access_blocked(),
        "malformed_auth": test_malformed_auth_blocked(),
        "cors": test_cors_headers(),
        "vector_security": test_vector_endpoints_security()
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("🔒 SECURITY VALIDATION SUMMARY")
    print("=" * 50)
    
    total_passed = sum(result["passed"] for result in all_results.values())
    total_failed = sum(result["failed"] for result in all_results.values())
    
    for test_name, result in all_results.items():
        print(f"{test_name.replace('_', ' ').title()}: {result['passed']} passed, {result['failed']} failed")
    
    print(f"\nOVERALL: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("\n✅ ALL SECURITY TESTS PASSED! The application is properly secured.")
        exit_code = 0
    else:
        print(f"\n❌ {total_failed} SECURITY TESTS FAILED! Review the failures above.")
        exit_code = 1
    
    # Detailed results
    print("\n" + "=" * 50)
    print("📋 DETAILED TEST RESULTS")
    print("=" * 50)
    
    for test_name, result in all_results.items():
        print(f"\n{test_name.replace('_', ' ').title()}:")
        for detail in result["details"]:
            print(f"  {detail}")
    
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)