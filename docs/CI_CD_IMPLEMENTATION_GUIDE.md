# CI/CD Implementation Guide

## Status: ⚠️ Currently Disabled

The GitHub Actions workflows are currently disabled to prevent failure notifications. This guide provides instructions for enabling CI/CD when ready.

## Overview

The repository includes comprehensive CI/CD workflows for:
- Automated testing on pull requests
- Deployment to staging (develop branch)
- Production deployment with manual approval
- Security scanning and code quality checks

## Current State

### ✅ Completed
- CI/CD workflow files created (but disabled)
- Pattern-based redaction implemented and tested
- Frontend and backend fully functional
- Documentation for CI/CD setup complete
- Develop branch created for staging

### ⚠️ Pending
- Create test files and dependencies
- Configure GitHub secrets
- Set up GitHub environments
- Enable workflows

## Required Setup

### 1. Missing Files to Create

#### `requirements-test.txt`
```txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
boto3==1.29.7
moto==4.2.11
bandit==1.7.5
```

#### `tests/test_lambda_function.py`
- Unit tests for document processing Lambda
- Mock S3 operations
- Test redaction logic
- Validate error handling

#### `tests/test_integration.py`
- End-to-end tests with mocked AWS services
- API endpoint testing
- File processing workflows

#### `monitoring-dashboard.json`
- CloudWatch dashboard configuration
- Metrics and alarms setup

### 2. GitHub Configuration

#### Secrets Required
```yaml
# AWS Credentials - Staging
AWS_ACCESS_KEY_ID_STAGING
AWS_SECRET_ACCESS_KEY_STAGING
AWS_REGION_STAGING

# AWS Credentials - Production  
AWS_ACCESS_KEY_ID_PRODUCTION
AWS_SECRET_ACCESS_KEY_PRODUCTION
AWS_REGION_PRODUCTION

# Terraform Variables
TF_VAR_domain_name
TF_VAR_hosted_zone_name
```

#### Environments
1. **staging**
   - No protection rules
   - Auto-deploy from develop branch
   
2. **production**
   - Require manual approval
   - Restrict to main branch
   - Add required reviewers

### 3. AWS IAM Requirements

Create IAM users with appropriate policies:

#### CI/CD User Permissions
- S3: Full access to redact buckets
- Lambda: Update function code and configuration
- CloudFormation: Manage stacks
- API Gateway: Update APIs
- CloudWatch: Create dashboards and alarms
- IAM: Manage Lambda execution roles

## Implementation Steps

### Step 1: Create Test Files
```bash
# Create test directory structure
mkdir -p tests

# Create test files (see templates above)
touch requirements-test.txt
touch tests/test_lambda_function.py
touch tests/test_integration.py
touch tests/__init__.py
```

### Step 2: Configure GitHub
1. Go to Repository Settings → Secrets and variables → Actions
2. Add all required secrets listed above
3. Go to Settings → Environments
4. Create `staging` and `production` environments
5. Configure protection rules for production

### Step 3: Test Locally
```bash
# Install act for local testing
brew install act  # or appropriate package manager

# Test PR workflow locally
act pull_request -s GITHUB_TOKEN=$GITHUB_TOKEN

# Test deployment workflow
act push -s GITHUB_TOKEN=$GITHUB_TOKEN
```

### Step 4: Enable Workflows
```bash
# Rename workflow files to enable them
mv .github/workflows/ci-cd.yml.disabled .github/workflows/ci-cd.yml
mv .github/workflows/pr-validation.yml.disabled .github/workflows/pr-validation.yml

# Commit and push
git add .github/workflows/
git commit -m "Enable GitHub Actions workflows"
git push
```

## Workflow Details

### PR Validation Workflow
- Triggers on: Pull requests to main/develop
- Actions:
  - Run Python tests with coverage
  - Security scanning with Bandit
  - Terraform validation
  - Build artifacts

### CI/CD Workflow
- Triggers on: Push to main/develop
- Staging: Auto-deploy from develop
- Production: Manual approval required
- Actions:
  - Deploy infrastructure with Terraform
  - Update Lambda functions
  - Invalidate CloudFront cache
  - Run smoke tests

## Monitoring and Rollback

### Health Checks
- API Gateway health endpoint monitoring
- Lambda function error rates
- S3 bucket accessibility
- CloudWatch alarms for failures

### Rollback Strategy
1. Revert commit in GitHub
2. Workflow automatically triggers
3. Previous version deployed
4. Manual intervention if needed

## Cost Considerations

GitHub Actions pricing:
- 2,000 free minutes/month for private repos
- Additional minutes: $0.008/minute
- Estimated usage: <500 minutes/month

## Recommendations

1. **Start with staging only** - Enable develop branch deployment first
2. **Add tests incrementally** - Begin with critical path tests
3. **Monitor costs** - Set up billing alerts for GitHub Actions
4. **Use caching** - Cache dependencies to reduce build time
5. **Implement gradually** - Don't enable everything at once

## Notes

The application is fully functional without CI/CD. The pipeline is for automated testing and deployment, which can be added when the team is ready for the additional complexity and maintenance overhead.