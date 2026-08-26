// Ceremli seating planner. Loaded before app.js so app.js can call seatingPage().
window.seatingPage = async function seatingPage(){
  const state = await api('/api/seating');
  const tables = state.tables || [];
  const guests = state.guests || [];
  const grid = document.querySelector('[data-table-grid]');
  const unseatedList = document.querySelector('[data-unseated-list]');
  const seatedEl = document.querySelector('[data-seated]');
  const unseatedEl = document.querySelector('[data-unseated]');
  const capEl = document.querySelector('[data-seat-capacity]');
  const pill = document.querySelector('[data-unseated-pill]');

  const assigned = guests.filter(g=>g.assignment);
  const unseated = guests.filter(g=>!g.assignment && g.rsvp!=='no');
  const capacity = tables.reduce((n,t)=>n+Number(t.capacity||0),0);
  if(seatedEl) seatedEl.textContent = assigned.length;
  if(unseatedEl) unseatedEl.textContent = unseated.length;
  if(capEl) capEl.textContent = capacity;
  if(pill) pill.textContent = `${unseated.length} guest${unseated.length===1?'':'s'}`;

  const guestName = id => guests.find(g=>Number(g.id)===Number(id))?.name || 'Guest';
  const tableGuests = tableId => guests.filter(g=>g.assignment && Number(g.assignment.table_id)===Number(tableId));

  function renderTables(){
    grid.innerHTML = tables.length ? tables.map(t=>{
      const seated = tableGuests(t.id);
      const free = Math.max(0, Number(t.capacity||0)-seated.length);
      return `<article class="seat-table-card" data-table-card="${t.id}">
        <div class="seat-table-head">
          <div><span class="eyebrow">${esc(t.shape||'round')} table</span><h3>${esc(t.name)}</h3></div>
          <span class="seat-count ${free===0?'full':''}">${seated.length}/${t.capacity}</span>
        </div>
        <div class="seat-guest-list">
          ${seated.length ? seated.map(g=>`<div class="seat-guest"><div><strong>${esc(g.name)}</strong><small>${g.rsvp==='yes'?'Attending':g.rsvp==='pending'?'Pending RSVP':'Declined'}</small></div><button class="icon-btn" type="button" title="Remove from table" data-unseat="${g.id}">×</button></div>`).join('') : '<div class="empty-state compact">No guests seated here yet.</div>'}
        </div>
        <div class="seat-table-actions">
          <select class="input" data-assign-select="${t.id}">
            <option value="">${free ? 'Add guest to table' : 'Table full'}</option>
            ${free ? unseated.map(g=>`<option value="${g.id}">${esc(g.name)}</option>`).join('') : ''}
          </select>
          <button class="btn btn-secondary btn-small" type="button" data-edit-table="${t.id}">Edit</button>
          <button class="text-link danger-link" type="button" data-delete-table="${t.id}">Delete</button>
        </div>
      </article>`;
    }).join('') : '<div class="empty-state">Create your first table to start planning the room.</div>';

    document.querySelectorAll('[data-assign-select]').forEach(sel=>sel.onchange=async()=>{
      if(!sel.value) return;
      sel.disabled=true;
      try{
        await api('/api/seating/assign',{method:'POST',body:JSON.stringify({guest_id:Number(sel.value),table_id:Number(sel.dataset.assignSelect)})});
        toast(`${guestName(sel.value)} seated`);
        await seatingPage();
      }catch(e){ toast(e.message||'Could not seat guest'); sel.disabled=false; }
    });

    document.querySelectorAll('[data-unseat]').forEach(btn=>btn.onclick=async()=>{
      await api(`/api/seating/assignments/${btn.dataset.unseat}`,{method:'DELETE'});
      toast(`${guestName(btn.dataset.unseat)} moved to unseated`);
      await seatingPage();
    });

    document.querySelectorAll('[data-delete-table]').forEach(btn=>btn.onclick=async()=>{
      const table=tables.find(x=>Number(x.id)===Number(btn.dataset.deleteTable));
      if(!confirm(`Delete ${table?.name||'this table'}? Guests seated here will become unseated.`)) return;
      await api(`/api/seating/tables/${btn.dataset.deleteTable}`,{method:'DELETE'});
      toast('Table deleted');
      await seatingPage();
    });

    document.querySelectorAll('[data-edit-table]').forEach(btn=>btn.onclick=()=>openTable(tables.find(x=>Number(x.id)===Number(btn.dataset.editTable))));
  }

  if(unseatedList){
    unseatedList.innerHTML = unseated.length ? unseated.map(g=>`<div class="unseated-guest"><div><strong>${esc(g.name)}</strong><small>${esc(g.group_name||'Guest')} · ${g.rsvp==='yes'?'Attending':'Pending RSVP'}</small></div></div>`).join('') : '<div class="empty-state compact">Everyone attending is seated.</div>';
  }

  const modal=document.querySelector('[data-table-modal]');
  const form=document.querySelector('[data-table-form]');
  const title=modal?.querySelector('.modal-head h3');
  let editing=null;
  const openTable=t=>{
    editing=t||null;
    form.reset();
    if(title) title.textContent=t?'Edit table':'Add a table';
    if(t){ form.elements.name.value=t.name||''; form.elements.capacity.value=t.capacity||8; form.elements.shape.value=t.shape||'round'; }
    modal.classList.add('open');
  };
  const add=document.querySelector('[data-add-table]');
  const close=document.querySelector('[data-close-table]');
  if(add) add.onclick=()=>openTable(null);
  if(close) close.onclick=()=>modal.classList.remove('open');
  if(modal) modal.onclick=e=>{ if(e.target===modal) modal.classList.remove('open'); };
  if(form) form.onsubmit=async e=>{
    e.preventDefault();
    const body=Object.fromEntries(new FormData(form).entries());
    const url=editing?`/api/seating/tables/${editing.id}`:'/api/seating/tables';
    await api(url,{method:editing?'PUT':'POST',body:JSON.stringify(body)});
    modal.classList.remove('open');
    toast(editing?'Table updated':'Table created');
    await seatingPage();
  };

  renderTables();
};
