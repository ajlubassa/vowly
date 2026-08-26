# Vowly Stage 14 — V1.0 launch-ready

This is the launch-readiness pass.

Adds:
- `/health` readiness endpoint
- security headers
- launch checklist page
- production/email readiness checks
- clearer error messaging
- final mobile interaction polish
- removal of leftover prototype wording

Deploy over the current GitHub repository.

Commit:
`Vowly V1.0 launch-ready`

Keep Railway `/data` unchanged.

Before real launch:
1. Set `APP_ENV=production`
2. Set the final `BASE_URL`
3. Configure `RESEND_API_KEY` for real email delivery
4. Open `Launch check` in Vowly
5. Confirm the core checks are ready
6. Test signup, login, guest RSVP, invitations, budget, seating and mobile navigation
