# AWS Cognito User Pool for authentication

# User Pool
resource "aws_cognito_user_pool" "redact_users" {
  name = "redact-users-${var.environment}"

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Username attributes
  username_attributes = ["email"]
  
  # Auto-verified attributes
  auto_verified_attributes = ["email"]

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # MFA configuration
  mfa_configuration = "OPTIONAL"
  
  software_token_mfa_configuration {
    enabled = true
  }

  # User attribute schema
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    mutable                  = true
    required                 = true
    developer_only_attribute = false
    
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                     = "role"
    attribute_data_type      = "String"
    mutable                  = true
    required                 = false
    developer_only_attribute = false
    
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Lambda triggers for custom authentication flow
  lambda_config {
    pre_sign_up = aws_lambda_function.cognito_pre_signup.arn
  }

  tags = {
    Project = var.project_name
    Environment = var.environment
  }
}

# User Pool Client
resource "aws_cognito_user_pool_client" "redact_web_client" {
  name         = "redact-web-client"
  user_pool_id = aws_cognito_user_pool.redact_users.id

  # OAuth flows
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                   = ["code", "implicit"]
  allowed_oauth_scopes                  = ["email", "openid", "profile"]
  
  # Callback URLs
  callback_urls = [
    "http://localhost:3000",
    "https://redact.9thcube.com"
  ]
  
  logout_urls = [
    "http://localhost:3000",
    "https://redact.9thcube.com"
  ]

  # Client settings
  generate_secret                      = false
  refresh_token_validity               = 30
  access_token_validity                = 1
  id_token_validity                    = 1
  enable_token_revocation              = true
  prevent_user_existence_errors        = "ENABLED"
  
  # Auth flows
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Read/write attributes
  read_attributes = [
    "email",
    "email_verified",
    "custom:role"
  ]
  
  write_attributes = [
    "email",
    "custom:role"
  ]
}

# Pre-signup Lambda to control user registration
resource "aws_lambda_function" "cognito_pre_signup" {
  filename         = "cognito_lambda.zip"
  function_name    = "redact-cognito-pre-signup"
  role            = aws_iam_role.cognito_lambda_role.arn
  handler         = "pre_signup.lambda_handler"
  runtime         = "python3.11"
  timeout         = 5
  
  environment {
    variables = {
      ALLOWED_DOMAINS = "gmail.com,outlook.com,yahoo.com,9thcube.com"  # Configure allowed email domains
      AUTO_CONFIRM    = "false"
    }
  }
  
  tags = {
    Project = var.project_name
    Environment = var.environment
  }
  
  depends_on = [data.archive_file.cognito_lambda_zip]
}

# Create Cognito Lambda ZIP file
data "archive_file" "cognito_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cognito_code"
  output_path = "${path.module}/cognito_lambda.zip"
}

# IAM role for Cognito Lambda
resource "aws_iam_role" "cognito_lambda_role" {
  name = "redact-cognito-lambda-role"

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
    Project = var.project_name
    Environment = var.environment
  }
}

# Basic execution role for Cognito Lambda
resource "aws_iam_role_policy_attachment" "cognito_lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.cognito_lambda_role.name
}

# Lambda permission for Cognito to invoke
resource "aws_lambda_permission" "cognito_pre_signup" {
  statement_id  = "AllowExecutionFromCognito"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognito_pre_signup.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.redact_users.arn
}

# Outputs
output "user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.redact_users.id
}

output "user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.redact_web_client.id
}

output "cognito_domain" {
  description = "Cognito domain for hosted UI"
  value       = "https://${aws_cognito_user_pool.redact_users.id}.auth.${var.aws_region}.amazoncognito.com"
}