"""Ceremli media layer: persistent wedding party and gallery data."""
import json,re
import server as core
from ceremli_launch_server import LaunchHandler, migrate_accounts

MAX_PARTY=20
MAX_GALLERY=24
MAX_DATA_URL=900000

def migrate_media():
    migrate_accounts()
    with core.conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS wedding_party_members(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          wedding_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          role TEXT DEFAULT '',
          bio TEXT DEFAULT '',
          photo_data TEXT DEFAULT '',
          sort_order INTEGER DEFAULT 0,
          FOREIGN KEY(wedding_id) REFERENCES weddings(id) ON DELETE CASCADE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS wedding_gallery(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          wedding_id INTEGER NOT NULL,
          image_data TEXT NOT NULL,
          sort_order INTEGER DEFAULT 0,
          FOREIGN KEY(wedding_id) REFERENCES weddings(id) ON DELETE CASCADE
        )''')

def valid_image(v):
    return isinstance(v,str) and len(v)<=MAX_DATA_URL and (not v or v.startswith('data:image/jpeg;base64,') or v.startswith('data:image/png;base64,') or v.startswith('data:image/webp;base64,'))

def media_payload(c,wid):
    party=[{'id':r['id'],'name':r['name'],'role':r['role'],'bio':r['bio'],'photo':r['photo_data']} for r in c.execute('SELECT * FROM wedding_party_members WHERE wedding_id=? ORDER BY sort_order,id',(wid,))]
    gallery=[{'id':r['id'],'src':r['image_data']} for r in c.execute('SELECT * FROM wedding_gallery WHERE wedding_id=? ORDER BY sort_order,id',(wid,))]
    return {'party':party,'gallery':gallery}

class MediaHandler(LaunchHandler):
    def do_GET(self):
        path=self.path.split('?',1)[0]
        if path=='/api/wedding/media':
            a=self.require()
            if not a:return
            with core.conn() as c:return self.send_json(media_payload(c,a['id']))
        m=re.fullmatch(r'/api/public/wedding/([^/]+)/media',path)
        if m:
            slug=core.urllib.parse.unquote(m.group(1))
            with core.conn() as c:
                w=c.execute('SELECT id FROM weddings WHERE slug=?',(slug,)).fetchone()
                if not w:return self.send_json({'error':'Wedding not found'},404)
                return self.send_json(media_payload(c,w['id']))
        return super().do_GET()

    def do_PUT(self):
        path=self.path.split('?',1)[0]
        if path=='/api/wedding/media':
            a=self.require(csrf=True)
            if not a:return
            d=self.body();party=d.get('party') or [];gallery=d.get('gallery') or []
            if not isinstance(party,list) or not isinstance(gallery,list):return self.send_json({'error':'Invalid media data'},400)
            if len(party)>MAX_PARTY or len(gallery)>MAX_GALLERY:return self.send_json({'error':'Too many photos'},400)
            clean_party=[]
            for p in party:
                if not isinstance(p,dict):continue
                name=str(p.get('name','')).strip()[:100];role=str(p.get('role','')).strip()[:100];bio=str(p.get('bio','')).strip()[:500];photo=p.get('photo','') or ''
                if not name:return self.send_json({'error':'Each wedding party member needs a name'},400)
                if not valid_image(photo):return self.send_json({'error':'One wedding party photo is too large or invalid'},400)
                clean_party.append((name,role,bio,photo))
            clean_gallery=[]
            for g in gallery:
                src=(g.get('src','') if isinstance(g,dict) else '') or ''
                if not valid_image(src) or not src:return self.send_json({'error':'One gallery photo is too large or invalid'},400)
                clean_gallery.append(src)
            with core.conn() as c:
                c.execute('DELETE FROM wedding_party_members WHERE wedding_id=?',(a['id'],));c.execute('DELETE FROM wedding_gallery WHERE wedding_id=?',(a['id'],))
                c.executemany('INSERT INTO wedding_party_members(wedding_id,name,role,bio,photo_data,sort_order) VALUES(?,?,?,?,?,?)',[(a['id'],*p,i) for i,p in enumerate(clean_party)])
                c.executemany('INSERT INTO wedding_gallery(wedding_id,image_data,sort_order) VALUES(?,?,?)',[(a['id'],src,i) for i,src in enumerate(clean_gallery)])
            return self.send_json({'ok':True,'party_count':len(clean_party),'gallery_count':len(clean_gallery)})
        return super().do_PUT()

if __name__=='__main__':
    migrate_media()
    from http.server import ThreadingHTTPServer
    import os
    port=int(os.environ.get('PORT','8000'))
    print(f'Ceremli media server on {port}')
    ThreadingHTTPServer(('0.0.0.0',port),MediaHandler).serve_forever()
