# Vowly Stage 6.1 — publish fix

This patch fixes the Website Studio publish/live-preview issue.

1. Open your existing GitHub repo: `ajlubassa/vowly`.
2. Upload all files from this Stage 6.1 folder into the repository root and replace the existing versions.
3. Commit with: `Vowly Stage 6.1 publish fix`.
4. Railway will redeploy automatically.
5. Keep the existing `web-volume` mounted at `/data`.
6. Wait until Railway shows the web service as **Online**.
7. On Vowly, do a hard refresh once: `Ctrl + F5`.
8. Open **Website studio**, make a change, and click **Publish changes**.
9. You should see `Published ✓`.
10. Click **Preview live ↗** and the new public site should reflect the saved changes.

This build also disables browser caching for Vowly HTML/JS/CSS so future GitHub deployments are less likely to show stale frontend code.
