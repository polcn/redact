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

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = aws_kms_key.document_scrubbing_key.key_id
}

output "vpc_id" {
  description = "VPC ID for the document scrubbing infrastructure"
  value       = aws_vpc.document_scrubbing_vpc.id
}