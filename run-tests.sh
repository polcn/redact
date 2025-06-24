#!/bin/bash
set -e

echo "🧪 Running Document Redaction System Tests"
echo "=========================================="

# Install test dependencies
echo "Installing test dependencies..."
pip install -r requirements-test.txt

# Run unit tests with coverage
echo ""
echo "Running unit tests with coverage..."
python -m pytest tests/ -v --cov=lambda_code --cov-report=html --cov-report=term-missing

# Run integration tests (if AWS credentials are available)
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo ""
    echo "Running integration tests..."
    python -m pytest tests/test_integration.py -v
else
    echo ""
    echo "⚠️  AWS credentials not configured - skipping integration tests"
fi

echo ""
echo "✅ Test run complete!"
echo "📊 Coverage report available in htmlcov/index.html"