// Ceremli invitation page enhancements.
(function(){
  const ready = () => {
    if(document.body?.dataset?.page !== 'invitations') return;

    const form = document.querySelector('[data-invite-form]');
    const select = document.querySelector('[data-guest-select]');
    const subject = document.querySelector('[data-invite-subject]');
    const send = document.querySelector('[data-send-invite]');
    const result = document.querySelector('[data-invite-result]');
    const remind = document.querySelector('[data-remind]');
    const reminderResult = document.querySelector('[data-reminder-result]');
    if(!form || !select) return;

    // Use the couple's names in the default subject while leaving custom subjects untouched.
    const couple = [ME?.wedding?.partner1, ME?.wedding?.partner2].filter(Boolean).join(' & ');
    if(subject && (!subject.value || subject.value === "You're invited to our wedding")) {
      subject.value = couple ? `You're invited to ${couple}'s wedding` : "You're invited to our wedding";
    }

    // Replace the original submit handler with one that prevents accidental double sends
    // and gives a clear delivery result before refreshing history.
    form.onsubmit = async e => {
      e.preventDefault();
      if(!select.value) return;
      const original = send?.textContent || 'Send invitation';
      if(send){ send.disabled = true; send.textContent = 'Sending…'; }
      if(result) result.textContent = 'Sending invitation…';
      try {
        const payload = Object.fromEntries(new FormData(form).entries());
        const d = await api('/api/invitations/send', {method:'POST', body:JSON.stringify(payload)});
        const message = d.sent ? 'Invitation sent successfully.' : 'Invitation recorded in preview mode.';
        if(result) result.textContent = message;
        toast(message);
        setTimeout(()=>location.reload(), 900);
      } catch(err) {
        const message = err.message || 'Could not send invitation.';
        if(result) result.textContent = message;
        toast(message);
        if(send){ send.disabled = false; send.textContent = original; }
      }
    };

    // Make reminder sends deliberate and show progress/results without an immediate reload.
    if(remind){
      remind.onclick = async () => {
        if(!confirm('Send an RSVP reminder to every pending guest with an email address?')) return;
        const original = remind.textContent;
        remind.disabled = true;
        remind.textContent = 'Sending reminders…';
        if(reminderResult) reminderResult.textContent = 'Processing pending guests…';
        try {
          const d = await api('/api/reminders/send', {method:'POST', body:'{}'});
          const delivered = Number(d.sent || 0);
          const processed = Number(d.count || 0);
          const text = delivered
            ? `${delivered} reminder email${delivered===1?'':'s'} delivered${processed>delivered?` (${processed-delivered} not delivered)`:''}.`
            : `${processed} reminder${processed===1?'':'s'} processed.`;
          if(reminderResult) reminderResult.textContent = text;
          toast(text);
        } catch(err) {
          const text = err.message || 'Could not send reminders.';
          if(reminderResult) reminderResult.textContent = text;
          toast(text);
        } finally {
          remind.disabled = false;
          remind.textContent = original;
        }
      };
    }
  };

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ()=>setTimeout(ready,0));
  else setTimeout(ready,0);
})();
