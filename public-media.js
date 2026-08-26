// Public Wedding Party + Gallery renderer.
(function(){
 const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
 async function start(){
  const slug=decodeURIComponent(location.pathname.split('/').filter(Boolean).pop()||'');if(!slug)return;
  try{
   const r=await fetch(`/api/public/wedding/${encodeURIComponent(slug)}/media`);const d=await r.json();if(!r.ok)return;
   const party=document.querySelector('[data-public-party]'),gallery=document.querySelector('[data-public-gallery]');
   if(party){const rows=d.party||[];party.hidden=!rows.length;if(rows.length)party.querySelector('[data-public-party-grid]').innerHTML=rows.map(p=>`<article class="public-party-card">${p.photo?`<img src="${p.photo}" alt="${esc(p.name)}">`:'<div class="public-party-placeholder">♡</div>'}<div><span class="eyebrow">${esc(p.role||'Wedding party')}</span><h3>${esc(p.name)}</h3>${p.bio?`<p>${esc(p.bio)}</p>`:''}</div></article>`).join('')}
   if(gallery){const rows=d.gallery||[];gallery.hidden=!rows.length;if(rows.length)gallery.querySelector('[data-public-gallery-grid]').innerHTML=rows.map((x,i)=>`<figure class="public-gallery-item"><img src="${x.src}" alt="Wedding photo ${i+1}" loading="lazy"></figure>`).join('')}
  }catch(e){console.error('Ceremli media',e)}
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();