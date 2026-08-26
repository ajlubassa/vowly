#!/usr/bin/env python3
"""Ceremli guest RSVP runner: personalized lookup and full RSVP persistence."""
import re, urllib.parse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import server as legacy
import ceremli_server as core


def stamp():
    return datetime.now(timezone.utc).isoformat()


def check_wedding_and_password(slug, password):
    with legacy.conn() as c:
        w=c.execute('SELECT * FROM weddings WHERE slug=?',(slug,)).fetchone()
    if not w:return None,('Wedding not found',404)
    if w['password'] and not legacy.hmac.compare_digest(str(password or ''),w['password']):return None,('Wedding password is incorrect',403)
    return w,None


class CeremliRSVPApp(core.CeremliApp):
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path

        m=re.fullmatch(r'/api/public/wedding/([^/]+)/guest',path)
        if m:
            if not self.rate_ok('guest-lookup:'+self.client_address[0],40,3600):return self.send_json({'error':'Too many attempts. Please try again later.'},429)
            slug=urllib.parse.unquote(m.group(1)); d=self.body(); name=str(d.get('name','')).strip()
            if not name:return self.send_json({'error':'Enter your name exactly as it appears on the invitation'},400)
            w,err=check_wedding_and_password(slug,d.get('sitePassword',''))
            if err:return self.send_json({'error':err[0]},err[1])
            with legacy.conn() as c:
                g=c.execute('SELECT * FROM guests WHERE wedding_id=? AND lower(trim(name))=lower(trim(?))',(w['id'],name)).fetchone()
                if not g:return self.send_json({'error':'We could not find that name on the guest list'},404)
                events=[dict(x) for x in c.execute('''SELECT gei.event_id,gei.rsvp,e.name,e.event_date,e.start_time,e.venue
                    FROM guest_event_invites gei JOIN wedding_events e ON e.id=gei.event_id
                    WHERE gei.guest_id=? AND gei.invited=1 ORDER BY e.event_date,e.start_time,e.id''',(g['id'],))]
                answers=[dict(x) for x in c.execute('''SELECT rq.id question_id,COALESCE(ra.answer,'') answer
                    FROM rsvp_questions rq LEFT JOIN rsvp_answers ra ON ra.question_id=rq.id AND ra.guest_id=?
                    WHERE rq.wedding_id=? ORDER BY rq.sort_order,rq.id''',(g['id'],w['id']))]
            guest={k:g[k] for k in ('id','name','rsvp','dietary','meal_choice','plus_one','plus_one_name','plus_one_meal') if k in g.keys()}
            guest['plus_one']=bool(guest.get('plus_one'));guest['events']=events;guest['answers']=answers
            return self.send_json({'guest':guest})

        m=re.fullmatch(r'/api/public/wedding/([^/]+)/rsvp',path)
        if m:
            if not self.rate_ok('rsvp:'+self.client_address[0],30,3600):return self.send_json({'error':'Too many RSVP attempts'},429)
            slug=urllib.parse.unquote(m.group(1)); d=self.body(); name=str(d.get('name','')).strip(); att=d.get('attendance')
            if att not in ('yes','no') or not name:return self.send_json({'error':'Enter your name and attendance'},400)
            w,err=check_wedding_and_password(slug,d.get('sitePassword',''))
            if err:return self.send_json({'error':err[0]},err[1])
            now=stamp()
            with legacy.conn() as c:
                g=c.execute('SELECT * FROM guests WHERE wedding_id=? AND lower(trim(name))=lower(trim(?))',(w['id'],name)).fetchone()
                if not g:return self.send_json({'error':'We could not find that name on the guest list'},404)
                previous=g['rsvp'] or 'pending'
                meal=str(d.get('meal_choice','')).strip()[:200]; dietary=str(d.get('dietary','')).strip()[:1000]
                plus_name=str(d.get('plus_one_name','')).strip()[:200] if g['plus_one'] else ''
                plus_meal=str(d.get('plus_one_meal','')).strip()[:200] if g['plus_one'] else ''
                c.execute('UPDATE guests SET rsvp=?,dietary=?,meal_choice=?,plus_one_name=?,plus_one_meal=?,rsvp_updated_at=? WHERE id=?',(att,dietary,meal,plus_name,plus_meal,now,g['id']))
                if previous!=att:
                    c.execute('INSERT INTO rsvp_history(wedding_id,guest_id,previous_rsvp,new_rsvp,source,created_at) VALUES(?,?,?,?,?,?)',(w['id'],g['id'],previous,att,'guest',now))

                supplied_events={int(x.get('event_id')):x.get('rsvp') for x in (d.get('events') or []) if str(x.get('event_id','')).isdigit() and x.get('rsvp') in ('yes','no','pending')}
                invited={x['event_id'] for x in c.execute('SELECT event_id FROM guest_event_invites WHERE guest_id=? AND invited=1',(g['id'],)).fetchall()}
                for eid,response in supplied_events.items():
                    if eid in invited:c.execute('UPDATE guest_event_invites SET rsvp=? WHERE guest_id=? AND event_id=?',(response,g['id'],eid))
                if not supplied_events:
                    c.execute('UPDATE guest_event_invites SET rsvp=? WHERE guest_id=? AND invited=1',(att,g['id']))

                allowed_questions={x['id'] for x in c.execute('SELECT id FROM rsvp_questions WHERE wedding_id=?',(w['id'],)).fetchall()}
                for answer in (d.get('answers') or []):
                    try:qid=int(answer.get('question_id'))
                    except:continue
                    if qid not in allowed_questions:continue
                    value=str(answer.get('answer','')).strip()[:2000]
                    c.execute('INSERT INTO rsvp_answers(guest_id,question_id,answer) VALUES(?,?,?) ON CONFLICT(guest_id,question_id) DO UPDATE SET answer=excluded.answer',(g['id'],qid,value))

                fresh=c.execute('SELECT id,name,rsvp,dietary,meal_choice,plus_one,plus_one_name,plus_one_meal,rsvp_updated_at FROM guests WHERE id=?',(g['id'],)).fetchone()
            guest=dict(fresh);guest['plus_one']=bool(guest.get('plus_one'))
            return self.send_json({'ok':True,'guest':guest,'updated_at':now})

        return super().do_POST()


if __name__=='__main__':
    core.migrate()
    legacy.os.chdir(legacy.ROOT)
    print(f'Ceremli RSVP running on http://0.0.0.0:{legacy.PORT} | DB={legacy.DB} | BASE_URL={legacy.BASE_URL}')
    ThreadingHTTPServer(('0.0.0.0',legacy.PORT),CeremliRSVPApp).serve_forever()
