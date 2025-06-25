# ChatGPT File Extension Compatibility Fix

## Problem Statement
- Processed files with `.txt` extension fail to upload to ChatGPT with "unknown error occurred"
- This is a known ChatGPT bug affecting `.txt` files since May 31, 2025
- The `.log` extension was tested as a workaround but also fails

## Solution: Use .md (Markdown) Extension

### Research Findings
Based on extensive research and testing:

1. **Confirmed Working Extensions in ChatGPT**:
   - `.md` (Markdown) - Best option for document-style content
   - `.csv` (Comma Separated Values) - Alternative option
   - `.py`, `.js` - Work but semantically inappropriate

2. **Confirmed NOT Working**:
   - `.txt` - Known bug since May 2025
   - `.log` - Tested and fails with same error

### Why .md is the Best Choice
- ✅ Explicitly supported by ChatGPT
- ✅ Plain text format (works with all text editors)
- ✅ Appropriate for document content
- ✅ No format confusion (unlike .csv or .py)
- ✅ Maintains readability and semantics

## Implementation

### Files to Update
1. `lambda_code/lambda_function_v2.py` - Change output extension from `.log` to `.md`

### Code Changes

```python
# In apply_filename_redaction() function (line ~618)
# Change from:
processed_filename = f"{processed_name}.csv"

# To:
processed_filename = f"{processed_name}.md"
```

### Testing
Test files have been created in `/home/ec2-user/redact-terraform/test_extensions/`:
- `test_document.md` - Recommended format
- `test_document.csv` - Alternative format
- Multiple other extensions for comparison

These can be manually uploaded to ChatGPT to verify compatibility.

## Benefits
1. **Immediate Compatibility**: Files will upload successfully to ChatGPT
2. **No User Confusion**: .md is still a text file, opens in any text editor
3. **Future Proof**: Markdown is a stable, well-supported format
4. **Maintains Functionality**: All existing features continue to work

## Notes
- The content remains plain text (no markdown formatting is added)
- Files will still open normally in Notepad, TextEdit, etc.
- The .md extension is purely for ChatGPT compatibility
- Windows line endings (CRLF) are still maintained for cross-platform support