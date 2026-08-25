# Vowly Stage 6.2 — publish route fix

This fixes the red `Not found` error in Website Studio.

Cause:
- The backend save endpoints use HTTP PUT.
- Stage 6/6.1 Website Studio was mistakenly sending POST.

Also fixed:
- Password-protected public RSVP now sends the correct password field.

Deploy:
1. Upload all Stage 6.2 files to the root of your existing `ajlubassa/vowly` GitHub repo.
2. Replace the existing files.
3. Commit: `Vowly Stage 6.2 publish route fix`
4. Keep Railway `web-volume` mounted at `/data`.
5. Wait for Railway to show Online.
6. Refresh Website Studio with Ctrl + F5.
7. Change a name or theme and press Publish changes.
8. It should show `Published ✓`.
9. Press Preview live ↗ and verify the change.
