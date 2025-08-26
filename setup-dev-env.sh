#!/bin/bash

# Setup Development Environment for Redact
# This script creates a separate Terraform workspace for development

set -e  # Exit on error

echo "🚀 Setting up Redact development environment..."

# Check if terraform is initialized
if [ ! -d ".terraform" ]; then
    echo "📦 Initializing Terraform..."
    terraform init
fi

# Create development workspace if it doesn't exist
if ! terraform workspace list | grep -q "development"; then
    echo "🌿 Creating development workspace..."
    terraform workspace new development
else
    echo "🌿 Switching to development workspace..."
    terraform workspace select development
fi

# Plan and apply development infrastructure
echo "📋 Planning development infrastructure..."
terraform plan -var-file="terraform.tfvars.dev" -out=dev.tfplan

echo "🏗️  Building development infrastructure..."
read -p "Do you want to apply the development environment? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply dev.tfplan
    
    # Get the outputs
    echo "📝 Development environment outputs:"
    terraform output
    
    echo "✅ Development environment is ready!"
    echo ""
    echo "Next steps:"
    echo "1. Update Claude SDK in development API handler"
    echo "2. Deploy API Lambda to development environment"
    echo "3. Test all functionality before promoting to production"
    echo ""
    echo "To deploy API updates to dev environment:"
    echo "./build_api_lambda.sh && aws lambda update-function-code --function-name \$(terraform output -raw api_lambda_function_name) --zip-file fileb://api_lambda.zip"
else
    echo "❌ Skipping terraform apply. Run 'terraform apply dev.tfplan' when ready."
fi

# Clean up plan file
rm -f dev.tfplan