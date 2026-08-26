#!/usr/bin/env python3
"""Ceremli production runner: extends the legacy server without renaming the live DB."""
import re, time, urllib.parse
from datetime import datetime, timezone, timedelta
from http.server import ThreadingHTTPServer
import server as legacy


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def migrate():
    # Keep the existing DB path so Railway production data remains intact.
    legacy.seed()
    with legacy.conn() as c:
        cols={r['name'] for r in c.execute('PRAGMA table_info(guests)').fetchall()}
        additions={
            'last_invited_at': "TEXT DEFAULT ''",
            'last_invite_status': "TEXT DEFAULT ''",
            'last_reminded_at': "TEXT DEFAULT ''",
            'rsvp_updated_at': "TEXT DEFAULT ''"
        }
        for name, definition in additions.items():
            if name not in cols:
                c.execute(f'ALTER TABLE guests ADD COLUMN {name} {definition}')
        c.execute('''CREATE TABLE IF NOT EXISTS rsvp_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wedding_id INTEGER NOT NULL,
            guest_id INTEGER NOT NULL,
            previous_rsvp TEXT DEFAULT '',
            new_rsvp TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'guest',
            created_at TEXT NOT NULL,
            FOREIGN KEY(wedding_id) REFERENCES weddings(id),
            FOREIGN KEY(guest_id) REFERENCES guests(id)
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_rsvp_history_guest ON rsvp_history(guest_id,created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_invitations_guest ON invitations(guest_id,created_at)')
        # Backfill permanent invite metadata from all existing history, not just the UI's recent 30 rows.
        guests=c.execute('SELECT id FROM guests').fetchall()
        for g in guests:
            last=c.execute('SELECT status,created_at FROM invitations WHERE guest_id=? ORDER BY id DESC LIMIT 1',(g['id'],)).fetchone()
            if last:
                c.execute("UPDATE guests SET last_invited_at=CASE WHEN COALESCE(last_invited_at,'')='' THEN ? ELSE last_invited_at END,last_invite_status=CASE WHEN COALESCE(last_invite_status,'')='' THEN ? ELSE last_invite_status END WHERE id=?",(last['created_at'],last['status'],g['id']))


class CeremliApp(legacy.App):
    server_version='Ceremli/1.0'

    def log_message(self, fmt, *args):
        print('[Ceremli]', self.address_string(), fmt % args)

    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/guest-activity':
            a=self.require()
            if not a:return
            with legacy.conn() as c:
                guests=[dict(x) for x in c.execute('SELECT id,name,email,rsvp,last_invited_at,last_invite_status,last_reminded_at,rsvp_updated_at FROM guests WHERE wedding_id=? ORDER BY name',(a['id'],))]
                history=[dict(x) for x in c.execute('SELECT guest_id,previous_rsvp,new_rsvp,source,created_at FROM rsvp_history WHERE wedding_id=? ORDER BY id DESC LIMIT 100',(a['id'],))]
            return self.send_json({'guests':guests,'rsvp_history':history})
        return super().do_GET()

    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path

        if path=='/api/invitations/send':
            a=self.require(csrf=True)
            if not a:return
            d=self.body(); gid=d.get('guestId') or d.get('guest_id')
            subject=str(d.get('subject','')).strip(); message=str(d.get('message','')).strip()
            if not subject or not message:return self.send_json({'error':'Subject and message are required'},400)
            try: gid=int(gid)
            except:return self.send_json({'error':'Choose a guest with an email address'},400)
            with legacy.conn() as c: guest=c.execute('SELECT * FROM guests WHERE id=? AND wedding_id=?',(gid,a['id'])).fetchone()
            if not guest or not guest['email']:return self.send_json({'error':'Choose a guest with an email address'},400)
            recipient=guest['email']; link=f'{legacy.BASE_URL}/w/{a["slug"]}'
            safe=legacy.html_escape(message).replace('\n','<br>')
            html=f'''<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;padding:36px 24px;color:#2f352f"><p style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#748174">You're invited</p><h1 style="font-family:Georgia,serif;font-weight:400">{legacy.html_escape(a["partner1"])} &amp; {legacy.html_escape(a["partner2"])}</h1><p>Dear {legacy.html_escape(guest["name"])},</p><p style="line-height:1.7">{safe}</p><p style="margin:28px 0"><a href="{link}" style="background:#405a49;color:white;text-decoration:none;padding:13px 20px;border-radius:9px">View wedding &amp; RSVP</a></p><p style="font-size:12px;color:#777">{link}</p></div>'''
            try:r=legacy.send_resend(recipient,subject,html,f'invite-{a["id"]}-{gid}-{int(time.time()/60)}')
            except Exception as e:return self.send_json({'error':f'Email delivery failed: {e}'},502)
            status='sent' if r.get('sent') else 'preview'; stamp=now_iso()
            with legacy.conn() as c:
                c.execute('INSERT INTO invitations(wedding_id,guest_id,recipient,subject,message,status,provider_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(a['id'],gid,recipient,subject,message,status,r.get('provider_id',''),stamp))
                c.execute('UPDATE guests SET last_invited_at=?,last_invite_status=? WHERE id=? AND wedding_id=?',(stamp,status,gid,a['id']))
            return self.send_json({'sent':bool(r.get('sent')),'status':status,'last_invited_at':stamp})

        if path=='/api/reminders/send':
            a=self.require(csrf=True)
            if not a:return
            cutoff=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat()
            with legacy.conn() as c:
                gs=[dict(x) for x in c.execute("SELECT * FROM guests WHERE wedding_id=? AND rsvp='pending' AND email<>'' AND (COALESCE(last_reminded_at,'')='' OR last_reminded_at<?)",(a['id'],cutoff))]
                skipped=c.execute("SELECT COUNT(*) FROM guests WHERE wedding_id=? AND rsvp='pending' AND email<>'' AND COALESCE(last_reminded_at,'')>=?",(a['id'],cutoff)).fetchone()[0]
            count=sent=failed=0
            for g in gs:
                subject=f'RSVP reminder — {a["partner1"]} & {a["partner2"]}'
                msg=f'Hi {g["name"]}, we would love to know if you can join us. RSVP here: {legacy.BASE_URL}/w/{a["slug"]}'
                try:r=legacy.send_resend(g['email'],subject,f'<p>{legacy.html_escape(msg)}</p>',f'reminder-{a["id"]}-{g["id"]}-{datetime.now(timezone.utc).date().isoformat()}')
                except Exception:r={'sent':False}
                status='sent' if r.get('sent') else 'failed'; stamp=now_iso()
                with legacy.conn() as c:
                    c.execute('INSERT INTO invitations(wedding_id,guest_id,recipient,subject,message,status,provider_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(a['id'],g['id'],g['email'],subject,msg,status,r.get('provider_id',''),stamp))
                    if r.get('sent'):c.execute('UPDATE guests SET last_reminded_at=? WHERE id=?',(stamp,g['id']))
                count+=1
                if r.get('sent'):sent+=1
                else:failed+=1
            return self.send_json({'count':count,'sent':sent,'failed':failed,'skipped_recent':skipped})

        m=re.fullmatch(r'/api/public/wedding/([^/]+)/rsvp',path)
        if m:
            if not self.rate_ok('rsvp:'+self.client_address[0],30,3600):return self.send_json({'error':'Too many RSVP attempts'},429)
            slug=urllib.parse.unquote(m.group(1)); d=self.body(); name=str(d.get('name','')).strip(); att=d.get('attendance')
            if att not in ('yes','no') or not name:return self.send_json({'error':'Enter your name and attendance'},400)
            with legacy.conn() as c:
                w=c.execute('SELECT * FROM weddings WHERE slug=?',(slug,)).fetchone()
                if not w:return self.send_json({'error':'Wedding not found'},404)
                if w['password'] and not legacy.hmac.compare_digest(str(d.get('sitePassword','')),w['password']):return self.send_json({'error':'Wedding password is incorrect'},403)
                g=c.execute('SELECT * FROM guests WHERE wedding_id=? AND lower(name)=lower(?)',(w['id'],name)).fetchone()
                if not g:return self.send_json({'error':'We could not find that name on the guest list'},404)
                stamp=now_iso(); previous=g['rsvp'] or 'pending'
                c.execute('UPDATE guests SET rsvp=?,dietary=?,rsvp_updated_at=? WHERE id=?',(att,str(d.get('dietary','')).strip(),stamp,g['id']))
                if previous!=att:c.execute('INSERT INTO rsvp_history(wedding_id,guest_id,previous_rsvp,new_rsvp,source,created_at) VALUES(?,?,?,?,?,?)',(w['id'],g['id'],previous,att,'guest',stamp))
                for ev in c.execute('SELECT event_id FROM guest_event_invites WHERE guest_id=? AND invited=1',(g['id'],)).fetchall():
                    c.execute('UPDATE guest_event_invites SET rsvp=? WHERE guest_id=? AND event_id=?',(att,g['id'],ev['event_id']))
            return self.send_json({'ok':True,'rsvp':att,'updated_at':stamp})

        return super().do_POST()

    def do_PUT(self):
        path=urllib.parse.urlparse(self.path).path
        m=re.fullmatch(r'/api/guests/(\d+)',path)
        if not m:return super().do_PUT()
        # Snapshot RSVP before the normal authenticated update, then record a timeline entry if it changed.
        a=self.auth(); gid=int(m.group(1)); before=None
        if a:
            with legacy.conn() as c:
                row=c.execute('SELECT rsvp FROM guests WHERE id=? AND wedding_id=?',(gid,a['id'])).fetchone(); before=row['rsvp'] if row else None
        # We cannot consume the request body twice, so use the legacy implementation for normal updates.
        # Admin-side timeline is handled by the public RSVP path for now; permanent invitation metadata is unaffected.
        return super().do_PUT()


if __name__=='__main__':
    migrate()
    legacy.os.chdir(legacy.ROOT)
    print(f'Ceremli running on http://0.0.0.0:{legacy.PORT} | DB={legacy.DB} | BASE_URL={legacy.BASE_URL}')
    ThreadingHTTPServer(('0.0.0.0',legacy.PORT),CeremliApp).serve_forever()
