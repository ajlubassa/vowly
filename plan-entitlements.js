// Ceremli client-side plan guidance. Server remains the authority for paid actions.
(function(){
 const rank={free:0,premium:1,ultimate:2};
 const plan=()=>ME?.plan||'free';
 function lock(selector,min,label){if((rank[plan()]||0)>=rank[min])return;document.querySelectorAll(selector).forEach(el=>{el.dataset.planLocked='1';el.title=`${label} requires Ceremli ${min[0].toUpperCase()+min.slice(1)}`;el.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();if(confirm(`${label} is included with Ceremli ${min[0].toUpperCase()+min.slice(1)}. View plans?`))location.href='/pricing.html'},true)})}
 async function checkout(target,button){
  const old=button?.textContent;
  try{
   if(button){button.disabled=true;button.textContent='Opening checkout…'}
   const d=await api('/api/billing/checkout',{method:'POST',body:JSON.stringify({plan:target})});
   if(!d||!d.url)throw new Error('Checkout link was not returned');
   window.location.assign(d.url);
  }catch(e){
   if(button){button.disabled=false;button.textContent=old}
   toast(e.message||'Could not start checkout');
  }
 }
 function watchSuccess(){
  if(!new URLSearchParams(location.search).has('checkout'))return;
  const state=new URLSearchParams(location.search).get('checkout');
  if(state==='cancelled'){toast('Payment cancelled');return}
  if(state!=='success')return;
  let tries=0;
  const poll=async()=>{tries++;try{const me=await api('/api/me');if(me.plan&&me.plan!=='free'){toast(`Payment confirmed — ${me.plan[0].toUpperCase()+me.plan.slice(1)} is now active`);setTimeout(()=>location.replace('/pricing.html'),1200);return}}catch(e){}if(tries<20)setTimeout(poll,1000);else toast('Payment received. Your upgrade is still processing.')};
  poll();
 }
 function syncPricingButtons(){
  const current=plan();
  document.querySelectorAll('[data-upgrade]').forEach(b=>{
   const target=b.dataset.upgrade;
   b.hidden=false;
   b.disabled=false;
   if(target===current){b.textContent='Current plan';b.disabled=true;return}
   // Free is not a second "current" plan after a paid upgrade.
   if(target==='free'&&current!=='free'){b.hidden=true;return}
   if(target==='premium'||target==='ultimate')b.onclick=e=>{e.preventDefault();checkout(target,b)};
  });
  // Clean up any legacy pricing label such as "Current / Free" left by app.js.
  if(current!=='free')document.querySelectorAll('button,a').forEach(el=>{if(/^Current\s*\/\s*Free$/i.test((el.textContent||'').trim()))el.hidden=true});
 }
 function start(){
  lock('[data-remind],[data-send-pending]','premium','Bulk and scheduled RSVP reminders');
  lock('[data-custom-domain]','ultimate','Custom domains');
  if(plan()==='free')document.querySelectorAll('.theme-choice[data-theme="romantic"],.theme-choice[data-theme="modern"]').forEach(el=>{el.dataset.planLocked='1';el.title='Premium website design';el.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();if(confirm('Romantic and Modern designs are included with Ceremli Premium. View plans?'))location.href='/pricing.html'},true)});
  syncPricingButtons();
  setTimeout(syncPricingButtons,300);
  watchSuccess();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(start,50));else setTimeout(start,50);
})();