# System Design Document

## Overview
The Redact system is a secure, serverless document processing pipeline designed to automatically detect and remove sensitive client information from uploaded documents.

## Architecture Decisions

### 1. Security-First Design
**Decision**: Private VPC with no internet access for processing
**Rationale**: 
- Ensures sensitive documents never leave AWS private network
- Prevents data exfiltration
- Meets compliance requirements for sensitive data handling

### 2. Event-Driven Processing
**Decision**: S3 event triggers → Lambda processing
**Rationale**:
- Real-time processing as documents are uploaded
- Serverless = no infrastructure to manage
- Cost-effective (pay per document processed)
- Auto-scaling based on upload volume

### 3. Three-Bucket Strategy
**Decision**: Separate buckets for input, processed, quarantine
**Rationale**:
- Clear data flow and lifecycle management
- Isolation of sensitive vs clean content
- Easy monitoring and auditing
- Compliance with data retention policies

### 4. KMS Encryption Everywhere
**Decision**: Customer-managed KMS key for all data
**Rationale**:
- Full control over encryption keys
- Audit trail for all data access
- Compliance with enterprise security standards
- Key rotation capabilities

## Processing Logic Design

### Document Classification
```
Input Document
    ↓
File Type Detection
    ↓
┌─ Text Files (.txt, .csv) → Direct text processing
├─ PDF Files → Textract + Image analysis  
├─ Images → Rekognition + Textract
└─ Other → Quarantine for manual review
```

### Pattern Detection Strategy
1. **Regex Patterns**: Company name structures
   - `[Company Name] + [Legal Suffix]` (Inc, LLC, Corp, etc.)
   - Technology company patterns
   - Custom client-specific patterns

2. **AI-Powered Detection**:
   - AWS Textract for text extraction from images/PDFs
   - AWS Rekognition for logo detection
   - Confidence thresholds for quarantine decisions

### Redaction Approach
- **Text Redaction**: Replace with `[REDACTED]` tokens
- **Image Redaction**: Black rectangle overlays
- **Metadata Preservation**: Track what was redacted for audit

## Component Design

### Lambda Function Architecture
```python
lambda_handler()
├── download_document()
├── classify_file_type()
├── process_content()
│   ├── extract_text() # Textract for PDFs/images
│   ├── detect_patterns() # Regex + AI
│   ├── detect_logos() # Rekognition
│   └── apply_redactions()
├── upload_result()
└── audit_log()
```

### Data Flow
1. **Upload**: Document → Input Bucket
2. **Trigger**: S3 event → Lambda function
3. **Process**: Extract, analyze, redact
4. **Decision**: Clean → Processed Bucket | Sensitive → Quarantine
5. **Audit**: Log all actions to CloudWatch

### Error Handling Strategy
- **Retry Logic**: 3 attempts for transient failures
- **Dead Letter Queue**: Failed processing for investigation
- **Quarantine**: Unknown file types or processing errors
- **Alerting**: SNS notifications for failures

## Security Architecture

### Network Security
- **VPC Isolation**: Lambda runs in private subnets
- **VPC Endpoints**: Secure access to AWS services
- **No Internet Gateway**: Zero external connectivity
- **Security Groups**: Minimal required access

### Access Control
- **IAM Roles**: Least privilege principle
- **S3 Bucket Policies**: Restricted access patterns
- **KMS Key Policies**: Controlled encryption access
- **Resource Tags**: Consistent access control

### Compliance Features
- **Audit Logging**: CloudTrail for all API calls
- **Data Encryption**: At rest and in transit
- **Access Monitoring**: CloudWatch metrics and logs
- **Retention Policies**: Configurable data lifecycle

## Scalability Design

### Performance Characteristics
- **Throughput**: ~100 documents/minute (estimated)
- **Latency**: 5-30 seconds per document (depending on size/complexity)
- **Concurrency**: 1000 Lambda concurrent executions
- **Storage**: Unlimited S3 scaling

### Cost Optimization
- **Lambda Sizing**: Right-sized memory/timeout
- **S3 Lifecycle**: Automatic archival to cheaper storage classes
- **VPC Endpoints**: Avoid data transfer charges
- **KMS Optimization**: Bulk operations where possible

## Monitoring & Observability

### Key Metrics
- Documents processed per hour/day
- Processing success/failure rates
- Average processing time
- Quarantine rates
- Cost per document

### Alerting Strategy
- High failure rates
- Unusual quarantine volumes
- Processing delays
- Cost threshold breaches

### Dashboards
- Real-time processing status
- Historical trends
- Cost analysis
- Security events

## Future Enhancements

### Phase 3: Advanced AI
- Custom ML models for company-specific patterns
- Natural language processing for context-aware redaction
- Image analysis for complex logo detection

### Phase 4: Enterprise Features
- Multi-tenant support
- Custom redaction rules per client
- API gateway for programmatic access
- Batch processing capabilities

### Phase 5: Compliance
- GDPR right-to-be-forgotten automation
- SOC 2 compliance automation
- Data residency controls
- Advanced audit reporting

## Risk Mitigation

### Technical Risks
- **Lambda Timeouts**: Chunked processing for large files
- **Memory Limits**: Streaming processing for large documents
- **VPC Cold Starts**: Provisioned concurrency for SLA requirements

### Security Risks
- **Data Leakage**: Network isolation + monitoring
- **Access Abuse**: Detailed audit logging + alerting
- **Key Compromise**: Regular key rotation

### Operational Risks
- **Service Limits**: Monitoring + automatic scaling
- **Cost Overruns**: Budget alerts + automatic limits
- **Human Error**: Infrastructure as code + peer review