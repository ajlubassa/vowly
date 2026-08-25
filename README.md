# Vowly — Stage 8

Stage 8 is the deployment-ready evolution of the wedding planning MVP.

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


## Stage 8 additions
- Premium visual Website Studio with 3 templates and 4 accents
- Live website preview
- Schedule, travel, FAQ and gifts sections
- Per-section visibility controls
- Public wedding site automatically reflects the selected theme
- Existing Stage 5 Railway volume/database remains compatible; schema upgrades automatically on boot

## Stage 8 additions
- Households/families
- Multiple wedding events
- Guest-to-event invitation tracking
- Custom RSVP questions
- Guest notes
- CSV guest export
- Public RSVP can answer event attendance + custom questions
- Existing Railway volume/database remains compatible; schema migrates additively

## Stage 8 additions
- Seating planner with table creation, capacities and guest assignments
- Round, rectangular and top-table layouts
- Unseated guest queue and seat-capacity counts
- Wedding budget tracker
- Planned vs actual vs paid totals
- Budget categories, suppliers, due dates and notes
- Additive database migration; existing Railway data remains compatible
