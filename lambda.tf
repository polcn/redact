# IAM role for Lambda functions
resource "aws_iam_role" "lambda_execution_role" {
  name = "document-scrubbing-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "document-scrubbing-lambda-role"
    Environment = var.environment
    Project     = "redact"
  }
}

# IAM policy for Lambda functions
resource "aws_iam_role_policy" "lambda_policy" {
  name = "document-scrubbing-lambda-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.input_documents.arn}/*",
          "${aws_s3_bucket.processed_documents.arn}/*",
          "${aws_s3_bucket.quarantine_documents.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "rekognition:DetectText",
          "rekognition:DetectLabels"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.document_scrubbing_key.arn
      }
    ]
  })
}

# Simple Lambda function for document processing
resource "aws_lambda_function" "document_processor" {
  filename         = "document_processor.zip"
  function_name    = "document-scrubbing-processor"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.11"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      INPUT_BUCKET      = aws_s3_bucket.input_documents.bucket
      OUTPUT_BUCKET     = aws_s3_bucket.processed_documents.bucket
      QUARANTINE_BUCKET = aws_s3_bucket.quarantine_documents.bucket
      KMS_KEY_ID        = aws_kms_key.document_scrubbing_key.key_id
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.lambda_logs,
    data.archive_file.document_processor_zip
  ]

  tags = {
    Name        = "document-scrubbing-processor"
    Environment = var.environment
    Project     = "redact"
  }
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/document-scrubbing-processor"
  retention_in_days = 14
  kms_key_id        = aws_kms_key.document_scrubbing_key.arn

  tags = {
    Name        = "document-scrubbing-lambda-logs"
    Environment = var.environment
    Project     = "redact"
  }
}

# S3 bucket notification to trigger Lambda
resource "aws_s3_bucket_notification" "input_bucket_notification" {
  bucket = aws_s3_bucket.input_documents.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.document_processor.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

# Lambda permission for S3 to invoke the function
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input_documents.arn
}

# Create Lambda deployment package
data "archive_file" "document_processor_zip" {
  type        = "zip"
  output_path = "document_processor.zip"
  source_dir  = "lambda_code"
}