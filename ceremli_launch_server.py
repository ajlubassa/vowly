"""Ceremli launch server: household RSVP + password recovery + account security."""
import time
import server as core
from ceremli_account_server import AccountHandler, migrate_accounts

class LaunchHandler(AccountHandler):
    def do_POST(self):
        path=self.path.split('?',1)[0]
        if path=='/api/account/password':
            a=self.require(csrf=True)
            if not a:return
            d=self.body();current=str(d.get('current_password',''));new=str(d.get('new_password',''))
            if len(new)<8:return self.send_json({'error':'New password must be at least 8 characters'},400)
            with core.conn() as c:
                u=c.execute('SELECT password_hash FROM users WHERE id=?',(a['user_id'],)).fetchone()
                if not u or not core.verify(current,u['password_hash']):return self.send_json({'error':'Current password is incorrect'},400)
                c.execute('UPDATE users SET password_hash=? WHERE id=?',(core.pbkdf(new),a['user_id']))
                # Keep the current session but invalidate every other device/session.
                tok=self.cookies().get('vowly_session'); current_token=tok.value if tok else ''
                c.execute('DELETE FROM sessions WHERE user_id=? AND token<>?',(a['user_id'],current_token))
            return self.send_json({'ok':True})
        return super().do_POST()

if __name__=='__main__':
    migrate_accounts()
    from http.server import ThreadingHTTPServer
    import os
    port=int(os.environ.get('PORT','8000'))
    print(f'Ceremli launch server on {port}')
    ThreadingHTTPServer(('0.0.0.0',port),LaunchHandler).serve_forever()
