# Email to PassKit Support

**To:** support@passkit.com  
**Subject:** API Issue - Pass Field Updates Not Working Despite 200 OK Responses

## Issue Summary

We're trying to update pass fields via the PassKit API, but while all requests return 200 OK responses, the actual pass data is not being updated in the PassKit dashboard or on the passes themselves.

## What We're Trying to Do

Update the "Next Match" field on all our Liverpool FC supporters club passes with upcoming match information. The field is configured in our pass template as:
- **Field Key:** `custom.nextMatch`
- **Label:** "Next Match"
- **Data Type:** Single Line Text

## API Endpoint We're Using

Based on your previous support response, we're using:
```
PUT https://api.pub2.passkit.io/members/member
```

**Headers:**
- Authorization: Bearer {API_KEY}
- X-Project-Key: {PROJECT_KEY}
- Content-Type: application/json

## Request Body Structure

```json
{
  "programId": "3yyTsbqwmtXaiKZ5qWhqTP",
  "id": "member_id_here",
  "person": {
    "displayName": "Test Tester",
    "emailAddress": "",
    "surname": "Tester",
    "forename": "Test"
  },
  "passOverrides": {
    "custom.nextMatch": "Man U | 10/19 11:30 AM"
  }
}
```

## What's Happening

1. ✅ **API accepts the request** - Returns 200 OK
2. ✅ **No error messages** - Response appears successful
3. ❌ **Pass data not updated** - Field still shows old value in PassKit dashboard
4. ❌ **Passes not updated** - Members still see old match info on their passes

## What We've Tried

### 1. Different Field Names
- `nextMatch`
- `Next Match`
- `custom.nextMatch` ← **This is the correct field name from our template**
- `next_match`
- `upcomingMatch`

### 2. Different Payload Structures
- With `passOverrides` wrapper
- Direct field assignment (no wrapper)
- Using `passMetaData` instead of `passOverrides`
- Including/excluding `externalId`
- **Nested custom fields:** `"custom": { "nextMatch": "value" }` (as suggested by support)
- **Dot notation:** `"custom.nextMatch": "value"`

### 3. Different HTTP Methods
- PUT (returns 200 OK)
- PATCH (returns 501 Method Not Allowed)
- POST (returns 200 OK)

### 4. Different Endpoints
- `/members/member` (returns 200 OK)
- `/passes/pass/{memberId}` (returns 404 Not Found)
- `/members/member/{memberId}` (returns 404 Not Found)

### 5. Server Verification
- Confirmed we're using `api.pub2.passkit.io` (USA server)
- Our account is on pub2, not pub1
- All other API calls (list members, checkout) work perfectly

### 6. Member Identification
- Using `id` field (member ID)
- Using `externalId` field (empty for our test member)
- Both approaches return 200 OK but don't update passes

### 7. Payload Validation
- Including all required PII fields (displayName, emailAddress, etc.)
- Minimal payloads (just passOverrides)
- With/without programId in payload

## Test Case

**Member ID:** `36dOqMlKp3aJNe4RAsM5WC` (Test Tester)

**Expected Result:** Next Match field should show "Man U | 10/19 11:30 AM"  
**Actual Result:** Field still shows "Chelsea | 10/4 12:30 PM"

## Working API Calls

These work perfectly:
- ✅ List members: `POST /members/member/list/{programId}`
- ✅ Checkout members: `POST /members/member/checkOut`
- ✅ Check-in members: `POST /members/member/checkIn`

## Questions

1. **Is the PUT `/members/member` endpoint the correct one for updating pass fields?**
2. **Are we missing required fields in our request payload?**
3. **Is there a different endpoint for updating pass template fields?**
4. **Do we need to trigger a pass refresh/regeneration after updating fields?**
5. **Has the API changed recently that might affect pass field updates?**
6. **Why do all requests return 200 OK but no actual updates occur?**
7. **Is there a different API approach for updating custom fields like `custom.nextMatch`?**
8. **Do we need special permissions or account settings to update pass fields?**

## Account Details

- **Program ID:** 3yyTsbqwmtXaiKZ5qWhqTP
- **Server:** pub2 (USA)
- **Template:** Liverpool FC supporters club pass
- **Field:** custom.nextMatch (Next Match)

## Request

Could you please:
1. **Verify the correct API endpoint** for updating pass fields
2. **Provide a working example** of updating the `custom.nextMatch` field
3. **Check if there are any account-specific settings** that might be preventing updates

We have 260+ members and would like to automate match updates, but we're stuck on this API issue.

Thank you for your help!

---
**Contact:** colby@colbyangusblack.com  
**Club:** Liverpool Official Supporters Club Brooklyn
