# Ceremli V1.0

Ceremli is a wedding planning platform with:
- couple accounts and secure sessions
- wedding dashboard
- guest and household management
- RSVPs and custom RSVP questions
- events
- invitations and reminders
- checklist
- seating plan
- budget tracking
- supplier discovery
- public wedding pages
- QR codes
- plan/pricing hooks
- Railway deployment support

## Production
Keep the Railway persistent volume mounted at `/data`.

Recommended environment variables:
- `APP_ENV=production`
- `BASE_URL=https://your-domain.example`
- `RESEND_API_KEY=...` for real email delivery

Health endpoint:
`/health`
