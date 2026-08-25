# Update your live Railway site to Stage 6

1. Open your `ajlubassa/vowly` repository on GitHub.
2. Upload/replace the files from this Stage 6 folder in the repository root.
3. Commit with message: `Vowly Stage 6`.
4. Railway will detect the GitHub commit and redeploy the existing `web` service automatically.
5. Do NOT delete the Railway volume. Keep it mounted at `/data`.
6. Wait for Railway to show the web service as Online.
7. Refresh your existing Railway Vowly URL.
8. Open **Website studio** from the dashboard and publish a design.

The database migration is additive: Stage 6 creates a `wedding_settings` table without deleting existing users, guests, RSVPs or tasks.
