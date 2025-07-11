# API Gateway Usage Plans and API Keys for rate limiting

# Usage plan for String.com API
resource "aws_api_gateway_usage_plan" "string_api_plan" {
  name         = "string-api-usage-plan"
  description  = "Usage plan for String.com API with rate limiting"

  api_stages {
    api_id = aws_api_gateway_rest_api.redact_api.id
    stage  = aws_api_gateway_stage.redact_api_stage.stage_name
  }

  quota_settings {
    limit  = 10000  # 10,000 requests per month
    period = "MONTH"
  }

  throttle_settings {
    rate_limit  = 100   # 100 requests per second
    burst_limit = 200   # 200 requests burst capacity
  }

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "string-api-rate-limiting"
  }
}

# API key for String.com
resource "aws_api_gateway_api_key" "string_api_key" {
  name        = "string-api-key"
  description = "API key for String.com redaction service"
  enabled     = true

  tags = {
    Project     = "redact"
    Environment = var.environment
    Service     = "string.com"
  }
}

# Associate API key with usage plan
resource "aws_api_gateway_usage_plan_key" "string_api_key_association" {
  key_id        = aws_api_gateway_api_key.string_api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.string_api_plan.id
}

# Note: The string_redact_post method in api-gateway.tf has been updated
# to include api_key_required = true

# Store the generated API key value in Parameter Store
resource "aws_ssm_parameter" "string_api_gateway_key" {
  name        = "/redact/api-keys/string-api-gateway-key"
  description = "API Gateway API key for String.com rate limiting"
  type        = "SecureString"
  value       = aws_api_gateway_api_key.string_api_key.value

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-gateway-rate-limiting"
  }
}

# CloudWatch alarm for API quota approaching limit
resource "aws_cloudwatch_metric_alarm" "api_quota_alarm" {
  alarm_name          = "string-api-quota-usage-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Count"
  namespace           = "AWS/ApiGateway"
  period              = "3600"  # 1 hour
  statistic           = "Sum"
  threshold           = "8000"  # Alert at 80% of monthly quota
  alarm_description   = "Alert when String.com API usage exceeds 80% of monthly quota"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.redact_api.name
    Stage   = aws_api_gateway_stage.redact_api_stage.stage_name
  }

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-monitoring"
  }
}

# CloudWatch alarm for API throttling
resource "aws_cloudwatch_metric_alarm" "api_throttle_alarm" {
  alarm_name          = "string-api-throttling-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "50"   # More than 50 4XX errors in 5 minutes
  alarm_description   = "Alert when String.com API has high 4XX error rate (likely throttling)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.redact_api.name
    Stage   = aws_api_gateway_stage.redact_api_stage.stage_name
  }

  tags = {
    Project     = "redact"
    Environment = var.environment
    Purpose     = "api-monitoring"
  }
}

# Output the API key ID for reference
output "string_api_key_id" {
  value       = aws_api_gateway_api_key.string_api_key.id
  description = "ID of the String.com API Gateway API key"
}

# Output the usage plan ID
output "string_usage_plan_id" {
  value       = aws_api_gateway_usage_plan.string_api_plan.id
  description = "ID of the String.com usage plan"
}