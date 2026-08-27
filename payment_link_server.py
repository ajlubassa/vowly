#!/usr/bin/env python3
"""Ceremli production server with account-bound Stripe Payment Link checkout."""
import json
import os
import hmac
import hashlib
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

import server as core
import ceremli_launch_server as launch
import stripe_checkout_server as stripe_hardened

PAYMENT_LINKS={
    'premium':'https://buy.stripe.com/test_8x214n2NH7Qz0do0ZQ6EU00',
    'ultimate':'https://buy.stripe.com/test_eVq00jdsl3AjgcmcIy6EU01',
}
TOKEN_SECRET=(os.getenv('STRIPE_WEBHOOK_SECRET','') or os.getenv('STRIPE_SECRET_KEY','')).strip()


def make_ref(user_id, plan):
    ts=int(time.time())
    payload=f'{user_id}:{plan}:{ts}'
    sig=hmac.new(TOKEN_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()[:24]
    return f'{payload}:{sig}'


def parse_ref(ref):
    try:
        uid,plan,ts,sig=ref.split(':',3)
        payload=f'{uid}:{plan}:{ts}'
        expected=hmac.new(TOKEN_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()[:24]
        if not TOKEN_SECRET or not hmac.compare_digest(sig,expected):return None
        if plan not in ('premium','ultimate'):return None
        if abs(int(time.time())-int(ts))>86400:return None
        return int(uid),plan
    except Exception:
        return None


class PaymentLinkApp(launch.CeremliLaunchApp):
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path

        # Create an account-bound Payment Link URL server-side. The browser never
        # decides which Ceremli user a payment belongs to.
        if path=='/api/billing/checkout':
            a=self.require(csrf=True)
            if not a:return
            d=self.body();plan=str(d.get('plan','')).lower()
            link=PAYMENT_LINKS.get(plan)
            if not link:return self.send_json({'error':'Unknown plan'},400)
            ref=make_ref(a['user_id'],plan)
            qs=urllib.parse.urlencode({'client_reference_id':ref,'prefilled_email':a['email']})
            return self.send_json({'url':f'{link}?{qs}'})

        if path!='/api/stripe/webhook':
            return super().do_POST()

        raw=self.body(raw=True)
        sig=self.headers.get('Stripe-Signature','')
        if not core.verify_stripe_sig(raw,sig):
            print('[stripe-link] invalid webhook signature',flush=True)
            return self.send_json({'error':'Invalid webhook signature'},400)

        evt=json.loads(raw or b'{}')
        print(f'[stripe-link] event={evt.get("type")}',flush=True)
        if evt.get('type')=='checkout.session.completed':
            s=evt.get('data',{}).get('object',{})
            ref=str(s.get('client_reference_id') or '')
            matched=parse_ref(ref)
            if not matched:
                print(f'[stripe-link] completed session not account-bound ref_present={bool(ref)}',flush=True)
                return self.send_json({'received':True})
            uid,plan=matched
            expected_amount=3900 if plan=='premium' else 6900
            amount=int(s.get('amount_total') or 0)
            if amount!=expected_amount or str(s.get('payment_status') or '')!='paid':
                print(f'[stripe-link] rejected session user={uid} plan={plan} amount={amount} status={s.get("payment_status")}',flush=True)
                return self.send_json({'received':True})
            with core.conn() as c:
                user=c.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone()
                if not user:
                    print(f'[stripe-link] unknown user={uid}',flush=True)
                    return self.send_json({'received':True})
                c.execute('UPDATE users SET plan=? WHERE id=?',(plan,uid))
                c.execute('INSERT OR REPLACE INTO payments(user_id,plan,stripe_session_id,status,created_at) VALUES(?,?,?,?,?)',(uid,plan,s.get('id'),'paid',datetime.now(timezone.utc).isoformat()))
            print(f'[stripe-link] upgraded user={uid} plan={plan}',flush=True)
        return self.send_json({'received':True})


if __name__=='__main__':
    launch.migrate_launch()
    core.os.chdir(core.ROOT)
    print(f'Ceremli Payment Link server on {core.PORT} | DB={core.DB}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',core.PORT),PaymentLinkApp).serve_forever()
