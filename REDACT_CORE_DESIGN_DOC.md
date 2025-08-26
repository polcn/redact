# Redact Tool - Core Design Document
## General Purpose Document Processing & Redaction Service

### Version: 2.0
### Date: August 25, 2025
### Project: https://github.com/polcn/redact
### Live System: https://redact.9thcube.com

**Purpose**: General-purpose document processing, redaction, and metadata extraction service
**Philosophy**: Keep core functions separate from domain-specific applications (audit, legal, etc.)

---

## 1. Executive Summary

Redact is a serverless document processing service that transforms various file formats into clean, structured data suitable for downstream applications. It focuses on three core capabilities: secure redaction, intelligent summarization, and metadata extraction. The tool is designed to be domain-agnostic, allowing various applications (audit systems, legal review, compliance tools) to consume its API.

## 2. Core Architecture

### 2.1 Current Implementation
```
[User Upload] → [CloudFront] → [API Gateway] → [Lambda] → [S3 Storage]
      ↓              ↓              ↓             ↓           ↓
  (Web UI)      (CDN/WAF)    (Auth/Rate Limit) (Process)  (Isolated)
                                    ↓
                            [AWS Bedrock/Claude]
                                    ↓
                         (Summaries & Metadata)
```

### 2.2 Core Services
- **Document Ingestion**: Multi-format support (PDF, DOCX, XLSX, etc.)
- **Redaction Engine**: Pattern-based PII removal
- **AI Processing**: Summarization and entity extraction
- **Output Preparation**: Structured data ready for vectorization

## 3. Core API Endpoints

### 3.1 Document Processing
```javascript
POST /documents/upload
{
  "file": "base64_encoded_content",
  "filename": "document.pdf",
  "options": {
    "redaction_level": "standard|aggressive|minimal",
    "extract_metadata": true,
    "generate_summary": true
  }
}

Response:
{
  "document_id": "uuid",
  "status": "processed",
  "redacted_content": "markdown_text",
  "metadata": {
    "document_type": "inferred_type",
    "dates_found": ["2025-01-15", "2025-02-20"],
    "entities": {
      "people": ["John Doe"],
      "organizations": ["Acme Corp"],
      "locations": ["New York"]
    },
    "statistics": {
      "pages": 10,
      "word_count": 5000,
      "redactions_made": 15
    }
  },
  "summary": "AI-generated summary...",
  "vector_ready": {
    "text_chunks": ["chunk1", "chunk2"],
    "metadata_structured": {}
  }
}
```

### 3.2 AI Services
```javascript
POST /documents/ai-summary
{
  "content": "document_text",
  "options": {
    "summary_length": "brief|detailed",
    "extract_entities": true,
    "identify_topics": true
  }
}
```

### 3.3 Metadata Operations
```javascript
POST /documents/extract-metadata
{
  "document_id": "uuid",
  "extraction_types": ["dates", "entities", "structure", "topics"]
}

GET /documents/{id}/metadata
Response: Comprehensive metadata object
```

## 4. Core Features

### 4.1 Redaction Capabilities
**Built-in Patterns:**
- Social Security Numbers
- Credit Card Numbers  
- Phone Numbers
- Email Addresses
- IP Addresses
- Driver's License Numbers

**Custom Patterns:**
```javascript
POST /redaction/patterns
{
  "pattern_name": "employee_id",
  "regex": "EMP[0-9]{6}",
  "replacement": "[EMPLOYEE_ID]"
}
```

### 4.2 Document Processing
- **Format Conversion**: Any supported format → Markdown
- **Structure Preservation**: Tables, lists, headings maintained
- **Image Handling**: OCR for scanned documents
- **Encoding**: UTF-8 with proper character handling

### 4.3 Metadata Extraction
**Automatic Extraction:**
- Document properties (author, creation date, title)
- Temporal references (dates, timeframes)
- Named entities (people, places, organizations)
- Document structure (sections, headings, tables)

**Output Format:**
```json
{
  "document_properties": {
    "title": "Annual Report 2025",
    "author": "Finance Department",
    "created": "2025-01-15",
    "modified": "2025-02-20"
  },
  "extracted_entities": {
    "dates": ["2025-01-15", "Q1 2025"],
    "people": ["John Smith", "Jane Doe"],
    "organizations": ["Acme Corp", "Beta LLC"],
    "monetary_values": ["$1.2M", "$500K"],
    "percentages": ["15%", "23.5%"]
  },
  "document_structure": {
    "sections": 5,
    "tables": 3,
    "lists": 8,
    "images": 2
  }
}
```

### 4.4 Vector Preparation
**Chunking Strategies:**
- Semantic chunking (preserve meaning)
- Size-based chunking (token limits)
- Structure-based chunking (sections, paragraphs)

**Output Options:**
```json
{
  "chunks": [
    {
      "text": "chunk_content",
      "metadata": {
        "source_page": 5,
        "section": "Financial Overview",
        "chunk_index": 12
      }
    }
  ],
  "embedding_ready": true,
  "recommended_embedding_model": "text-embedding-ada-002"
}
```

## 5. Security & Privacy

### 5.1 Data Handling
- User-isolated storage (Cognito-based)
- Encryption at rest and in transit
- Automatic data expiration options
- No persistent storage of sensitive data

### 5.2 Compliance Features
- Audit trail of all operations
- Configurable retention policies
- GDPR-compliant data deletion
- Access logging and monitoring

## 6. Integration Guidelines

### 6.1 For Application Developers
```python
# Example: Legal Review System
from redact_client import RedactAPI

client = RedactAPI(api_key="...")

# Process confidential document
result = client.process_document(
    file="contract.pdf",
    redaction_level="aggressive",
    custom_patterns=["CONF-[0-9]{6}"]
)

# Use clean data for further processing
clean_text = result.redacted_content
metadata = result.metadata
```

### 6.2 For Vector Databases
```python
# Prepare for vectorization
chunks = client.prepare_for_vectors(
    document_id=result.document_id,
    chunk_size=512,
    overlap=50
)

# Feed to vector DB
for chunk in chunks:
    vector_db.add(
        text=chunk.text,
        metadata=chunk.metadata
    )
```

## 7. Performance Specifications

### 7.1 Processing Speeds
- PDF: < 500ms per page
- DOCX: < 2 seconds per document
- Image OCR: < 1 second per page
- AI Summary: < 3 seconds per document

### 7.2 Scalability
- Serverless auto-scaling
- Concurrent processing support
- No practical document size limits
- Rate limiting for fair usage

## 8. Extensibility

### 8.1 Plugin Architecture
Future support for:
- Custom redaction plugins
- Industry-specific extractors
- Language-specific processors
- Format-specific handlers

### 8.2 Webhook Support
```javascript
POST /webhooks/configure
{
  "event": "document_processed",
  "url": "https://your-app.com/webhook",
  "secret": "webhook_secret"
}
```

## 9. What Redact Does NOT Do

To maintain focus and simplicity:
- ❌ Domain-specific processing (audit trails, legal citations)
- ❌ Workflow management
- ❌ Long-term document storage
- ❌ User collaboration features
- ❌ Industry-specific compliance checking

These features belong in domain-specific applications that consume the Redact API.

## 10. Success Metrics

- **Availability**: 99.9% uptime
- **Processing Accuracy**: 99%+ redaction accuracy
- **API Response Time**: < 100ms (excluding processing)
- **Customer Satisfaction**: Tool remains simple and focused

---

## Appendix: Supported Formats

### Input Formats
- PDF (including scanned)
- Microsoft Office (DOCX, XLSX, PPTX)
- Plain text (TXT, MD)
- Images (JPG, PNG) with OCR
- Structured data (CSV, JSON)

### Output Formats
- Markdown (primary)
- Structured JSON
- Vector-ready chunks
- Original format with redactions applied

---

*This design ensures Redact remains a focused, high-performance document processing service that can be leveraged by any application requiring clean, structured, and safe document data.*