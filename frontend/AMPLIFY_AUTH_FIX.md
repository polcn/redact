# AWS Amplify v6 Authentication Fix

## Issue: "There is already a signed in user"

This error occurs in AWS Amplify v6 when attempting to sign in while a session already exists. This is a breaking change from Amplify v5 where concurrent sessions were handled differently.

## Root Cause

AWS Amplify v6 enforces stricter session management:
- Only one active session is allowed per browser instance
- The `signIn` method throws an error if a user is already authenticated
- This prevents accidental session overwrites and improves security

## Solutions Implemented

### 1. Auto Sign-Out Before New Sign-In
Modified `AuthContext.tsx` to automatically sign out any existing user before attempting a new sign-in:

```typescript
const handleSignIn = async (email: string, password: string) => {
  try {
    // Check if there's already a signed-in user and sign them out first
    try {
      const currentUser = await getCurrentUser();
      if (currentUser) {
        console.log('Signing out existing user before new sign in');
        await signOut();
      }
    } catch (error) {
      // No current user, proceed with sign in
    }
    
    await signIn({ username: email, password });
    await refreshUser();
  } catch (error) {
    console.error('Sign in error:', error);
    throw error;
  }
};
```

### 2. Redirect Already Authenticated Users
Added logic to `Login.tsx` to redirect authenticated users away from the login page:

```typescript
// Redirect if already logged in
useEffect(() => {
  if (user) {
    navigate('/');
  }
}, [user, navigate]);
```

### 3. Improved Error Messages
Enhanced error handling to provide clearer messages to users:

```typescript
if (err.message?.includes('already a signed in user')) {
  setError('You are already signed in. Please refresh the page or clear your browser data if you need to sign in with a different account.');
}
```

## Alternative Solutions

### 1. Force Sign Out Button
Add a "Sign Out" button on the login page for users who need to switch accounts:

```typescript
{user && (
  <button onClick={() => signOut()} className="...">
    Sign out current user
  </button>
)}
```

### 2. Global Sign Out
Use global sign out to clear all sessions across devices:

```typescript
import { signOut } from 'aws-amplify/auth';

await signOut({ global: true });
```

### 3. Browser Storage Clear
Clear browser storage to remove stale sessions:

```typescript
// Clear all Amplify-related storage
localStorage.clear();
sessionStorage.clear();
```

## Testing

1. **Test Sign In Flow**:
   - Sign in with User A
   - Navigate to `/login`
   - Should auto-redirect to home page
   - If not redirected, attempt to sign in with User B
   - Should automatically sign out User A and sign in User B

2. **Test Error Handling**:
   - Open browser developer tools
   - Manually create a session in localStorage
   - Attempt to sign in
   - Should see friendly error message

3. **Test Multi-Tab Scenarios**:
   - Open app in two tabs
   - Sign in on Tab 1
   - Attempt to sign in on Tab 2
   - Should handle gracefully

## Prevention

1. **Always check for existing sessions** before showing login form
2. **Provide clear sign-out options** throughout the app
3. **Handle session expiration** gracefully
4. **Use consistent session management** across all components

## References

- [AWS Amplify v6 Migration Guide](https://docs.amplify.aws/react/build-a-backend/auth/enable-sign-up/)
- [Amplify Auth API Reference](https://docs.amplify.aws/react/build-a-backend/auth/connect-your-frontend/)
- [Common Authentication Scenarios](https://docs.amplify.aws/react/build-a-backend/auth/manage-user-sessions/)