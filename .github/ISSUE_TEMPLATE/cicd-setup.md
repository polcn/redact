---
name: Enable CI/CD Pipeline
about: Track the setup required to enable GitHub Actions workflows
title: 'Enable CI/CD Pipeline for Automated Testing and Deployment'
labels: enhancement, infrastructure
assignees: ''
---

## Overview
The repository has GitHub Actions workflows configured but they are currently disabled due to missing dependencies and configuration. This issue tracks the work needed to properly enable CI/CD.

## Current Status
- Workflows are renamed to `.disabled` to prevent failure emails
- Located in `.github/workflows/`:
  - `ci-cd.yml.disabled` - Main CI/CD pipeline
  - `pr-validation.yml.disabled` - PR validation checks

## Required Setup

### 1. Create Missing Files
- [ ] `requirements-test.txt` with test dependencies:
  ```
  pytest==7.4.0
  pytest-cov==4.1.0
  boto3==1.26.137
  moto==4.1.11
  bandit==1.7.5
  ```
- [ ] `tests/test_lambda_function.py` - Unit tests for Lambda functions
- [ ] `tests/test_integration.py` - Integration tests
- [ ] `monitoring-dashboard.json` - CloudWatch dashboard configuration

### 2. Configure GitHub Repository
- [ ] Add GitHub Secrets:
  - `AWS_ACCESS_KEY_ID_STAGING`
  - `AWS_SECRET_ACCESS_KEY_STAGING`
  - `AWS_ACCESS_KEY_ID` (production)
  - `AWS_SECRET_ACCESS_KEY` (production)
- [ ] Create GitHub Environments:
  - `staging` environment
  - `production` environment with protection rules
- [ ] Create `develop` branch for staging deployments

### 3. Write Tests
- [ ] Unit tests for document processing Lambda
- [ ] Unit tests for API handler Lambda
- [ ] Integration tests for S3 operations
- [ ] Integration tests for API endpoints

### 4. Re-enable Workflows
```bash
mv .github/workflows/ci-cd.yml.disabled .github/workflows/ci-cd.yml
mv .github/workflows/pr-validation.yml.disabled .github/workflows/pr-validation.yml
```

## Benefits When Enabled
- Automated testing on every PR
- Security scanning with Bandit
- Terraform validation
- Automated deployments to staging (develop branch)
- Automated deployments to production (main branch)
- Code coverage reporting

## References
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)