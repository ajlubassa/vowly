"""Ceremli launch server: household RSVP, account security and plan entitlements."""
import server as core
from ceremli_account_server import AccountHandler, migrate_accounts

PLAN_RANK={'free':0,'premium':1,'ultimate':2}
# Server-side gates for features that create/send paid functionality.
PREMIUM_POST={'/api/invitations/send','/api/reminders/send'}

def allowed(plan,minimum): return PLAN_RANK.get(plan or 'free',0)>=PLAN_RANK[minimum]

class LaunchHandler(AccountHandler):
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
        return super().do_POST()

if __name__=='__main__':
    migrate_accounts()
    from http.server import ThreadingHTTPServer
    import os
    port=int(os.environ.get('PORT','8000'))
    print(f'Ceremli launch server on {port}')
    ThreadingHTTPServer(('0.0.0.0',port),LaunchHandler).serve_forever()
