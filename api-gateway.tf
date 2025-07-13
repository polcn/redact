# API Gateway for REST access to document redaction system

# API Gateway REST API
resource "aws_api_gateway_rest_api" "redact_api" {
  name        = "document-redaction-api"
  description = "REST API for document redaction system"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = {
    Project = "redact"
    Environment = var.environment
  }
}

# API Gateway Resource - /documents
resource "aws_api_gateway_resource" "documents" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_rest_api.redact_api.root_resource_id
  path_part   = "documents"
}

# API Gateway Resource - /documents/upload
resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.documents.id
  path_part   = "upload"
}

# API Gateway Resource - /documents/batch-download
resource "aws_api_gateway_resource" "batch_download" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.documents.id
  path_part   = "batch-download"
}

# API Gateway Resource - /documents/status
resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.documents.id
  path_part   = "status"
}

# API Gateway Resource - /documents/status/{id}
resource "aws_api_gateway_resource" "status_id" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.status.id
  path_part   = "{id}"
}

# API Gateway Resource - /health
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_rest_api.redact_api.root_resource_id
  path_part   = "health"
}

# API Gateway Resource - /user
resource "aws_api_gateway_resource" "user" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_rest_api.redact_api.root_resource_id
  path_part   = "user"
}

# API Gateway Resource - /user/files
resource "aws_api_gateway_resource" "user_files" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.user.id
  path_part   = "files"
}

# API Gateway Resource - /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_rest_api.redact_api.root_resource_id
  path_part   = "api"
}

# API Gateway Resource - /api/config
resource "aws_api_gateway_resource" "api_config" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "config"
}

# API Gateway Resource - /api/string
resource "aws_api_gateway_resource" "api_string" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "string"
}

# API Gateway Resource - /api/string/redact
resource "aws_api_gateway_resource" "api_string_redact" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.api_string.id
  path_part   = "redact"
}

# API Gateway Resource - /api/test-redaction
resource "aws_api_gateway_resource" "api_test_redaction" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "test-redaction"
}

# API Gateway Resource - /documents/{id} for DELETE
resource "aws_api_gateway_resource" "documents_id" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  parent_id   = aws_api_gateway_resource.documents.id
  path_part   = "{id}"
}

# POST /documents/upload - Upload document for redaction
resource "aws_api_gateway_method" "upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
  
  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# POST /documents/batch-download - Download multiple files as ZIP
resource "aws_api_gateway_method" "batch_download_post" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.batch_download.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
  
  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# GET /documents/status/{id} - Check processing status
resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
  
  request_parameters = {
    "method.request.path.id" = true
  }
}

# GET /health - Health check endpoint
resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

# GET /user/files - List user's files
resource "aws_api_gateway_method" "user_files_get" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.user_files.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
}

# GET /api/config - Get redaction configuration
resource "aws_api_gateway_method" "api_config_get" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.api_config.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
}

# PUT /api/config - Update redaction configuration
resource "aws_api_gateway_method" "api_config_put" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.api_config.id
  http_method   = "PUT"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
  
  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# DELETE /documents/{id} - Delete document
resource "aws_api_gateway_method" "documents_delete" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.documents_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
  
  request_parameters = {
    "method.request.path.id" = true
  }
}

# POST /api/string/redact - String.com redaction endpoint
resource "aws_api_gateway_method" "string_redact_post" {
  rest_api_id      = aws_api_gateway_rest_api.redact_api.id
  resource_id      = aws_api_gateway_resource.api_string_redact.id
  http_method      = "POST"
  authorization    = "NONE"  # Uses custom API key authentication
  api_key_required = true    # Require API Gateway API key for rate limiting
  
  request_parameters = {
    "method.request.header.Authorization" = true  # Bearer token for our validation
    "method.request.header.Content-Type"  = true
    "method.request.header.x-api-key"     = true  # API Gateway API key
  }
}

# POST /api/test-redaction - Test redaction endpoint for UI
resource "aws_api_gateway_method" "test_redaction_post" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.api_test_redaction.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_authorizer.id
  
  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# Lambda function for API Gateway integration
resource "aws_lambda_function" "api_handler" {
  filename         = "api_lambda.zip"
  function_name    = "redact-api-handler"
  role            = aws_iam_role.api_lambda_role.arn
  handler         = "api_handler_simple.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256
  
  environment {
    variables = {
      INPUT_BUCKET      = aws_s3_bucket.input_documents.bucket
      PROCESSED_BUCKET  = aws_s3_bucket.processed_documents.bucket
      QUARANTINE_BUCKET = aws_s3_bucket.quarantine_documents.bucket
      CONFIG_BUCKET     = aws_s3_bucket.config_bucket.bucket
      USER_POOL_ID      = aws_cognito_user_pool.redact_users.id
      STAGE             = var.environment
    }
  }
  
  tags = {
    Project = "redact"
    Environment = var.environment
  }
  
  depends_on = [data.archive_file.api_lambda_zip]
}

# Create API Lambda ZIP file
data "archive_file" "api_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/api_code"
  output_path = "${path.module}/api_lambda.zip"
}

# IAM role for API Lambda
resource "aws_iam_role" "api_lambda_role" {
  name = "redact-api-lambda-role"

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
    Project = "redact"
    Environment = var.environment
  }
}

# IAM policy for API Lambda
resource "aws_iam_role_policy" "api_lambda_policy" {
  name = "redact-api-lambda-policy"
  role = aws_iam_role.api_lambda_role.id

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
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.input_documents.arn}",
          "${aws_s3_bucket.input_documents.arn}/*",
          "${aws_s3_bucket.processed_documents.arn}",
          "${aws_s3_bucket.processed_documents.arn}/*",
          "${aws_s3_bucket.quarantine_documents.arn}",
          "${aws_s3_bucket.quarantine_documents.arn}/*",
          "${aws_s3_bucket.config_bucket.arn}",
          "${aws_s3_bucket.config_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/redact/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# API Gateway integrations
resource "aws_api_gateway_integration" "upload_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "batch_download_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.batch_download.id
  http_method = aws_api_gateway_method.batch_download_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "status_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "health_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "user_files_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.user_files.id
  http_method = aws_api_gateway_method.user_files_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "api_config_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_config.id
  http_method = aws_api_gateway_method.api_config_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "api_config_put_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_config.id
  http_method = aws_api_gateway_method.api_config_put.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "documents_delete_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_delete.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "string_redact_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_string_redact.id
  http_method = aws_api_gateway_method.string_redact_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

resource "aws_api_gateway_integration" "test_redaction_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_test_redaction.id
  http_method = aws_api_gateway_method.test_redaction_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.api_handler.invoke_arn
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.redact_api.execution_arn}/*/*"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "redact_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.upload_integration,
    aws_api_gateway_integration.status_integration,
    aws_api_gateway_integration.health_integration,
    aws_api_gateway_integration.user_files_integration,
    aws_api_gateway_integration.api_config_get_integration,
    aws_api_gateway_integration.api_config_put_integration,
    aws_api_gateway_integration.documents_delete_integration,
    # CORS integrations
    aws_api_gateway_integration_response.upload_options_integration_response,
    aws_api_gateway_integration_response.status_id_options_integration_response,
    aws_api_gateway_integration_response.user_files_options_integration_response,
    aws_api_gateway_integration_response.api_config_options_integration_response,
    aws_api_gateway_integration_response.documents_id_options_integration_response,
  ]

  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  stage_name  = var.environment
  
  lifecycle {
    create_before_destroy = true
  }
  
  # Force new deployment when configuration changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.upload.id,
      aws_api_gateway_method.upload_post.id,
      aws_api_gateway_integration.upload_integration.id,
      aws_api_gateway_authorizer.cognito_authorizer.id,
      timestamp(),
    ]))
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "redact_api_stage" {
  deployment_id = aws_api_gateway_deployment.redact_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  stage_name    = var.environment
  
  # Note: Commenting out access logs for now - requires CloudWatch Logs role ARN in account settings
  # access_log_settings {
  #   destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
  #   format = jsonencode({
  #     requestId      = "$context.requestId"
  #     ip            = "$context.identity.sourceIp"
  #     caller        = "$context.identity.caller"
  #     user          = "$context.identity.user"
  #     requestTime   = "$context.requestTime"
  #     httpMethod    = "$context.httpMethod"
  #     resourcePath  = "$context.resourcePath"
  #     status        = "$context.status"
  #     protocol      = "$context.protocol"
  #     responseLength = "$context.responseLength"
  #   })
  # }
  
  tags = {
    Project = "redact"
    Environment = var.environment
  }
}

# CloudWatch log group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/document-redaction-api"
  retention_in_days = 14
  
  tags = {
    Project = "redact"
    Environment = var.environment
  }
}

# API Gateway method responses
resource "aws_api_gateway_method_response" "upload_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "status_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_get.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "health_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "user_files_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.user_files.id
  http_method = aws_api_gateway_method.user_files_get.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "api_config_get_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_config.id
  http_method = aws_api_gateway_method.api_config_get.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "api_config_put_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_config.id
  http_method = aws_api_gateway_method.api_config_put.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "documents_delete_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_delete.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}