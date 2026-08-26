// Launch fix: resend a single guest invitation with sensible defaults.
(function(){
 document.addEventListener('click',async function(e){
  const b=e.target.closest('[data-resend-guest]');
  if(!b)return;
  e.preventDefault();e.stopImmediatePropagation();
  const id=Number(b.dataset.resendGuest);if(!id)return;
  b.disabled=true;const old=b.textContent;b.textContent='Sending…';
  try{
   await api('/api/invitations/send',{method:'POST',body:JSON.stringify({guest_id:id,subject:"You're invited to our wedding",message:'We would love for you to celebrate our wedding with us. Please visit our wedding page for the details and let us know if you can join us.'})});
   toast('Invitation sent');
  }catch(err){toast(err.message||'Could not send invitation')}
  finally{b.disabled=false;b.textContent=old}
 },true);
})();