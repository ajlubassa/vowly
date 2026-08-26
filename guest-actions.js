// Ceremli guest invitation actions
(function(){
  const inviteSubject = () => {
    const p1 = ME?.wedding?.partner1 || '';
    const p2 = ME?.wedding?.partner2 || '';
    return p1 && p2 ? `You're invited to ${p1} & ${p2}'s wedding` : "You're invited to our wedding";
  };

  const inviteMessage = 'We would love for you to celebrate our wedding with us. Please visit our wedding page for the details and let us know if you can join us.';

  async function getGuest(guestId){
    const data = await api('/api/guests');
    return (data.guests || []).find(g => Number(g.id) === Number(guestId));
  }

  async function resendGuestInvite(button){
    const guestId = Number(button.dataset.resendGuest);
    if(!guestId) return;

    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Sending…';

    try{
      const guest = await getGuest(guestId);
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

    try{
      const data = await api('/api/guests');
      const pending = (data.guests || []).filter(g => g.rsvp === 'pending' && g.email);

      if(!pending.length){
        toast('No pending guests with email addresses');
        return;
      }

      const confirmed = window.confirm(
        `Send wedding invitations to ${pending.length} pending guest${pending.length === 1 ? '' : 's'}?`
      );
      if(!confirmed) return;

      button.disabled = true;
      button.textContent = `Sending 0/${pending.length}…`;

      let sent = 0;
      let failed = 0;

      for(let i = 0; i < pending.length; i++){
        const guest = pending[i];
        button.textContent = `Sending ${i + 1}/${pending.length}…`;

        try{
          const result = await api('/api/invitations/send', {
            method: 'POST',
            body: JSON.stringify({
              guest_id: guest.id,
              subject: inviteSubject(),
              message: inviteMessage
            })
          });
          result.sent ? sent++ : failed++;
        }catch(err){
          failed++;
          console.error('Invite failed for', guest.email, err);
        }
      }

      toast(failed ? `${sent} sent · ${failed} failed` : `${sent} invitation${sent === 1 ? '' : 's'} sent`);
    }catch(e){
      console.error(e);
      toast(e.message || 'Could not send invitations');
    }finally{
      button.disabled = false;
      button.textContent = original;
    }
  }

  function exportCeremliGuests(button){
    button.disabled = true;
    const original = button.textContent;
    button.textContent = 'Exporting…';

    api('/api/guests').then(data => {
      const rows = data.guests || [];
      const head = ['Name','Email','Household','Group','RSVP','Meal','Dietary','Plus one','Plus-one name','Notes'];
      const csvRows = [head, ...rows.map(g => [
        g.name,
        g.email || '',
        g.household_name || '',
        g.group_name || '',
        g.rsvp || '',
        g.meal_choice || '',
        g.dietary || '',
        g.plus_one ? 'Yes' : 'No',
        g.plus_one_name || '',
        g.notes || ''
      ])];

      const csv = csvRows
        .map(row => row.map(value => `"${String(value ?? '').replaceAll('"','""')}"`).join(','))
        .join('\n');

      const blob = new Blob([csv], {type:'text/csv;charset=utf-8'});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'ceremli-guests.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(link.href);
      toast('Guest list exported');
    }).catch(e => {
      console.error(e);
      toast(e.message || 'Could not export guest list');
    }).finally(() => {
      button.disabled = false;
      button.textContent = original;
    });
  }

  // Capture phase prevents legacy click handlers in app.js from running for these controls.
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
      return;
    }

    const exportButton = e.target.closest('[data-export]');
    if(exportButton){
      e.preventDefault();
      e.stopPropagation();
      exportCeremliGuests(exportButton);
    }
  }, true);
})();
