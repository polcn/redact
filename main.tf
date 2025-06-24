terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Additional provider for us-east-1 (required for CloudFront ACM certificates)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Cost-optimized: Using AWS-managed encryption instead of customer-managed KMS
# This saves $1/month and is still secure for most use cases

# S3 Buckets
resource "aws_s3_bucket" "input_documents" {
  bucket = "${var.project_name}-input-documents-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "input-documents"
    Environment = var.environment
    Purpose     = "document-scrubbing"
    Project     = "redact"
  }
}

resource "aws_s3_bucket" "processed_documents" {
  bucket = "${var.project_name}-processed-documents-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "processed-documents"
    Environment = var.environment
    Purpose     = "document-scrubbing"
    Project     = "redact"
  }
}

resource "aws_s3_bucket" "quarantine_documents" {
  bucket = "${var.project_name}-quarantine-documents-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "quarantine-documents"
    Environment = var.environment
    Purpose     = "document-scrubbing"
    Project     = "redact"
  }
}

resource "aws_s3_bucket" "config_bucket" {
  bucket = "${var.project_name}-config-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "config-bucket"
    Environment = var.environment
    Purpose     = "document-scrubbing"
    Project     = "redact"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket encryption (AWS-managed for cost optimization)
resource "aws_s3_bucket_server_side_encryption_configuration" "input_documents" {
  bucket = aws_s3_bucket.input_documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_documents" {
  bucket = aws_s3_bucket.processed_documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "quarantine_documents" {
  bucket = aws_s3_bucket.quarantine_documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config_bucket" {
  bucket = aws_s3_bucket.config_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "input_documents" {
  bucket = aws_s3_bucket.input_documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "processed_documents" {
  bucket = aws_s3_bucket.processed_documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket public access block
resource "aws_s3_bucket_public_access_block" "input_documents" {
  bucket = aws_s3_bucket.input_documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "processed_documents" {
  bucket = aws_s3_bucket.processed_documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "quarantine_documents" {
  bucket = aws_s3_bucket.quarantine_documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "config_bucket" {
  bucket = aws_s3_bucket.config_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Lifecycle policies for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "input_documents" {
  bucket = aws_s3_bucket.input_documents.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "processed_documents" {
  bucket = aws_s3_bucket.processed_documents.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "quarantine_documents" {
  bucket = aws_s3_bucket.quarantine_documents.id

  rule {
    id     = "keep-for-review"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 180
    }
  }
}

# Cost-optimized: Removed VPC infrastructure to save ~$22/month
# Lambda will run in public subnets with strong IAM policies for security
# This is acceptable for free tier usage and still secure with proper S3 bucket policies

# Data sources
data "aws_caller_identity" "current" {}