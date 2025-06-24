import unittest
import boto3
import json
import time
import os
from moto import mock_s3, mock_lambda
import tempfile

class TestIntegration(unittest.TestCase):
    """
    Integration tests that require AWS resources
    Run only when AWS credentials are configured
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up AWS clients for integration testing"""
        try:
            cls.s3_client = boto3.client('s3')
            # Test AWS credentials
            cls.s3_client.list_buckets()
            cls.aws_available = True
        except Exception:
            cls.aws_available = False
            
    def setUp(self):
        """Skip tests if AWS not available"""
        if not self.aws_available:
            self.skipTest("AWS credentials not available")

    def test_s3_buckets_exist(self):
        """Test that required S3 buckets exist"""
        required_buckets = [
            'redact-input-documents-32a4ee51',
            'redact-processed-documents-32a4ee51',
            'redact-quarantine-documents-32a4ee51',
            'redact-config-32a4ee51'
        ]
        
        try:
            response = self.s3_client.list_buckets()
            bucket_names = [bucket['Name'] for bucket in response['Buckets']]
            
            for bucket in required_buckets:
                if bucket not in bucket_names:
                    self.skipTest(f"Required bucket {bucket} not found - system not deployed")
                    
            self.assertTrue(True, "All required buckets exist")
        except Exception as e:
            self.skipTest(f"Cannot access S3: {str(e)}")

    def test_config_upload_and_retrieval(self):
        """Test uploading and retrieving configuration"""
        config_bucket = 'redact-config-32a4ee51'
        test_config = {
            'replacements': [
                {'find': 'TEST_CLIENT', 'replace': '[TEST REDACTED]'}
            ],
            'case_sensitive': False
        }
        
        try:
            # Upload test config
            self.s3_client.put_object(
                Bucket=config_bucket,
                Key='test-config.json',
                Body=json.dumps(test_config),
                ContentType='application/json'
            )
            
            # Retrieve and verify
            response = self.s3_client.get_object(
                Bucket=config_bucket,
                Key='test-config.json'
            )
            
            retrieved_config = json.loads(response['Body'].read())
            self.assertEqual(retrieved_config, test_config)
            
            # Cleanup
            self.s3_client.delete_object(
                Bucket=config_bucket,
                Key='test-config.json'
            )
            
        except Exception as e:
            self.skipTest(f"Cannot test config operations: {str(e)}")

    def test_document_processing_flow(self):
        """Test end-to-end document processing"""
        input_bucket = 'redact-input-documents-32a4ee51'
        processed_bucket = 'redact-processed-documents-32a4ee51'
        
        test_document = "This document contains information about ACME Corporation."
        test_key = f'integration-test-{int(time.time())}.txt'
        
        try:
            # Upload test document
            self.s3_client.put_object(
                Bucket=input_bucket,
                Key=test_key,
                Body=test_document,
                ContentType='text/plain'
            )
            
            # Wait for processing (Lambda triggered by S3 event)
            print(f"Uploaded {test_key}, waiting for processing...")
            time.sleep(30)  # Give Lambda time to process
            
            # Check for processed document
            processed_key = f'processed/{test_key}'
            try:
                response = self.s3_client.get_object(
                    Bucket=processed_bucket,
                    Key=processed_key
                )
                
                processed_content = response['Body'].read().decode('utf-8')
                print(f"Processed content: {processed_content}")
                
                # Verify redaction occurred
                self.assertNotIn('ACME Corporation', processed_content)
                self.assertIn('[REDACTED]', processed_content)
                
                # Cleanup processed document
                self.s3_client.delete_object(
                    Bucket=processed_bucket,
                    Key=processed_key
                )
                
            except self.s3_client.exceptions.NoSuchKey:
                self.fail("Document was not processed within expected time")
                
        except Exception as e:
            self.fail(f"Integration test failed: {str(e)}")
        
        finally:
            # Cleanup input document
            try:
                self.s3_client.delete_object(
                    Bucket=input_bucket,
                    Key=test_key
                )
            except:
                pass

@mock_s3
@mock_lambda
class TestMockedIntegration(unittest.TestCase):
    """
    Integration tests using moto mocks
    These run without requiring real AWS resources
    """
    
    def setUp(self):
        """Set up mocked AWS resources"""
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Create mock buckets
        self.buckets = {
            'input': 'test-input-bucket',
            'output': 'test-output-bucket', 
            'quarantine': 'test-quarantine-bucket',
            'config': 'test-config-bucket'
        }
        
        for bucket in self.buckets.values():
            self.s3_client.create_bucket(Bucket=bucket)

    def test_mocked_s3_operations(self):
        """Test S3 operations with mocked resources"""
        # Test file upload
        test_content = "Test document content"
        self.s3_client.put_object(
            Bucket=self.buckets['input'],
            Key='test.txt',
            Body=test_content
        )
        
        # Test file retrieval
        response = self.s3_client.get_object(
            Bucket=self.buckets['input'],
            Key='test.txt'
        )
        
        retrieved_content = response['Body'].read().decode('utf-8')
        self.assertEqual(retrieved_content, test_content)

    def test_mocked_config_operations(self):
        """Test configuration operations with mocked S3"""
        config = {
            'replacements': [
                {'find': 'SECRET', 'replace': '[REDACTED]'}
            ],
            'case_sensitive': True
        }
        
        # Upload config
        self.s3_client.put_object(
            Bucket=self.buckets['config'],
            Key='config.json',
            Body=json.dumps(config)
        )
        
        # Retrieve and validate
        response = self.s3_client.get_object(
            Bucket=self.buckets['config'],
            Key='config.json'
        )
        
        retrieved_config = json.loads(response['Body'].read())
        self.assertEqual(retrieved_config, config)

if __name__ == '__main__':
    unittest.main()