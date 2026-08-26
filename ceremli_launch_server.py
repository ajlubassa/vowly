"""Ceremli launch server: household RSVP, account security, plan entitlements and privacy controls."""
import json
import server as core
from ceremli_account_server import AccountHandler, migrate_accounts

PLAN_RANK={'free':0,'premium':1,'ultimate':2}
PREMIUM_POST={'/api/invitations/send','/api/reminders/send'}

def allowed(plan,minimum): return PLAN_RANK.get(plan or 'free',0)>=PLAN_RANK[minimum]

def rows(c,sql,args=()): return [dict(x) for x in c.execute(sql,args).fetchall()]

class LaunchHandler(AccountHandler):
    def do_GET(self):
        path=self.path.split('?',1)[0]
        if path=='/api/account/export':
            a=self.require()
            if not a:return
            wid=a['id'];uid=a['user_id']
            with core.conn() as c:
                payload={
                    'exported_at':core.datetime.now(core.timezone.utc).isoformat(),
                    'account':{'email':a['email'],'plan':a['plan']},
                    'wedding':{k:a.get(k) for k in ('partner1','partner2','date','venue','story','slug')},
                    'guests':rows(c,'SELECT * FROM guests WHERE wedding_id=? ORDER BY id',(wid,)),
                    'households':rows(c,'SELECT * FROM households WHERE wedding_id=? ORDER BY id',(wid,)),
                    'events':rows(c,'SELECT * FROM wedding_events WHERE wedding_id=? ORDER BY id',(wid,)),
                    'tasks':rows(c,'SELECT * FROM tasks WHERE wedding_id=? ORDER BY id',(wid,)),
                    'invitations':rows(c,'SELECT recipient,subject,message,status,created_at FROM invitations WHERE wedding_id=? ORDER BY id',(wid,)),
                    'rsvp_questions':rows(c,'SELECT * FROM rsvp_questions WHERE wedding_id=? ORDER BY id',(wid,)),
                    'budget_items':rows(c,'SELECT * FROM budget_items WHERE wedding_id=? ORDER BY id',(wid,)),
                    'budget_settings':rows(c,'SELECT * FROM budget_settings WHERE wedding_id=?',(wid,)),
                    'seating_tables':rows(c,'SELECT * FROM seating_tables WHERE wedding_id=? ORDER BY id',(wid,)),
                    'supplier_leads':rows(c,'SELECT * FROM supplier_leads WHERE wedding_id=? ORDER BY id',(wid,)),
                    'payments':rows(c,'SELECT plan,status,created_at FROM payments WHERE user_id=? ORDER BY id',(uid,))
                }
                guest_ids=[x['id'] for x in payload['guests']]
                event_ids=[x['id'] for x in payload['events']]
                if guest_ids:
                    marks=','.join('?'*len(guest_ids))
                    payload['rsvp_answers']=rows(c,f'SELECT * FROM rsvp_answers WHERE guest_id IN ({marks})',guest_ids)
                    payload['seating_assignments']=rows(c,f'SELECT * FROM seating_assignments WHERE guest_id IN ({marks})',guest_ids)
                    payload['guest_event_invites']=rows(c,f'SELECT * FROM guest_event_invites WHERE guest_id IN ({marks})',guest_ids)
                    try:payload['rsvp_history']=rows(c,f'SELECT * FROM rsvp_history WHERE guest_id IN ({marks})',guest_ids)
                    except:payload['rsvp_history']=[]
            body=json.dumps(payload,indent=2,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Disposition','attachment; filename="ceremli-data-export.json"');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        return super().do_GET()

    def do_POST(self):
        path=self.path.split('?',1)[0]
        if path in PREMIUM_POST:
            a=self.require(csrf=True)
            if not a:return
            if not allowed(a['plan'],'premium'):
                return self.send_json({'error':'This feature requires Ceremli Premium or Ultimate','upgrade_required':True,'minimum_plan':'premium'},403)
        if path=='/api/account/password':
            a=self.require(csrf=True)
            if not a:return
            d=self.body();current=str(d.get('current_password',''));new=str(d.get('new_password',''))
            if len(new)<8:return self.send_json({'error':'New password must be at least 8 characters'},400)
            with core.conn() as c:
                u=c.execute('SELECT password_hash FROM users WHERE id=?',(a['user_id'],)).fetchone()
                if not u or not core.verify(current,u['password_hash']):return self.send_json({'error':'Current password is incorrect'},400)
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(core.pbkdf(new),a['user_id']))
                tok=self.cookies().get('vowly_session');current_token=tok.value if tok else ''
                c.execute('DELETE FROM sessions WHERE user_id=? AND token<>?',(a['user_id'],current_token))
            return self.send_json({'ok':True})
        if path=='/api/account/delete':
            a=self.require(csrf=True)
            if not a:return
            d=self.body();password=str(d.get('password',''));confirmation=str(d.get('confirmation','')).strip()
            if confirmation!='DELETE':return self.send_json({'error':'Type DELETE to confirm account deletion'},400)
            with core.conn() as c:
                u=c.execute('SELECT password_hash FROM users WHERE id=?',(a['user_id'],)).fetchone()
                if not u or not core.verify(password,u['password_hash']):return self.send_json({'error':'Password is incorrect'},400)
                wid=a['id'];uid=a['user_id'];guest_ids=[r['id'] for r in c.execute('SELECT id FROM guests WHERE wedding_id=?',(wid,)).fetchall()];event_ids=[r['id'] for r in c.execute('SELECT id FROM wedding_events WHERE wedding_id=?',(wid,)).fetchall()];qids=[r['id'] for r in c.execute('SELECT id FROM rsvp_questions WHERE wedding_id=?',(wid,)).fetchall()]
                if guest_ids:
                    marks=','.join('?'*len(guest_ids));c.execute(f'DELETE FROM rsvp_answers WHERE guest_id IN ({marks})',guest_ids);c.execute(f'DELETE FROM guest_event_invites WHERE guest_id IN ({marks})',guest_ids);c.execute(f'DELETE FROM seating_assignments WHERE guest_id IN ({marks})',guest_ids)
                    try:c.execute(f'DELETE FROM rsvp_history WHERE guest_id IN ({marks})',guest_ids)
                    except:pass
                c.execute('DELETE FROM invitations WHERE wedding_id=?',(wid,));c.execute('DELETE FROM supplier_leads WHERE wedding_id=?',(wid,));c.execute('DELETE FROM budget_items WHERE wedding_id=?',(wid,));c.execute('DELETE FROM budget_settings WHERE wedding_id=?',(wid,));c.execute('DELETE FROM seating_assignments WHERE wedding_id=?',(wid,));c.execute('DELETE FROM seating_tables WHERE wedding_id=?',(wid,));c.execute('DELETE FROM rsvp_questions WHERE wedding_id=?',(wid,));c.execute('DELETE FROM wedding_events WHERE wedding_id=?',(wid,));c.execute('DELETE FROM households WHERE wedding_id=?',(wid,));c.execute('DELETE FROM tasks WHERE wedding_id=?',(wid,));c.execute('DELETE FROM wedding_settings WHERE wedding_id=?',(wid,));c.execute('DELETE FROM guests WHERE wedding_id=?',(wid,));c.execute('DELETE FROM payments WHERE user_id=?',(uid,));c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
                try:c.execute('DELETE FROM password_reset_tokens WHERE user_id=?',(uid,))
                except:pass
                c.execute('DELETE FROM weddings WHERE id=?',(wid,));c.execute('DELETE FROM users WHERE id=?',(uid,))
            return self.session_response('',{'ok':True,'deleted':True},expire=True)
        return super().do_POST()

if __name__=='__main__':
    migrate_accounts()
    from http.server import ThreadingHTTPServer
    import os
    port=int(os.environ.get('PORT','8000'))
    print(f'Ceremli launch server on {port}')
    ThreadingHTTPServer(('0.0.0.0',port),LaunchHandler).serve_forever()
