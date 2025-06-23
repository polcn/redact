#!/bin/bash

# Deployment script for AWS Document Scrubbing System

set -e

echo "Starting deployment of AWS Document Scrubbing System with 'redact' tags..."

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

# Plan deployment
echo "Planning Terraform deployment..."
terraform plan

echo "Deployment plan complete! Use 'terraform apply' to deploy the infrastructure."
echo ""
echo "This will create:"
echo "- KMS key for encryption (tagged: Project=redact)"
echo "- 3 S3 buckets (input, processed, quarantine) with encryption"
echo "- VPC with private subnets for secure processing"
echo "- VPC endpoints for AWS services"
echo "- Security groups and networking"
echo ""
echo "All resources will be tagged with Project=redact for easy identification and billing."