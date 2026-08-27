#!/usr/bin/env python3
"""Ceremli production server with account-bound Stripe Payment Link checkout."""
import json, os, hmac, hashlib, time, urllib.parse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import server as core
import ceremli_launch_server as launch
import stripe_checkout_server as stripe_hardened

PAYMENT_LINKS={'premium':'https://buy.stripe.com/test_8x214n2NH7Qz0do0ZQ6EU00','ultimate':'https://buy.stripe.com/test_eVq00jdsl3AjgcmcIy6EU01'}
TOKEN_SECRET=(os.getenv('STRIPE_WEBHOOK_SECRET','') or os.getenv('STRIPE_SECRET_KEY','')).strip()

def ensure_pending_table():
    with core.conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS pending_checkouts(
          id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,plan TEXT NOT NULL,
          email TEXT NOT NULL,created_at INTEGER NOT NULL,consumed INTEGER NOT NULL DEFAULT 0)''')

def make_ref(user_id,plan):
    ts=int(time.time()); payload=f'{user_id}:{plan}:{ts}'
    sig=hmac.new(TOKEN_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()[:24]
    return f'{payload}:{sig}'

def parse_ref(ref):
    try:
        uid,plan,ts,sig=ref.split(':',3); payload=f'{uid}:{plan}:{ts}'
        expected=hmac.new(TOKEN_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()[:24]
        if not TOKEN_SECRET or not hmac.compare_digest(sig,expected): return None
        if plan not in ('premium','ultimate') or abs(int(time.time())-int(ts))>86400:return None
        return int(uid),plan
    except Exception:return None

def payment_link_checkout(plan,user_id):
    plan=str(plan).lower(); link=PAYMENT_LINKS.get(plan)
    if not link:return None
    return {'url':f'{link}?'+urllib.parse.urlencode({'client_reference_id':make_ref(int(user_id),plan)})}
core.stripe_checkout=payment_link_checkout

class PaymentLinkApp(launch.CeremliLaunchApp):
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/billing/checkout':
            a=self.require(csrf=True)
            if not a:return
            d=self.body(); plan=str(d.get('plan','')).lower(); link=PAYMENT_LINKS.get(plan)
            if not link:return self.send_json({'error':'Unknown plan'},400)
            email=str(a['email']).strip().lower(); now=int(time.time())
            with core.conn() as c:
                c.execute('DELETE FROM pending_checkouts WHERE created_at<? OR consumed=1',(now-86400,))
                c.execute('INSERT INTO pending_checkouts(user_id,plan,email,created_at,consumed) VALUES(?,?,?,?,0)',(a['user_id'],plan,email,now))
            ref=make_ref(a['user_id'],plan)
            qs=urllib.parse.urlencode({'client_reference_id':ref,'prefilled_email':email})
            print(f'[stripe-link] checkout user={a["user_id"]} plan={plan}',flush=True)
            return self.send_json({'url':f'{link}?{qs}'})
        if path!='/api/stripe/webhook':return super().do_POST()
        raw=self.body(raw=True); sig=self.headers.get('Stripe-Signature','')
        if not core.verify_stripe_sig(raw,sig):return self.send_json({'error':'Invalid webhook signature'},400)
        evt=json.loads(raw or b'{}'); et=evt.get('type'); print(f'[stripe-link] event={et}',flush=True)
        if et=='checkout.session.completed':
            s=evt.get('data',{}).get('object',{}); amount=int(s.get('amount_total') or 0); status=str(s.get('payment_status') or '')
            plan={3900:'premium',6900:'ultimate'}.get(amount); uid=None
            matched=parse_ref(str(s.get('client_reference_id') or ''))
            if matched:
                uid,ref_plan=matched
                if plan!=ref_plan:uid=None
            details=s.get('customer_details') or {}; email=str(details.get('email') or s.get('customer_email') or '').strip().lower()
            # Authoritative fallback: checkout ownership was persisted before leaving Ceremli.
            if uid is None and plan and status=='paid' and email:
                with core.conn() as c:
                    row=c.execute('''SELECT id,user_id FROM pending_checkouts
                      WHERE email=? AND plan=? AND consumed=0 AND created_at>=?
                      ORDER BY id DESC LIMIT 1''',(email,plan,int(time.time())-86400)).fetchone()
                    if row:
                        uid=int(row['user_id']); c.execute('UPDATE pending_checkouts SET consumed=1 WHERE id=?',(row['id'],))
                print(f'[stripe-link] pending checkout match={bool(uid)} plan={plan}',flush=True)
            if uid is None or not plan or status!='paid':
                print(f'[stripe-link] ignored completed session ref={bool(s.get("client_reference_id"))} email={bool(email)} amount={amount} status={status}',flush=True)
                return self.send_json({'received':True})
            with core.conn() as c:
                if not c.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone():return self.send_json({'received':True})
                c.execute('UPDATE users SET plan=? WHERE id=?',(plan,uid))
                c.execute('INSERT OR REPLACE INTO payments(user_id,plan,stripe_session_id,status,created_at) VALUES(?,?,?,?,?)',(uid,plan,s.get('id'),'paid',datetime.now(timezone.utc).isoformat()))
            print(f'[stripe-link] upgraded user={uid} plan={plan}',flush=True)
        return self.send_json({'received':True})

if __name__=='__main__':
    launch.migrate_launch(); ensure_pending_table(); core.os.chdir(core.ROOT)
    print(f'Ceremli Payment Link server on {core.PORT} | DB={core.DB}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',core.PORT),PaymentLinkApp).serve_forever()
