# PassKit API Troubleshooting Briefing for Copilot & Gemini

## Problem Statement
We're trying to update custom pass fields via PassKit API, but **all requests return 200 OK yet no actual updates occur** in the PassKit dashboard or on the passes themselves.

## What We're Trying to Do
Update a custom field called "Next Match" on Liverpool FC supporter passes with upcoming match information.

## Technical Details

### PassKit Configuration
- **Server:** `https://api.pub2.passkit.io` (USA)
- **Program ID:** `3yyTsbqwmtXaiKZ5qWhqTP`
- **Field Name:** `custom.nextMatch` (from pass template)
- **Field Type:** Single Line Text
- **Current Value:** "Chelsea | 10/4 12:30 PM"
- **Target Value:** "Man U | 10/19 11:30 AM"

### Test Member
- **Member ID:** `36dOqMlKp3aJNe4RAsM5WC`
- **Name:** "Test Tester"
- **External ID:** Empty (not set)

## API Endpoint & Authentication
```http
PUT https://api.pub2.passkit.io/members/member
Headers:
  Authorization: Bearer {API_KEY}
  X-Project-Key: {PROJECT_KEY}
  Content-Type: application/json
```

## What We've Tried (All Return 200 OK)

### 1. Field Name Variations
```json
"passOverrides": {
  "nextMatch": "value"
}
```
```json
"passOverrides": {
  "Next Match": "value"
}
```
```json
"passOverrides": {
  "custom.nextMatch": "value"
}
```
```json
"passOverrides": {
  "custom": {
    "nextMatch": "value"
  }
}
```

### 2. Payload Structures
```json
{
  "programId": "3yyTsbqwmtXaiKZ5qWhqTP",
  "id": "36dOqMlKp3aJNe4RAsM5WC",
  "person": {
    "displayName": "Test Tester",
    "emailAddress": "",
    "surname": "Tester",
    "forename": "Test"
  },
  "passOverrides": {
    "custom": {
      "nextMatch": "Man U | 10/19 11:30 AM"
    }
  }
}
```

### 3. HTTP Methods
- ✅ PUT (200 OK, no update)
- ❌ PATCH (501 Method Not Allowed)
- ✅ POST (200 OK, no update)

### 4. Alternative Endpoints
- ✅ `/members/member` (200 OK, no update)
- ❌ `/passes/pass/{memberId}` (404 Not Found)
- ❌ `/members/member/{memberId}` (404 Not Found)

## What Works Perfectly
These API calls work flawlessly:
- ✅ `POST /members/member/list/{programId}` - List members
- ✅ `POST /members/member/checkOut` - Checkout members
- ✅ `POST /members/member/checkIn` - Check-in members

## The Core Issue
**API accepts all requests with 200 OK responses, but the actual pass data never updates.** This suggests:
1. Wrong endpoint for pass field updates
2. Incorrect payload structure
3. API bug or limitation
4. Missing required fields or permissions

## Specific Questions for AI Assistants

### For Copilot (GitHub Copilot)
1. **API Pattern Analysis:** Based on the working endpoints (list, checkout, checkin), what's the correct pattern for updating pass fields?
2. **PassKit Documentation:** Can you find the official PassKit API documentation for updating custom pass fields?
3. **Similar Issues:** Are there any GitHub issues or Stack Overflow posts about PassKit pass field updates not working?

### For Gemini (Google's AI)
1. **API Research:** Can you find the latest PassKit API documentation for updating pass template fields?
2. **Alternative Approaches:** Are there different ways to update pass fields (webhook, template updates, etc.)?
3. **Error Analysis:** Why might an API return 200 OK but not actually perform the update?

## What We Need
A working example of updating a custom pass field (`custom.nextMatch`) that actually updates the pass in the PassKit dashboard.

## Success Criteria
- API request returns 200 OK ✅ (already working)
- PassKit dashboard shows updated field value ❌ (not working)
- Actual pass shows updated value ❌ (not working)

## Additional Context
- This is for a Liverpool FC supporters club with 260+ members
- We want to automate match updates across all passes
- Other PassKit features (check-in/out, member listing) work perfectly
- We have valid API credentials and proper authentication

---

**Goal:** Find the correct API approach to actually update pass fields, not just get successful responses.
