# Issue: verifying pass content shouldn't be able to touch a real member's credentials

## What happened, twice

While verifying pass-content fixes (relevantDate removal on Aug 24, the
venue-location fix on Aug 29), the same real member's real Apple Wallet
pass was rebuilt via `_issue_member_pkpass(member, season)` using their
actual `member_id` to check what the generated `pass.json` looked like.

`_issue_member_pkpass` calls `db.issue_wallet_token()`, which **rotates**
the pass's serial number and `auth_token` as a real, permanent side
effect (same as a legitimate admin-triggered resend). Each verification
call silently invalidated whatever pass was actually installed on that
member's phone, because the installed pass's cached credentials no
longer matched the new database row. Symptom both times: the phone
stopped successfully completing its wallet-content refresh (silent 401
on `passkit_get_latest_pass`, not a visible error to anyone), so it kept
showing stale content indefinitely, looking exactly like "the push
mechanism doesn't work" when the actual mechanism was fine — verification
itself was the thing breaking it.

Both times this was caught, diagnosed, and fixed by rebuilding a fresh
pass and hand-delivering it — but it's now happened twice in one week,
on the same real account, right after saying it wouldn't happen again.
Relying on "remember to use the dummy account" has already failed twice;
this needs an actual structural fix, not a reminder.

## Root cause

There are two genuinely different things that get conflated under
"build a pass to check something":

1. **"What does the pass.json look like for these field values?"** — a
   pure content question. Doesn't need a real member, doesn't need a
   real serial number, doesn't need any database write at all.
2. **"Actually issue/reissue a real pass for this real person."** — a
   real, deliberate action that legitimately needs to rotate credentials
   (that's the whole point of a resend: invalidate the old QR).

`_issue_member_pkpass(member, season)` is the only path currently used
for #1, but it always does #2's side effect, because it always calls
`db.issue_wallet_token()`. There's no way to ask "just show me the
pass.json" without also rotating a real row.

## Proposed fix

Add a verification path that never touches the database, using pieces
that already exist and already don't require a real member:

- `_member_pass_data(member, serial_number, raw_token, season_name, auth_token="")`
  (`app.py`) only reads `member['first_name']` / `member['last_name']`
  — it never needs `member` to be a real DB row.
- `build_member_pkpass(pass_data)` (`wallet_pass.py`) only needs a
  `MemberPassData` instance — never touches the database either.

So a pure-content verification helper could look like:

```python
def _preview_pass_json(**overrides):
    """Build a pass.json for inspection only -- no DB read or write,
    no real or dummy member row involved, cannot invalidate anyone's
    installed pass. Use this instead of _issue_member_pkpass() for any
    'does the pass contain the right field' check."""
    fake_member = {"first_name": "Preview", "last_name": "Pass"}
    pass_data, _, _ = _member_pass_data(
        fake_member, "PREVIEW-0000", "preview-raw-token", "2026/27",
        auth_token="preview-auth-token",
    )
    for key, value in overrides.items():
        setattr(pass_data, key, value)
    pkpass_bytes = build_member_pkpass(pass_data)
    import zipfile, io, json
    return json.loads(zipfile.ZipFile(io.BytesIO(pkpass_bytes)).read('pass.json'))
```

This should become the default way to check "does the pass have the
right relevantDate / expirationDate / locations / next-match text" —
never `_issue_member_pkpass()` with a real `member_id`, dummy or not
(the dummy account is *better* than the real one, but still leaves a
live row that something could later mistake for real, and still isn't
necessary for a pure content check).

`_issue_member_pkpass()` itself should be reserved for what it actually
is: issuing or resending a real pass, triggered from a real admin
action (`admin_member_resend_pass`, the bulk-send routes, initial
signup) — never from an ad-hoc verification script.

## Suggested scope for this task

1. Add the preview/dry-run helper (or equivalent) to `app.py`.
2. Optionally expose it as a small admin-only debug route
   (`/admin/pass-preview.json` or similar) so verifying a content
   change doesn't even require a Python shell — just a page load.
3. Nothing else needs to change — `_issue_member_pkpass` and
   `issue_wallet_token` are correct as-is for their real purpose; this
   is purely about giving verification a non-mutating path so it can't
   be pointed at the wrong thing again.

## Still true as of Aug 31

The Forest → Ipswich / Spurs 12/19 work was verified with production SQL
counts (`pass_devices.last_fetched_at`, issued-before timestamps) and
real-phone confirmation — **not** `_issue_member_pkpass` on a real
member. Do not "just rebuild" member id 8 (or anyone else) to inspect
`pass.json`. Preview helper above is still unbuilt; until it exists,
inspect a dummy serial or unzip a locally built preview, never rotate a
live token to look at a field.
