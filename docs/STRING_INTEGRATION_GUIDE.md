# String.com Integration Guide

## Overview

The Redact API provides a secure endpoint for String.com to redact sensitive information from meeting transcripts. The API supports content-based conditional rules, allowing different redaction patterns based on document content.

## API Endpoint

```
POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact
```

## Authentication

Use Bearer token authentication with your API key:

```
Authorization: Bearer sk_live_your_api_key_here
```

## Request Format

### Headers
```
Content-Type: application/json
Authorization: Bearer sk_live_your_api_key_here
```

### Request Body
```json
{
  "text": "Your meeting transcript text here",
  "config": {  // Optional - uses your saved config if not provided
    "conditional_rules": [...]
  }
}
```

### Request Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | The raw transcript text to redact |
| `config` | object | No | Optional configuration override. If not provided, uses your saved configuration |

## Response Format

### Success Response (200 OK)
```json
{
  "success": true,
  "redacted_text": "The cleaned transcript with redactions applied",
  "replacements_made": 15,
  "processing_time_ms": 234
}
```

### Error Response (400/401/500)
```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_CODE"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `AUTH_REQUIRED` | Missing or invalid authorization header |
| `INVALID_API_KEY` | API key is invalid or expired |
| `INVALID_JSON` | Request body contains invalid JSON |
| `MISSING_TEXT` | No text provided in request |
| `TEXT_TOO_LARGE` | Text exceeds 1MB limit |
| `INTERNAL_ERROR` | Server error occurred |

## Configuration

### Default Configuration

Your API key comes with default redaction rules for common patterns:

```json
{
  "conditional_rules": [
    {
      "name": "Choice Hotels",
      "enabled": true,
      "trigger": {
        "contains": ["Choice Hotels", "Choice"],
        "case_sensitive": false
      },
      "replacements": [
        {"find": "Choice Hotels", "replace": "CH"},
        {"find": "Choice", "replace": "CH"}
      ]
    },
    {
      "name": "Cronos",
      "enabled": true,
      "trigger": {
        "contains": ["Cronos"],
        "case_sensitive": false
      },
      "replacements": [
        {"find": "Cronos", "replace": "CR"}
      ]
    }
  ]
}
```

### Custom Configuration

You can override the configuration per request:

```json
{
  "text": "Meeting transcript...",
  "config": {
    "conditional_rules": [
      {
        "name": "Custom Rule",
        "enabled": true,
        "trigger": {
          "contains": ["Acme Corp", "Acme"],
          "case_sensitive": false
        },
        "replacements": [
          {"find": "Acme Corp", "replace": "AC"},
          {"find": "Acme", "replace": "AC"}
        ]
      }
    ],
    "replacements": [
      {"find": "confidential", "replace": "[REDACTED]"}
    ],
    "patterns": {
      "ssn": true,
      "phone": true,
      "email": true
    }
  }
}
```

## Examples

### Basic Request

```bash
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact \
  -H "Authorization: Bearer sk_live_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Meeting with Choice Hotels about the new Cronos project. Contact: john@example.com, 555-123-4567"
  }'
```

### Response
```json
{
  "success": true,
  "redacted_text": "Meeting with CH about the new CR project. Contact: john@example.com, 555-123-4567",
  "replacements_made": 2,
  "processing_time_ms": 45
}
```

### With Custom Configuration

```bash
curl -X POST https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact \
  -H "Authorization: Bearer sk_live_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Meeting with Choice Hotels about confidential pricing",
    "config": {
      "conditional_rules": [{
        "name": "Choice Rule",
        "enabled": true,
        "trigger": {"contains": ["Choice"], "case_sensitive": false},
        "replacements": [{"find": "Choice Hotels", "replace": "CH"}]
      }],
      "replacements": [
        {"find": "confidential", "replace": "[REDACTED]"}
      ]
    }
  }'
```

## Rate Limits

- **Requests**: 1000 per hour
- **Text Size**: Maximum 1MB per request
- **Concurrent Requests**: 10

## Best Practices

1. **Batch Processing**: Send complete transcripts rather than fragments for better context-aware redaction
2. **Configuration Caching**: Use the default configuration when possible to reduce request size
3. **Error Handling**: Implement retry logic with exponential backoff for transient errors
4. **Text Encoding**: Ensure text is properly UTF-8 encoded before sending

## Integration Code Examples

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function redactTranscript(text) {
  try {
    const response = await axios.post(
      'https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact',
      { text },
      {
        headers: {
          'Authorization': 'Bearer sk_live_your_api_key_here',
          'Content-Type': 'application/json'
        }
      }
    );
    
    return response.data.redacted_text;
  } catch (error) {
    console.error('Redaction failed:', error.response?.data || error.message);
    throw error;
  }
}
```

### Python

```python
import requests
import json

def redact_transcript(text):
    url = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/api/string/redact"
    headers = {
        "Authorization": "Bearer sk_live_your_api_key_here",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json={"text": text}, headers=headers)
    
    if response.status_code == 200:
        return response.json()["redacted_text"]
    else:
        raise Exception(f"Redaction failed: {response.json()}")
```

## Support

For API key requests or technical support, please contact the Redact team.

## Changelog

### Version 1.0 (2025-01-15)
- Initial release with content-based conditional rules
- Support for String.com default configuration
- Pattern-based PII detection