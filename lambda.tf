# SQS Dead Letter Queue for failed Lambda invocations
resource "aws_sqs_queue" "lambda_dlq" {
  name                      = "document-scrubbing-dlq"
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 300     # 5 minutes

  tags = {
    Name        = "document-scrubbing-dlq"
    Environment = var.environment
    Project     = "redact"
  }
}

# CloudWatch alarm for DLQ messages
resource "aws_cloudwatch_metric_alarm" "dlq_alarm" {
  alarm_name          = "document-scrubbing-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "Alert when messages are in the DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.lambda_dlq.name
  }

  tags = {
    Name        = "document-scrubbing-dlq-alarm"
    Environment = var.environment
    Project     = "redact"
  }
}

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
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.input_documents.arn}/*",
          "${aws_s3_bucket.processed_documents.arn}/*",
          "${aws_s3_bucket.quarantine_documents.arn}/*",
          "${aws_s3_bucket.config_bucket.arn}/*"
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
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.lambda_dlq.arn
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
      CONFIG_BUCKET     = aws_s3_bucket.config_bucket.bucket
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
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