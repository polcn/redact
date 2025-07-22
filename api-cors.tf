# CORS Configuration for API Gateway

# OPTIONS method for /documents/upload
resource "aws_api_gateway_method" "upload_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "upload_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "upload_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
  
  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "upload_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = aws_api_gateway_method_response.upload_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /documents/batch-download
resource "aws_api_gateway_method" "batch_download_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.batch_download.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "batch_download_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.batch_download.id
  http_method = aws_api_gateway_method.batch_download_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "batch_download_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.batch_download.id
  http_method = aws_api_gateway_method.batch_download_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
  
  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "batch_download_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.batch_download.id
  http_method = aws_api_gateway_method.batch_download_options.http_method
  status_code = aws_api_gateway_method_response.batch_download_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /documents/combine
resource "aws_api_gateway_method" "combine_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.combine.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "combine_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.combine.id
  http_method = aws_api_gateway_method.combine_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "combine_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.combine.id
  http_method = aws_api_gateway_method.combine_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
  
  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "combine_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.combine.id
  http_method = aws_api_gateway_method.combine_options.http_method
  status_code = aws_api_gateway_method_response.combine_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /documents/status/{id}
resource "aws_api_gateway_method" "status_id_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "status_id_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_id_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "status_id_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_id_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "status_id_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_id_options.http_method
  status_code = aws_api_gateway_method_response.status_id_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /user/files
resource "aws_api_gateway_method" "user_files_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.user_files.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "user_files_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.user_files.id
  http_method = aws_api_gateway_method.user_files_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "user_files_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.user_files.id
  http_method = aws_api_gateway_method.user_files_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "user_files_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.user_files.id
  http_method = aws_api_gateway_method.user_files_options.http_method
  status_code = aws_api_gateway_method_response.user_files_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /api/config
resource "aws_api_gateway_method" "api_config_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.api_config.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "api_config_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_config.id
  http_method = aws_api_gateway_method.api_config_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "api_config_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_config.id
  http_method = aws_api_gateway_method.api_config_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "api_config_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_config.id
  http_method = aws_api_gateway_method.api_config_options.http_method
  status_code = aws_api_gateway_method_response.api_config_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,PUT,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /documents/{id}
resource "aws_api_gateway_method" "documents_id_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.documents_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "documents_id_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_id_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "documents_id_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_id_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "documents_id_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.documents_id.id
  http_method = aws_api_gateway_method.documents_id_options.http_method
  status_code = aws_api_gateway_method_response.documents_id_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /api/string/redact
resource "aws_api_gateway_method" "string_redact_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.api_string_redact.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "string_redact_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_string_redact.id
  http_method = aws_api_gateway_method.string_redact_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "string_redact_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_string_redact.id
  http_method = aws_api_gateway_method.string_redact_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "string_redact_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_string_redact.id
  http_method = aws_api_gateway_method.string_redact_options.http_method
  status_code = aws_api_gateway_method_response.string_redact_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS method for /api/test-redaction
resource "aws_api_gateway_method" "test_redaction_options" {
  rest_api_id   = aws_api_gateway_rest_api.redact_api.id
  resource_id   = aws_api_gateway_resource.api_test_redaction.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "test_redaction_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_test_redaction.id
  http_method = aws_api_gateway_method.test_redaction_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "test_redaction_options_200" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_test_redaction.id
  http_method = aws_api_gateway_method.test_redaction_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "test_redaction_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.redact_api.id
  resource_id = aws_api_gateway_resource.api_test_redaction.id
  http_method = aws_api_gateway_method.test_redaction_options.http_method
  status_code = aws_api_gateway_method_response.test_redaction_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}