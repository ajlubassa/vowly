#!/usr/bin/env python3
"""Ceremli production server with Stripe Payment Link webhook support."""
import json
import urllib.parse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

import server as core
import ceremli_launch_server as launch
import stripe_checkout_server as stripe_hardened  # keeps hardened API checkout fallback available


class PaymentLinkApp(launch.CeremliLaunchApp):
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != '/api/stripe/webhook':
            return super().do_POST()

        raw = self.body(raw=True)
        sig = self.headers.get('Stripe-Signature', '')
        if not core.verify_stripe_sig(raw, sig):
            return self.send_json({'error': 'Invalid webhook signature'}, 400)

        evt = json.loads(raw or b'{}')
        if evt.get('type') == 'checkout.session.completed':
            s = evt.get('data', {}).get('object', {})
            meta = s.get('metadata') or {}
            uid = meta.get('user_id')
            plan = meta.get('plan')
            email = ''

            # Payment Links use client_reference_id rather than Checkout Session metadata.
            ref = str(s.get('client_reference_id') or '')
            if ref and '|' in ref:
                ref_plan, ref_email = ref.split('|', 1)
                if ref_plan in ('premium', 'ultimate'):
                    plan = ref_plan
                email = ref_email.strip().lower()

            details = s.get('customer_details') or {}
            if not email:
                email = str(details.get('email') or s.get('customer_email') or '').strip().lower()

            # Final fallback for these one-off plans: infer from the charged amount.
            if plan not in ('premium', 'ultimate'):
                amount = int(s.get('amount_total') or 0)
                if amount == 3900:
                    plan = 'premium'
                elif amount == 6900:
                    plan = 'ultimate'

            with core.conn() as c:
                if not uid and email:
                    row = c.execute('SELECT id FROM users WHERE lower(email)=lower(?)', (email,)).fetchone()
                    if row:
                        uid = row['id']
                if uid and plan in ('premium', 'ultimate'):
                    c.execute('UPDATE users SET plan=? WHERE id=?', (plan, int(uid)))
                    c.execute(
                        'INSERT OR REPLACE INTO payments(user_id,plan,stripe_session_id,status,created_at) VALUES(?,?,?,?,?)',
                        (int(uid), plan, s.get('id'), 'paid', datetime.now(timezone.utc).isoformat())
                    )
                    print(f'[stripe-link] upgraded user={uid} plan={plan}')
                else:
                    print(f'[stripe-link] completed payment could not be matched ref={ref!r} email={email!r} amount={s.get("amount_total")}')

        return self.send_json({'received': True})


if __name__ == '__main__':
    launch.migrate_launch()
    core.os.chdir(core.ROOT)
    print(f'Ceremli Payment Link server on {core.PORT} | DB={core.DB}')
    ThreadingHTTPServer(('0.0.0.0', core.PORT), PaymentLinkApp).serve_forever()
