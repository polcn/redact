# API Key Rotation Infrastructure

# Lambda function for API key rotation
resource "aws_lambda_function" "api_key_rotation" {
  filename      = "api_lambda.zip" # Reuse the same ZIP that includes all API code
  function_name = "redact-api-key-rotation"
  role          = aws_iam_role.api_key_rotation_role.arn
  handler       = "api_key_rotation.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 128

  environment {
    variables = {
      API_GATEWAY_KEY_ID = aws_api_gateway_api_key.string_api_key.id
    }
  }

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-key-rotation"
  }

  depends_on = [data.archive_file.api_lambda_zip]
}

# Lambda function for cleaning up old keys
resource "aws_lambda_function" "api_key_cleanup" {
  filename      = "api_lambda.zip"
  function_name = "redact-api-key-cleanup"
  role          = aws_iam_role.api_key_rotation_role.arn
  handler       = "api_key_rotation.cleanup_old_keys"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 128

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-key-cleanup"
  }

  depends_on = [data.archive_file.api_lambda_zip]
}

# IAM role for API key rotation Lambda
resource "aws_iam_role" "api_key_rotation_role" {
  name = "redact-api-key-rotation-role"

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
    Project     = "redact"
    Environment = var.environment
  }
}

# IAM policy for API key rotation
resource "aws_iam_role_policy" "api_key_rotation_policy" {
  name = "redact-api-key-rotation-policy"
  role = aws_iam_role.api_key_rotation_role.id

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
          "ssm:GetParameter",
          "ssm:PutParameter",
          "ssm:DeleteParameter"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/redact/api-keys/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "apigateway:GET",
          "apigateway:PATCH"
        ]
        Resource = [
          "arn:aws:apigateway:${var.aws_region}::/apikeys/${aws_api_gateway_api_key.string_api_key.id}"
        ]
      }
    ]
  })
}

# EventBridge rule for monthly API key rotation
resource "aws_cloudwatch_event_rule" "api_key_rotation_schedule" {
  name                = "redact-api-key-rotation-schedule"
  description         = "Trigger API key rotation monthly"
  schedule_expression = "rate(30 days)" # Rotate every 30 days

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-key-rotation"
  }
}

# EventBridge rule for cleanup (7 days after rotation)
resource "aws_cloudwatch_event_rule" "api_key_cleanup_schedule" {
  name                = "redact-api-key-cleanup-schedule"
  description         = "Clean up old API keys after grace period"
  schedule_expression = "rate(1 day)" # Check daily if cleanup is needed

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-key-cleanup"
  }
}

# EventBridge target for rotation Lambda
resource "aws_cloudwatch_event_target" "api_key_rotation_target" {
  rule      = aws_cloudwatch_event_rule.api_key_rotation_schedule.name
  target_id = "ApiKeyRotationLambda"
  arn       = aws_lambda_function.api_key_rotation.arn
}

# EventBridge target for cleanup Lambda
resource "aws_cloudwatch_event_target" "api_key_cleanup_target" {
  rule      = aws_cloudwatch_event_rule.api_key_cleanup_schedule.name
  target_id = "ApiKeyCleanupLambda"
  arn       = aws_lambda_function.api_key_cleanup.arn
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "allow_eventbridge_rotation" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_key_rotation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.api_key_rotation_schedule.arn
}

resource "aws_lambda_permission" "allow_eventbridge_cleanup" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_key_cleanup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.api_key_cleanup_schedule.arn
}

# CloudWatch log groups
resource "aws_cloudwatch_log_group" "api_key_rotation_logs" {
  name              = "/aws/lambda/redact-api-key-rotation"
  retention_in_days = 14

  tags = {
    Project     = "redact"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "api_key_cleanup_logs" {
  name              = "/aws/lambda/redact-api-key-cleanup"
  retention_in_days = 14

  tags = {
    Project     = "redact"
    Environment = var.environment
  }
}

# CloudWatch alarm for rotation failures
resource "aws_cloudwatch_metric_alarm" "api_key_rotation_failure" {
  alarm_name          = "api-key-rotation-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when API key rotation fails"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api_key_rotation.function_name
  }

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-monitoring"
  }
}