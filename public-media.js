// Public Wedding Party + Gallery renderer.
(function(){
 const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
 const groupOf=p=>{if(p.group)return p.group;const r=String(p.role||'').toLowerCase();if(/groom|best man/.test(r))return'groomsmen';if(/bride|maid of honour|maid of honor|matron/.test(r))return'bridesmaids';return'other'};
 const groupLabel=g=>g==='bridesmaids'?'Bridesmaids':g==='groomsmen'?'Groomsmen':'Family & others';
 const card=p=>`<article class="public-party-card">${p.photo?`<img src="${p.photo}" alt="${esc(p.name)}">`:'<div class="public-party-placeholder">♡</div>'}<div><span class="eyebrow">${esc(p.role||'Wedding party')}</span><h3>${esc(p.name)}</h3>${p.bio?`<p>${esc(p.bio)}</p>`:''}</div></article>`;
 async function start(){
  const slug=decodeURIComponent(location.pathname.split('/').filter(Boolean).pop()||'');if(!slug)return;
  try{
   const r=await fetch(`/api/public/wedding/${encodeURIComponent(slug)}/media`);const d=await r.json();if(!r.ok)return;
   const party=document.querySelector('[data-public-party]'),gallery=document.querySelector('[data-public-gallery]');
   if(party){const rows=d.party||[];party.hidden=!rows.length;if(rows.length){party.querySelector('[data-public-party-grid]').innerHTML=['bridesmaids','groomsmen','other'].map(g=>{const items=rows.filter(p=>groupOf(p)===g);return items.length?`<section class="public-party-group"><h3 class="public-party-group-title">${groupLabel(g)}</h3><div class="public-party-subgrid">${items.map(card).join('')}</div></section>`:''}).join('')}}
   if(gallery){const rows=d.gallery||[];gallery.hidden=!rows.length;if(rows.length)gallery.querySelector('[data-public-gallery-grid]').innerHTML=rows.map((x,i)=>`<figure class="public-gallery-item"><img src="${x.src}" alt="Wedding photo ${i+1}" loading="lazy"></figure>`).join('')}
  }catch(e){console.error('Ceremli media',e)}
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();