# Vowly — Stage 5

Stage 5 is the deployment-ready evolution of the wedding planning MVP.

## Included
- Couple sign-up/login and secure session cookies
- Wedding dashboard, builder, guest list and checklist
- Public wedding pages and RSVP collection
- QR code generation
- Free/Premium/Ultimate plan flow
- Stripe Checkout/webhook integration hooks
- Resend invitation/reminder integration hooks
- Supplier marketplace + qualified lead capture
- `/health` readiness endpoint
- Railway deployment configuration (`railway.toml`)
- Automatic Railway public-domain detection
- Automatic persistent SQLite location when a Railway Volume is attached

## Local run
```bash
python -m pip install -r requirements.txt
python server.py
```
Then open http://localhost:8000.

Demo login: `demo@vowly.local` / `demo123`.

## Railway deployment
See `DEPLOY-IPHONE.md` for the phone-friendly deployment checklist.

## Production database note
This build intentionally remains a single-instance SQLite application for simplicity. On Railway, attach a persistent volume (for example `/data`) so the DB survives redeploys. For multi-instance scaling, the next architecture step should migrate the data layer to PostgreSQL.
