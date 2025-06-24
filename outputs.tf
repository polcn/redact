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

# Cost-optimized: KMS and VPC outputs removed as these resources were eliminated