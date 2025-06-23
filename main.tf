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

# KMS Key for encryption
resource "aws_kms_key" "document_scrubbing_key" {
  description             = "KMS key for document scrubbing encryption"
  deletion_window_in_days = 7
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "document-scrubbing-key"
    Environment = var.environment
    Purpose     = "document-scrubbing"
    Project     = "redact"
  }
}

resource "aws_kms_alias" "document_scrubbing_alias" {
  name          = "alias/document-scrubbing"
  target_key_id = aws_kms_key.document_scrubbing_key.key_id
}

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

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "input_documents" {
  bucket = aws_s3_bucket.input_documents.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.document_scrubbing_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_documents" {
  bucket = aws_s3_bucket.processed_documents.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.document_scrubbing_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "quarantine_documents" {
  bucket = aws_s3_bucket.quarantine_documents.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.document_scrubbing_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
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

# VPC for Lambda functions
resource "aws_vpc" "document_scrubbing_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "document-scrubbing-vpc"
    Environment = var.environment
    Project     = "redact"
  }
}

resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.document_scrubbing_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name        = "document-scrubbing-private-1"
    Environment = var.environment
    Project     = "redact"
  }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.document_scrubbing_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name        = "document-scrubbing-private-2"
    Environment = var.environment
    Project     = "redact"
  }
}

# VPC Endpoints for secure access
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.document_scrubbing_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name        = "document-scrubbing-s3-endpoint"
    Environment = var.environment
    Project     = "redact"
  }
}

resource "aws_vpc_endpoint" "textract" {
  vpc_id              = aws_vpc.document_scrubbing_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.textract"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true

  tags = {
    Name        = "document-scrubbing-textract-endpoint"
    Environment = var.environment
    Project     = "redact"
  }
}

resource "aws_vpc_endpoint" "rekognition" {
  vpc_id              = aws_vpc.document_scrubbing_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.rekognition"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true

  tags = {
    Name        = "document-scrubbing-rekognition-endpoint"
    Environment = var.environment
    Project     = "redact"
  }
}

# Route table for private subnets
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.document_scrubbing_vpc.id

  tags = {
    Name        = "document-scrubbing-private-rt"
    Environment = var.environment
    Project     = "redact"
  }
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_subnet_2.id
  route_table_id = aws_route_table.private.id
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoint" {
  name_prefix = "document-scrubbing-vpc-endpoint-"
  vpc_id      = aws_vpc.document_scrubbing_vpc.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.document_scrubbing_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "document-scrubbing-vpc-endpoint-sg"
    Environment = var.environment
    Project     = "redact"
  }
}

# Security group for Lambda functions
resource "aws_security_group" "lambda" {
  name_prefix = "document-scrubbing-lambda-"
  vpc_id      = aws_vpc.document_scrubbing_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "document-scrubbing-lambda-sg"
    Environment = var.environment
    Project     = "redact"
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}