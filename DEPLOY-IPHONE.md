# Put Vowly online from an iPhone (Railway)

This Stage 5 package is prepared for Railway.

## What you need
- A GitHub account
- A Railway account
- This Vowly Stage 5 folder uploaded to a GitHub repository

## Railway setup
1. In Railway, create a new project from your GitHub repository.
2. Select the Vowly repository as the service source.
3. Railway will build from the included `Dockerfile` / `railway.toml`.
4. Add a Volume to the web service and mount it at `/data`.
5. In the service Variables tab add:
   - `APP_ENV=production`
   - `DEMO_MODE=true` (safe testing; no real charges if Stripe is not configured)
6. Open Settings > Networking and choose **Generate Domain**.
7. Redeploy if needed, then open the generated Railway URL in Safari.
8. Visit `/health` on that domain. You should see `"ok": true`.

## Demo login
- Email: `demo@vowly.local`
- Password: `demo123`

## Turn real email on later
Set `RESEND_API_KEY` and a verified `EMAIL_FROM` address/domain.

## Turn real payments on later
Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PREMIUM_PRICE_ID`, and `STRIPE_ULTIMATE_PRICE_ID`, then set `DEMO_MODE=false`.

Important: keep `DEMO_MODE=true` until you intentionally want checkout to use Stripe.
