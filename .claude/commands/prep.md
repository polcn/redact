# Prepare Codebase for Compaction

Prepare the codebase for compaction with cleanup, documentation, and git operations.

## Instructions

1. **Review and Clean Files**
   - Check for temporary files, logs, or build artifacts that should be removed
   - Review and clean up any redundant or obsolete files  
   - Suggest files that could be removed to reduce codebase size

2. **Update Documentation**
   - Update README.md if there were significant changes
   - Update CLAUDE.md with any new patterns or important notes
   - Check if any new features need documentation

3. **Git Operations**
   - Review all changes with `git status` and `git diff`
   - Create a meaningful commit message using $ARGUMENTS if provided, otherwise generate one
   - Stage all relevant changes with `git add`
   - Create commit with proper attribution
   - Push to remote repository

4. **Final Preparation** 
   - Verify all tests pass (if applicable)
   - Check that the build succeeds  
   - Confirm no sensitive data is being committed
   - Report what was cleaned up and committed

Provide a clear summary of all actions taken and confirm the codebase is ready for compaction.