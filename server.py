#!/usr/bin/env python3
import os, re, io, json, time, hmac, hashlib, sqlite3, secrets, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from datetime import datetime, timedelta, timezone

ROOT=Path(__file__).resolve().parent
VOLUME_PATH=os.getenv('RAILWAY_VOLUME_MOUNT_PATH','').strip()
default_db=(Path(VOLUME_PATH)/'vowly.db') if VOLUME_PATH else (ROOT/'vowly.db')
DB=Path(os.getenv('SQLITE_PATH', str(default_db)))
DB.parent.mkdir(parents=True, exist_ok=True)
PORT=int(os.getenv('PORT','8000'))
railway_domain=os.getenv('RAILWAY_PUBLIC_DOMAIN','').strip()
default_base=(f'https://{railway_domain}' if railway_domain else f'http://localhost:{PORT}')
BASE_URL=os.getenv('BASE_URL',default_base).rstrip('/')
APP_ENV=os.getenv('APP_ENV','development')
STRIPE_SECRET_KEY=os.getenv('STRIPE_SECRET_KEY','')
STRIPE_WEBHOOK_SECRET=os.getenv('STRIPE_WEBHOOK_SECRET','')
STRIPE_PREMIUM_PRICE_ID=os.getenv('STRIPE_PREMIUM_PRICE_ID','')
STRIPE_ULTIMATE_PRICE_ID=os.getenv('STRIPE_ULTIMATE_PRICE_ID','')
RESEND_API_KEY=os.getenv('RESEND_API_KEY','')
EMAIL_FROM=os.getenv('EMAIL_FROM','Vowly <onboarding@resend.dev>')
DEMO_MODE=os.getenv('DEMO_MODE','true').lower() in ('1','true','yes')
RATE={}

SCHEMA='''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,plan TEXT NOT NULL DEFAULT 'free',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS weddings(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER UNIQUE NOT NULL,partner1 TEXT NOT NULL,partner2 TEXT NOT NULL,date TEXT NOT NULL,venue TEXT NOT NULL,story TEXT DEFAULT '',slug TEXT UNIQUE NOT NULL,password TEXT DEFAULT '',FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS guests(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,name TEXT NOT NULL,email TEXT DEFAULT '',group_name TEXT DEFAULT 'Other',plus_one INTEGER DEFAULT 0,rsvp TEXT DEFAULT 'pending',dietary TEXT DEFAULT '',FOREIGN KEY(wedding_id) REFERENCES weddings(id));
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,title TEXT NOT NULL,due TEXT DEFAULT '',done INTEGER DEFAULT 0,FOREIGN KEY(wedding_id) REFERENCES weddings(id));
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,csrf TEXT NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS invitations(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,guest_id INTEGER,recipient TEXT,subject TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL,provider_id TEXT DEFAULT '',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT NOT NULL,location TEXT NOT NULL,description TEXT NOT NULL,price_from INTEGER DEFAULT 0,email TEXT DEFAULT '',featured INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS supplier_leads(id INTEGER PRIMARY KEY AUTOINCREMENT,supplier_id INTEGER NOT NULL,wedding_id INTEGER NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'new',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,plan TEXT NOT NULL,stripe_session_id TEXT UNIQUE,status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS wedding_settings(wedding_id INTEGER PRIMARY KEY,theme TEXT NOT NULL DEFAULT 'editorial',accent TEXT NOT NULL DEFAULT 'sage',hero_title TEXT DEFAULT '',schedule TEXT DEFAULT '',travel TEXT DEFAULT '',faq TEXT DEFAULT '',registry TEXT DEFAULT '',show_story INTEGER DEFAULT 1,show_schedule INTEGER DEFAULT 1,show_travel INTEGER DEFAULT 1,show_faq INTEGER DEFAULT 1,show_registry INTEGER DEFAULT 1,FOREIGN KEY(wedding_id) REFERENCES weddings(id));
CREATE TABLE IF NOT EXISTS households(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,name TEXT NOT NULL,notes TEXT DEFAULT '',FOREIGN KEY(wedding_id) REFERENCES weddings(id));
CREATE TABLE IF NOT EXISTS wedding_events(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,name TEXT NOT NULL,event_date TEXT DEFAULT '',start_time TEXT DEFAULT '',venue TEXT DEFAULT '',description TEXT DEFAULT '',rsvp_deadline TEXT DEFAULT '',is_primary INTEGER DEFAULT 0,FOREIGN KEY(wedding_id) REFERENCES weddings(id));
CREATE TABLE IF NOT EXISTS guest_event_invites(id INTEGER PRIMARY KEY AUTOINCREMENT,guest_id INTEGER NOT NULL,event_id INTEGER NOT NULL,invited INTEGER DEFAULT 1,rsvp TEXT DEFAULT 'pending',UNIQUE(guest_id,event_id),FOREIGN KEY(guest_id) REFERENCES guests(id),FOREIGN KEY(event_id) REFERENCES wedding_events(id));
CREATE TABLE IF NOT EXISTS rsvp_questions(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,prompt TEXT NOT NULL,question_type TEXT NOT NULL DEFAULT 'text',required INTEGER DEFAULT 0,options TEXT DEFAULT '',sort_order INTEGER DEFAULT 0,FOREIGN KEY(wedding_id) REFERENCES weddings(id));
CREATE TABLE IF NOT EXISTS rsvp_answers(id INTEGER PRIMARY KEY AUTOINCREMENT,guest_id INTEGER NOT NULL,question_id INTEGER NOT NULL,answer TEXT DEFAULT '',UNIQUE(guest_id,question_id),FOREIGN KEY(guest_id) REFERENCES guests(id),FOREIGN KEY(question_id) REFERENCES rsvp_questions(id));
CREATE TABLE IF NOT EXISTS seating_tables(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,name TEXT NOT NULL,capacity INTEGER NOT NULL DEFAULT 8,shape TEXT NOT NULL DEFAULT 'round',sort_order INTEGER DEFAULT 0,FOREIGN KEY(wedding_id) REFERENCES weddings(id));
CREATE TABLE IF NOT EXISTS seating_assignments(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,guest_id INTEGER UNIQUE NOT NULL,table_id INTEGER NOT NULL,seat_number INTEGER DEFAULT 0,FOREIGN KEY(wedding_id) REFERENCES weddings(id),FOREIGN KEY(guest_id) REFERENCES guests(id),FOREIGN KEY(table_id) REFERENCES seating_tables(id));
CREATE TABLE IF NOT EXISTS budget_items(id INTEGER PRIMARY KEY AUTOINCREMENT,wedding_id INTEGER NOT NULL,category TEXT NOT NULL,name TEXT NOT NULL,planned REAL DEFAULT 0,actual REAL DEFAULT 0,paid REAL DEFAULT 0,due_date TEXT DEFAULT '',supplier TEXT DEFAULT '',notes TEXT DEFAULT '',FOREIGN KEY(wedding_id) REFERENCES weddings(id));
'''

def conn():
    c=sqlite3.connect(DB,timeout=10); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def pbkdf(password,salt=None):
    salt=salt or secrets.token_bytes(16); dk=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,220000); return f'pbkdf2_sha256$220000${salt.hex()}${dk.hex()}'
def verify(password,stored):
    try:
        _,rounds,salt,dk=stored.split('$'); got=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds)); return hmac.compare_digest(got.hex(),dk)
    except: return False

def slugify(s):
    s=re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-'); return s or secrets.token_hex(4)
def unique_slug(c,base):
    s=base; n=2
    while c.execute('SELECT 1 FROM weddings WHERE slug=?',(s,)).fetchone(): s=f'{base}-{n}'; n+=1
    return s

def seed():
    with conn() as c:
        c.executescript(SCHEMA)
        cols=[r['name'] for r in c.execute("PRAGMA table_info(guests)").fetchall()]
        if 'household_id' not in cols:c.execute('ALTER TABLE guests ADD COLUMN household_id INTEGER')
        if 'notes' not in cols:c.execute("ALTER TABLE guests ADD COLUMN notes TEXT DEFAULT ''")
        if not c.execute('SELECT 1 FROM users WHERE email=?',('demo@vowly.local',)).fetchone():
            now=datetime.now(timezone.utc).isoformat(); cur=c.execute('INSERT INTO users(email,password_hash,plan,created_at) VALUES(?,?,?,?)',('demo@vowly.local',pbkdf('demo123'),'free',now)); uid=cur.lastrowid
            w=c.execute('INSERT INTO weddings(user_id,partner1,partner2,date,venue,story,slug,password) VALUES(?,?,?,?,?,?,?,?)',(uid,'Amelia','Noah','2027-06-18','The Orangery, London','We met in London and cannot wait to celebrate this next chapter with our favourite people.','amelia-noah','')).lastrowid
            guests=[('Maya Thompson','maya@example.com','Friends',1,'pending',''),('Daniel Harris','daniel@example.com','Family',0,'yes','Vegetarian'),('Sofia Bennett','sofia@example.com','Friends',1,'pending','')]
            c.executemany('INSERT INTO guests(wedding_id,name,email,group_name,plus_one,rsvp,dietary) VALUES(?,?,?,?,?,?,?)',[(w,*g) for g in guests])
            tasks=[('Confirm ceremony venue','Done',1),('Finalise guest list','Today',0),('Book photographer','5 Sep',0),('Send save the dates','18 Sep',0),('Choose florist','30 Sep',0)]
            c.executemany('INSERT INTO tasks(wedding_id,title,due,done) VALUES(?,?,?,?)',[(w,*t) for t in tasks])
        if c.execute('SELECT COUNT(*) FROM suppliers').fetchone()[0]==0:
            rows=[('North & Pine Photo','Photography','London','Relaxed editorial wedding photography with full-day coverage.',1600,'supplier@example.com',1),('Bloom & Stem','Florist','London','Seasonal ceremony and reception florals.',850,'supplier@example.com',1),('Afterglow Films','Videography','London','Cinematic wedding films and highlight edits.',1450,'supplier@example.com',0),('The Vinyl Social','DJ','London','Open-format wedding DJ with lighting packages.',700,'supplier@example.com',0),('Sugar & Ivory','Cakes','London','Modern tiered wedding cakes and tasting boxes.',420,'supplier@example.com',0)]
            c.executemany('INSERT INTO suppliers(name,category,location,description,price_from,email,featured) VALUES(?,?,?,?,?,?,?)',rows)
        c.execute("INSERT OR IGNORE INTO wedding_settings(wedding_id) SELECT id FROM weddings")
        for wr in c.execute('SELECT id,date,venue FROM weddings').fetchall():
            if not c.execute('SELECT 1 FROM wedding_events WHERE wedding_id=?',(wr['id'],)).fetchone():
                eid=c.execute('INSERT INTO wedding_events(wedding_id,name,event_date,start_time,venue,description,is_primary) VALUES(?,?,?,?,?,?,1)',(wr['id'],'Wedding day',wr['date'],'14:00',wr['venue'],'Ceremony and celebration')).lastrowid
                for gr in c.execute('SELECT id FROM guests WHERE wedding_id=?',(wr['id'],)).fetchall():
                    c.execute('INSERT OR IGNORE INTO guest_event_invites(guest_id,event_id,invited,rsvp) VALUES(?,?,1,(SELECT rsvp FROM guests WHERE id=?))',(gr['id'],eid,gr['id']))

        for wr in c.execute('SELECT id FROM weddings').fetchall():
            if not c.execute('SELECT 1 FROM seating_tables WHERE wedding_id=?',(wr['id'],)).fetchone():
                c.execute('INSERT INTO seating_tables(wedding_id,name,capacity,shape,sort_order) VALUES(?,?,?,?,?)',(wr['id'],'Table 1',8,'round',1))
            if not c.execute('SELECT 1 FROM budget_items WHERE wedding_id=?',(wr['id'],)).fetchone():
                c.executemany('INSERT INTO budget_items(wedding_id,category,name,planned,actual,paid,due_date,supplier,notes) VALUES(?,?,?,?,?,?,?,?,?)',[
                    (wr['id'],'Venue','Venue & catering',8000,0,0,'','',''),
                    (wr['id'],'Photography','Photographer',1800,0,0,'','',''),
                    (wr['id'],'Flowers','Florals & décor',1200,0,0,'','','')
                ])

def json_bytes(x): return json.dumps(x,separators=(',',':')).encode()
def send_resend(to,subject,html,idempotency=None):
    if not RESEND_API_KEY: return {'sent':False,'preview':True}
    body=json_bytes({'from':EMAIL_FROM,'to':[to],'subject':subject,'html':html})
    req=urllib.request.Request('https://api.resend.com/emails',data=body,method='POST',headers={'Authorization':f'Bearer {RESEND_API_KEY}','Content-Type':'application/json'})
    if idempotency: req.add_header('Idempotency-Key',idempotency)
    with urllib.request.urlopen(req,timeout=15) as r: out=json.loads(r.read())
    return {'sent':True,'provider_id':out.get('id','')}

def stripe_checkout(plan,user_id):
    price={'premium':STRIPE_PREMIUM_PRICE_ID,'ultimate':STRIPE_ULTIMATE_PRICE_ID}.get(plan,'')
    if not STRIPE_SECRET_KEY or not price: return None
    data=urllib.parse.urlencode({'mode':'payment','success_url':f'{BASE_URL}/pricing.html?checkout=success','cancel_url':f'{BASE_URL}/pricing.html?checkout=cancelled','line_items[0][price]':price,'line_items[0][quantity]':'1','metadata[user_id]':str(user_id),'metadata[plan]':plan}).encode()
    req=urllib.request.Request('https://api.stripe.com/v1/checkout/sessions',data=data,method='POST',headers={'Authorization':f'Bearer {STRIPE_SECRET_KEY}','Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=15) as r: return json.loads(r.read())

def verify_stripe_sig(payload,header):
    if not STRIPE_WEBHOOK_SECRET: return False
    parts={}
    for item in header.split(','):
        if '=' in item:
            k,v=item.split('=',1); parts.setdefault(k,[]).append(v)
    try: ts=int(parts['t'][0])
    except: return False
    if abs(time.time()-ts)>300:return False
    signed=f'{ts}.'.encode()+payload; expected=hmac.new(STRIPE_WEBHOOK_SECRET.encode(),signed,hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected,s) for s in parts.get('v1',[]))

class App(SimpleHTTPRequestHandler):
    server_version='Vowly/5'
    def end_headers(self):
        path=urllib.parse.urlparse(self.path).path
        if path.endswith(('.html','.js','.css')) or path=='/':
            self.send_header('Cache-Control','no-cache, no-store, must-revalidate')
            self.send_header('Pragma','no-cache')
            self.send_header('Expires','0')
        super().end_headers()

    def log_message(self,fmt,*args): print('[Vowly]',fmt%args)
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY'); self.send_header('Referrer-Policy','strict-origin-when-cross-origin'); self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()');
        if APP_ENV=='production': self.send_header('Strict-Transport-Security','max-age=31536000; includeSubDomains')
        super().end_headers()
    def translate_path(self,path):
        rel=urllib.parse.urlparse(path).path.lstrip('/') or 'index.html'; return str(ROOT/rel)
    def send_json(self,obj,status=200,headers=None):
        b=json_bytes(obj); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); [self.send_header(k,v) for k,v in (headers or {}).items()]; self.end_headers(); self.wfile.write(b)
    def body(self,raw=False):
        n=int(self.headers.get('Content-Length','0')); data=self.rfile.read(n)
        if raw:return data
        try:return json.loads(data or b'{}')
        except:return {}
    def cookies(self):
        c=SimpleCookie(); c.load(self.headers.get('Cookie','')); return c
    def auth(self):
        tok=self.cookies().get('vowly_session'); tok=tok.value if tok else ''
        if not tok:return None
        with conn() as c:
            r=c.execute('SELECT s.token,s.user_id,s.csrf,u.email,u.plan,w.* FROM sessions s JOIN users u ON u.id=s.user_id JOIN weddings w ON w.user_id=u.id WHERE s.token=? AND s.expires_at>?',(tok,int(time.time()))).fetchone(); return dict(r) if r else None
    def require(self,csrf=False):
        a=self.auth()
        if not a:self.send_json({'error':'Authentication required'},401); return None
        if csrf and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),a['csrf']):self.send_json({'error':'Invalid CSRF token'},403); return None
        return a
    def rate_ok(self,key,limit=20,window=60):
        now=time.time(); xs=[t for t in RATE.get(key,[]) if now-t<window]
        if len(xs)>=limit:return False
        xs.append(now); RATE[key]=xs; return True
    def do_GET(self):
        p=urllib.parse.urlparse(self.path); path=p.path
        if path=='/health':
            try:
                with conn() as c: c.execute('SELECT 1').fetchone()
                return self.send_json({'ok':True,'stage':5,'database':'sqlite','base_url':BASE_URL})
            except Exception as e:
                return self.send_json({'ok':False,'error':str(e)},503)
        if path=='/health': return self.send_json({'ok':True,'service':'vowly','stage':4})
        if path=='/api/me':
            a=self.require();
            if not a:return
            return self.send_json({'email':a['email'],'plan':a['plan'],'csrf':a['csrf'],'wedding':{k:a[k] for k in ('id','partner1','partner2','date','venue','story','slug','password')}})
        if path=='/api/dashboard':
            a=self.require();
            if not a:return
            with conn() as c:
                gs=c.execute('SELECT rsvp,COUNT(*) n FROM guests WHERE wedding_id=? GROUP BY rsvp',(a['id'],)).fetchall(); counts={r['rsvp']:r['n'] for r in gs}; total=sum(counts.values()); ts=[dict(x) for x in c.execute('SELECT * FROM tasks WHERE wedding_id=? ORDER BY id',(a['id'],))]; done=sum(x['done'] for x in ts); progress=round(done/len(ts)*100) if ts else 0
            
            with conn() as c: ws=c.execute('SELECT * FROM wedding_settings WHERE wedding_id=?',(a['id'],)).fetchone()
            return self.send_json({'wedding':{k:a[k] for k in ('partner1','partner2','date','venue','story','slug')},'settings':dict(ws) if ws else {},'stats':{'total':total,'yes':counts.get('yes',0),'pending':counts.get('pending',0),'no':counts.get('no',0),'progress':progress},'tasks':ts})
        if path=='/api/guests':
            a=self.require();
            if not a:return
            with conn() as c:
                rows=[dict(x) for x in c.execute('SELECT g.*,h.name household_name FROM guests g LEFT JOIN households h ON h.id=g.household_id WHERE g.wedding_id=? ORDER BY g.name',(a['id'],))]
                evs=[dict(x) for x in c.execute('SELECT * FROM wedding_events WHERE wedding_id=? ORDER BY event_date,start_time,id',(a['id'],))]
                inv=[dict(x) for x in c.execute('SELECT gei.guest_id,gei.event_id,gei.invited,gei.rsvp FROM guest_event_invites gei JOIN guests g ON g.id=gei.guest_id WHERE g.wedding_id=?',(a['id'],))]
            invite_map={}
            for x in inv: invite_map.setdefault(x['guest_id'],[]).append(x)
            for r in rows:
                r['plus_one']=bool(r['plus_one']);r['events']=invite_map.get(r['id'],[])
            return self.send_json({'guests':rows,'events':evs})
        if path=='/api/tasks':
            a=self.require();
            if not a:return
            with conn() as c: rows=[dict(x) for x in c.execute('SELECT * FROM tasks WHERE wedding_id=? ORDER BY id',(a['id'],))]
            for r in rows:r['done']=bool(r['done'])
            return self.send_json(rows)
        if path=='/api/invitations':
            a=self.require();
            if not a:return
            with conn() as c: hist=[dict(x) for x in c.execute('SELECT recipient,subject,status,created_at FROM invitations WHERE wedding_id=? ORDER BY id DESC LIMIT 20',(a['id'],))]; guests=[dict(x) for x in c.execute('SELECT id,name,email,rsvp FROM guests WHERE wedding_id=? ORDER BY name',(a['id'],))]
            return self.send_json({'history':hist,'guests':guests,'email_live':bool(RESEND_API_KEY)})
        if path=='/api/households':
            a=self.require();
            if not a:return
            with conn() as c: rows=[dict(x) for x in c.execute('SELECT h.*,COUNT(g.id) guest_count FROM households h LEFT JOIN guests g ON g.household_id=h.id WHERE h.wedding_id=? GROUP BY h.id ORDER BY h.name',(a['id'],))]
            return self.send_json(rows)
        if path=='/api/events':
            a=self.require();
            if not a:return
            with conn() as c: rows=[dict(x) for x in c.execute('SELECT * FROM wedding_events WHERE wedding_id=? ORDER BY event_date,start_time,id',(a['id'],))]
            return self.send_json(rows)
        if path=='/api/rsvp/questions':
            a=self.require();
            if not a:return
            with conn() as c: rows=[dict(x) for x in c.execute('SELECT * FROM rsvp_questions WHERE wedding_id=? ORDER BY sort_order,id',(a['id'],))]
            for r in rows:r['required']=bool(r['required'])
            return self.send_json(rows)
        if path=='/api/seating':
            a=self.require();
            if not a:return
            with conn() as c:
                tables=[dict(x) for x in c.execute('SELECT * FROM seating_tables WHERE wedding_id=? ORDER BY sort_order,id',(a['id'],))]
                guests=[dict(x) for x in c.execute('SELECT id,name,email,group_name,rsvp FROM guests WHERE wedding_id=? ORDER BY name',(a['id'],))]
                assignments=[dict(x) for x in c.execute('SELECT sa.guest_id,sa.table_id,sa.seat_number FROM seating_assignments sa WHERE sa.wedding_id=?',(a['id'],))]
            amap={x['guest_id']:x for x in assignments}
            for g in guests:g['assignment']=amap.get(g['id'])
            return self.send_json({'tables':tables,'guests':guests})
        if path=='/api/budget':
            a=self.require();
            if not a:return
            with conn() as c: rows=[dict(x) for x in c.execute('SELECT * FROM budget_items WHERE wedding_id=? ORDER BY category,name,id',(a['id'],))]
            totals={'planned':sum(float(x['planned'] or 0) for x in rows),'actual':sum(float(x['actual'] or 0) for x in rows),'paid':sum(float(x['paid'] or 0) for x in rows)}
            totals['remaining']=totals['actual']-totals['paid']
            return self.send_json({'items':rows,'totals':totals})
        if path=='/api/suppliers':
            if not self.require():return
            with conn() as c: rows=[dict(x) for x in c.execute('SELECT * FROM suppliers ORDER BY featured DESC,name')]
            for r in rows:r['featured']=bool(r['featured']);r.pop('email',None)
            return self.send_json(rows)
        if path.startswith('/api/public/wedding/') and not path.endswith('/rsvp'):
            slug=urllib.parse.unquote(path.split('/')[-1]);
            with conn() as c:r=c.execute('SELECT partner1,partner2,date,venue,story,password FROM weddings WHERE slug=?',(slug,)).fetchone()
            if not r:return self.send_json({'error':'Wedding not found'},404)
            d=dict(r);d['password_required']=bool(d.pop('password'))
            with conn() as c: ws=c.execute('SELECT theme,accent,hero_title,schedule,travel,faq,registry,show_story,show_schedule,show_travel,show_faq,show_registry FROM wedding_settings WHERE wedding_id=(SELECT id FROM weddings WHERE slug=?)',(slug,)).fetchone()
            d['settings']=dict(ws) if ws else {}
            with conn() as c:
                d['events']=[dict(x) for x in c.execute('SELECT id,name,event_date,start_time,venue,description,rsvp_deadline,is_primary FROM wedding_events WHERE wedding_id=(SELECT id FROM weddings WHERE slug=?) ORDER BY event_date,start_time,id',(slug,))]
                d['questions']=[dict(x) for x in c.execute('SELECT id,prompt,question_type,required,options FROM rsvp_questions WHERE wedding_id=(SELECT id FROM weddings WHERE slug=?) ORDER BY sort_order,id',(slug,))]
            return self.send_json(d)
        if path=='/api/wedding/settings':
            a=self.require();
            if not a:return
            with conn() as c:
                c.execute('INSERT OR IGNORE INTO wedding_settings(wedding_id) VALUES(?)',(a['id'],));r=c.execute('SELECT * FROM wedding_settings WHERE wedding_id=?',(a['id'],)).fetchone()
            return self.send_json(dict(r))
        if path=='/api/wedding/qr.png':
            a=self.require();
            if not a:return
            q=urllib.parse.parse_qs(p.query);slug=q.get('slug',[a['slug']])[0]
            if slug!=a['slug']:return self.send_json({'error':'Not allowed'},403)
            try:
                import qrcode; img=qrcode.make(f'{BASE_URL}/w/{slug}'); buf=io.BytesIO();img.save(buf,format='PNG');b=buf.getvalue();self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
            except Exception as e:return self.send_json({'error':'QR support requires qrcode package'},500)
        if path.startswith('/w/'):
            self.path='/public.html'; return super().do_GET()
        return super().do_GET()
    def do_POST(self):
        p=urllib.parse.urlparse(self.path); path=p.path
        if path=='/api/signup':
            if not self.rate_ok('signup:'+self.client_address[0],6,3600):return self.send_json({'error':'Too many attempts'},429)
            d=self.body(); required=['partner1','partner2','date','venue','email','password']
            if any(not str(d.get(k,'')).strip() for k in required):return self.send_json({'error':'Complete all required fields'},400)
            if len(d['password'])<8:return self.send_json({'error':'Password must be at least 8 characters'},400)
            email=d['email'].strip().lower()
            try:
                with conn() as c:
                    now=datetime.now(timezone.utc).isoformat();cur=c.execute('INSERT INTO users(email,password_hash,plan,created_at) VALUES(?,?,?,?)',(email,pbkdf(d['password']),'free',now));uid=cur.lastrowid;slug=unique_slug(c,slugify(f"{d['partner1']}-{d['partner2']}"));wid=c.execute('INSERT INTO weddings(user_id,partner1,partner2,date,venue,story,slug,password) VALUES(?,?,?,?,?,?,?,?)',(uid,d['partner1'].strip(),d['partner2'].strip(),d['date'],d['venue'].strip(),'We cannot wait to celebrate with you.',slug,'')).lastrowid;c.executemany('INSERT INTO tasks(wedding_id,title,due,done) VALUES(?,?,?,?)',[(wid,'Build guest list','',0),(wid,'Choose venue details','',0),(wid,'Send invitations','',0)])
                    token,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(24);c.execute('INSERT INTO sessions(token,user_id,csrf,expires_at) VALUES(?,?,?,?)',(token,uid,csrf,int(time.time()+60*60*24*14)))
            except sqlite3.IntegrityError:return self.send_json({'error':'An account with that email already exists'},409)
            return self.session_response(token,{'ok':True})
        if path=='/api/login':
            if not self.rate_ok('login:'+self.client_address[0],12,900):return self.send_json({'error':'Too many login attempts'},429)
            d=self.body();email=str(d.get('email','')).strip().lower();pw=str(d.get('password',''))
            with conn() as c:
                u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                if not u or not verify(pw,u['password_hash']):return self.send_json({'error':'Incorrect email or password'},401)
                token,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(24);c.execute('INSERT INTO sessions(token,user_id,csrf,expires_at) VALUES(?,?,?,?)',(token,u['id'],csrf,int(time.time()+60*60*24*14)))
            return self.session_response(token,{'ok':True})
        if path=='/api/logout':
            a=self.require(csrf=True);
            if not a:return
            tok=self.cookies().get('vowly_session');
            with conn() as c:c.execute('DELETE FROM sessions WHERE token=?',(tok.value,))
            return self.session_response('',{'ok':True},expire=True)
        if path=='/api/guests':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();name=str(d.get('name','')).strip();email=str(d.get('email','')).strip()
            if not name:return self.send_json({'error':'Guest name required'},400)
            with conn() as c:
                cur=c.execute('INSERT INTO guests(wedding_id,name,email,group_name,plus_one,rsvp,dietary,household_id,notes) VALUES(?,?,?,?,?,?,?,?,?)',(a['id'],name,email,d.get('group_name','Other'),1 if d.get('plus_one') else 0,'pending','',d.get('household_id') or None,str(d.get('notes',''))))
                gid=cur.lastrowid
                for ev in c.execute('SELECT id FROM wedding_events WHERE wedding_id=?',(a['id'],)).fetchall():c.execute('INSERT OR IGNORE INTO guest_event_invites(guest_id,event_id,invited,rsvp) VALUES(?,?,1,?)',(gid,ev['id'],'pending'))
            return self.send_json({'id':gid},201)
        if path=='/api/tasks':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();title=str(d.get('title','')).strip()
            if not title:return self.send_json({'error':'Task title required'},400)
            with conn() as c:cur=c.execute('INSERT INTO tasks(wedding_id,title,due,done) VALUES(?,?,?,0)',(a['id'],title,d.get('due','')))
            return self.send_json({'id':cur.lastrowid},201)
        if path=='/api/households':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();name=str(d.get('name','')).strip()
            if not name:return self.send_json({'error':'Household name required'},400)
            with conn() as c:cur=c.execute('INSERT INTO households(wedding_id,name,notes) VALUES(?,?,?)',(a['id'],name,str(d.get('notes',''))))
            return self.send_json({'id':cur.lastrowid},201)
        if path=='/api/events':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();name=str(d.get('name','')).strip()
            if not name:return self.send_json({'error':'Event name required'},400)
            with conn() as c:
                cur=c.execute('INSERT INTO wedding_events(wedding_id,name,event_date,start_time,venue,description,rsvp_deadline,is_primary) VALUES(?,?,?,?,?,?,?,?)',(a['id'],name,d.get('event_date',''),d.get('start_time',''),str(d.get('venue','')),str(d.get('description','')),d.get('rsvp_deadline',''),1 if d.get('is_primary') else 0))
                eid=cur.lastrowid
                for g in c.execute('SELECT id FROM guests WHERE wedding_id=?',(a['id'],)).fetchall():c.execute('INSERT OR IGNORE INTO guest_event_invites(guest_id,event_id,invited,rsvp) VALUES(?,?,1,?)',(g['id'],eid,'pending'))
            return self.send_json({'id':eid},201)
        if path=='/api/rsvp/questions':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();prompt=str(d.get('prompt','')).strip()
            if not prompt:return self.send_json({'error':'Question required'},400)
            qtype=d.get('question_type','text')
            if qtype not in ('text','yesno','choice'):qtype='text'
            with conn() as c:
                order=c.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM rsvp_questions WHERE wedding_id=?',(a['id'],)).fetchone()[0]
                cur=c.execute('INSERT INTO rsvp_questions(wedding_id,prompt,question_type,required,options,sort_order) VALUES(?,?,?,?,?,?)',(a['id'],prompt,qtype,1 if d.get('required') else 0,str(d.get('options','')),order))
            return self.send_json({'id':cur.lastrowid},201)
        if path=='/api/seating/tables':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();name=str(d.get('name','')).strip()
            if not name:return self.send_json({'error':'Table name required'},400)
            try:cap=max(1,min(30,int(d.get('capacity',8))))
            except:cap=8
            shape=d.get('shape','round')
            if shape not in ('round','rectangular','top'):shape='round'
            with conn() as c:
                order=c.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM seating_tables WHERE wedding_id=?',(a['id'],)).fetchone()[0]
                cur=c.execute('INSERT INTO seating_tables(wedding_id,name,capacity,shape,sort_order) VALUES(?,?,?,?,?)',(a['id'],name,cap,shape,order))
            return self.send_json({'id':cur.lastrowid},201)
        if path=='/api/seating/assign':
            a=self.require(csrf=True);
            if not a:return
            d=self.body()
            try:gid=int(d.get('guest_id'));tid=int(d.get('table_id'))
            except:return self.send_json({'error':'Choose a guest and table'},400)
            with conn() as c:
                g=c.execute('SELECT 1 FROM guests WHERE id=? AND wedding_id=?',(gid,a['id'])).fetchone()
                t=c.execute('SELECT capacity FROM seating_tables WHERE id=? AND wedding_id=?',(tid,a['id'])).fetchone()
                if not g or not t:return self.send_json({'error':'Guest or table not found'},404)
                count=c.execute('SELECT COUNT(*) FROM seating_assignments WHERE table_id=? AND guest_id<>?',(tid,gid)).fetchone()[0]
                if count>=t['capacity']:return self.send_json({'error':'That table is full'},409)
                c.execute('INSERT INTO seating_assignments(wedding_id,guest_id,table_id,seat_number) VALUES(?,?,?,0) ON CONFLICT(guest_id) DO UPDATE SET table_id=excluded.table_id,wedding_id=excluded.wedding_id',(a['id'],gid,tid))
            return self.send_json({'ok':True})
        if path=='/api/budget':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();name=str(d.get('name','')).strip();category=str(d.get('category','Other')).strip() or 'Other'
            if not name:return self.send_json({'error':'Budget item name required'},400)
            def num(v):
                try:return max(0,float(v or 0))
                except:return 0
            with conn() as c:cur=c.execute('INSERT INTO budget_items(wedding_id,category,name,planned,actual,paid,due_date,supplier,notes) VALUES(?,?,?,?,?,?,?,?,?)',(a['id'],category,name,num(d.get('planned')),num(d.get('actual')),num(d.get('paid')),str(d.get('due_date','')),str(d.get('supplier','')),str(d.get('notes',''))))
            return self.send_json({'id':cur.lastrowid},201)
        if path=='/api/billing/checkout':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();plan=d.get('plan')
            if plan not in ('premium','ultimate'):return self.send_json({'error':'Invalid plan'},400)
            try: session=stripe_checkout(plan,a['user_id'])
            except Exception as e:return self.send_json({'error':f'Stripe checkout failed: {e}'},502)
            if session:
                with conn() as c:c.execute('INSERT OR IGNORE INTO payments(user_id,plan,stripe_session_id,status,created_at) VALUES(?,?,?,?,?)',(a['user_id'],plan,session['id'],'pending',datetime.now(timezone.utc).isoformat()))
                return self.send_json({'url':session['url']})
            if DEMO_MODE:
                with conn() as c:c.execute('UPDATE users SET plan=? WHERE id=?',(plan,a['user_id']))
                return self.send_json({'demo':True,'plan':plan})
            return self.send_json({'error':'Stripe is not configured'},503)
        if path=='/api/stripe/webhook':
            raw=self.body(raw=True);sig=self.headers.get('Stripe-Signature','')
            if not verify_stripe_sig(raw,sig):return self.send_json({'error':'Invalid webhook signature'},400)
            evt=json.loads(raw or b'{}')
            if evt.get('type')=='checkout.session.completed':
                s=evt.get('data',{}).get('object',{});meta=s.get('metadata',{});uid=meta.get('user_id');plan=meta.get('plan')
                if uid and plan in ('premium','ultimate'):
                    with conn() as c:c.execute('UPDATE users SET plan=? WHERE id=?',(plan,int(uid)));c.execute('UPDATE payments SET status=? WHERE stripe_session_id=?',('paid',s.get('id')))
            return self.send_json({'received':True})
        if path=='/api/invitations/send':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();gid=d.get('guestId') or d.get('guest_id');subject=str(d.get('subject','')).strip();message=str(d.get('message','')).strip()
            if not subject or not message:return self.send_json({'error':'Subject and message are required'},400)
            recipient=''; guest=None
            with conn() as c:
                if gid:guest=c.execute('SELECT * FROM guests WHERE id=? AND wedding_id=?',(int(gid),a['id'])).fetchone()
            if guest:recipient=guest['email']
            if not recipient:return self.send_json({'error':'Choose a guest with an email address'},400)
            link=f'{BASE_URL}/w/{a["slug"]}';html=f'<h2>{a["partner1"]} &amp; {a["partner2"]}</h2><p>{message}</p><p><a href="{link}">View wedding & RSVP</a></p>'
            try:r=send_resend(recipient,subject,html,f'invite-{a["id"]}-{gid}-{hashlib.sha1(subject.encode()).hexdigest()[:10]}')
            except Exception as e:return self.send_json({'error':f'Email delivery failed: {e}'},502)
            status='sent' if r.get('sent') else 'preview'
            with conn() as c:c.execute('INSERT INTO invitations(wedding_id,guest_id,recipient,subject,message,status,provider_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(a['id'],int(gid),recipient,subject,message,status,r.get('provider_id',''),datetime.now(timezone.utc).isoformat()))
            return self.send_json({'sent':bool(r.get('sent')),'status':status})
        if path=='/api/reminders/send':
            a=self.require(csrf=True);
            if not a:return
            with conn() as c:gs=[dict(x) for x in c.execute("SELECT * FROM guests WHERE wedding_id=? AND rsvp='pending' AND email<>''",(a['id'],))]
            count=0;sent=0
            for g in gs:
                subject=f'RSVP reminder — {a["partner1"]} & {a["partner2"]}';msg=f'Hi {g["name"]}, we would love to know if you can join us. RSVP here: {BASE_URL}/w/{a["slug"]}'
                try:r=send_resend(g['email'],subject,f'<p>{msg}</p>',f'reminder-{a["id"]}-{g["id"]}')
                except:r={'sent':False}
                with conn() as c:c.execute('INSERT INTO invitations(wedding_id,guest_id,recipient,subject,message,status,provider_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(a['id'],g['id'],g['email'],subject,msg,'sent' if r.get('sent') else 'preview',r.get('provider_id',''),datetime.now(timezone.utc).isoformat()))
                count+=1;sent+=1 if r.get('sent') else 0
            return self.send_json({'count':count,'sent':sent})
        m=re.fullmatch(r'/api/suppliers/(\d+)/leads',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            d=self.body();msg=str(d.get('message','')).strip()
            if not msg:return self.send_json({'error':'Tell the supplier what you need'},400)
            sid=int(m.group(1))
            with conn() as c:s=c.execute('SELECT * FROM suppliers WHERE id=?',(sid,)).fetchone();
            if not s:return self.send_json({'error':'Supplier not found'},404)
            with conn() as c:c.execute('INSERT INTO supplier_leads(supplier_id,wedding_id,message,status,created_at) VALUES(?,?,?,?,?)',(sid,a['id'],msg,'new',datetime.now(timezone.utc).isoformat()))
            subject=f'New Vowly enquiry — {a["partner1"]} & {a["partner2"]}';html=f'<p><strong>Wedding:</strong> {a["partner1"]} &amp; {a["partner2"]}</p><p><strong>Date:</strong> {a["date"]}</p><p><strong>Venue:</strong> {a["venue"]}</p><p>{msg}</p>'
            try:r=send_resend(s['email'],subject,html,f'lead-{sid}-{a["id"]}-{int(time.time()/300)}')
            except:r={'sent':False}
            return self.send_json({'saved':True,'emailed':bool(r.get('sent'))})
        m=re.fullmatch(r'/api/public/wedding/([^/]+)/rsvp',path)
        if m:
            if not self.rate_ok('rsvp:'+self.client_address[0],30,3600):return self.send_json({'error':'Too many RSVP attempts'},429)
            slug=urllib.parse.unquote(m.group(1));d=self.body();name=str(d.get('name','')).strip();att=d.get('attendance')
            if att not in ('yes','no') or not name:return self.send_json({'error':'Enter your name and attendance'},400)
            with conn() as c:
                w=c.execute('SELECT * FROM weddings WHERE slug=?',(slug,)).fetchone()
                if not w:return self.send_json({'error':'Wedding not found'},404)
                if w['password'] and not hmac.compare_digest(str(d.get('sitePassword','')),w['password']):return self.send_json({'error':'Wedding password is incorrect'},403)
                g=c.execute('SELECT * FROM guests WHERE wedding_id=? AND lower(name)=lower(?)',(w['id'],name)).fetchone()
                if not g:return self.send_json({'error':'We could not find that name on the guest list'},404)
                c.execute('UPDATE guests SET rsvp=?,dietary=? WHERE id=?',(att,str(d.get('dietary','')).strip(),g['id']))
            return self.send_json({'ok':True})
        return self.send_json({'error':'Not found'},404)
    def do_PUT(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/wedding/settings':
            a=self.require(csrf=True);
            if not a:return
            d=self.body(); allowed_themes=('editorial','romantic','modern'); allowed_accents=('sage','rose','blue','plum')
            theme=d.get('theme','editorial') if d.get('theme','editorial') in allowed_themes else 'editorial';accent=d.get('accent','sage') if d.get('accent','sage') in allowed_accents else 'sage'
            vals=(theme,accent,str(d.get('hero_title',''))[:120],str(d.get('schedule',''))[:3000],str(d.get('travel',''))[:3000],str(d.get('faq',''))[:3000],str(d.get('registry',''))[:3000],1 if d.get('show_story',True) else 0,1 if d.get('show_schedule',True) else 0,1 if d.get('show_travel',True) else 0,1 if d.get('show_faq',True) else 0,1 if d.get('show_registry',True) else 0,a['id'])
            with conn() as c:
                c.execute('INSERT OR IGNORE INTO wedding_settings(wedding_id) VALUES(?)',(a['id'],));c.execute('UPDATE wedding_settings SET theme=?,accent=?,hero_title=?,schedule=?,travel=?,faq=?,registry=?,show_story=?,show_schedule=?,show_travel=?,show_faq=?,show_registry=? WHERE wedding_id=?',vals)
            return self.send_json({'ok':True})
        if path=='/api/wedding':
            a=self.require(csrf=True);
            if not a:return
            d=self.body();slug=slugify(str(d.get('slug',a['slug'])))
            try:
                with conn() as c:c.execute('UPDATE weddings SET partner1=?,partner2=?,date=?,venue=?,story=?,slug=?,password=? WHERE id=?',(str(d.get('partner1','')).strip(),str(d.get('partner2','')).strip(),d.get('date',''),str(d.get('venue','')).strip(),str(d.get('story','')).strip(),slug,str(d.get('password','')),a['id']))
            except sqlite3.IntegrityError:return self.send_json({'error':'That wedding URL is already in use'},409)
            with conn() as c:w=dict(c.execute('SELECT * FROM weddings WHERE id=?',(a['id'],)).fetchone())
            return self.send_json({'wedding':w})
        m=re.fullmatch(r'/api/seating/tables/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            d=self.body();tid=int(m.group(1))
            try:cap=max(1,min(30,int(d.get('capacity',8))))
            except:cap=8
            shape=d.get('shape','round')
            if shape not in ('round','rectangular','top'):shape='round'
            with conn() as c:c.execute('UPDATE seating_tables SET name=?,capacity=?,shape=? WHERE id=? AND wedding_id=?',(str(d.get('name','')).strip() or 'Table',cap,shape,tid,a['id']))
            return self.send_json({'ok':True})
        m=re.fullmatch(r'/api/budget/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            d=self.body();bid=int(m.group(1))
            def num(v):
                try:return max(0,float(v or 0))
                except:return 0
            with conn() as c:c.execute('UPDATE budget_items SET category=?,name=?,planned=?,actual=?,paid=?,due_date=?,supplier=?,notes=? WHERE id=? AND wedding_id=?',(str(d.get('category','Other')),str(d.get('name','')).strip(),num(d.get('planned')),num(d.get('actual')),num(d.get('paid')),str(d.get('due_date','')),str(d.get('supplier','')),str(d.get('notes','')),bid,a['id']))
            return self.send_json({'ok':True})
        m=re.fullmatch(r'/api/guests/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            d=self.body();gid=int(m.group(1))
            with conn() as c:
                c.execute('UPDATE guests SET name=?,email=?,group_name=?,plus_one=?,household_id=?,notes=? WHERE id=? AND wedding_id=?',(str(d.get('name','')).strip(),str(d.get('email','')).strip(),d.get('group_name','Other'),1 if d.get('plus_one') else 0,d.get('household_id') or None,str(d.get('notes','')),gid,a['id']))
                for x in d.get('events',[]):
                    c.execute('INSERT INTO guest_event_invites(guest_id,event_id,invited,rsvp) VALUES(?,?,?,COALESCE((SELECT rsvp FROM guest_event_invites WHERE guest_id=? AND event_id=?),"pending")) ON CONFLICT(guest_id,event_id) DO UPDATE SET invited=excluded.invited',(gid,int(x['event_id']),1 if x.get('invited') else 0,gid,int(x['event_id'])))
            return self.send_json({'ok':True})
        m=re.fullmatch(r'/api/tasks/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            d=self.body();
            with conn() as c:c.execute('UPDATE tasks SET done=? WHERE id=? AND wedding_id=?',(1 if d.get('done') else 0,int(m.group(1)),a['id']))
            return self.send_json({'ok':True})
        return self.send_json({'error':'Not found'},404)
    def do_DELETE(self):
        path=urllib.parse.urlparse(self.path).path
        m=re.fullmatch(r'/api/seating/assignments/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            with conn() as c:c.execute('DELETE FROM seating_assignments WHERE guest_id=? AND wedding_id=?',(int(m.group(1)),a['id']))
            return self.send_json({'ok':True})
        m=re.fullmatch(r'/api/seating/tables/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            tid=int(m.group(1))
            with conn() as c:
                c.execute('DELETE FROM seating_assignments WHERE table_id=? AND wedding_id=?',(tid,a['id']))
                c.execute('DELETE FROM seating_tables WHERE id=? AND wedding_id=?',(tid,a['id']))
            return self.send_json({'ok':True})
        m=re.fullmatch(r'/api/budget/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            with conn() as c:c.execute('DELETE FROM budget_items WHERE id=? AND wedding_id=?',(int(m.group(1)),a['id']))
            return self.send_json({'ok':True})
        m=re.fullmatch(r'/api/guests/(\d+)',path)
        if m:
            a=self.require(csrf=True);
            if not a:return
            with conn() as c:c.execute('DELETE FROM guests WHERE id=? AND wedding_id=?',(int(m.group(1)),a['id']))
            return self.send_json({'ok':True})
        return self.send_json({'error':'Not found'},404)
    def session_response(self,token,obj,expire=False):
        b=json_bytes(obj);self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));cookie=f'vowly_session={token}; Path=/; HttpOnly; SameSite=Lax'
        if APP_ENV=='production':cookie+='; Secure'
        if expire:cookie+='; Max-Age=0'
        else:cookie+='; Max-Age=1209600'
        self.send_header('Set-Cookie',cookie);self.end_headers();self.wfile.write(b)

if __name__=='__main__':
    seed(); os.chdir(ROOT); print(f'Vowly Stage 8 running on http://0.0.0.0:{PORT} | DB={DB} | BASE_URL={BASE_URL}'); ThreadingHTTPServer(('0.0.0.0',PORT),App).serve_forever()
