// Ceremli client-side plan guidance. Server remains the authority for paid actions.
(function(){
 const rank={free:0,premium:1,ultimate:2};
 const plan=()=>ME?.plan||'free';
 function lock(selector,min,label){if((rank[plan()]||0)>=rank[min])return;document.querySelectorAll(selector).forEach(el=>{el.dataset.planLocked='1';el.title=`${label} requires Ceremli ${min[0].toUpperCase()+min.slice(1)}`;el.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();if(confirm(`${label} is included with Ceremli ${min[0].toUpperCase()+min.slice(1)}. View plans?`))location.href='/pricing.html'},true)})}
 function start(){
  lock('[data-send-invite],[data-remind],[data-send-pending]','premium','Email invitations and reminders');
  lock('[data-custom-domain]','ultimate','Custom domains');
  document.querySelectorAll('[data-upgrade]').forEach(b=>{const target=b.dataset.upgrade;if(target===plan()){b.textContent='Current plan';b.disabled=true}});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(start,20));else setTimeout(start,20);
})();