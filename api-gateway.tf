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

# POST /documents/upload - Upload document for redaction
resource "aws_api_gateway_method" "upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "AWS_IAM"
  
  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# GET /documents/status/{id} - Check processing status
resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  
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

# Lambda function for API Gateway integration
resource "aws_lambda_function" "api_handler" {
  filename         = "api_lambda.zip"
  function_name    = "redact-api-handler"
  role            = aws_iam_role.api_lambda_role.arn
  handler         = "api_handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256
  
  environment {
    variables = {
      INPUT_BUCKET      = aws_s3_bucket.input_documents.bucket
      PROCESSED_BUCKET  = aws_s3_bucket.processed_documents.bucket
      QUARANTINE_BUCKET = aws_s3_bucket.quarantine_documents.bucket
      CONFIG_BUCKET     = aws_s3_bucket.config_bucket.bucket
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
  ]

  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  stage_name  = var.environment
  
  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "redact_api_stage" {
  deployment_id = aws_api_gateway_deployment.redact_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  stage_name    = var.environment
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      caller        = "$context.identity.caller"
      user          = "$context.identity.user"
      requestTime   = "$context.requestTime"
      httpMethod    = "$context.httpMethod"
      resourcePath  = "$context.resourcePath"
      status        = "$context.status"
      protocol      = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
  
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