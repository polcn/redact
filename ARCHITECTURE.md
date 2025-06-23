# Architecture Documentation

## System Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │    │   AWS Cloud      │    │   Outputs       │
│                 │    │   (VPC Isolated) │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Documents   │ │    │ │   Lambda     │ │    │ │ Clean Docs  │ │
│ │ (PDFs, etc) │ ├───►│ │ Processing   │ ├───►│ │ (Redacted)  │ │
│ └─────────────┘ │    │ │              │ │    │ └─────────────┘ │
│                 │    │ └──────────────┘ │    │                 │
└─────────────────┘    │        │         │    │ ┌─────────────┐ │
                       │        ▼         │    │ │ Quarantine  │ │
                       │ ┌──────────────┐ │    │ │ (Sensitive) │ │
                       │ │ AI Services  │ │    │ └─────────────┘ │
                       │ │ Textract +   │ │    └─────────────────┘
                       │ │ Rekognition  │ │
                       │ └──────────────┘ │
                       └──────────────────┘
```

## Component Architecture

### 1. Data Layer
```
Input Layer:
├── S3 Input Bucket (redact-input-documents-*)
│   ├── Event Notifications → Lambda Trigger
│   ├── Versioning Enabled
│   └── KMS Encryption

Processing Layer:
├── Lambda Function (document-scrubbing-processor)
│   ├── Python 3.11 Runtime
│   ├── 1024MB Memory / 300s Timeout
│   └── VPC Isolated (Future Enhancement)

AI Services:
├── AWS Textract (Text Extraction)
├── AWS Rekognition (Logo Detection)
└── Regex Engine (Pattern Matching)

Output Layer:
├── S3 Processed Bucket (redact-processed-documents-*)
├── S3 Quarantine Bucket (redact-quarantine-documents-*)
└── CloudWatch Logs (Audit Trail)
```

### 2. Security Architecture
```
Network Security:
├── VPC (vpc-09b9d34d87641d465)
│   ├── Private Subnets (2 AZ)
│   ├── No Internet Gateway
│   └── VPC Endpoints for AWS Services

Access Control:
├── IAM Roles (Least Privilege)
├── S3 Bucket Policies
├── KMS Key Policies
└── Resource-Based Permissions

Encryption:
├── KMS Customer Managed Key
├── S3 Server-Side Encryption
├── Lambda Environment Variables
└── CloudWatch Logs Encryption
```

### 3. Processing Pipeline
```
Document Upload:
│
├── S3 Event Trigger
│   └── Lambda Invocation
│
├── Document Classification
│   ├── File Type Detection
│   ├── Size Validation
│   └── Format Support Check
│
├── Content Extraction
│   ├── Text Files → Direct Processing
│   ├── PDFs → Textract + PyMuPDF
│   ├── Images → Textract + Rekognition
│   └── Unknown → Quarantine
│
├── Pattern Detection
│   ├── Regex Patterns (Company Names)
│   ├── AI Detection (Context Aware)
│   └── Logo Recognition (Visual)
│
├── Redaction Process
│   ├── Text Replacement
│   ├── Image Overlay
│   └── Metadata Preservation
│
└── Output Decision
    ├── Clean → Processed Bucket
    ├── Sensitive → Quarantine Bucket
    └── Error → Dead Letter Queue
```

## Data Flow Diagrams

### 1. Happy Path Flow
```
[Upload] → [S3 Input] → [Lambda Trigger] → [Process] → [Clean Output]
                                              │
                                              ├── Textract
                                              ├── Rekognition  
                                              └── Regex Engine
```

### 2. Quarantine Flow
```
[Upload] → [S3 Input] → [Lambda] → [Sensitive Detected] → [S3 Quarantine]
                          │                                      │
                          └── [Audit Log] → [CloudWatch] ← ──────┘
```

### 3. Error Handling Flow
```
[Processing Error] → [Retry Logic] → [Dead Letter Queue] → [Manual Review]
       │                   │               │
       ├── [CloudWatch] ───┤               └── [SNS Alert]
       └── [Audit Log] ────┘
```

## Technology Stack

### Infrastructure as Code
- **Terraform**: Infrastructure provisioning
- **Git**: Version control and change tracking
- **AWS Provider**: Cloud resource management

### Compute & Processing
- **AWS Lambda**: Serverless computing platform
- **Python 3.11**: Runtime environment
- **PyMuPDF**: PDF processing library
- **Boto3**: AWS SDK for Python

### AI & ML Services
- **AWS Textract**: Document text extraction
- **AWS Rekognition**: Image and logo analysis
- **Regex Engine**: Pattern matching
- **Custom ML Models**: Future enhancement

### Storage & Database
- **Amazon S3**: Object storage for documents
- **S3 Versioning**: Document version control
- **S3 Lifecycle**: Automated data management
- **CloudWatch Logs**: Audit and monitoring data

### Security & Compliance
- **AWS KMS**: Encryption key management
- **IAM**: Identity and access management
- **VPC**: Network isolation
- **CloudTrail**: API audit logging

### Monitoring & Observability
- **CloudWatch**: Metrics and monitoring
- **CloudWatch Logs**: Application logging
- **SNS**: Alerting and notifications
- **AWS Config**: Configuration compliance

## Deployment Architecture

### Environment Strategy
```
Development:
├── Single Region (us-east-1)
├── Reduced Retention Periods
└── Cost-Optimized Sizing

Production:
├── Multi-AZ Deployment
├── Enhanced Monitoring
├── Backup & Recovery
└── Performance Optimized
```

### CI/CD Pipeline (Future)
```
Git Commit → Terraform Plan → Security Scan → Deploy → Test → Monitor
     │             │              │            │       │       │
     ├── Linting ──┤              │            │       │       └── Rollback
     └── Tests ────┤              │            │       └── Integration Tests
                   └── Policy ────┘            └── Blue/Green Deploy
```

## Scalability Considerations

### Current Limits
- **Lambda Concurrency**: 1000 concurrent executions
- **Processing Rate**: ~100 documents/minute
- **File Size**: 10MB max per Lambda execution
- **Memory**: 1024MB per function

### Scaling Strategies
```
Horizontal Scaling:
├── Lambda Auto-scaling (Concurrent Executions)
├── S3 Unlimited Storage
└── VPC Endpoint Scaling

Vertical Scaling:
├── Lambda Memory Increase
├── Timeout Adjustment
└── Batch Processing Implementation

Performance Optimization:
├── Provisioned Concurrency
├── Connection Pooling
├── Caching Strategies
└── Asynchronous Processing
```

## Security Model

### Defense in Depth
```
Layer 1: Network (VPC, Private Subnets, No IGW)
Layer 2: Identity (IAM Roles, Policies)
Layer 3: Application (Input Validation, Error Handling)
Layer 4: Data (KMS Encryption, S3 Policies)
Layer 5: Monitoring (CloudTrail, CloudWatch)
```

### Threat Model
- **Data Exfiltration**: VPC isolation, no internet access
- **Unauthorized Access**: IAM least privilege, MFA
- **Data Tampering**: Versioning, audit logs, checksums
- **Service Abuse**: Rate limiting, cost monitoring
- **Key Compromise**: Regular rotation, access monitoring

## Cost Architecture

### Cost Components
```
Fixed Costs:
├── VPC Endpoints: ~$22/month
├── NAT Gateway: $0 (private only)
└── KMS Key: $1/month

Variable Costs:
├── Lambda Execution: $0.0000166667 per GB-second
├── S3 Storage: $0.023 per GB/month
├── S3 Requests: $0.0004 per 1000 requests
└── Data Transfer: $0 (VPC endpoints)

Estimated Monthly (1000 docs):
├── Lambda: ~$5-10
├── S3 Storage: ~$2-5
├── AI Services: ~$10-20
└── Total: ~$40-60
```

### Cost Optimization
- **S3 Intelligent Tiering**: Automatic cost optimization
- **Lambda Right-sizing**: Memory and timeout optimization
- **VPC Endpoints**: Eliminate data transfer charges
- **Reserved Capacity**: For predictable workloads

## Disaster Recovery

### RTO/RPO Targets
- **RTO (Recovery Time Objective)**: 1 hour
- **RPO (Recovery Point Objective)**: 15 minutes
- **Availability Target**: 99.9%

### Backup Strategy
```
Data Backup:
├── S3 Cross-Region Replication
├── Version Retention (30 days)
└── Point-in-Time Recovery

Infrastructure Backup:
├── Terraform State in S3
├── Infrastructure as Code
└── Automated Rebuilds

Configuration Backup:
├── Parameter Store
├── Environment Variables
└── IAM Policies
```

## Compliance Framework

### Data Protection
- **Encryption at Rest**: All data encrypted with KMS
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Data Residency**: Single region deployment
- **Data Retention**: Configurable lifecycle policies

### Audit Requirements
- **Access Logging**: All API calls logged
- **Change Tracking**: Infrastructure changes via Terraform
- **Processing Logs**: Document processing audit trail
- **Compliance Reports**: Automated generation capability