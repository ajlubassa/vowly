// Ceremli guest invitation actions
(function(){
  const inviteSubject = () => {
    const p1 = ME?.wedding?.partner1 || '';
    const p2 = ME?.wedding?.partner2 || '';
    return p1 && p2 ? `You're invited to ${p1} & ${p2}'s wedding` : "You're invited to our wedding";
  };
  const inviteMessage = 'We would love for you to celebrate our wedding with us. Please visit our wedding page for the details and let us know if you can join us.';

  async function resendGuestInvite(button){
    const guestId = Number(button.dataset.resendGuest);
    if(!guestId) return;
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Sending…';
    try{
      const data = await api('/api/guests');
      const guest = (data.guests || []).find(g => Number(g.id) === guestId);
      if(!guest) throw new Error('Guest not found');
      if(!guest.email) throw new Error('This guest has no email address');
      const result = await api('/api/invitations/send', {
        method: 'POST',
        body: JSON.stringify({guest_id: guest.id, subject: inviteSubject(), message: inviteMessage})
      });
      toast(result.sent ? `Invitation resent to ${guest.email}` : 'Invitation recorded in preview mode');
    }catch(e){
      console.error(e);
      toast(e.message || 'Could not resend invitation');
    }finally{
      button.disabled = false;
      button.textContent = original;
    }
  }

  async function sendPendingInvites(button){
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Sending…';
    try{
      const data = await api('/api/guests');
      const pending = (data.guests || []).filter(g => g.rsvp === 'pending' && g.email);
      if(!pending.length){ toast('No pending guests with email addresses'); return; }
      let sent = 0, failed = 0;
      for(const guest of pending){
        try{
          const result = await api('/api/invitations/send', {
            method: 'POST',
            body: JSON.stringify({guest_id: guest.id, subject: inviteSubject(), message: inviteMessage})
          });
          result.sent ? sent++ : failed++;
        }catch(err){ failed++; console.error('Invite failed for', guest.email, err); }
      }
      toast(failed ? `${sent} sent · ${failed} failed` : `${sent} invitation${sent===1?'':'s'} sent`);
    }catch(e){
      console.error(e);
      toast(e.message || 'Could not send invitations');
    }finally{
      button.disabled = false;
      button.textContent = original;
    }
  }

  // Capture-phase handling prevents the older inline guest handler in app.js from firing too.
  document.addEventListener('click', e => {
    const resend = e.target.closest('[data-resend-guest]');
    if(resend){
      e.preventDefault();
      e.stopPropagation();
      resendGuestInvite(resend);
      return;
    }
    const pending = e.target.closest('[data-send-pending-invites]');
    if(pending){
      e.preventDefault();
      e.stopPropagation();
      sendPendingInvites(pending);
    }
  }, true);
})();
