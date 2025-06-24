output "input_bucket_name" {
  description = "Name of the input S3 bucket"
  value       = aws_s3_bucket.input_documents.bucket
}

output "processed_bucket_name" {
  description = "Name of the processed documents S3 bucket"
  value       = aws_s3_bucket.processed_documents.bucket
}

output "quarantine_bucket_name" {
  description = "Name of the quarantine S3 bucket"  
  value       = aws_s3_bucket.quarantine_documents.bucket
}

output "config_bucket_name" {
  description = "Name of the config S3 bucket"
  value       = aws_s3_bucket.config_bucket.bucket
}

# Cost-optimized: KMS and VPC outputs removed as these resources were eliminated

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.redact_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

output "api_endpoints" {
  description = "Available API endpoints"
  value = {
    health = "GET /health"
    upload = "POST /documents/upload"
    status = "GET /documents/status/{id}"
  }
}