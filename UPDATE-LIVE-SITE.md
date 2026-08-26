# Vowly Stage 13.4 — Full mobile layout cleanup

This patch replaces the previous experimental mobile headers with one stable layout across all app pages.

Fixes:
- Smaller mobile headings
- No heading can sit on top of a button
- Action buttons move to a clean second row
- Menu button remains separately tappable
- Dashboard, Guests, Events, Invitations, Checklist, Seating, Budget and Website Studio use the same safe mobile structure
- Website Studio preview and URL no longer overflow
- Forms collapse to one column on mobile
- Metric cards stay within the viewport
- Removes horizontal overflow from app pages
- Raises button stacking so page text cannot block taps

Deploy over the current GitHub repository.

Commit:
`Vowly Stage 13.4 full mobile cleanup`

Keep Railway `/data` unchanged. Wait for Online, then refresh the phone page.
