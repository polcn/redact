# Redact Project - Claude Instructions

## Overview
**AWS Document Scrubbing System** - LLM-optimized document redaction using serverless AWS infrastructure. Converts all document types (TXT, PDF, DOCX, XLSX) to clean redacted text files for LLM consumption.

**Status**: ✅ Production Ready | **Cost**: $0-5/month | **API**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production

## Quick Commands

### Deploy & Test
```bash
# Deploy complete system
./deploy-improvements.sh

# Update redaction rules
cat > config.json << 'EOF'
{"replacements": [{"find": "ACME Corporation", "replace": "[REDACTED]"}], "case_sensitive": false}
EOF
aws s3 cp config.json s3://redact-config-32a4ee51/

# Test processing
echo "Confidential data from ACME Corporation" > test.txt
aws s3 cp test.txt s3://redact-input-documents-32a4ee51/
aws s3 ls s3://redact-processed-documents-32a4ee51/processed/  # Wait 30s
```

### Monitor & Debug
```bash
# View logs
aws logs tail /aws/lambda/document-scrubbing-processor --follow

# Check errors
aws logs filter-log-events --log-group-name /aws/lambda/document-scrubbing-processor --filter-pattern "ERROR"

# Run tests
./run-tests.sh
```

## Live Resources
```
Input:      redact-input-documents-32a4ee51
Processed:  redact-processed-documents-32a4ee51  
Quarantine: redact-quarantine-documents-32a4ee51
Config:     redact-config-32a4ee51
Lambda:     document-scrubbing-processor, redact-api-handler
API:        https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production
DLQ:        document-scrubbing-dlq
```

## Architecture
```
Upload → API Gateway/S3 → Lambda (Batch) → Text Extraction → Redaction → S3 Output
                                ↓
                         CloudWatch Logs + DLQ
```

## Key Features
- **LLM-Optimized**: All formats → clean text output (90% size reduction)
- **Perfect Redaction**: 100% reliable text replacement
- **Multi-Format**: TXT, PDF, DOCX, XLSX support (all working)
- **Configurable**: S3-based rules, no code changes needed
- **Secure**: AES256 encryption, private buckets, IAM least privilege
- **Cost-Optimized**: $0-5/month (down from $30-40/month)

## Config Format
```json
{
  "replacements": [
    {"find": "CLIENT_NAME", "replace": "Company X"},
    {"find": "John Smith", "replace": "[NAME REDACTED]"}
  ],
  "case_sensitive": false
}
```

## Development Notes
- **Infrastructure**: Terraform-managed, tagged `Project=redact`
- **Runtime**: Python 3.11 Lambda
- **Core Logic**: `lambda_code/lambda_function.py`
- **Testing**: 80%+ coverage with CI/CD pipeline
- **Emergency**: `terraform destroy` removes all resources

## MCP Configuration
**Active MCPs**: AWS Documentation, CDK, Core, Serverless
**Config**: `~/.claude/mcp_settings.json` (persists across sessions)
```json
{
  "mcpServers": {
    "aws-documentation": {"command": "/home/ec2-user/.cache/uv/archive-v0/gPM3Lk9MgQi7qwfpV2LES/bin/awslabs.aws-documentation-mcp-server"},
    "aws-cdk": {"command": "/home/ec2-user/.cache/uv/archive-v0/YT1nEqgRKH2pipWfH3Q9S/bin/awslabs.cdk-mcp-server"},
    "aws-core": {"command": "/home/ec2-user/.cache/uv/archive-v0/NBh4bWKphlKovtgTqTV4Z/bin/awslabs.core-mcp-server"},
    "aws-serverless": {"command": "/home/ec2-user/.cache/uv/archive-v0/4LCGfwR-ADtBe4c_XsvTf/bin/awslabs.aws-serverless-mcp-server"}
  }
}
```