let ME=null,CSRF='';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const api=async(path,opts={})=>{const headers={'Content-Type':'application/json',...(opts.headers||{})};if(CSRF&&opts.method&&opts.method!=='GET')headers['X-CSRF-Token']=CSRF;const r=await fetch(path,{credentials:'include',headers,...opts});let d={};try{d=await r.json()}catch{}if(r.status===401){location.href='/login.html';throw new Error('Please log in')}if(!r.ok)throw new Error(d.error||'Request failed');return d};
const toast=m=>{const t=document.createElement('div');t.className='toast';t.textContent=m;document.body.append(t);setTimeout(()=>t.remove(),2600)};
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
async function initCommon(){if(document.body.dataset.page){ME=await api('/api/me');CSRF=ME.csrf;$$('[data-logout]').forEach(b=>b.onclick=async()=>{await api('/api/logout',{method:'POST',body:'{}'});location.href='/'});$$('[data-public-link],[data-site-button]').forEach(a=>a.href=`/w/${ME.wedding.slug}`);$$('[data-current-plan]').forEach(x=>x.textContent=`${cap(ME.plan)} plan`);const sf=$('.side-foot');if(sf&&sf.textContent.includes('Free plan'))sf.innerHTML=`<strong>${cap(ME.plan)} plan</strong><br>${ME.plan==='free'?'Upgrade for invitations and premium tools.':'Your wedding upgrade is active.'}`}}
const cap=s=>s?String(s)[0].toUpperCase()+String(s).slice(1):'';
function daysUntil(d){const n=Math.ceil((new Date(d+'T12:00:00')-new Date())/86400000);return n>0?`${n} days to go`:n===0?'Today ♡':'Wedding day passed'}
async function dashboard(){const d=await api('/api/dashboard');$('[data-couple]').textContent=`${d.wedding.partner1} & ${d.wedding.partner2}`;$('[data-countdown]').textContent=daysUntil(d.wedding.date);$('[data-guests]').textContent=d.stats.total;$('[data-yes]').textContent=d.stats.yes;$('[data-pending]').textContent=d.stats.pending;$('[data-progress]').textContent=d.stats.progress+'%';$('[data-progressbar]').style.width=d.stats.progress+'%';$('[data-yes-count]').textContent=d.stats.yes;$('[data-pending-count]').textContent=d.stats.pending;$('[data-no-count]').textContent=d.stats.no;const tl=$('[data-task-list]');tl.innerHTML=d.tasks.slice(0,5).map(t=>`<div class="task ${t.done?'done':''}"><input type="checkbox" ${t.done?'checked':''} disabled><label>${esc(t.title)}</label><small>${esc(t.due||'')}</small></div>`).join('');$('[data-site-url]').href=`/w/${d.wedding.slug}`;$('[data-site-url] strong').textContent=`${location.host}/w/${d.wedding.slug}`;$('[data-monogram]').textContent=`${d.wedding.partner1[0]} & ${d.wedding.partner2[0]}`}
async function builder(){
 const w=ME.wedding,s=await api('/api/wedding/settings');
 const fields=['partner1','partner2','date','venue','story','slug','password'];
 fields.forEach(n=>{const el=$(`[name=${n}]`);if(el)el.value=w[n]||''});
 ['hero_title','schedule','travel','faq','registry'].forEach(n=>{const el=$(`[name=${n}]`);if(el)el.value=s[n]||''});
 ['show_story','show_schedule','show_travel','show_faq','show_registry'].forEach(n=>{const el=$(`[name=${n}]`);if(el)el.checked=!!s[n]});
 let theme=s.theme||'editorial',accent=s.accent||'sage';
 const render=()=>{
  const p1=$('[name=partner1]').value||'You',p2=$('[name=partner2]').value||'Your love';
  $('[data-preview-names]').textContent=`${p1} & ${p2}`;
  $('.pv-nav').firstChild.textContent=`${p1[0]} ♡ ${p2[0]} `;
  $('[data-preview-date]').textContent=$('[name=date]').value;
  $('[data-preview-venue]').textContent=$('[name=venue]').value;
  $('[data-preview-hero]').textContent=$('[name=hero_title]').value||"We can't wait to celebrate with you";
  $('[data-preview-story]').textContent=$('[name=story]').value;
  ['schedule','travel','faq','registry'].forEach(n=>{const el=$(`[data-preview-${n}]`);if(el)el.textContent=$(`[name=${n}]`).value});
  ['story','schedule','travel','faq','registry'].forEach(n=>{const sec=$(`[data-pv-${n}]`);if(sec)sec.hidden=!$(`[name=show_${n}]`).checked});
  $('[data-preview-url]').textContent=`${location.host}/w/${$('[name=slug]').value}`;
  const pv=$('[data-site-preview]');pv.className=`site-preview ${theme} accent-${accent}`;
 };
 $$('input,textarea').forEach(x=>x.addEventListener('input',render));$$('input[type=checkbox]').forEach(x=>x.addEventListener('change',render));
 $$('.theme-choice').forEach(b=>{b.classList.toggle('active',b.dataset.theme===theme);b.onclick=()=>{theme=b.dataset.theme;$$('.theme-choice').forEach(x=>x.classList.toggle('active',x===b));render()}});
 $$('.swatch').forEach(b=>{b.classList.toggle('active',b.dataset.accent===accent);b.onclick=()=>{accent=b.dataset.accent;$$('.swatch').forEach(x=>x.classList.toggle('active',x===b));render()}});
 render();$('[data-qr]').src=`/api/wedding/qr.png?slug=${encodeURIComponent(w.slug)}`;
 const saveBtn=$('[data-save]'),status=$('[data-publish-status]');
 saveBtn.onclick=async()=>{
  const original=saveBtn.textContent;
  saveBtn.disabled=true;saveBtn.textContent='Publishing…';
  if(status){status.textContent='Saving…';status.className='publish-status saving'}
  try{
   const body={};fields.forEach(n=>body[n]=$(`[name=${n}]`).value);
   const r=await api('/api/wedding',{method:'PUT',body:JSON.stringify(body)});
   const sb={theme,accent};
   ['hero_title','schedule','travel','faq','registry'].forEach(n=>sb[n]=$(`[name=${n}]`).value);
   ['show_story','show_schedule','show_travel','show_faq','show_registry'].forEach(n=>sb[n]=$(`[name=${n}]`).checked);
   await api('/api/wedding/settings',{method:'PUT',body:JSON.stringify(sb)});
   ME.wedding=r.wedding;
   $$('[data-public-link]').forEach(a=>a.href=`/w/${ME.wedding.slug}?v=${Date.now()}`);
   $('[data-qr]').src=`/api/wedding/qr.png?slug=${encodeURIComponent(ME.wedding.slug)}&t=${Date.now()}`;
   if(status){status.textContent='Published ✓';status.className='publish-status success'}
   toast('Wedding website published');
  }catch(e){
   console.error(e);
   if(status){status.textContent=e.message||'Could not publish';status.className='publish-status error'}
   toast(e.message||'Could not publish changes');
  }finally{
   saveBtn.disabled=false;saveBtn.textContent=original;
  }
 };
}async function guests(){
 const data=await api('/api/guests'),rows=data.guests||[],events=data.events||[],households=await api('/api/households');
 const tb=$('tbody'),search=$('[data-search]'),filter=$('[data-filter]');
 $('[data-total]').textContent=rows.length;$('[data-attending]').textContent=rows.filter(g=>g.rsvp==='yes').length;$('[data-awaiting]').textContent=rows.filter(g=>g.rsvp==='pending').length;$('[data-households]').textContent=households.length;
 $('[data-household-list]').innerHTML=households.length?households.map(h=>`<span class="chip">${esc(h.name)} <strong>${h.guest_count}</strong></span>`).join(''):'<span class="muted">No households yet</span>';
 const hs=$('[name=household_id]');if(hs)hs.innerHTML='<option value="">None</option>'+households.map(h=>`<option value="${h.id}">${esc(h.name)}</option>`).join('');
 const draw=()=>{const q=(search.value||'').toLowerCase(),st=filter.value;tb.innerHTML=rows.filter(g=>(!q||[g.name,g.email,g.group_name,g.household_name,g.notes].join(' ').toLowerCase().includes(q))&&(!st||g.rsvp===st)).map(g=>{const invited=(g.events||[]).filter(x=>x.invited).length;return `<tr><td><strong>${esc(g.name)}</strong><small>${esc(g.email||'')}</small></td><td>${esc(g.household_name||'—')}</td><td>${esc(g.group_name)}</td><td>${invited}/${events.length}</td><td>${g.plus_one?'Yes':'No'}</td><td><span class="status ${g.rsvp}">${cap(g.rsvp)}</span></td><td>${esc(g.notes||'—')}</td><td><button class="icon-btn" data-del="${g.id}">×</button></td></tr>`}).join('');$$('[data-del]').forEach(b=>b.onclick=async()=>{if(confirm('Remove this guest?')){await api('/api/guests/'+b.dataset.del,{method:'DELETE'});location.reload()}})};
 search.oninput=draw;filter.onchange=draw;draw();
 $('[data-open-modal]').onclick=()=>$('.modal-backdrop').classList.add('show');$('[data-close-modal]').onclick=()=>$('.modal-backdrop').classList.remove('show');
 $('[data-guest-form]').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget);await api('/api/guests',{method:'POST',body:JSON.stringify({name:f.get('name'),email:f.get('email'),group_name:f.get('group'),household_id:f.get('household_id')||null,notes:f.get('notes'),plus_one:f.get('plusOne')==='on'})});location.reload()};
 $('[data-add-household]').onclick=async()=>{const name=prompt('Household name (e.g. The Thompson family)');if(name){await api('/api/households',{method:'POST',body:JSON.stringify({name})});location.reload()}};
 $('[data-export]').onclick=()=>{const head=['Name','Email','Household','Group','RSVP','Dietary','Notes'];const lines=[head,...rows.map(g=>[g.name,g.email||'',g.household_name||'',g.group_name,g.rsvp,g.dietary||'',g.notes||''])].map(r=>r.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\n');const blob=new Blob([lines],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='vowly-guests.csv';a.click();URL.revokeObjectURL(a.href)}
}
async function eventsPage(){const rows=await api('/api/events'),list=$('[data-event-list]');list.innerHTML=rows.map(e=>`<article class="event-card"><span class="eyebrow">${e.is_primary?'Main event':'Event'}</span><h3>${esc(e.name)}</h3><p><strong>${esc(e.event_date||'Date TBD')} ${esc(e.start_time||'')}</strong></p><p>${esc(e.venue||'Venue TBD')}</p><p>${esc(e.description||'')}</p>${e.rsvp_deadline?`<small>RSVP by ${esc(e.rsvp_deadline)}</small>`:''}</article>`).join('')||'<div class="empty-state">No events yet.</div>';const add=$('[data-add-event]'),wrap=$('[data-event-form-wrap]'),cancel=$('[data-cancel-event]');if(add&&wrap)add.onclick=()=>{wrap.hidden=false;wrap.scrollIntoView({behavior:'smooth',block:'start'})};if(cancel&&wrap)cancel.onclick=()=>wrap.hidden=true;const form=$('[data-event-form]');if(form)form.onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget),body=Object.fromEntries(f.entries());body.is_primary=f.get('is_primary')==='on';await api('/api/events',{method:'POST',body:JSON.stringify(body)});location.reload()}}
async function questionsPage(){const rows=await api('/api/rsvp/questions'),list=$('[data-question-list]');list.innerHTML=rows.map((q,i)=>`<article class="question-card"><span class="q-num">${i+1}</span><div><h3>${esc(q.prompt)}</h3><p>${cap(q.question_type)}${q.required?' · Required':''}</p>${q.options?`<small>${esc(q.options)}</small>`:''}</div></article>`).join('')||'<div class="empty-state">No custom questions yet.</div>';$('[data-question-form]').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget),body=Object.fromEntries(f.entries());body.required=f.get('required')==='on';await api('/api/rsvp/questions',{method:'POST',body:JSON.stringify(body)});location.reload()}}
async function checklist(){const ts=await api('/api/tasks'),done=ts.filter(t=>t.done).length,p=ts.length?Math.round(done/ts.length*100):0;$('[data-pct]').textContent=p+'% complete';$('[data-progressbar]').style.width=p+'%';$('[data-checklist]').innerHTML=ts.map(t=>`<div class="task ${t.done?'done':''}"><input data-task="${t.id}" type="checkbox" ${t.done?'checked':''}><label>${esc(t.title)}</label><small>${esc(t.due||'')}</small></div>`).join('');$$('[data-task]').forEach(c=>c.onchange=async()=>{await api(`/api/tasks/${c.dataset.task}`,{method:'PUT',body:JSON.stringify({done:c.checked})});await checklist()});$('[data-add-task]').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget);await api('/api/tasks',{method:'POST',body:JSON.stringify({title:f.get('task'),due:f.get('due')})});e.currentTarget.reset();await checklist()}}
async function pricing(){$$('[data-upgrade]').forEach(b=>b.onclick=async()=>{const plan=b.dataset.upgrade;if(plan==='free'){toast('Free plan remains active');return}try{const d=await api('/api/billing/checkout',{method:'POST',body:JSON.stringify({plan})});if(d.url)location.href=d.url;else if(d.demo){toast(`${cap(plan)} activated in demo mode`);setTimeout(()=>location.reload(),700)}}catch(e){toast(e.message)}})}
async function invitations(){const state=await api('/api/invitations');const list=$('[data-invite-history]')||$('[data-invitation-history]')||$('[data-history]');if(list)list.innerHTML=state.history.map(i=>`<div class="task"><span>✉</span><label><strong>${esc(i.subject)}</strong><br><small>${esc(i.recipient)}</small></label><small>${esc(i.status)}</small></div>`).join('')||'<p>No invitations sent yet.</p>';const sel=$('[data-guest-select]');if(sel)sel.innerHTML='<option value="">Choose a guest</option>'+state.guests.filter(g=>g.email).map(g=>`<option value="${g.id}">${esc(g.name)} — ${esc(g.email)}</option>`).join('');const form=$('[data-invite-form]')||$('form[data-invitation-form]');if(form)form.onsubmit=async e=>{e.preventDefault();const f=new FormData(form);const d=await api('/api/invitations/send',{method:'POST',body:JSON.stringify(Object.fromEntries(f))});toast(d.sent?'Invitation sent':'Invitation recorded in preview mode');setTimeout(()=>location.reload(),700)};const rb=$('[data-send-reminders]')||$('[data-remind]');if(rb)rb.onclick=async()=>{const d=await api('/api/reminders/send',{method:'POST',body:'{}'});toast(`${d.count} reminder${d.count===1?'':'s'} processed`);const out=$('[data-reminder-result]');if(out)out.textContent=state.email_live?`${d.sent} email reminder(s) delivered.`:`${d.count} reminder(s) recorded in preview mode.`}}
async function suppliers(){const data=await api('/api/suppliers');const root=$('[data-suppliers]')||$('.supplier-grid');if(!root)return;root.innerHTML=data.map(s=>`<article class="supplier-card ${s.featured?'featured':''}"><span class="eyebrow">${s.featured?'Featured · ':''}${esc(s.category)}</span><h3>${esc(s.name)}</h3><p>${esc(s.description)}</p><div class="supplier-meta">${esc(s.location)} · From £${s.price_from}</div><form class="lead-form" data-lead="${s.id}"><input class="input" name="message" required placeholder="Tell them what you need"><button class="btn btn-primary" style="width:100%;margin-top:8px">Request quote</button></form></article>`).join('');$$('[data-lead]').forEach(f=>f.onsubmit=async e=>{e.preventDefault();const d=await api(`/api/suppliers/${f.dataset.lead}/leads`,{method:'POST',body:JSON.stringify({message:new FormData(f).get('message')})});toast(d.emailed?'Enquiry sent to supplier':'Enquiry saved — supplier email is in preview mode');f.reset()})}
(async()=>{try{await initCommon();const p=document.body.dataset.page;if(p==='dashboard')await dashboard();if(p==='builder')await builder();if(p==='guests')await guests();if(p==='events')await eventsPage();if(p==='questions')await questionsPage();if(p==='checklist')await checklist();if(p==='pricing')await pricing();if(p==='invitations')await invitations();if(p==='suppliers')await suppliers()}catch(e){console.error(e)}})();
