# SSM Parameter for AI Configuration
resource "aws_ssm_parameter" "ai_config" {
  name        = "/redact/ai-config"
  description = "AI summary configuration for document processing"
  type        = "String"
  tier        = "Standard"

  value = jsonencode({
    enabled       = true
    default_model = "anthropic.claude-3-haiku-20240307-v1:0"
    available_models = [
      "anthropic.claude-3-haiku-20240307-v1:0",
      "anthropic.claude-3-sonnet-20240229-v1:0",
      "anthropic.claude-3-5-sonnet-20240620-v1:0",
      "anthropic.claude-3-5-sonnet-20241022-v2:0",
      "anthropic.claude-3-opus-20240229-v1:0",
      "anthropic.claude-instant-v1"
    ]
    admin_override_model = "anthropic.claude-3-opus-20240229-v1:0"
    summary_types = {
      brief = {
        max_tokens  = 150
        temperature = 0.3
        instruction = "Provide a brief 2-3 sentence summary of the key points in this document."
      }
      standard = {
        max_tokens  = 500
        temperature = 0.5
        instruction = "Provide a comprehensive summary of this document, including main topics, key findings, and important details."
      }
      detailed = {
        max_tokens  = 1000
        temperature = 0.7
        instruction = "Provide a detailed analysis and summary of this document, including all major points, supporting details, context, and implications."
      }
    }
    default_summary_type = "standard"
  })

  tags = {
    Name        = "redact-ai-config"
    Environment = var.environment
    Project     = "redact"
  }
}

# IAM policy to allow API Lambda to read AI config
resource "aws_iam_role_policy" "api_lambda_ai_policy" {
  name = "api-lambda-ai-policy"
  role = aws_iam_role.api_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter"
        ]
        Resource = [
          aws_ssm_parameter.ai_config.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-opus-20240229-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-instant-v1"
        ]
      }
    ]
  })
}