// Ceremli dashboard enhancements.
(function(){
  async function enhanceDashboard(){
    if(document.body?.dataset?.page !== 'dashboard') return;
    try{
      const d = await api('/api/dashboard');
      const total = Number(d?.stats?.total || 0);
      const yes = Number(d?.stats?.yes || 0);
      const pending = Number(d?.stats?.pending || 0);
      const no = Number(d?.stats?.no || 0);
      const responded = Math.max(0, total - pending);
      const responsePct = total ? Math.round(responded / total * 100) : 0;

      const pct = document.querySelector('[data-rsvp-percent]');
      if(pct) pct.textContent = `${responsePct}%`;

      const donut = document.querySelector('[data-rsvp-donut]');
      if(donut){
        const angle = Math.max(0, Math.min(100, responsePct)) * 3.6;
        donut.style.background = `conic-gradient(var(--sage-dark) 0deg ${angle}deg, var(--sand) ${angle}deg 360deg)`;
      }

      const title = document.querySelector('[data-next-title]');
      const copy = document.querySelector('[data-next-copy]');
      const link = document.querySelector('[data-next-link]');
      const tasks = Array.isArray(d?.tasks) ? d.tasks : [];
      const incomplete = tasks.filter(t => !t.done);

      let next = {
        title: 'Build your guest list',
        copy: 'Add the people you want to celebrate with so you can start collecting RSVPs.',
        href: 'guests.html',
        label: 'Manage guests'
      };

      if(total > 0 && pending > 0){
        next = {
          title: `${pending} guest${pending===1?' is':'s are'} awaiting an RSVP`,
          copy: 'Send invitations or reminders and keep an eye on responses from one place.',
          href: 'invitations.html',
          label: 'Open invitations'
        };
      } else if(total > 0 && incomplete.length){
        next = {
          title: incomplete[0].title || 'Continue your wedding checklist',
          copy: incomplete[0].due ? `Next task · ${incomplete[0].due}` : 'Keep your planning moving with the next task on your checklist.',
          href: 'checklist.html',
          label: 'View checklist'
        };
      } else if(total > 0 && responded === total){
        next = {
          title: 'Your guest responses are up to date',
          copy: `${yes} attending${no ? ` · ${no} declined` : ''}. You can now focus on seating, events and the final details.`,
          href: 'seating.html',
          label: 'Plan seating'
        };
      }

      if(title) title.textContent = next.title;
      if(copy) copy.textContent = next.copy;
      if(link){ link.href = next.href; link.textContent = next.label; }
    }catch(e){
      console.error('Dashboard enhancement failed', e);
    }
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ()=>setTimeout(enhanceDashboard,0));
  else setTimeout(enhanceDashboard,0);
})();
