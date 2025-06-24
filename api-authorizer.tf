# Cognito Authorizer for API Gateway

resource "aws_api_gateway_authorizer" "cognito_authorizer" {
  name                   = "redact-cognito-authorizer"
  type                   = "COGNITO_USER_POOLS"
  rest_api_id           = aws_api_gateway_rest_api.redact_api.id
  provider_arns         = [aws_cognito_user_pool.redact_users.arn]
  identity_source       = "method.request.header.Authorization"
}

# Update method authorizations to use Cognito
# This will be applied via separate updates to api-gateway.tf