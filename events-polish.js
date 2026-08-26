// Ceremli event management UI
(function(){
  if(document.body?.dataset?.page!=='events') return;
  let state={events:[],guests:[]},editing=null;
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

  async function load(){state=await api('/api/events/manage');render()}
  function render(){
    const list=$('[data-event-list]');
    list.innerHTML=state.events.length?state.events.map(e=>`<article class="event-card">
      <div class="panel-head"><div><span class="eyebrow">${e.is_primary?'Main event':'Event'}</span><h3>${esc(e.name)}</h3></div></div>
      <p><strong>${esc(e.event_date||'Date TBD')} ${esc(e.start_time||'')}</strong></p><p>${esc(e.venue||'Venue TBD')}</p><p>${esc(e.description||'')}</p>
      <div class="guest-details"><div><span>Invited</span><strong>${e.stats.invited}</strong></div><div><span>Attending</span><strong>${e.stats.yes}</strong></div><div><span>Pending</span><strong>${e.stats.pending}</strong></div><div><span>Declined</span><strong>${e.stats.no}</strong></div></div>
      <div class="guest-card-actions"><button class="btn btn-secondary btn-small" data-edit-event="${e.id}">Edit</button><button class="btn btn-secondary btn-small" data-event-guests="${e.id}">Guests</button><button class="text-link danger-link" data-delete-event="${e.id}">Delete</button></div>
    </article>`).join(''):'<div class="empty-state">No events yet.</div>';
  }

  const wrap=$('[data-event-form-wrap]'),form=$('[data-event-form]');
  $('[data-add-event]').onclick=()=>{editing=null;form.reset();wrap.hidden=false;wrap.querySelector('h3').textContent='Add event';wrap.scrollIntoView({behavior:'smooth'})};
  $('[data-cancel-event]').onclick=()=>{wrap.hidden=true;editing=null};
  form.onsubmit=async e=>{e.preventDefault();const f=new FormData(form),body=Object.fromEntries(f.entries());body.is_primary=f.get('is_primary')==='on';await api(editing?`/api/events/${editing.id}`:'/api/events',{method:editing?'PUT':'POST',body:JSON.stringify(body)});toast(editing?'Event updated':'Event added');wrap.hidden=true;editing=null;await load()};

  document.addEventListener('click',async e=>{
    const eb=e.target.closest('[data-edit-event]');
    if(eb){editing=state.events.find(x=>x.id===Number(eb.dataset.editEvent));if(!editing)return;form.reset();['name','event_date','start_time','rsvp_deadline','venue','description'].forEach(k=>{if(form.elements[k])form.elements[k].value=editing[k]||''});form.elements.is_primary.checked=!!editing.is_primary;wrap.querySelector('h3').textContent='Edit event';wrap.hidden=false;wrap.scrollIntoView({behavior:'smooth'});return}
    const db=e.target.closest('[data-delete-event]');
    if(db){const ev=state.events.find(x=>x.id===Number(db.dataset.deleteEvent));if(ev&&confirm(`Delete ${ev.name}?`)){await api(`/api/events/${ev.id}`,{method:'DELETE'});toast('Event deleted');await load()}return}
    const gb=e.target.closest('[data-event-guests]');
    if(gb)openGuests(Number(gb.dataset.eventGuests));
  });

  function openGuests(id){
    const ev=state.events.find(x=>x.id===id);if(!ev)return;
    const selected=new Set(ev.invited_guest_ids||[]);
    const back=document.createElement('div');back.className='modal-backdrop open';back.innerHTML=`<div class="modal guest-modal"><div class="modal-head"><div><span class="eyebrow">Event guests</span><h3>${esc(ev.name)}</h3></div><button class="icon-btn" data-close>×</button></div><p class="muted">Choose exactly who is invited to this event.</p><div style="max-height:420px;overflow:auto">${state.guests.map(g=>`<label class="check-row"><input type="checkbox" value="${g.id}" ${selected.has(g.id)?'checked':''}> <span><strong>${esc(g.name)}</strong>${g.email?`<small style="display:block">${esc(g.email)}</small>`:''}</span></label>`).join('')}</div><button class="btn btn-primary" data-save style="width:100%;margin-top:14px">Save guest list</button></div>`;document.body.append(back);
    back.querySelector('[data-close]').onclick=()=>back.remove();back.onclick=e=>{if(e.target===back)back.remove()};back.querySelector('[data-save]').onclick=async()=>{const ids=$$('input[type=checkbox]:checked',back).map(x=>Number(x.value));await api(`/api/events/${id}/invites`,{method:'PUT',body:JSON.stringify({guest_ids:ids})});toast('Event guest list updated');back.remove();await load()};
  }
  load().catch(e=>toast(e.message||'Could not load events'));
})();
