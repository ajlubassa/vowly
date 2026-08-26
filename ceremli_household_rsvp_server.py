#!/usr/bin/env python3
"""Ceremli household RSVP runner: one lookup can manage every guest in a household."""
import re, urllib.parse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

# Migrate the SQLite database from the old ephemeral /app location to the
# new persistent /data volume (if needed) before anything touches the DB.
import migrate_db
migrate_db.migrate()

import server as legacy
import ceremli_server as core
import ceremli_rsvp_server as rsvp_core


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def guest_payload(c, guest, wedding_id):
    events=[dict(x) for x in c.execute('''SELECT gei.event_id,gei.rsvp,e.name,e.event_date,e.start_time,e.venue
        FROM guest_event_invites gei JOIN wedding_events e ON e.id=gei.event_id
        WHERE gei.guest_id=? AND gei.invited=1 ORDER BY e.event_date,e.start_time,e.id''',(guest['id'],))]
    answers=[dict(x) for x in c.execute('''SELECT rq.id question_id,COALESCE(ra.answer,'') answer
        FROM rsvp_questions rq LEFT JOIN rsvp_answers ra ON ra.question_id=rq.id AND ra.guest_id=?
        WHERE rq.wedding_id=? ORDER BY rq.sort_order,rq.id''',(guest['id'],wedding_id))]
    out={k:guest[k] for k in ('id','name','rsvp','dietary','meal_choice','plus_one','plus_one_name','plus_one_meal','household_id') if k in guest.keys()}
    out['plus_one']=bool(out.get('plus_one')); out['events']=events; out['answers']=answers
    return out


class CeremliHouseholdRSVPApp(rsvp_core.CeremliRSVPApp):
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path

        m=re.fullmatch(r'/api/public/wedding/([^/]+)/guest',path)
        if m:
            if not self.rate_ok('guest-lookup:'+self.client_address[0],40,3600):return self.send_json({'error':'Too many attempts. Please try again later.'},429)
            slug=urllib.parse.unquote(m.group(1)); d=self.body(); name=str(d.get('name','')).strip()
            if not name:return self.send_json({'error':'Enter your name exactly as it appears on the invitation'},400)
            w,err=rsvp_core.check_wedding_and_password(slug,d.get('sitePassword',''))
            if err:return self.send_json({'error':err[0]},err[1])
            with legacy.conn() as c:
                guest=c.execute('SELECT * FROM guests WHERE wedding_id=? AND lower(trim(name))=lower(trim(?))',(w['id'],name)).fetchone()
                if not guest:return self.send_json({'error':'We could not find that name on the guest list'},404)
                household=None; members=[]
                if guest['household_id']:
                    h=c.execute('SELECT id,name FROM households WHERE id=? AND wedding_id=?',(guest['household_id'],w['id'])).fetchone()
                    if h:
                        household=dict(h)
                        rows=c.execute('SELECT * FROM guests WHERE wedding_id=? AND household_id=? ORDER BY name',(w['id'],h['id'])).fetchall()
                        members=[guest_payload(c,x,w['id']) for x in rows]
                if not members:members=[guest_payload(c,guest,w['id'])]
            return self.send_json({'guest':guest_payload(legacy.conn(),guest,w['id']) if False else members[0],'household':household,'members':members})

        m=re.fullmatch(r'/api/public/wedding/([^/]+)/household-rsvp',path)
        if m:
            if not self.rate_ok('household-rsvp:'+self.client_address[0],20,3600):return self.send_json({'error':'Too many RSVP attempts'},429)
            slug=urllib.parse.unquote(m.group(1)); d=self.body(); lookup_name=str(d.get('lookup_name','')).strip()
            if not lookup_name:return self.send_json({'error':'Invitation name is required'},400)
            w,err=rsvp_core.check_wedding_and_password(slug,d.get('sitePassword',''))
            if err:return self.send_json({'error':err[0]},err[1])
            supplied=d.get('members') or []
            if not isinstance(supplied,list) or not supplied:return self.send_json({'error':'No RSVP responses supplied'},400)
            stamp=now_iso(); updated=[]
            with legacy.conn() as c:
                anchor=c.execute('SELECT * FROM guests WHERE wedding_id=? AND lower(trim(name))=lower(trim(?))',(w['id'],lookup_name)).fetchone()
                if not anchor:return self.send_json({'error':'We could not find that invitation'},404)
                if anchor['household_id']:
                    allowed={x['id']:x for x in c.execute('SELECT * FROM guests WHERE wedding_id=? AND household_id=?',(w['id'],anchor['household_id'])).fetchall()}
                else:allowed={anchor['id']:anchor}
                allowed_questions={x['id'] for x in c.execute('SELECT id FROM rsvp_questions WHERE wedding_id=?',(w['id'],)).fetchall()}

                for item in supplied:
                    try:gid=int(item.get('id'))
                    except:continue
                    guest=allowed.get(gid)
                    if not guest:continue
                    attendance=item.get('attendance')
                    if attendance not in ('yes','no','pending'):continue
                    previous=guest['rsvp'] or 'pending'
                    dietary=str(item.get('dietary','')).strip()[:1000]
                    meal=str(item.get('meal_choice','')).strip()[:200]
                    plus_name=str(item.get('plus_one_name','')).strip()[:200] if guest['plus_one'] else ''
                    plus_meal=str(item.get('plus_one_meal','')).strip()[:200] if guest['plus_one'] else ''
                    c.execute('UPDATE guests SET rsvp=?,dietary=?,meal_choice=?,plus_one_name=?,plus_one_meal=?,rsvp_updated_at=? WHERE id=?',(attendance,dietary,meal,plus_name,plus_meal,stamp,gid))
                    if previous!=attendance:
                        c.execute('INSERT INTO rsvp_history(wedding_id,guest_id,previous_rsvp,new_rsvp,source,created_at) VALUES(?,?,?,?,?,?)',(w['id'],gid,previous,attendance,'household_guest',stamp))

                    event_responses={int(x.get('event_id')):x.get('rsvp') for x in (item.get('events') or []) if str(x.get('event_id','')).isdigit() and x.get('rsvp') in ('yes','no','pending')}
                    invited={x['event_id'] for x in c.execute('SELECT event_id FROM guest_event_invites WHERE guest_id=? AND invited=1',(gid,)).fetchall()}
                    for eid,response in event_responses.items():
                        if eid in invited:c.execute('UPDATE guest_event_invites SET rsvp=? WHERE guest_id=? AND event_id=?',(response,gid,eid))
                    if not event_responses and attendance in ('yes','no'):
                        c.execute('UPDATE guest_event_invites SET rsvp=? WHERE guest_id=? AND invited=1',(attendance,gid))

                    for answer in (item.get('answers') or []):
                        try:qid=int(answer.get('question_id'))
                        except:continue
                        if qid not in allowed_questions:continue
                        value=str(answer.get('answer','')).strip()[:2000]
                        c.execute('INSERT INTO rsvp_answers(guest_id,question_id,answer) VALUES(?,?,?) ON CONFLICT(guest_id,question_id) DO UPDATE SET answer=excluded.answer',(gid,qid,value))
                    fresh=c.execute('SELECT * FROM guests WHERE id=?',(gid,)).fetchone()
                    updated.append(guest_payload(c,fresh,w['id']))
            return self.send_json({'ok':True,'members':updated,'updated_at':stamp})

        return super().do_POST()


if __name__=='__main__':
    core.migrate()
    legacy.os.chdir(legacy.ROOT)
    print(f'Ceremli Household RSVP running on http://0.0.0.0:{legacy.PORT} | DB={legacy.DB} | BASE_URL={legacy.BASE_URL}')
    ThreadingHTTPServer(('0.0.0.0',legacy.PORT),CeremliHouseholdRSVPApp).serve_forever()
