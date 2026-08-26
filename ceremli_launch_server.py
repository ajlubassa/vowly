#!/usr/bin/env python3
"""Ceremli consolidated production server."""
import json, hashlib, secrets, time, urllib.parse, re, os
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import server as core
import ceremli_events_server as events

PLAN_RANK={'free':0,'premium':1,'ultimate':2}
PREMIUM_POST={'/api/invitations/send','/api/reminders/send'}

def allowed(plan,minimum): return PLAN_RANK.get(plan or 'free',0)>=PLAN_RANK[minimum]
def rows(c,sql,args=()): return [dict(x) for x in c.execute(sql,args).fetchall()]
def thash(t): return hashlib.sha256(t.encode()).hexdigest()

def migrate_launch():
    events.core.migrate()
    with core.conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,token_hash TEXT NOT NULL UNIQUE,expires_at INTEGER NOT NULL,used_at TEXT DEFAULT '',created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS wedding_media(wedding_id INTEGER PRIMARY KEY,media_json TEXT NOT NULL DEFAULT '{"party":[],"gallery":[]}')''')

class CeremliLaunchApp(events.CeremliEventsApp):
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/wedding/media':
            a=self.require()
            if not a:return
            with core.conn() as c:r=c.execute('SELECT media_json FROM wedding_media WHERE wedding_id=?',(a['id'],)).fetchone()
            try:data=json.loads(r['media_json']) if r else {'party':[],'gallery':[]}
            except:data={'party':[],'gallery':[]}
            return self.send_json(data)
        m=re.fullmatch(r'/api/public/wedding/([^/]+)/media',path)
        if m:
            slug=urllib.parse.unquote(m.group(1))
            with core.conn() as c:
                w=c.execute('SELECT id FROM weddings WHERE slug=?',(slug,)).fetchone()
                if not w:return self.send_json({'error':'Wedding not found'},404)
                r=c.execute('SELECT media_json FROM wedding_media WHERE wedding_id=?',(w['id'],)).fetchone()
            try:data=json.loads(r['media_json']) if r else {'party':[],'gallery':[]}
            except:data={'party':[],'gallery':[]}
            return self.send_json(data)
        if path=='/api/account/export':
            a=self.require()
            if not a:return
            wid=a['id'];uid=a['user_id']
            with core.conn() as c:
                payload={'exported_at':datetime.now(timezone.utc).isoformat(),'account':{'email':a['email'],'plan':a['plan']},'wedding':{k:a.get(k) for k in ('partner1','partner2','date','venue','story','slug')},'guests':rows(c,'SELECT * FROM guests WHERE wedding_id=? ORDER BY id',(wid,)),'households':rows(c,'SELECT * FROM households WHERE wedding_id=? ORDER BY id',(wid,)),'events':rows(c,'SELECT * FROM wedding_events WHERE wedding_id=? ORDER BY id',(wid,)),'tasks':rows(c,'SELECT * FROM tasks WHERE wedding_id=? ORDER BY id',(wid,)),'invitations':rows(c,'SELECT recipient,subject,message,status,created_at FROM invitations WHERE wedding_id=? ORDER BY id',(wid,)),'budget_items':rows(c,'SELECT * FROM budget_items WHERE wedding_id=? ORDER BY id',(wid,)),'seating_tables':rows(c,'SELECT * FROM seating_tables WHERE wedding_id=? ORDER BY id',(wid,)),'payments':rows(c,'SELECT plan,status,created_at FROM payments WHERE user_id=? ORDER BY id',(uid,))}
                mr=c.execute('SELECT media_json FROM wedding_media WHERE wedding_id=?',(wid,)).fetchone();payload['media']=json.loads(mr['media_json']) if mr else {'party':[],'gallery':[]}
            body=json.dumps(payload,indent=2,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Disposition','attachment; filename="ceremli-data-export.json"');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        return super().do_GET()

    def do_PUT(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/wedding/media':
            a=self.require(csrf=True)
            if not a:return
            d=self.body();party=d.get('party') or [];gallery=d.get('gallery') or []
            if not isinstance(party,list) or not isinstance(gallery,list) or len(party)>20 or len(gallery)>24:return self.send_json({'error':'Too many photos'},400)
            raw=json.dumps({'party':party,'gallery':gallery},separators=(',',':'))
            if len(raw)>12_000_000:return self.send_json({'error':'Wedding photos are too large. Please use fewer or smaller images.'},413)
            with core.conn() as c:c.execute('INSERT INTO wedding_media(wedding_id,media_json) VALUES(?,?) ON CONFLICT(wedding_id) DO UPDATE SET media_json=excluded.media_json',(a['id'],raw))
            return self.send_json({'ok':True})
        return super().do_PUT()

    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path
        if path in PREMIUM_POST:
            a=self.require(csrf=True)
            if not a:return
            if not allowed(a['plan'],'premium'):return self.send_json({'error':'This feature requires Ceremli Premium or Ultimate','upgrade_required':True},403)
        if path=='/api/password/forgot':
            d=self.body();email=str(d.get('email','')).strip().lower();msg={'ok':True,'message':'If an account exists, a reset email will be sent.'}
            if not self.rate_ok('forgot:'+self.client_address[0],5,900):return self.send_json(msg)
            with core.conn() as c:
                u=c.execute('SELECT id,email FROM users WHERE email=?',(email,)).fetchone()
                if u:
                    token=secrets.token_urlsafe(40);now=int(time.time());c.execute('DELETE FROM password_reset_tokens WHERE user_id=? OR expires_at<?',(u['id'],now));c.execute('INSERT INTO password_reset_tokens(user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)',(u['id'],thash(token),now+1800,datetime.now(timezone.utc).isoformat()))
                    try:core.send_email(u['email'],'Reset your Ceremli password',f'Reset your password: {core.BASE_URL}/reset-password.html?token={token}\n\nThis link expires in 30 minutes.')
                    except Exception as e:print('password reset email failed',e)
            return self.send_json(msg)
        if path=='/api/password/reset':
            d=self.body();token=str(d.get('token',''));pw=str(d.get('password',''))
            if len(pw)<8:return self.send_json({'error':'Password must be at least 8 characters'},400)
            with core.conn() as c:
                r=c.execute('SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at="" AND expires_at>?',(thash(token),int(time.time()))).fetchone()
                if not r:return self.send_json({'error':'This reset link is invalid or has expired'},400)
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(core.pbkdf(pw),r['user_id']));c.execute('UPDATE password_reset_tokens SET used_at=? WHERE id=?',(datetime.now(timezone.utc).isoformat(),r['id']));c.execute('DELETE FROM sessions WHERE user_id=?',(r['user_id'],))
            return self.send_json({'ok':True})
        if path=='/api/account/password':
            a=self.require(csrf=True)
            if not a:return
            d=self.body();current=str(d.get('current_password',''));new=str(d.get('new_password',''))
            if len(new)<8:return self.send_json({'error':'New password must be at least 8 characters'},400)
            with core.conn() as c:
                u=c.execute('SELECT password_hash FROM users WHERE id=?',(a['user_id'],)).fetchone()
                if not u or not core.verify(current,u['password_hash']):return self.send_json({'error':'Current password is incorrect'},400)
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(core.pbkdf(new),a['user_id']));tok=self.cookies().get('vowly_session');current_token=tok.value if tok else '';c.execute('DELETE FROM sessions WHERE user_id=? AND token<>?',(a['user_id'],current_token))
            return self.send_json({'ok':True})
        return super().do_POST()

if __name__=='__main__':
    migrate_launch();core.os.chdir(core.ROOT);print(f'Ceremli launch server on {core.PORT} | DB={core.DB}');ThreadingHTTPServer(('0.0.0.0',core.PORT),CeremliLaunchApp).serve_forever()
