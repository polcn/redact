# Manual Test Checklist for Pattern Detection Fix

## Quick Test Steps

### 1. Open the Application
- Navigate to https://redact.9thcube.com
- Login with your test account

### 2. Test Pattern Checkboxes
On the home page configuration section:

1. **Click each checkbox** and verify:
   - [ ] SSN checkbox responds to clicks
   - [ ] Credit Card checkbox responds to clicks  
   - [ ] Phone Numbers checkbox responds to clicks
   - [ ] Email Addresses checkbox responds to clicks
   - [ ] IP Addresses checkbox responds to clicks
   - [ ] Driver's License checkbox responds to clicks

2. **Visual feedback**:
   - [ ] Checkboxes show orange color when hovered
   - [ ] Checkboxes show orange background when checked
   - [ ] White checkmark appears when checked
   - [ ] Focus ring appears when using keyboard navigation

3. **Save configuration**:
   - [ ] Click "Save Configuration" button
   - [ ] Verify success message appears
   - [ ] No errors in browser console

4. **Test persistence**:
   - [ ] Refresh the page (F5)
   - [ ] Verify all checkbox states are preserved
   - [ ] Previously checked items remain checked
   - [ ] Previously unchecked items remain unchecked

### 3. Test Pattern Detection

1. Create a test file named `pattern_test.txt` with this content:
```
My SSN is 123-45-6789 and my phone is (555) 123-4567.
Email me at test@example.com
Credit card: 4532-1234-5678-9012
IP: 192.168.1.100
Driver's License: D1234567
```

2. Enable only specific patterns and upload the test file:
   - [ ] Enable only SSN → verify only SSN is redacted
   - [ ] Enable only Phone → verify only phone is redacted
   - [ ] Enable only Email → verify only email is redacted
   - [ ] Enable all patterns → verify all patterns are redacted

### 4. Browser Console Check
Open Developer Tools (F12) and check:
- [ ] No JavaScript errors in console
- [ ] No failed network requests
- [ ] Config API calls succeed (200 status)

## Expected Results

✅ **Success Criteria**:
- All checkboxes are clickable and maintain state
- Configuration saves without errors
- Settings persist after page reload
- Pattern detection works according to selected options

❌ **Known Issues to Watch For**:
- Checkboxes not responding to clicks
- State not persisting after save
- Console errors about undefined patterns
- API errors when saving configuration