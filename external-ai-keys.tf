# External AI API Keys Storage (GPT and Gemini)

# SSM Parameter for OpenAI API Key
resource "aws_ssm_parameter" "openai_api_key" {
  name        = "/redact/api-keys/openai-api-key"
  description = "OpenAI API key for GPT models"
  type        = "SecureString"
  value       = "placeholder-will-be-updated-manually"
  
  lifecycle {
    ignore_changes = [value]  # Don't overwrite after manual update
  }

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "openai-api-integration"
  }
}

# SSM Parameter for Google Gemini API Key
resource "aws_ssm_parameter" "gemini_api_key" {
  name        = "/redact/api-keys/gemini-api-key"
  description = "Google API key for Gemini models"
  type        = "SecureString"
  value       = "placeholder-will-be-updated-manually"
  
  lifecycle {
    ignore_changes = [value]  # Don't overwrite after manual update
  }

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "gemini-api-integration"
  }
}

# Update Lambda IAM policy to allow access to these new parameters
# This policy needs to be attached to both Lambda roles
resource "aws_iam_role_policy" "api_lambda_external_ai_keys_access" {
  name = "api-lambda-external-ai-keys-access"
  role = aws_iam_role.api_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.openai_api_key.arn,
          aws_ssm_parameter.gemini_api_key.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [
          data.aws_kms_alias.ssm.target_key_arn
        ]
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Also attach to the document processor Lambda
resource "aws_iam_role_policy" "processor_lambda_external_ai_keys_access" {
  name = "processor-lambda-external-ai-keys-access"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.openai_api_key.arn,
          aws_ssm_parameter.gemini_api_key.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [
          data.aws_kms_alias.ssm.target_key_arn
        ]
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Data source for SSM KMS key
data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

# Output instructions for setting API keys
output "external_ai_keys_setup" {
  value = <<-EOT
    To set your API keys, run these commands:
    
    # Set OpenAI API key:
    aws ssm put-parameter --name "/redact/api-keys/openai-api-key" \
      --value "YOUR_OPENAI_API_KEY" \
      --type SecureString \
      --overwrite
    
    # Set Google Gemini API key:
    aws ssm put-parameter --name "/redact/api-keys/gemini-api-key" \
      --value "YOUR_GEMINI_API_KEY" \
      --type SecureString \
      --overwrite
    
    # Verify API keys are set:
    aws ssm get-parameter --name "/redact/api-keys/openai-api-key" --with-decryption --query 'Parameter.Value' --output text | head -c 10
    aws ssm get-parameter --name "/redact/api-keys/gemini-api-key" --with-decryption --query 'Parameter.Value' --output text | head -c 10
  EOT
}