# CI/CD Setup Documentation

This document outlines the requirements and setup process for enabling the GitHub Actions CI/CD pipeline for the Document Redaction System.

## Required GitHub Secrets

### AWS Credentials
The following secrets must be configured in your GitHub repository settings under Settings → Secrets and variables → Actions:

#### Production Environment
- `AWS_ACCESS_KEY_ID_PRODUCTION` - AWS access key ID for production deployments
- `AWS_SECRET_ACCESS_KEY_PRODUCTION` - AWS secret access key for production deployments
- `AWS_REGION_PRODUCTION` - AWS region (e.g., `us-east-1`)

#### Staging Environment
- `AWS_ACCESS_KEY_ID_STAGING` - AWS access key ID for staging deployments
- `AWS_SECRET_ACCESS_KEY_STAGING` - AWS secret access key for staging deployments
- `AWS_REGION_STAGING` - AWS region for staging (e.g., `us-east-1`)

### Terraform Variables
- `TF_VAR_domain_name` - Domain name for the application (e.g., `redact.9thcube.com`)
- `TF_VAR_frontend_bucket_name` - S3 bucket name for frontend (e.g., `redact-frontend-9thcube`)

## GitHub Environments Setup

### 1. Create Environments
Navigate to Settings → Environments and create:

1. **staging**
   - Protection rules: None (for automatic deployments)
   - Environment secrets: Add staging-specific AWS credentials

2. **production**
   - Protection rules:
     - Required reviewers: 1
     - Restrict deployments to protected branches
   - Environment secrets: Add production-specific AWS credentials

### 2. Branch Strategy
- `main` - Production branch (protected)
- `develop` - Staging/development branch

## Required Files for CI/CD

### 1. Test Dependencies
Create `requirements-test.txt`:
```txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
boto3==1.29.7
moto==4.2.11
```

### 2. Unit Tests
Create `tests/test_lambda_function.py`:
```python
import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda_code.lambda_function_v2 import (
    lambda_handler, 
    apply_redaction_rules,
    validate_file,
    PII_PATTERNS
)

class TestLambdaFunction:
    def test_apply_redaction_rules_text(self):
        """Test text-based redaction rules"""
        config = {
            "replacements": [
                {"find": "secret", "replace": "[REDACTED]"}
            ],
            "case_sensitive": False
        }
        text = "This is a secret document with SECRET information."
        result, redacted = apply_redaction_rules(text, config)
        assert result == "This is a [REDACTED] document with [REDACTED] information."
        assert redacted == True
    
    def test_apply_redaction_patterns(self):
        """Test pattern-based PII detection"""
        config = {
            "replacements": [],
            "patterns": {
                "ssn": True,
                "email": True
            }
        }
        text = "SSN: 123-45-6789, Email: test@example.com"
        result, redacted = apply_redaction_rules(text, config)
        assert "123-45-6789" not in result
        assert "test@example.com" not in result
        assert "[SSN]" in result
        assert "[EMAIL]" in result
    
    def test_validate_file_valid(self):
        """Test file validation with valid file"""
        with patch('lambda_code.lambda_function_v2.s3') as mock_s3:
            mock_s3.head_object.return_value = {
                'ContentLength': 1000
            }
            result = validate_file('test-bucket', 'users/123/test.txt')
            assert result == True
    
    def test_validate_file_too_large(self):
        """Test file validation with oversized file"""
        with patch('lambda_code.lambda_function_v2.s3') as mock_s3:
            mock_s3.head_object.return_value = {
                'ContentLength': 100 * 1024 * 1024  # 100MB
            }
            with pytest.raises(ValueError, match="File too large"):
                validate_file('test-bucket', 'users/123/test.txt')
```

### 3. Integration Tests
Create `tests/test_integration.py`:
```python
import pytest
import boto3
import json
from moto import mock_s3
import os

@mock_s3
class TestIntegration:
    def setup_method(self):
        """Set up test S3 buckets"""
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.input_bucket = 'test-input-bucket'
        self.output_bucket = 'test-output-bucket'
        self.config_bucket = 'test-config-bucket'
        
        # Create buckets
        self.s3_client.create_bucket(Bucket=self.input_bucket)
        self.s3_client.create_bucket(Bucket=self.output_bucket)
        self.s3_client.create_bucket(Bucket=self.config_bucket)
        
        # Set environment variables
        os.environ['INPUT_BUCKET'] = self.input_bucket
        os.environ['OUTPUT_BUCKET'] = self.output_bucket
        os.environ['CONFIG_BUCKET'] = self.config_bucket
    
    def test_end_to_end_processing(self):
        """Test complete document processing flow"""
        # Upload test config
        config = {
            "replacements": [{"find": "test", "replace": "[REDACTED]"}],
            "patterns": {"email": True}
        }
        self.s3_client.put_object(
            Bucket=self.config_bucket,
            Key='config.json',
            Body=json.dumps(config)
        )
        
        # Upload test document
        test_content = "This is a test document. Email: test@example.com"
        self.s3_client.put_object(
            Bucket=self.input_bucket,
            Key='users/123/test.txt',
            Body=test_content
        )
        
        # Test processing would happen here
        # (In real integration test, trigger Lambda and verify output)
```

### 4. CloudWatch Dashboard Configuration
Create `monitoring-dashboard.json`:
```json
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
                    [".", "Errors", {"stat": "Sum"}],
                    [".", "Duration", {"stat": "Average"}]
                ],
                "period": 300,
                "stat": "Average",
                "region": "us-east-1",
                "title": "Lambda Performance"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/S3", "BucketSizeBytes", {"stat": "Average"}],
                    [".", "NumberOfObjects", {"stat": "Average"}]
                ],
                "period": 86400,
                "stat": "Average",
                "region": "us-east-1",
                "title": "S3 Storage Metrics"
            }
        }
    ]
}
```

## Setup Steps

### 1. Create IAM User for CI/CD
```bash
# Create policy for CI/CD
aws iam create-policy --policy-name RedactCICDPolicy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "lambda:*",
        "apigateway:*",
        "cognito-idp:*",
        "cloudfront:*",
        "iam:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}'

# Create user and attach policy
aws iam create-user --user-name github-actions-redact
aws iam attach-user-policy --user-name github-actions-redact --policy-arn arn:aws:iam::YOUR_ACCOUNT:policy/RedactCICDPolicy

# Create access keys
aws iam create-access-key --user-name github-actions-redact
```

### 2. Configure GitHub Secrets
1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add the secrets listed above

### 3. Create Develop Branch
```bash
git checkout -b develop
git push -u origin develop
```

### 4. Enable GitHub Actions
Move the disabled workflow files back:
```bash
mv .github/workflows/ci-cd.yml.disabled .github/workflows/ci-cd.yml
mv .github/workflows/pr-validation.yml.disabled .github/workflows/pr-validation.yml
git add .github/workflows/
git commit -m "Enable GitHub Actions workflows"
git push
```

## Monitoring CI/CD

### GitHub Actions Dashboard
- Monitor workflow runs at: `https://github.com/YOUR_REPO/actions`
- Set up notifications for failed workflows

### AWS CloudWatch
- Lambda function logs: `/aws/lambda/document-scrubbing-processor`
- API Gateway logs: `/aws/api-gateway/redact-api`

### Cost Monitoring
- Set up AWS Budget alerts for CI/CD costs
- Monitor S3 storage costs for test artifacts

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify secrets are correctly set in GitHub
   - Check IAM permissions for the CI/CD user

2. **Terraform State Issues**
   - Ensure S3 backend is configured for state storage
   - Check state locking with DynamoDB

3. **Test Failures**
   - Review test logs in GitHub Actions
   - Run tests locally to debug

## Security Best Practices

1. **Rotate Access Keys**
   - Rotate CI/CD AWS access keys every 90 days
   - Use GitHub's secret scanning to detect exposed keys

2. **Least Privilege**
   - Limit CI/CD IAM permissions to only required resources
   - Use separate AWS accounts for staging/production

3. **Branch Protection**
   - Enable branch protection rules on main
   - Require PR reviews before merging

## Next Steps

After setting up CI/CD:
1. Test the pipeline with a small change
2. Monitor the first few deployments closely
3. Set up alerts for pipeline failures
4. Document any custom configurations