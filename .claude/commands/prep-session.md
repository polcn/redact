# Generate Session Summary

Generate a comprehensive session summary with completed features, fixes, and changes.

## Instructions

1. **Session Header**
   - Use "$1" as the session title if provided, otherwise use today's date
   - Include current date and time

2. **Analyze Recent Work**
   - Review recent git commits and changes
   - Check modified files and their purposes
   - Identify patterns in the work completed

3. **Create Summary Sections**
   - **✅ Completed Features**: List all new features implemented with descriptions
   - **🔧 Critical Fixes Applied**: Security patches, bug fixes, performance improvements
   - **🏗️ API/Infrastructure Changes**: New endpoints, configuration changes, deployment updates
   - **⚠️ Known Issues Remaining**: Unresolved problems, TODO items, future improvements
   - **🧪 Testing Notes**: Tests performed, coverage status, validation results
   - **📊 Statistics**: Files modified, lines changed, commits created

4. **Session Documentation**
   - Save the summary as `SESSION_SUMMARY_$(date +%Y%m%d).md`
   - Stage the file in git
   - Suggest a commit message for the session work
   - Prepare for compaction

Provide a comprehensive overview of all work accomplished in this session.