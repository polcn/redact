# Quick Cleanup and Git Operations

Perform quick cleanup and git operations before compaction.

## Instructions

1. **Cleanup Checklist**
   - Remove temporary files: `__pycache__` directories, `*.pyc`, `*.tmp`, `*.log`
   - Clear test output files and build artifacts
   - Clean up any editor temporary files
   - Remove node_modules if it will be rebuilt

2. **Git Review**
   - Show current git status: `git status`
   - Display summary of changes: `git diff --stat`
   - Review staged vs unstaged changes

3. **Stage and Commit**
   - Stage all changes: `git add -A`
   - Create commit using $ARGUMENTS if provided as the message
   - If no message provided, auto-generate based on changes
   - Use proper Git attribution format

4. **Push and Verify**
   - Push changes to remote repository: `git push origin main`
   - Verify working tree is clean: `git status`
   - Confirm push succeeded

5. **Compaction Readiness**
   - Report all cleanup actions taken
   - List files removed or modified
   - Confirm repository is ready for `/compact`

Execute these steps systematically and provide a summary of all actions performed.