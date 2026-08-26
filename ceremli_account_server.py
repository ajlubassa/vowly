"""Ceremli account and password recovery layer."""
import json, re, secrets, time, hashlib
from datetime import datetime, timezone
import server as core
from ceremli_household_server import HouseholdHandler


def migrate_accounts():
    with core.conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          token_hash TEXT NOT NULL UNIQUE,
          expires_at INTEGER NOT NULL,
          used_at TEXT DEFAULT '',
          created_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_hash ON password_reset_tokens(token_hash)')


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def send_reset_email(email, url):
    if not core.RESEND_API_KEY:
        return False
    subject='Reset your Ceremli password'
    message=f'''We received a request to reset your Ceremli password.\n\nReset your password: {url}\n\nThis link expires in 30 minutes. If you did not request this, you can ignore this email.'''
    return core.send_email(email, subject, message)


class AccountHandler(HouseholdHandler):
    def do_POST(self):
        path=self.path.split('?',1)[0]
        if path=='/api/password/forgot':
            if not self.rate_ok('forgot:'+self.client_address[0],5,900):
                return self.send_json({'ok':True,'message':'If an account exists, a reset email will be sent.'})
            d=self.body(); email=str(d.get('email','')).strip().lower()
            # Always return the same response to avoid exposing registered emails.
            with core.conn() as c:
                u=c.execute('SELECT id,email FROM users WHERE email=?',(email,)).fetchone()
                if u:
                    raw=secrets.token_urlsafe(40); now=int(time.time());
                    c.execute('DELETE FROM password_reset_tokens WHERE user_id=? OR expires_at<?',(u['id'],now))
                    c.execute('INSERT INTO password_reset_tokens(user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)',(u['id'],token_hash(raw),now+1800,datetime.now(timezone.utc).isoformat()))
                    url=f'{core.BASE_URL}/reset-password.html?token={raw}'
                    try: send_reset_email(u['email'],url)
                    except Exception as e: print('password reset email failed',e)
            return self.send_json({'ok':True,'message':'If an account exists, a reset email will be sent.'})
        if path=='/api/password/reset':
            d=self.body(); raw=str(d.get('token','')); pw=str(d.get('password',''))
            if len(pw)<8:return self.send_json({'error':'Password must be at least 8 characters'},400)
            if len(raw)<20:return self.send_json({'error':'This reset link is invalid or has expired'},400)
            now=int(time.time()); h=token_hash(raw)
            with core.conn() as c:
                r=c.execute('SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at="" AND expires_at>?',(h,now)).fetchone()
                if not r:return self.send_json({'error':'This reset link is invalid or has expired'},400)
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(core.pbkdf(pw),r['user_id']))
                c.execute('UPDATE password_reset_tokens SET used_at=? WHERE id=?',(datetime.now(timezone.utc).isoformat(),r['id']))
                c.execute('DELETE FROM sessions WHERE user_id=?',(r['user_id'],))
            return self.send_json({'ok':True})
        return super().do_POST()


if __name__=='__main__':
    migrate_accounts()
    from http.server import ThreadingHTTPServer
    port=int(__import__('os').environ.get('PORT','8000'))
    print(f'Ceremli account server on {port}')
    ThreadingHTTPServer(('0.0.0.0',port),AccountHandler).serve_forever()
