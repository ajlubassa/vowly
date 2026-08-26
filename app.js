let ME=null,CSRF='';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const api=async(path,opts={})=>{const headers={'Content-Type':'application/json',...(opts.headers||{})};if(CSRF&&opts.method&&opts.method!=='GET')headers['X-CSRF-Token']=CSRF;const r=await fetch(path,{credentials:'include',headers,...opts});let d={};try{d=await r.json()}catch{}if(r.status===401){location.href='/login.html';throw new Error('Please log in')}if(!r.ok)throw new Error(d.error||'Request failed');return d};
const toast=m=>{const t=document.createElement('div');t.className='toast';t.textContent=m;document.body.append(t);setTimeout(()=>t.remove(),2600)};
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
async function initCommon(){if(document.body.dataset.page){ME=await api('/api/me');CSRF=ME.csrf;$$('[data-logout]').forEach(b=>b.onclick=async()=>{await api('/api/logout',{method:'POST',body:'{}'});location.href='/'});$$('[data-public-link],[data-site-button]').forEach(a=>a.href=`/w/${ME.wedding.slug}`);$$('[data-current-plan]').forEach(x=>x.textContent=`${cap(ME.plan)} plan`);const initials=`${(ME.wedding.partner1||'')[0]||''}${(ME.wedding.partner2||'')[0]||''}`.toUpperCase();$$('.avatar').forEach(x=>x.textContent=initials||'V');const sf=$('.side-foot');if(sf&&sf.textContent.includes('Free plan'))sf.innerHTML=`<strong>${cap(ME.plan)} plan</strong><br>${ME.plan==='free'?'Upgrade for invitations and premium tools.':'Your wedding upgrade is active.'}`}}
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
 const search=$('[data-search]'),filter=$('[data-filter]'),groupFilter=$('[data-group-filter]'),list=$('[data-guest-list]');
 $('[data-total]').textContent=rows.length;$('[data-attending]').textContent=rows.filter(g=>g.rsvp==='yes').length;$('[data-awaiting]').textContent=rows.filter(g=>g.rsvp==='pending').length;$('[data-declined]').textContent=rows.filter(g=>g.rsvp==='no').length;
 $('[data-household-list]').innerHTML=households.length?households.map(h=>`<span class="chip">${esc(h.name)} <strong>${h.guest_count}</strong></span>`).join(''):'<span class="muted">No households yet</span>';
 const hs=$('[name=household_id]');hs.innerHTML='<option value="">None</option>'+households.map(h=>`<option value="${h.id}">${esc(h.name)}</option>`).join('');
 const statusLabel=s=>s==='yes'?'Attending':s==='no'?'Declined':'Pending';
 const draw=()=>{const q=(search.value||'').toLowerCase(),st=filter.value,gr=groupFilter.value;const filtered=rows.filter(g=>(!q||[g.name,g.email,g.group_name,g.household_name,g.notes,g.dietary,g.meal_choice].join(' ').toLowerCase().includes(q))&&(!st||g.rsvp===st)&&(!gr||g.group_name===gr));list.innerHTML=filtered.length?filtered.map(g=>{const invited=(g.events||[]).filter(x=>x.invited).length,answers=(g.answers||[]).filter(x=>x.answer);return `<article class="guest-card"><div class="guest-card-head"><div><span class="eyebrow">${esc(g.group_name||'Other')}${g.household_name?' · '+esc(g.household_name):''}</span><h3>${esc(g.name)}</h3><p>${esc(g.email||'No email')}</p></div><span class="status ${g.rsvp}">${statusLabel(g.rsvp)}</span></div><div class="guest-details"><div><span>Events</span><strong>${invited}/${events.length}</strong></div><div><span>Meal</span><strong>${esc(g.meal_choice||'—')}</strong></div><div><span>Dietary</span><strong>${esc(g.dietary||'—')}</strong></div><div><span>Plus one</span><strong>${g.plus_one?esc(g.plus_one_name||'Allowed'):'No'}</strong></div></div>${answers.length?`<div class="guest-answers">${answers.slice(0,3).map(a=>`<div><span>${esc(a.prompt)}</span><strong>${esc(a.answer)}</strong></div>`).join('')}</div>`:''}<div class="guest-card-actions"><button class="btn btn-secondary btn-small" data-edit-guest="${g.id}">Edit</button><button class="btn btn-secondary btn-small" data-resend-guest="${g.id}">Resend invite</button><button class="text-link danger-link" data-del="${g.id}">Remove</button></div></article>`}).join(''):'<div class="empty-state">No guests match your filters.</div>';
 $$('[data-edit-guest]').forEach(b=>b.onclick=()=>openGuest(rows.find(g=>g.id===Number(b.dataset.editGuest))));$$('[data-del]').forEach(b=>b.onclick=async()=>{if(confirm('Remove this guest?')){await api('/api/guests/'+b.dataset.del,{method:'DELETE'});location.reload()}})};
 search.oninput=draw;filter.onchange=draw;groupFilter.onchange=draw;
 const modal=$('.modal-backdrop'),form=$('[data-guest-form]');let editing=null;
 const openGuest=g=>{editing=g||null;form.reset();$('[data-guest-modal-title]').textContent=g?'Edit guest':'Add a guest';$('[data-guest-save]').textContent=g?'Save changes':'Add guest';if(g){['name','email','group_name','rsvp','meal_choice','dietary','plus_one_name','plus_one_meal','notes'].forEach(k=>{if(form.elements[k])form.elements[k].value=g[k]??''});form.elements.household_id.value=g.household_id||'';form.elements.plus_one.checked=!!g.plus_one}modal.classList.add('open')};
 $('[data-open-modal]').onclick=()=>openGuest(null);$('[data-close-modal]').onclick=()=>modal.classList.remove('open');modal.onclick=e=>{if(e.target===modal)modal.classList.remove('open')};
 form.onsubmit=async e=>{e.preventDefault();const f=new FormData(form),body=Object.fromEntries(f.entries());body.plus_one=form.elements.plus_one.checked;body.household_id=body.household_id||null;await api(editing?'/api/guests/'+editing.id:'/api/guests',{method:editing?'PUT':'POST',body:JSON.stringify(body)});location.reload()};
 $('[data-add-household]').onclick=async()=>{const name=prompt('Household name (e.g. The Thompson family)');if(name){await api('/api/households',{method:'POST',body:JSON.stringify({name})});location.reload()}};
 $('[data-export]').onclick=()=>{const head=['Name','Email','Household','Group','RSVP','Meal','Dietary','Plus one','Plus-one name','Notes'];const lines=[head,...rows.map(g=>[g.name,g.email||'',g.household_name||'',g.group_name,g.rsvp,g.meal_choice||'',g.dietary||'',g.plus_one?'Yes':'No',g.plus_one_name||'',g.notes||''])].map(r=>r.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\n');const blob=new Blob([lines],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='vowly-guests.csv';a.click();URL.revokeObjectURL(a.href)};
 draw();
 $('[data-resend-guest]').forEach(b => b.onclick = async () => {
  const g = rows.find(x => x.id === Number(b.dataset.resendGuest));

  if (!g || !g.email) {
    alert('This guest has no email address.');
    return;
  }

  try {
    await api('/api/invitations/send', {
      method: 'POST',
      body: JSON.stringify({
        guest_id: g.id
      })
    });

    alert(`Invitation resent to ${g.email}`);
  } catch (e) {
    alert(`Could not resend invitation: ${e.message}`);
  }
});
}

async function eventsPage(){const rows=await api('/api/events'),list=$('[data-event-list]');list.innerHTML=rows.map(e=>`<article class="event-card"><span class="eyebrow">${e.is_primary?'Main event':'Event'}</span><h3>${esc(e.name)}</h3><p><strong>${esc(e.event_date||'Date TBD')} ${esc(e.start_time||'')}</strong></p><p>${esc(e.venue||'Venue TBD')}</p><p>${esc(e.description||'')}</p>${e.rsvp_deadline?`<small>RSVP by ${esc(e.rsvp_deadline)}</small>`:''}</article>`).join('')||'<div class="empty-state">No events yet.</div>';const add=$('[data-add-event]'),wrap=$('[data-event-form-wrap]'),cancel=$('[data-cancel-event]');if(add&&wrap)add.onclick=()=>{wrap.hidden=false;wrap.scrollIntoView({behavior:'smooth',block:'start'})};if(cancel&&wrap)cancel.onclick=()=>wrap.hidden=true;const form=$('[data-event-form]');if(form)form.onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget),body=Object.fromEntries(f.entries());body.is_primary=f.get('is_primary')==='on';await api('/api/events',{method:'POST',body:JSON.stringify(body)});location.reload()}}
async function questionsPage(){const rows=await api('/api/rsvp/questions'),list=$('[data-question-list]');list.innerHTML=rows.map((q,i)=>`<article class="question-card"><span class="q-num">${i+1}</span><div><h3>${esc(q.prompt)}</h3><p>${cap(q.question_type)}${q.required?' · Required':''}</p>${q.options?`<small>${esc(q.options)}</small>`:''}</div></article>`).join('')||'<div class="empty-state">No custom questions yet.</div>';$('[data-question-form]').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget),body=Object.fromEntries(f.entries());body.required=f.get('required')==='on';await api('/api/rsvp/questions',{method:'POST',body:JSON.stringify(body)});location.reload()}}
async function checklist(){const ts=await api('/api/tasks'),done=ts.filter(t=>t.done).length,p=ts.length?Math.round(done/ts.length*100):0;$('[data-pct]').textContent=p+'% complete';$('[data-progressbar]').style.width=p+'%';$('[data-checklist]').innerHTML=ts.map(t=>`<div class="task ${t.done?'done':''}"><input data-task="${t.id}" type="checkbox" ${t.done?'checked':''}><label>${esc(t.title)}</label><small>${esc(t.due||'')}</small></div>`).join('');$$('[data-task]').forEach(c=>c.onchange=async()=>{await api(`/api/tasks/${c.dataset.task}`,{method:'PUT',body:JSON.stringify({done:c.checked})});await checklist()});$('[data-add-task]').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget);await api('/api/tasks',{method:'POST',body:JSON.stringify({title:f.get('task'),due:f.get('due')})});e.currentTarget.reset();await checklist()}}
async function pricing(){$$('[data-upgrade]').forEach(b=>b.onclick=async()=>{const plan=b.dataset.upgrade;if(plan==='free'){toast('Free plan remains active');return}try{const d=await api('/api/billing/checkout',{method:'POST',body:JSON.stringify({plan})});if(d.url)location.href=d.url;else if(d.demo){toast(`${cap(plan)} activated in demo mode`);setTimeout(()=>location.reload(),700)}}catch(e){toast(e.message)}})}
async function invitations(){
 const state=await api('/api/invitations'),stats=state.stats||{},list=$('[data-invite-history]');
 $('[data-invite-total]').textContent=stats.total||0;$('[data-invite-email]').textContent=stats.with_email||0;$('[data-invite-pending]').textContent=stats.pending||0;$('[data-invite-attending]').textContent=stats.attending||0;
 const url=$('[data-wedding-url]');url.value=state.wedding_url||'';
 $('[data-copy-link]').onclick=async()=>{try{await navigator.clipboard.writeText(url.value);toast('RSVP link copied')}catch{url.select();document.execCommand('copy');toast('RSVP link copied')}};
 $('[data-email-mode]').textContent=state.email_live?'Live email':'Preview mode';
 $('[data-email-note]').textContent=state.email_live?'Invitations will be delivered by email.':'Email delivery is not configured yet. Sends are recorded safely in preview mode.';
 list.innerHTML=state.history.length?state.history.map(i=>`<div class="invite-history-row"><div><strong>${esc(i.subject)}</strong><span>${esc(i.recipient)}</span></div><div><span class="payment-status ${i.status==='sent'?'paid':'deposit'}">${i.status==='sent'?'Sent':'Preview'}</span><small>${esc((i.created_at||'').slice(0,10))}</small></div></div>`).join(''):'<div class="empty-state compact">No invitations sent yet.</div>';
 const sel=$('[data-guest-select]');sel.innerHTML='<option value="">Choose a guest with email</option>'+state.guests.filter(g=>g.email).map(g=>`<option value="${g.id}">${esc(g.name)} — ${esc(g.email)}</option>`).join('');
 const form=$('[data-invite-form]');form.onsubmit=async e=>{e.preventDefault();const f=new FormData(form);const d=await api('/api/invitations/send',{method:'POST',body:JSON.stringify(Object.fromEntries(f.entries()))});toast(d.sent?'Invitation sent':'Invitation recorded in preview mode');setTimeout(()=>location.reload(),650)};
 $('[data-remind]').onclick=async()=>{if(!stats.pending){toast('No pending RSVPs');return}const d=await api('/api/reminders/send',{method:'POST',body:'{}'});toast(`${d.count} reminder${d.count===1?'':'s'} processed`);$('[data-reminder-result]').textContent=state.email_live?`${d.sent} reminder email(s) delivered.`:`${d.count} reminder(s) recorded in preview mode.`};
}
const money=n=>'£'+Number(n||0).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:2});
async function budgetPage(){
 const d=await api('/api/budget'),rows=d.items||[],t=d.totals||{},today=new Date().toISOString().slice(0,10);
 $('[data-budget-total]').textContent=money(t.budget);
 $('[data-budget-planned]').textContent=money(t.planned);
 $('[data-budget-actual]').textContent=money(t.actual);
 $('[data-budget-paid]').textContent=money(t.paid);
 $('[data-budget-remaining]').textContent=money(t.remaining);
 $('[data-budget-progress]').style.width=Math.min(100,Number(t.percent||0))+'%';
 $('[data-budget-progress-label]').textContent=`${t.percent||0}% committed`;
 $('[data-budget-remaining-copy]').textContent=`${money(t.remaining)} remaining`;

 const warning=$('[data-budget-warning]');
 if(Number(t.actual)>Number(t.budget)&&Number(t.budget)>0){
  warning.hidden=false;
  warning.innerHTML=`<strong>Over budget by ${money(t.actual-t.budget)}</strong><span>Your actual wedding costs have exceeded the total budget.</span>`;
 }

 const statusLabel=s=>s==='paid'?'Paid':s==='deposit'?'Deposit paid':'Not paid';

 const due=rows.filter(x=>x.due_date&&x.payment_status!=='paid').sort((a,b)=>a.due_date.localeCompare(b.due_date)).slice(0,5);
 $('[data-upcoming-payments]').innerHTML=due.length?due.map(x=>`<div class="payment-row ${x.due_date<today?'overdue':''}">
   <div><strong>${esc(x.name)}</strong><small>${x.due_date<today?'Overdue · ':''}${esc(x.due_date)}</small></div>
   <div><strong>${money(Math.max(0,Number(x.actual||x.planned||0)-Number(x.paid||0)))}</strong><span class="payment-status ${x.payment_status}">${statusLabel(x.payment_status)}</span></div>
 </div>`).join(''):'<div class="empty-state compact">No upcoming payments.</div>';

 const grouped={};
 rows.forEach(x=>{const k=x.category||'Other';grouped[k]=(grouped[k]||0)+Number(x.actual||x.planned||0)});
 const max=Math.max(1,...Object.values(grouped));
 $('[data-category-breakdown]').innerHTML=Object.entries(grouped).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<div class="category-row">
   <div><strong>${esc(k)}</strong><span>${money(v)}</span></div>
   <div class="category-track"><i style="width:${Math.round(v/max*100)}%"></i></div>
 </div>`).join('')||'<div class="empty-state compact">No categories yet.</div>';

 const cats=[...new Set(rows.map(x=>x.category).filter(Boolean))].sort();
 const cat=$('[data-budget-category]');
 cat.innerHTML='<option value="">All categories</option>'+cats.map(c=>`<option>${esc(c)}</option>`).join('');
 const search=$('[data-budget-search]'),list=$('[data-budget-expense-list]');

 const draw=()=>{
   const q=(search.value||'').toLowerCase(),c=cat.value;
   const filtered=rows.filter(x=>(!q||[x.name,x.category,x.supplier,x.notes].join(' ').toLowerCase().includes(q))&&(!c||x.category===c));
   list.innerHTML=filtered.length?filtered.map(x=>{
     const dueClass=x.due_date&&x.due_date<today&&x.payment_status!=='paid'?'overdue-text':'';
     return `<article class="expense-row">
       <div class="expense-main">
         <div>
           <span class="eyebrow">${esc(x.category||'Other')}</span>
           <h4>${esc(x.name)}</h4>
           ${x.supplier?`<p>${esc(x.supplier)}</p>`:''}
           ${x.notes?`<small>${esc(x.notes)}</small>`:''}
         </div>
         <span class="payment-status ${x.payment_status}">${statusLabel(x.payment_status)}</span>
       </div>
       <div class="expense-numbers">
         <div><span>Estimate</span><strong>${money(x.planned)}</strong></div>
         <div><span>Actual</span><strong>${money(x.actual)}</strong></div>
         <div><span>Paid</span><strong>${money(x.paid)}</strong></div>
         <div><span>Due</span><strong class="${dueClass}">${esc(x.due_date||'—')}</strong></div>
       </div>
       <div class="expense-actions">
         <button class="btn btn-secondary btn-small" data-edit-expense="${x.id}">Edit</button>
         <button class="text-link danger-link" data-delete-budget="${x.id}">Delete</button>
       </div>
     </article>`;
   }).join(''):'<div class="empty-state">No expenses match your filters.</div>';

   $$('[data-delete-budget]').forEach(b=>b.onclick=async()=>{
     if(confirm('Delete this expense?')){
       await api('/api/budget/'+b.dataset.deleteBudget,{method:'DELETE'});
       location.reload();
     }
   });

   $$('[data-edit-expense]').forEach(b=>b.onclick=()=>openExpense(rows.find(x=>x.id===Number(b.dataset.editExpense))));
 };

 search.oninput=draw;
 cat.onchange=draw;

 const modal=$('[data-budget-modal]'),form=$('[data-budget-form]');
 let editing=null;

 const openExpense=x=>{
   editing=x||null;
   form.reset();
   $('[data-expense-modal-title]').textContent=x?'Edit expense':'Add expense';
   $('[data-expense-save]').textContent=x?'Save changes':'Save expense';
   if(x)Object.entries(x).forEach(([k,v])=>{const el=form.elements[k];if(el)el.value=v??''});
   modal.classList.add('open');
 };

 $('[data-open-budget]').onclick=()=>openExpense(null);
 $('[data-close-budget]').onclick=()=>modal.classList.remove('open');
 modal.onclick=e=>{if(e.target===modal)modal.classList.remove('open')};
 form.onsubmit=async e=>{
   e.preventDefault();
   const body=Object.fromEntries(new FormData(form).entries());
   await api(editing?'/api/budget/'+editing.id:'/api/budget',{method:editing?'PUT':'POST',body:JSON.stringify(body)});
   location.reload();
 };

 draw();

 const totalModal=$('[data-total-budget-modal]');
 $('[data-edit-budget]').onclick=()=>{
   $('[name=total_budget]').value=t.budget||0;
   totalModal.classList.add('open');
 };
 $('[data-close-total-budget]').onclick=()=>totalModal.classList.remove('open');
 totalModal.onclick=e=>{if(e.target===totalModal)totalModal.classList.remove('open')};
 $('[data-total-budget-form]').onsubmit=async e=>{
   e.preventDefault();
   const f=new FormData(e.currentTarget);
   await api('/api/budget/settings',{method:'PUT',body:JSON.stringify({total_budget:f.get('total_budget')})});
   location.reload();
 };
}


async function launchPage(){
 const d=await api('/api/launch/readiness'),checks=d.checks||[],root=$('[data-launch-checks]');
 const ok=checks.filter(x=>x.ok).length,total=checks.length||1,pct=Math.round(ok/total*100);
 $('[data-launch-score]').textContent=pct+'%';
 $('[data-launch-status]').textContent=d.ready?'Core setup ready':'A few things still need attention';
 root.innerHTML=checks.map(x=>`<div class="launch-check ${x.ok?'ok':'todo'}"><span class="launch-dot"></span><div><strong>${esc(x.label)}</strong><small>${x.ok?'Ready':'Needs attention'}</small></div></div>`).join('');
 $('[data-email-readiness]').innerHTML=d.email_live?'Real invitation email delivery is configured.':'Email is still in <strong>preview mode</strong>. Configure your Resend API key before inviting real guests by email.';
}
(async()=>{try{await initCommon();const p=document.body.dataset.page;if(p==='dashboard')await dashboard();if(p==='builder')await builder();if(p==='guests')await guests();if(p==='events')await eventsPage();if(p==='questions')await questionsPage();if(p==='seating')await seatingPage();if(p==='budget')await budgetPage();if(p==='checklist')await checklist();if(p==='pricing')await pricing();if(p==='invitations')await invitations();if(p==='suppliers')await suppliers()}catch(e){console.error(e)}})();


function initMobileNav(){
 const sidebar=document.querySelector('.sidebar'), topbar=document.querySelector('.topbar');
 if(!sidebar||!topbar)return;
 let btn=document.querySelector('.mobile-nav-toggle');
 if(!btn){btn=document.createElement('button');btn.type='button';btn.className='mobile-nav-toggle';btn.setAttribute('aria-label','Open navigation');btn.textContent='☰';const left=topbar.firstElementChild;left&&left.insertBefore(btn,left.firstChild)}
 const backdrop=document.createElement('div');backdrop.className='mobile-nav-backdrop';document.body.appendChild(backdrop);
 const close=()=>{document.body.classList.remove('nav-open');backdrop.classList.remove('open');btn.textContent='☰';btn.setAttribute('aria-label','Open navigation')};
 btn.onclick=()=>{const open=!document.body.classList.contains('nav-open');document.body.classList.toggle('nav-open',open);backdrop.classList.toggle('open',open);btn.textContent=open?'×':'☰';btn.setAttribute('aria-label',open?'Close navigation':'Open navigation')};
 backdrop.onclick=close;sidebar.querySelectorAll('a').forEach(a=>a.addEventListener('click',close));document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
}
document.addEventListener('DOMContentLoaded',initMobileNav);
