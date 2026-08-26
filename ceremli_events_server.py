#!/usr/bin/env python3
"""Ceremli event-management server."""
import re, urllib.parse
from http.server import ThreadingHTTPServer
import server as legacy
import ceremli_server as core
import ceremli_household_rsvp_server as household


class CeremliEventsApp(household.CeremliHouseholdRSVPApp):
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/events/manage':
            a=self.require()
            if not a:return
            with legacy.conn() as c:
                events=[dict(x) for x in c.execute('SELECT * FROM wedding_events WHERE wedding_id=? ORDER BY event_date,start_time,id',(a['id'],))]
                guests=[dict(x) for x in c.execute('SELECT id,name,email,group_name,household_id,rsvp FROM guests WHERE wedding_id=? ORDER BY name',(a['id'],))]
                rows=[dict(x) for x in c.execute('''SELECT gei.event_id,gei.guest_id,gei.invited,gei.rsvp
                    FROM guest_event_invites gei JOIN wedding_events e ON e.id=gei.event_id
                    WHERE e.wedding_id=?''',(a['id'],))]
            by_event={}
            for r in rows:by_event.setdefault(r['event_id'],[]).append(r)
            for e in events:
                rs=by_event.get(e['id'],[])
                invited=[r for r in rs if r['invited']]
                e['stats']={
                    'invited':len(invited),
                    'yes':sum(1 for r in invited if r['rsvp']=='yes'),
                    'pending':sum(1 for r in invited if r['rsvp']=='pending'),
                    'no':sum(1 for r in invited if r['rsvp']=='no')
                }
                e['invited_guest_ids']=[r['guest_id'] for r in invited]
                e['is_primary']=bool(e['is_primary'])
            return self.send_json({'events':events,'guests':guests})
        return super().do_GET()

    def do_PUT(self):
        path=urllib.parse.urlparse(self.path).path
        m=re.fullmatch(r'/api/events/(\d+)',path)
        if m:
            a=self.require(csrf=True)
            if not a:return
            d=self.body();eid=int(m.group(1));name=str(d.get('name','')).strip()
            if not name:return self.send_json({'error':'Event name required'},400)
            primary=1 if d.get('is_primary') else 0
            with legacy.conn() as c:
                found=c.execute('SELECT 1 FROM wedding_events WHERE id=? AND wedding_id=?',(eid,a['id'])).fetchone()
                if not found:return self.send_json({'error':'Event not found'},404)
                if primary:c.execute('UPDATE wedding_events SET is_primary=0 WHERE wedding_id=?',(a['id'],))
                c.execute('''UPDATE wedding_events SET name=?,event_date=?,start_time=?,venue=?,description=?,rsvp_deadline=?,is_primary=?
                    WHERE id=? AND wedding_id=?''',(name,str(d.get('event_date','')),str(d.get('start_time','')),str(d.get('venue','')).strip(),str(d.get('description','')).strip(),str(d.get('rsvp_deadline','')),primary,eid,a['id']))
            return self.send_json({'ok':True})
        m=re.fullmatch(r'/api/events/(\d+)/invites',path)
        if m:
            a=self.require(csrf=True)
            if not a:return
            eid=int(m.group(1));d=self.body();ids=d.get('guest_ids') or []
            try:ids={int(x) for x in ids}
            except:return self.send_json({'error':'Invalid guest selection'},400)
            with legacy.conn() as c:
                ev=c.execute('SELECT 1 FROM wedding_events WHERE id=? AND wedding_id=?',(eid,a['id'])).fetchone()
                if not ev:return self.send_json({'error':'Event not found'},404)
                allowed={x['id'] for x in c.execute('SELECT id FROM guests WHERE wedding_id=?',(a['id'],)).fetchall()}
                ids=ids & allowed
                c.execute('UPDATE guest_event_invites SET invited=0 WHERE event_id=?',(eid,))
                for gid in ids:
                    c.execute('''INSERT INTO guest_event_invites(guest_id,event_id,invited,rsvp)
                        VALUES(?,?,1,COALESCE((SELECT rsvp FROM guests WHERE id=?),'pending'))
                        ON CONFLICT(guest_id,event_id) DO UPDATE SET invited=1''',(gid,eid,gid))
            return self.send_json({'ok':True,'invited':len(ids)})
        return super().do_PUT()

    def do_DELETE(self):
        path=urllib.parse.urlparse(self.path).path
        m=re.fullmatch(r'/api/events/(\d+)',path)
        if m:
            a=self.require(csrf=True)
            if not a:return
            eid=int(m.group(1))
            with legacy.conn() as c:
                ev=c.execute('SELECT name FROM wedding_events WHERE id=? AND wedding_id=?',(eid,a['id'])).fetchone()
                if not ev:return self.send_json({'error':'Event not found'},404)
                c.execute('DELETE FROM guest_event_invites WHERE event_id=?',(eid,))
                c.execute('DELETE FROM wedding_events WHERE id=? AND wedding_id=?',(eid,a['id']))
            return self.send_json({'ok':True})
        return super().do_DELETE()


if __name__=='__main__':
    core.migrate()
    legacy.os.chdir(legacy.ROOT)
    print(f'Ceremli Events running on http://0.0.0.0:{legacy.PORT} | DB={legacy.DB} | BASE_URL={legacy.BASE_URL}')
    ThreadingHTTPServer(('0.0.0.0',legacy.PORT),CeremliEventsApp).serve_forever()
