// Ceremli wedding party + gallery editor. Media is resized in-browser then persisted to the wedding account.
(function(){
 const MAX_PARTY=20,MAX_GALLERY=24;
 const injectFixes=()=>{if(document.getElementById('ceremli-party-fixes'))return;const st=document.createElement('style');st.id='ceremli-party-fixes';st.textContent=`
 [data-party-form]{display:grid;gap:16px;margin-top:18px}
 [data-party-form] label{display:block;font-weight:800;color:var(--ink);line-height:1.35}
 [data-party-form] label>.input{display:block;margin-top:7px}
 [data-party-form] button[type=submit]{color:var(--ink)!important;background:#fff!important;border:1px solid var(--line)!important;min-height:46px;line-height:1.2;white-space:normal;padding:12px 18px}
 [data-party-form] button[type=submit]:disabled{opacity:.65}
 .media-person{display:grid;grid-template-columns:64px minmax(0,1fr) 40px;gap:14px;align-items:start;padding:14px 0;border-bottom:1px solid var(--line)}
 .media-person>img{width:64px;height:64px;object-fit:cover;border-radius:14px;background:var(--sand)}
 .media-person>div{min-width:0}
 .media-person strong,.media-person small,.media-person p{display:block}
 .media-person strong{font-size:17px;line-height:1.25;color:var(--ink)}
 .media-person small{margin-top:3px;color:var(--sage-dark);font-weight:800}
 .media-person p{margin:7px 0 0;color:var(--muted);line-height:1.5;overflow-wrap:anywhere}
 .media-person .icon-btn{justify-self:end;line-height:1;color:var(--danger)}
 .gallery-edit-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
 .gallery-edit-item{position:relative;overflow:hidden;border-radius:14px;background:var(--sand);aspect-ratio:1}
 .gallery-edit-item img{width:100%;height:100%;object-fit:cover;display:block}
 .gallery-edit-item .icon-btn{position:absolute;top:6px;right:6px;width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.92);color:var(--danger);display:grid;place-items:center}
 @media(max-width:560px){[data-party-form] button[type=submit]{width:100%}.media-person{grid-template-columns:56px minmax(0,1fr) 36px}.media-person>img{width:56px;height:56px}.gallery-edit-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
 `;document.head.appendChild(st)};
 const compress=file=>new Promise((resolve,reject)=>{const img=new Image(),url=URL.createObjectURL(file);img.onload=()=>{try{const max=1200,scale=Math.min(1,max/Math.max(img.width,img.height)),c=document.createElement('canvas');c.width=Math.max(1,Math.round(img.width*scale));c.height=Math.max(1,Math.round(img.height*scale));c.getContext('2d').drawImage(img,0,0,c.width,c.height);const data=c.toDataURL('image/jpeg',.82);URL.revokeObjectURL(url);resolve(data)}catch(e){reject(e)}};img.onerror=()=>{URL.revokeObjectURL(url);reject(new Error('Could not read image'))};img.src=url});
 async function start(){
  if(document.body?.dataset?.page!=='builder')return;
  injectFixes();
  let s={party:[],gallery:[]};
  try{s=await api('/api/wedding/media')}catch(e){console.error(e);toast('Could not load wedding photos')}
  s.party=s.party||[];s.gallery=s.gallery||[];
  const party=document.querySelector('[data-party-list]'),gallery=document.querySelector('[data-gallery-list]');
  const persist=async()=>{await api('/api/wedding/media',{method:'PUT',body:JSON.stringify(s)})};
  const renderPreview=()=>{const pp=document.querySelector('[data-preview-party]'),pg=document.querySelector('[data-preview-gallery]');if(pp){pp.style.display=s.party.length?'block':'none';pp.querySelector('[data-preview-party-grid]').innerHTML=s.party.map(p=>`<div class="party-preview-card">${p.photo?`<img src="${p.photo}" alt="${esc(p.name)}">`:''}<strong>${esc(p.name)}</strong><small>${esc(p.role)}</small><p>${esc(p.bio||'')}</p></div>`).join('')}if(pg){pg.style.display=s.gallery.length?'block':'none';pg.querySelector('[data-preview-gallery-grid]').innerHTML=s.gallery.map(x=>`<img src="${x.src}" alt="Wedding photo">`).join('')}};
  const draw=()=>{party.innerHTML=s.party.length?s.party.map((p,i)=>`<div class="media-person">${p.photo?`<img src="${p.photo}" alt="">`:'<div aria-hidden="true"></div>'}<div><strong>${esc(p.name)}</strong><small>${esc(p.role)}</small><p>${esc(p.bio||'')}</p></div><button class="icon-btn" data-party-delete="${i}" type="button" aria-label="Remove ${esc(p.name)}">×</button></div>`).join(''):'<p class="muted">No wedding party members added yet.</p>';gallery.innerHTML=s.gallery.length?s.gallery.map((x,i)=>`<div class="gallery-edit-item"><img src="${x.src}" alt=""><button class="icon-btn" data-gallery-delete="${i}" type="button" aria-label="Remove photo">×</button></div>`).join(''):'<p class="muted">No gallery photos yet.</p>';renderPreview()};
  document.querySelector('[data-party-form]').onsubmit=async e=>{e.preventDefault();if(s.party.length>=MAX_PARTY)return toast(`You can add up to ${MAX_PARTY} wedding party members`);const f=e.currentTarget,d=Object.fromEntries(new FormData(f)),photo=f.elements.photo.files[0];const btn=f.querySelector('button[type=submit]');btn.disabled=true;btn.textContent='Saving…';try{if(photo)d.photo=await compress(photo);s.party.push({name:String(d.name||'').trim(),role:String(d.role||'').trim(),bio:String(d.bio||'').trim(),photo:d.photo||''});await persist();f.reset();draw();toast('Wedding party member saved')}catch(x){s.party.pop();toast(x.message||'Could not save photo')}finally{btn.disabled=false;btn.textContent='Add wedding party member'}};
  document.querySelector('[data-gallery-input]').onchange=async e=>{const files=[...e.target.files].slice(0,MAX_GALLERY-s.gallery.length);if(!files.length)return;toast('Preparing photos…');const startCount=s.gallery.length;try{for(const f of files)s.gallery.push({src:await compress(f)});await persist();draw();toast(`${files.length} photo${files.length===1?'':'s'} saved`)}catch(x){s.gallery=s.gallery.slice(0,startCount);draw();toast(x.message||'Could not save photos')}e.target.value=''};
  document.addEventListener('click',async e=>{let b=e.target.closest('[data-party-delete]');if(b){const i=+b.dataset.partyDelete,old=s.party.splice(i,1)[0];draw();try{await persist();toast('Wedding party member removed')}catch{s.party.splice(i,0,old);draw();toast('Could not remove member')}return}b=e.target.closest('[data-gallery-delete]');if(b){const i=+b.dataset.galleryDelete,old=s.gallery.splice(i,1)[0];draw();try{await persist();toast('Photo removed')}catch{s.gallery.splice(i,0,old);draw();toast('Could not remove photo')}}});draw();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(start,0));else setTimeout(start,0);
})();