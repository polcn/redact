# ChromaDB Vector Integration Testing Guide

This guide explains how to run and interpret the comprehensive test suite for the ChromaDB vector integration.

## Quick Start

### Prerequisites
```bash
# Ensure required packages are installed
pip3 install chromadb requests boto3 psutil requests-mock
```

### Run Basic Integration Test
```bash
python3 test_vector_integration.py
```

### Run Live API Endpoint Tests
```bash
python3 test_vector_endpoints.py
```

### Run Comprehensive Test Suite
```bash
python3 run_vector_tests.py
```

## Test Files Overview

### Core Test Files
- **`test_vector_integration.py`** - Fixed integration test with proper error handling
- **`test_vector_endpoints.py`** - Live API endpoint testing (no auth required)
- **`run_vector_tests.py`** - Comprehensive test runner with reporting

### Advanced Test Suites
- **`tests/test_chromadb_client.py`** - Unit tests for ChromaDB client (25+ tests)
- **`tests/test_vector_api_integration.py`** - API integration tests with auth
- **`tests/test_vector_performance.py`** - Performance benchmarking
- **`tests/test_vector_security.py`** - Security and isolation tests
- **`tests/test_vector_export.py`** - Export functionality tests

### Utility Files
- **`tests/test_auth_utils.py`** - Authentication helpers and mocks
- **`tests/__init__.py`** - Test package initialization

## Test Categories

### 1. Unit Tests (ChromaDB Client)
**File:** `tests/test_chromadb_client.py`  
**Tests:** 25+ individual test methods

```bash
# Run specific unit tests
python3 -m unittest tests.test_chromadb_client -v
```

**Coverage:**
- Client initialization and configuration
- Document ID generation and uniqueness  
- Vector storage operations
- Search functionality with filters
- User isolation enforcement
- Document deletion
- Statistics calculation
- Error handling scenarios
- Large data handling
- Unicode and special characters

### 2. Integration Tests (API Handlers)
**File:** `tests/test_vector_api_integration.py`  
**Tests:** 15+ integration scenarios

```bash
# Run API integration tests
python3 -m unittest tests.test_vector_api_integration -v
```

**Coverage:**
- Live API endpoint testing
- Handler function testing with mocks
- Authentication flow validation
- User isolation in API context
- Error response handling

### 3. Performance Tests
**File:** `tests/test_vector_performance.py`  
**Tests:** 10+ performance scenarios

```bash
# Run performance tests
python3 -m unittest tests.test_vector_performance -v
```

**Coverage:**
- Small batch performance (10 chunks)
- Medium batch performance (100 chunks)
- Large batch performance (500 chunks)
- Concurrent operations testing
- Memory usage analysis
- Scaling characteristics
- Response time benchmarks

### 4. Security Tests
**File:** `tests/test_vector_security.py`  
**Tests:** 20+ security scenarios

```bash
# Run security tests
python3 -m unittest tests.test_vector_security -v
```

**Coverage:**
- User data isolation verification
- Cross-user access prevention
- Malicious input handling
- Metadata injection prevention
- Authentication boundary testing
- Data leakage prevention
- Input sanitization

### 5. Export Tests
**File:** `tests/test_vector_export.py`  
**Tests:** 8+ export scenarios

```bash
# Run export tests
python3 -m unittest tests.test_vector_export -v
```

**Coverage:**
- RedactExporter functionality
- JSON export format
- ChromaDB export format
- RAG-ready export format
- Data consistency verification
- Export error handling

## Live API Testing

### Basic Endpoint Verification
```bash
# Test live endpoints (no auth needed)
python3 test_vector_endpoints.py
```

This tests:
- Endpoint availability
- Authentication requirement enforcement
- CORS configuration
- HTTP status code correctness

### Expected Results
All endpoints should return `403 "Missing Authentication Token"` which confirms:
- ✅ Endpoints are deployed
- ✅ Authentication is required
- ✅ CORS is properly configured

## Test Result Interpretation

### Success Indicators
- **All Passed**: System ready for production
- **95%+ Success**: Minor issues, mostly production ready
- **80%+ Success**: Needs some fixes before deployment
- **< 80% Success**: Major issues requiring attention

### Common Test Outputs

#### ✅ Successful Test Run
```
============================================================
Test Summary
============================================================
ChromaDB Installation          ✅ PASS
ChromaDB Import                ✅ PASS
ChromaDB Initialization        ✅ PASS
Vector Operations              ✅ PASS
API Handler Imports            ✅ PASS
Export Script                  ✅ PASS
------------------------------------------------------------
Total: 6/6 tests passed

🎉 All tests passed! The integration is ready to deploy.
```

#### ⚠️ Common Warnings
```
⚠️  ChromaDB not available, skipping performance tests
⚠️  psutil not available (performance monitoring limited)
⚠️  API handlers not available for performance testing
```

These warnings are usually due to missing optional dependencies and don't affect core functionality.

## Troubleshooting

### Missing Dependencies
```bash
# Install ChromaDB
pip3 install chromadb

# Install optional performance monitoring
pip3 install psutil

# Install test utilities
pip3 install requests-mock
```

### Permission Issues
```bash
# If ChromaDB has permission issues with /tmp
export CHROMADB_PERSIST_DIR=/tmp/chromadb_test
chmod 755 /tmp/chromadb_test
```

### Import Errors
```bash
# Ensure Python path includes project directories
export PYTHONPATH="/home/ec2-user/redact-terraform:/home/ec2-user/redact-terraform/api_code:/home/ec2-user/redact-terraform/tests"
```

### AWS Credential Issues
```bash
# Set mock AWS credentials for testing
export AWS_ACCESS_KEY_ID=test-key
export AWS_SECRET_ACCESS_KEY=test-secret
export AWS_DEFAULT_REGION=us-east-1
```

## Advanced Testing

### Running Specific Test Classes
```bash
# Run only security tests
python3 -m unittest tests.test_vector_security.TestVectorUserIsolation -v

# Run only performance tests  
python3 -m unittest tests.test_vector_performance.TestVectorPerformance -v
```

### Custom Test Configuration
```bash
# Set custom ChromaDB directory
export CHROMADB_PERSIST_DIR=/custom/path

# Set custom collection name
export CHROMADB_COLLECTION=custom_test_collection

# Run with custom settings
python3 test_vector_integration.py
```

## Continuous Integration

### CI/CD Integration
Add to your CI pipeline:
```bash
# In .github/workflows or similar
- name: Run Vector Integration Tests
  run: |
    pip3 install chromadb requests boto3 psutil requests-mock
    python3 test_vector_integration.py
    python3 test_vector_endpoints.py
```

### Test Reporting
The comprehensive test runner generates JSON reports:
```bash
python3 run_vector_tests.py
# Generates: vector_integration_test_report_YYYYMMDD_HHMMSS.json
```

## Test Data Cleanup

Tests automatically clean up after themselves, but you can manually clean:
```bash
# Remove test ChromaDB data
rm -rf /tmp/*chromadb*
rm -rf /tmp/test_*

# Remove test export data  
rm -rf ./redact_export
rm -f *.json
```

## Getting Help

### Test Failures
1. Check the test output for specific error messages
2. Verify all dependencies are installed
3. Ensure AWS credentials are configured (even mock ones)
4. Check file permissions for ChromaDB directories

### Performance Issues
1. Monitor system resources during tests
2. Check ChromaDB logs for bottlenecks
3. Verify disk space is sufficient
4. Consider running tests on more powerful hardware

### Security Test Failures
Security test failures are critical and should be addressed immediately:
1. Review user isolation implementation
2. Check authentication flow
3. Verify input sanitization
4. Test with real user tokens if available

---

For additional support, review the comprehensive test report in `vector_integration_test_report.md` or examine individual test files for specific scenarios.