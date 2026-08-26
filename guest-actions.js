// Ceremli guest invitation actions
(function(){
  const inviteSubject = () => `You're invited to ${ME?.wedding?.partner1 || 'our'} & ${ME?.wedding?.partner2 || ''}'s wedding`.replace(' & \'s',' wedding');
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
        body: JSON.stringify({
          guest_id: guest.id,
          subject: inviteSubject(),
          message: inviteMessage
        })
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
      if(!pending.length){
        toast('No pending guests with email addresses');
        return;
      }
      let sent = 0;
      for(const guest of pending){
        try{
          const result = await api('/api/invitations/send', {
            method: 'POST',
            body: JSON.stringify({guest_id: guest.id, subject: inviteSubject(), message: inviteMessage})
          });
          if(result.sent) sent += 1;
        }catch(err){ console.error('Invite failed for', guest.email, err); }
      }
      toast(`${sent} invitation${sent===1?'':'s'} sent`);
    }catch(e){
      console.error(e);
      toast(e.message || 'Could not send invitations');
    }finally{
      button.disabled = false;
      button.textContent = original;
    }
  }

  document.addEventListener('click', e => {
    const resend = e.target.closest('[data-resend-guest]');
    if(resend){ e.preventDefault(); resendGuestInvite(resend); return; }
    const pending = e.target.closest('[data-send-pending-invites]');
    if(pending){ e.preventDefault(); sendPendingInvites(pending); }
  });
})();
