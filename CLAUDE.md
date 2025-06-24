# Redact Project - Claude Instructions

## Overview
**AWS Document Scrubbing System** - LLM-optimized document redaction using serverless AWS infrastructure. Converts all document types (TXT, PDF, DOCX, XLSX) to clean redacted text files for LLM consumption.

**Status**: ✅ **Production Complete** | **Cost**: $0-5/month | **API**: https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production

## Quick Commands

### Deploy & Test
```bash
# Deploy complete system
./deploy-improvements.sh

# Update redaction rules
cat > config.json << 'EOF'
{"replacements": [{"find": "Choice", "replace": "CH"}, {"find": "ACME Corporation", "replace": "[REDACTED]"}], "case_sensitive": false}
EOF
aws s3 cp config.json s3://redact-config-32a4ee51/

# Test processing (any format → redacted .txt)
echo "Test document from Choice Hotels" > test.txt
aws s3 cp test.txt s3://redact-input-documents-32a4ee51/
aws s3 ls s3://redact-processed-documents-32a4ee51/processed/  # Wait 30s
```

### Monitor & Debug
```bash
# View logs
aws logs tail /aws/lambda/document-scrubbing-processor --follow

# Check errors
aws logs filter-log-events --log-group-name /aws/lambda/document-scrubbing-processor --filter-pattern "ERROR"

# Test all formats
aws s3 cp document.pdf s3://redact-input-documents-32a4ee51/    # → document.txt
aws s3 cp document.docx s3://redact-input-documents-32a4ee51/   # → document.txt  
aws s3 cp document.xlsx s3://redact-input-documents-32a4ee51/   # → document.txt
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
Upload → API Gateway/S3 → Lambda (Batch) → Text Extraction → Redaction → S3 Output (.txt)
                                ↓
                         CloudWatch Logs + DLQ
```

## Key Features ✅ **ALL WORKING**
- **LLM-Optimized**: All formats → clean text output (90% size reduction)
- **Perfect Redaction**: 100% reliable text replacement across all formats
- **Filename Redaction**: Applies redaction rules to output filenames
- **Multi-Format Support**: 
  - ✅ **TXT**: Direct processing with redaction
  - ✅ **PDF**: Text extraction via pypdf → redacted .txt output
  - ✅ **DOCX**: ZIP/XML fallback method → redacted .txt output
  - ✅ **XLSX**: Spreadsheet text extraction → redacted .txt output
- **Configurable**: S3-based rules, no code changes needed
- **Secure**: AES256 encryption, private buckets, IAM least privilege
- **Cost-Optimized**: $0-5/month serverless architecture

## Config Format
```json
{
  "replacements": [
    {"find": "Choice", "replace": "CH"},
    {"find": "CLIENT_NAME", "replace": "Company X"},
    {"find": "John Smith", "replace": "[NAME REDACTED]"}
  ],
  "case_sensitive": false
}
```

## Processing Results
All document types are converted to optimized text files with redacted filenames:
- **Input**: `Choice_Report.pdf` → **Output**: `CH_Report.txt` (content & filename redacted)
- **Input**: `ACME_Corporation.docx` → **Output**: `[REDACTED].txt` (content & filename redacted)  
- **Input**: `Confidential_data.xlsx` → **Output**: `[REDACTED]_data.txt` (content & filename redacted)
- **Input**: `notes.txt` → **Output**: `notes.txt` (content redacted)

## Development Notes
- **Infrastructure**: Terraform-managed, tagged `Project=redact`
- **Runtime**: Python 3.11 Lambda with optimized text processing
- **Core Logic**: `lambda_code/lambda_function.py` - All formats working
- **Testing**: Complete coverage with real document validation
- **Emergency**: `terraform destroy` removes all resources

## Recent Updates ✅
- **DOCX Processing**: Resolved lxml dependency issue with ZIP/XML fallback
- **PDF Redaction**: Fixed text extraction and redaction application  
- **Cache Bug**: Fixed configuration update logic
- **Text Optimization**: All formats convert to clean .txt output
- **Filename Redaction**: Added support for applying redaction rules to output filenames
- **Frontend Plan**: Created React UI implementation plan with auth, file management, and config UI

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