// Ceremli supplier workspace: shortlist, enquiry tracking and budget handoff.
(function(){
 const page=()=>document.body?.dataset?.page==='suppliers';
 const money=n=>'£'+Number(n||0).toLocaleString('en-GB',{maximumFractionDigits:0});
 const key='ceremli_supplier_workspace_v1';
 const load=()=>{try{return JSON.parse(localStorage.getItem(key)||'{}')}catch{return {}}};
 const save=x=>localStorage.setItem(key,JSON.stringify(x));
 async function start(){
  if(!page())return;
  const rows=await api('/api/suppliers');
  const state=load(),root=document.querySelector('[data-suppliers]'),search=document.querySelector('[data-supplier-search]'),cat=document.querySelector('[data-supplier-category]');
  const cats=[...new Set(rows.map(x=>x.category).filter(Boolean))].sort();
  cat.innerHTML='<option value="">All categories</option>'+cats.map(x=>`<option>${esc(x)}</option>`).join('');
  const status=s=>state[s.id]?.status||'researching';
  const shortlisted=s=>!!state[s.id]?.shortlisted;
  const draw=()=>{
   const q=(search.value||'').toLowerCase(),c=cat.value;
   const filtered=rows.filter(s=>(!q||[s.name,s.category,s.location,s.description].join(' ').toLowerCase().includes(q))&&(!c||s.category===c));
   root.innerHTML=filtered.length?filtered.map(s=>`<article class="supplier-card">
    <div class="supplier-card-head"><div><span class="eyebrow">${esc(s.category||'Supplier')}</span><h3>${esc(s.name)}</h3><p>${esc(s.location||'')}</p></div><button type="button" class="supplier-heart ${shortlisted(s)?'active':''}" data-shortlist="${s.id}" aria-label="${shortlisted(s)?'Remove from':'Add to'} shortlist">${shortlisted(s)?'♥':'♡'}</button></div>
    <p>${esc(s.description||'')}</p>
    <div class="supplier-meta">${s.price_from?`<span>From <strong>${money(s.price_from)}</strong></span>`:''}${s.rating?`<span><strong>${esc(s.rating)}</strong> rating</span>`:''}${s.featured?'<span class="badge">Featured</span>':''}</div>
    <label class="supplier-status-label">Planning status<select class="input" data-supplier-status="${s.id}"><option value="researching" ${status(s)==='researching'?'selected':''}>Researching</option><option value="contacted" ${status(s)==='contacted'?'selected':''}>Contacted</option><option value="quote" ${status(s)==='quote'?'selected':''}>Quote received</option><option value="booked" ${status(s)==='booked'?'selected':''}>Booked</option><option value="passed" ${status(s)==='passed'?'selected':''}>Not proceeding</option></select></label>
    <div class="supplier-actions"><button class="btn btn-secondary btn-small" data-enquire="${s.id}">Prepare enquiry</button><button class="btn btn-primary btn-small" data-supplier-budget="${s.id}">Add to budget</button></div>
   </article>`).join(''):'<div class="empty-state">No suppliers match your search.</div>';
   document.querySelectorAll('[data-shortlist]').forEach(b=>b.onclick=()=>{const id=b.dataset.shortlist;state[id]={...(state[id]||{}),shortlisted:!state[id]?.shortlisted};save(state);draw();updateSummary()});
   document.querySelectorAll('[data-supplier-status]').forEach(x=>x.onchange=()=>{const id=x.dataset.supplierStatus;state[id]={...(state[id]||{}),status:x.value};save(state);updateSummary()});
   document.querySelectorAll('[data-enquire]').forEach(b=>b.onclick=()=>openEnquiry(rows.find(x=>String(x.id)===b.dataset.enquire)));
   document.querySelectorAll('[data-supplier-budget]').forEach(b=>b.onclick=()=>openBudget(rows.find(x=>String(x.id)===b.dataset.supplierBudget)));
  };
  const updateSummary=()=>{
   const vals=rows.map(s=>state[s.id]||{});
   const set=(q,v)=>{const e=document.querySelector(q);if(e)e.textContent=v};
   set('[data-supplier-shortlisted]',vals.filter(x=>x.shortlisted).length);
   set('[data-supplier-contacted]',vals.filter(x=>['contacted','quote','booked'].includes(x.status)).length);
   set('[data-supplier-quotes]',vals.filter(x=>['quote','booked'].includes(x.status)).length);
   set('[data-supplier-booked]',vals.filter(x=>x.status==='booked').length);
  };
  search.oninput=draw;cat.onchange=draw;draw();updateSummary();
 }
 function openEnquiry(s){
  if(!s)return;
  const modal=document.querySelector('[data-enquiry-modal]');
  modal.querySelector('[data-enquiry-supplier]').textContent=s.name;
  const couple=[ME?.wedding?.partner1,ME?.wedding?.partner2].filter(Boolean).join(' & ');
  modal.querySelector('[data-enquiry-text]').value=`Hi ${s.name},\n\n${couple||'We'} are planning our wedding${ME?.wedding?.date?' on '+ME.wedding.date:''}${ME?.wedding?.venue?' at '+ME.wedding.venue:''} and would love to learn more about your ${String(s.category||'wedding').toLowerCase()} services.\n\nCould you please let us know your availability, packages and pricing?\n\nThank you.`;
  modal.classList.add('open');
 }
 function openBudget(s){
  if(!s)return;const m=document.querySelector('[data-supplier-budget-modal]'),f=m.querySelector('form');f.reset();f.elements.name.value=s.category?`${s.category} — ${s.name}`:s.name;f.elements.category.value=s.category||'Supplier';f.elements.supplier.value=s.name;f.elements.planned.value=s.price_from||'';m.classList.add('open');
 }
 document.addEventListener('click',async e=>{
  if(e.target.closest('[data-close-enquiry]'))document.querySelector('[data-enquiry-modal]')?.classList.remove('open');
  if(e.target.closest('[data-copy-enquiry]')){const t=document.querySelector('[data-enquiry-text]');try{await navigator.clipboard.writeText(t.value);toast('Enquiry copied')}catch{t.select();document.execCommand('copy');toast('Enquiry copied')}}
  if(e.target.closest('[data-close-supplier-budget]'))document.querySelector('[data-supplier-budget-modal]')?.classList.remove('open');
 });
 document.addEventListener('submit',async e=>{
  if(!e.target.matches('[data-supplier-budget-form]'))return;e.preventDefault();const f=e.target,body=Object.fromEntries(new FormData(f).entries());body.payment_status=body.payment_status==='unpaid'?'not_paid':body.payment_status;await api('/api/budget',{method:'POST',body:JSON.stringify(body)});document.querySelector('[data-supplier-budget-modal]').classList.remove('open');toast('Supplier added to budget');
 });
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(start,0));else setTimeout(start,0);
})();