// Ceremli client-side plan guidance. Server remains the authority for paid actions.
(function(){
 const rank={free:0,premium:1,ultimate:2};
 const plan=()=>ME?.plan||'free';
 function lock(selector,min,label){if((rank[plan()]||0)>=rank[min])return;document.querySelectorAll(selector).forEach(el=>{el.dataset.planLocked='1';el.title=`${label} requires Ceremli ${min[0].toUpperCase()+min.slice(1)}`;el.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();if(confirm(`${label} is included with Ceremli ${min[0].toUpperCase()+min.slice(1)}. View plans?`))location.href='/pricing.html'},true)})}
 async function checkout(target){
  try{
   const d=await api('/api/billing/checkout',{method:'POST',body:JSON.stringify({plan:target})});
   if(d.url)location.href=d.url;else toast('Checkout is unavailable. Please try again.');
  }catch(e){toast(e.message||'Could not start checkout')}
 }
 function watchSuccess(){
  if(!new URLSearchParams(location.search).has('checkout'))return;
  const state=new URLSearchParams(location.search).get('checkout');
  if(state==='cancelled'){toast('Payment cancelled');return}
  if(state!=='success')return;
  let tries=0;
  const poll=async()=>{tries++;try{const me=await api('/api/me');if(me.plan&&me.plan!=='free'){toast(`${me.plan[0].toUpperCase()+me.plan.slice(1)} is now active`);setTimeout(()=>location.replace('/pricing.html'),700);return}}catch(e){}if(tries<20)setTimeout(poll,1000);else toast('Payment received. Your upgrade is still processing.')};
  poll();
 }
 function start(){
  lock('[data-remind],[data-send-pending]','premium','Bulk and scheduled RSVP reminders');
  lock('[data-custom-domain]','ultimate','Custom domains');
  if(plan()==='free')document.querySelectorAll('.theme-choice[data-theme="romantic"],.theme-choice[data-theme="modern"]').forEach(el=>{el.dataset.planLocked='1';el.title='Premium website design';el.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();if(confirm('Romantic and Modern designs are included with Ceremli Premium. View plans?'))location.href='/pricing.html'},true)});
  document.querySelectorAll('[data-upgrade]').forEach(b=>{const target=b.dataset.upgrade;if(target===plan()){b.textContent='Current plan';b.disabled=true;return}if(target==='premium'||target==='ultimate')b.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();checkout(target)},true)});
  watchSuccess();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(start,20));else setTimeout(start,20);
})();