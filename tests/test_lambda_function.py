import unittest
import json
import os
from unittest.mock import Mock, patch, MagicMock
import tempfile
from io import BytesIO
import sys

# Add the lambda_code directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda_code'))

import lambda_function

class TestLambdaFunction(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            'replacements': [
                {'find': 'ACME Corporation', 'replace': '[CLIENT REDACTED]'},
                {'find': 'john.doe@example.com', 'replace': '[EMAIL REDACTED]'},
                {'find': 'Confidential', 'replace': '[REDACTED]'}
            ],
            'case_sensitive': False
        }
        
        self.mock_context = Mock()
        self.mock_context.aws_request_id = 'test-request-123'
        
        # Set environment variables
        os.environ['INPUT_BUCKET'] = 'test-input-bucket'
        os.environ['OUTPUT_BUCKET'] = 'test-output-bucket'
        os.environ['QUARANTINE_BUCKET'] = 'test-quarantine-bucket'
        os.environ['CONFIG_BUCKET'] = 'test-config-bucket'

    def test_validate_config_valid(self):
        """Test config validation with valid configuration"""
        valid_config = {
            'replacements': [
                {'find': 'test', 'replace': 'TEST'},
                {'find': 'secret', 'replace': '[REDACTED]'}
            ],
            'case_sensitive': False
        }
        
        # Should not raise exception
        result = lambda_function.validate_config(valid_config)
        self.assertTrue(result)

    def test_validate_config_invalid_structure(self):
        """Test config validation with invalid structure"""
        with self.assertRaises(ValueError):
            lambda_function.validate_config("invalid")
        
        with self.assertRaises(ValueError):
            lambda_function.validate_config({'invalid': 'config'})
        
        with self.assertRaises(ValueError):
            lambda_function.validate_config({'replacements': 'not_a_list'})

    def test_validate_config_too_many_replacements(self):
        """Test config validation with too many replacement rules"""
        many_replacements = [{'find': f'test{i}', 'replace': f'TEST{i}'} for i in range(101)]
        config = {'replacements': many_replacements}
        
        with self.assertRaises(ValueError):
            lambda_function.validate_config(config)

    def test_validate_config_invalid_replacement_rule(self):
        """Test config validation with invalid replacement rules"""
        invalid_configs = [
            {'replacements': ['not_a_dict']},
            {'replacements': [{'replace': 'TEST'}]},  # missing 'find'
            {'replacements': [{'find': '', 'replace': 'TEST'}]}  # empty 'find'
        ]
        
        for config in invalid_configs:
            with self.assertRaises(ValueError):
                lambda_function.validate_config(config)

    @patch('lambda_function.s3')
    def test_validate_file_valid(self, mock_s3):
        """Test file validation with valid file"""
        mock_s3.head_object.return_value = {'ContentLength': 1000}
        
        result = lambda_function.validate_file('test-bucket', 'test.txt')
        self.assertTrue(result)

    @patch('lambda_function.s3')
    def test_validate_file_too_large(self, mock_s3):
        """Test file validation with oversized file"""
        mock_s3.head_object.return_value = {'ContentLength': 100 * 1024 * 1024}  # 100MB
        
        with self.assertRaises(ValueError) as cm:
            lambda_function.validate_file('test-bucket', 'large.txt')
        
        self.assertIn('File too large', str(cm.exception))

    @patch('lambda_function.s3')
    def test_validate_file_empty(self, mock_s3):
        """Test file validation with empty file"""
        mock_s3.head_object.return_value = {'ContentLength': 0}
        
        with self.assertRaises(ValueError) as cm:
            lambda_function.validate_file('test-bucket', 'empty.txt')
        
        self.assertIn('File is empty', str(cm.exception))

    @patch('lambda_function.s3')
    def test_validate_file_unsupported_type(self, mock_s3):
        """Test file validation with unsupported file type"""
        mock_s3.head_object.return_value = {'ContentLength': 1000}
        
        with self.assertRaises(ValueError) as cm:
            lambda_function.validate_file('test-bucket', 'test.exe')
        
        self.assertIn('Unsupported file type', str(cm.exception))

    def test_apply_redaction_rules_basic(self):
        """Test basic redaction functionality"""
        content = "This document is from ACME Corporation and contains Confidential information."
        processed, redacted = lambda_function.apply_redaction_rules(content, self.test_config)
        
        expected = "This document is from [CLIENT REDACTED] and contains [REDACTED] information."
        self.assertEqual(processed, expected)
        self.assertTrue(redacted)

    def test_apply_redaction_rules_case_insensitive(self):
        """Test case-insensitive redaction"""
        content = "Contact acme corporation at JOHN.DOE@EXAMPLE.COM"
        processed, redacted = lambda_function.apply_redaction_rules(content, self.test_config)
        
        expected = "Contact [CLIENT REDACTED] at [EMAIL REDACTED]"
        self.assertEqual(processed, expected)
        self.assertTrue(redacted)

    def test_apply_redaction_rules_no_matches(self):
        """Test redaction with no matches"""
        content = "This is a clean document with no sensitive data."
        processed, redacted = lambda_function.apply_redaction_rules(content, self.test_config)
        
        self.assertEqual(processed, content)
        self.assertFalse(redacted)

    def test_apply_redaction_rules_case_sensitive(self):
        """Test case-sensitive redaction"""
        case_sensitive_config = {
            'replacements': [{'find': 'Secret', 'replace': '[REDACTED]'}],
            'case_sensitive': True
        }
        
        content = "This Secret document has secret information."
        processed, redacted = lambda_function.apply_redaction_rules(content, case_sensitive_config)
        
        expected = "This [REDACTED] document has secret information."
        self.assertEqual(processed, expected)
        self.assertTrue(redacted)

    @patch('lambda_function.s3')
    def test_process_text_file_success(self, mock_s3):
        """Test successful text file processing"""
        test_content = "Document from ACME Corporation"
        mock_s3.get_object.return_value = {
            'Body': BytesIO(test_content.encode('utf-8'))
        }
        mock_s3.put_object.return_value = {}
        
        result = lambda_function.process_text_file('test-bucket', 'test.txt', self.test_config)
        self.assertTrue(result)
        
        # Verify S3 operations were called
        mock_s3.get_object.assert_called_once()
        mock_s3.put_object.assert_called_once()

    @patch('lambda_function.s3')
    def test_quarantine_document(self, mock_s3):
        """Test document quarantine functionality"""
        mock_s3.copy_object.return_value = {}
        
        lambda_function.quarantine_document('source-bucket', 'test.txt', 'Test reason')
        
        mock_s3.copy_object.assert_called_once()
        call_args = mock_s3.copy_object.call_args
        
        self.assertEqual(call_args[1]['CopySource']['Bucket'], 'source-bucket')
        self.assertEqual(call_args[1]['CopySource']['Key'], 'test.txt')
        self.assertEqual(call_args[1]['Bucket'], 'test-quarantine-bucket')
        self.assertEqual(call_args[1]['Key'], 'quarantine/test.txt')

    @patch('lambda_function.s3')
    @patch('lambda_function.get_redaction_config')
    @patch('lambda_function.validate_file')
    @patch('lambda_function.process_text_file')
    def test_lambda_handler_single_file(self, mock_process, mock_validate, mock_get_config, mock_s3):
        """Test Lambda handler with single file"""
        mock_get_config.return_value = self.test_config
        mock_validate.return_value = True
        mock_process.return_value = True
        
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test.txt'}
                }
            }]
        }
        
        response = lambda_function.lambda_handler(event, self.mock_context)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['processed'], 1)
        self.assertEqual(body['total'], 1)
        self.assertEqual(len(body['results']), 1)
        self.assertEqual(body['results'][0]['status'], 'SUCCESS')

    @patch('lambda_function.s3')
    @patch('lambda_function.get_redaction_config')
    @patch('lambda_function.validate_file')
    @patch('lambda_function.process_text_file')
    def test_lambda_handler_batch_processing(self, mock_process, mock_validate, mock_get_config, mock_s3):
        """Test Lambda handler with batch processing"""
        mock_get_config.return_value = self.test_config
        mock_validate.return_value = True
        mock_process.return_value = True
        
        # Create event with multiple files
        event = {
            'Records': [
                {'s3': {'bucket': {'name': 'test-bucket'}, 'object': {'key': f'test{i}.txt'}}}
                for i in range(3)
            ]
        }
        
        response = lambda_function.lambda_handler(event, self.mock_context)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['processed'], 3)
        self.assertEqual(body['total'], 3)
        self.assertEqual(len(body['results']), 3)

    @patch('lambda_function.s3')
    @patch('lambda_function.get_redaction_config')
    def test_lambda_handler_config_error(self, mock_get_config, mock_s3):
        """Test Lambda handler with configuration error"""
        mock_get_config.side_effect = Exception("Config error")
        
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test.txt'}
                }
            }]
        }
        
        response = lambda_function.lambda_handler(event, self.mock_context)
        
        self.assertEqual(response['statusCode'], 500)

    @patch('lambda_function.s3')
    def test_get_redaction_config_from_s3(self, mock_s3):
        """Test loading configuration from S3"""
        config_data = json.dumps(self.test_config)
        mock_s3.head_object.return_value = {
            'LastModified': '2023-01-01T00:00:00Z',
            'ContentLength': len(config_data)
        }
        mock_s3.get_object.return_value = {
            'Body': BytesIO(config_data.encode('utf-8'))
        }
        
        result = lambda_function.get_redaction_config()
        
        self.assertEqual(result, self.test_config)

    @patch('lambda_function.s3')
    def test_get_redaction_config_no_file(self, mock_s3):
        """Test loading configuration when no config file exists"""
        mock_s3.head_object.side_effect = lambda_function.s3.exceptions.NoSuchKey({}, 'NoSuchKey')
        
        result = lambda_function.get_redaction_config()
        
        # Should return default config
        self.assertIn('replacements', result)
        self.assertEqual(result['case_sensitive'], False)

    @patch('lambda_function.s3')
    def test_get_redaction_config_invalid_json(self, mock_s3):
        """Test loading configuration with invalid JSON"""
        mock_s3.head_object.return_value = {
            'LastModified': '2023-01-01T00:00:00Z',
            'ContentLength': 20
        }
        mock_s3.get_object.return_value = {
            'Body': BytesIO(b'{invalid json}')
        }
        
        result = lambda_function.get_redaction_config()
        
        # Should return default config on JSON error
        self.assertIn('replacements', result)

    @patch('lambda_function.exponential_backoff_retry')
    def test_download_document_with_retry(self, mock_retry):
        """Test document download with retry logic"""
        mock_content = b"test content"
        mock_retry.return_value = mock_content
        
        result = lambda_function.download_document('test-bucket', 'test.txt')
        
        self.assertEqual(result, mock_content)
        mock_retry.assert_called_once()

    def test_exponential_backoff_retry_success(self):
        """Test exponential backoff retry with successful call"""
        mock_func = Mock(return_value="success")
        
        result = lambda_function.exponential_backoff_retry(mock_func, "arg1", kwarg1="value1")
        
        self.assertEqual(result, "success")
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_exponential_backoff_retry_permanent_error(self):
        """Test exponential backoff retry with permanent error"""
        from botocore.exceptions import ClientError
        
        error_response = {'Error': {'Code': 'NoSuchKey'}}
        mock_func = Mock(side_effect=ClientError(error_response, 'GetObject'))
        
        with self.assertRaises(ClientError):
            lambda_function.exponential_backoff_retry(mock_func)
        
        # Should not retry permanent errors
        mock_func.assert_called_once()

    @patch('time.sleep')
    def test_exponential_backoff_retry_transient_error(self, mock_sleep):
        """Test exponential backoff retry with transient error"""
        from botocore.exceptions import ClientError
        
        error_response = {'Error': {'Code': 'ServiceUnavailable'}}
        mock_func = Mock(side_effect=[
            ClientError(error_response, 'GetObject'),
            ClientError(error_response, 'GetObject'),
            "success"
        ])
        
        result = lambda_function.exponential_backoff_retry(mock_func)
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

if __name__ == '__main__':
    unittest.main()