// Ceremli client-side plan guidance. Server remains the authority for paid actions.
(function(){
 const rank={free:0,premium:1,ultimate:2};
 const plan=()=>ME?.plan||'free';
 const paymentLinks={
  premium:'https://buy.stripe.com/test_8x214n2NH7Qz0do0ZQ6EU00',
  ultimate:'https://buy.stripe.com/test_eVq00jdsl3AjgcmcIy6EU01'
 };
 function lock(selector,min,label){if((rank[plan()]||0)>=rank[min])return;document.querySelectorAll(selector).forEach(el=>{el.dataset.planLocked='1';el.title=`${label} requires Ceremli ${min[0].toUpperCase()+min.slice(1)}`;el.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();if(confirm(`${label} is included with Ceremli ${min[0].toUpperCase()+min.slice(1)}. View plans?`))location.href='/pricing.html'},true)})}
 function start(){
  // Individual email invitations are part of Free. Premium starts at automation/polish.
  lock('[data-remind],[data-send-pending]','premium','Bulk and scheduled RSVP reminders');
  lock('[data-custom-domain]','ultimate','Custom domains');
  if(plan()==='free'){
   document.querySelectorAll('.theme-choice[data-theme="romantic"],.theme-choice[data-theme="modern"]').forEach(el=>{
    el.dataset.planLocked='1';el.title='Premium website design';
    el.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();if(confirm('Romantic and Modern designs are included with Ceremli Premium. View plans?'))location.href='/pricing.html'},true)
   });
  }
  document.querySelectorAll('[data-upgrade]').forEach(b=>{
   const target=b.dataset.upgrade;
   if(target===plan()){b.textContent='Current plan';b.disabled=true;return}
   if(paymentLinks[target]){
    b.addEventListener('click',e=>{
     e.preventDefault();e.stopImmediatePropagation();
     const sep=paymentLinks[target].includes('?')?'&':'?';
     const ref=`${target}|${ME?.email||''}`;
     location.href=`${paymentLinks[target]}${sep}client_reference_id=${encodeURIComponent(ref)}${ME?.email?`&prefilled_email=${encodeURIComponent(ME.email)}`:''}`;
    },true);
   }
  });
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(start,20));else setTimeout(start,20);
})();