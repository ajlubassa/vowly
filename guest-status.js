// Ceremli guest invitation status indicators.
(function(){
  const fmtDate = value => {
    if(!value) return '';
    const d = new Date(value);
    if(Number.isNaN(d.getTime())) return String(value).slice(0,10);
    return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
  };

  async function refreshInviteStatus(){
    if(document.body?.dataset?.page !== 'guests') return;
    try{
      const [guestData, inviteData] = await Promise.all([
        api('/api/guests'),
        api('/api/invitations')
      ]);
      const guests = guestData.guests || [];
      const history = inviteData.history || [];
      const latestByEmail = new Map();
      history.forEach(item => {
        const email = String(item.recipient || '').trim().toLowerCase();
        if(email && !latestByEmail.has(email)) latestByEmail.set(email,item);
      });

      document.querySelectorAll('[data-resend-guest]').forEach(button => {
        const id = Number(button.dataset.resendGuest);
        const guest = guests.find(g => Number(g.id) === id);
        if(!guest) return;
        const actions = button.closest('.guest-card-actions');
        const card = button.closest('.guest-card');
        if(!actions || !card) return;
        card.querySelector('[data-invite-status]')?.remove();

        const email = String(guest.email || '').trim().toLowerCase();
        const last = latestByEmail.get(email);
        const wrap = document.createElement('div');
        wrap.dataset.inviteStatus = 'true';
        wrap.style.marginTop = '12px';
        wrap.style.display = 'flex';
        wrap.style.alignItems = 'center';
        wrap.style.gap = '8px';
        wrap.style.flexWrap = 'wrap';
        wrap.style.fontSize = '12px';

        const badge = document.createElement('span');
        badge.style.padding = '5px 9px';
        badge.style.borderRadius = '999px';
        badge.style.background = 'var(--sand, #f4efe8)';
        badge.style.fontWeight = '700';

        if(!email){
          badge.textContent = 'No email address';
          button.disabled = true;
          button.title = 'Add an email address before sending an invitation';
        } else if(last){
          badge.textContent = last.status === 'sent' ? 'Invite sent' : 'Invite previewed';
          const date = document.createElement('span');
          date.style.color = 'var(--muted, #777)';
          date.textContent = `Last sent ${fmtDate(last.created_at)}`;
          wrap.append(badge,date);
          button.textContent = 'Resend invite';
        } else {
          badge.textContent = 'Not yet invited';
          wrap.append(badge);
          button.textContent = 'Send invite';
        }

        if(!wrap.contains(badge)) wrap.append(badge);
        actions.parentNode.insertBefore(wrap, actions);
      });
    }catch(err){
      console.error('Could not load invitation status',err);
    }
  }

  document.addEventListener('ceremli:invite-sent', refreshInviteStatus);
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded',()=>setTimeout(refreshInviteStatus,150));
  else setTimeout(refreshInviteStatus,150);
})();
