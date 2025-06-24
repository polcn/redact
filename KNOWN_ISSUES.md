# Known Issues

## Configuration Cache Bug (Critical)

**Issue**: Lambda configuration caching logic has a bug in line 334 of `lambda_function.py` that prevents config updates from being applied.

**Current Logic**: `last_modified <= _config_last_modified` 
**Should Be**: `last_modified == _config_last_modified`

**Impact**: Configuration changes uploaded to S3 are not reflected in document processing until Lambda cold start.

**Workaround**: Force Lambda cold start by updating the function code or wait for natural cold start.

## DOCX Processing Issues

**Issue**: 14KB DOCX files are not being processed (neither in processed nor quarantine buckets).

**Possible Causes**:
1. Missing `python-docx` library in Lambda deployment package
2. File extension validation issue
3. Silent failure in DOCX processing code

**Files Affected**: 
- Small DOCX files (tested: 14KB) not appearing in any bucket

## Configuration Testing Results

**Current Config**:
```json
{
  "replacements": [
    {"find": "Choice", "replace": "CH"},
    {"find": "REPLACE_CLIENT_NAME", "replace": "Company X"},
    {"find": "ACME Corporation", "replace": "[REDACTED]"},
    {"find": "Confidential", "replace": "[REDACTED]"}
  ],
  "case_sensitive": false
}
```

**Test Results**: Choice → CH replacement not working due to config cache bug.

## Next Steps

1. Fix config cache logic and redeploy
2. Investigate DOCX processing pipeline
3. Add better error logging for failed file types
4. Test with various file sizes and formats