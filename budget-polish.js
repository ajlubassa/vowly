// Ceremli budget enhancements: cashflow, payment health, quick actions, export.
(function(){
  const money=n=>'£'+Number(n||0).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:2});
  const today=()=>new Date().toISOString().slice(0,10);
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

  async function ready(){
    if(document.body?.dataset?.page!=='budget') return;
    let data;
    try{ data=await api('/api/budget'); }catch(e){ console.error(e); return; }
    const rows=data.items||[], totals=data.totals||{}, now=today();

    const committed=rows.reduce((s,x)=>s+Number(x.actual||x.planned||0),0);
    const paid=rows.reduce((s,x)=>s+Number(x.paid||0),0);
    const outstanding=Math.max(0,committed-paid);
    const overdue=rows.filter(x=>x.due_date&&x.due_date<now&&x.payment_status!=='paid');
    const dueSoon=rows.filter(x=>x.due_date&&x.due_date>=now&&x.payment_status!=='paid')
      .sort((a,b)=>a.due_date.localeCompare(b.due_date));

    const out=document.querySelector('[data-budget-outstanding]');
    const overdueEl=document.querySelector('[data-budget-overdue]');
    const paidPct=document.querySelector('[data-budget-paid-pct]');
    if(out) out.textContent=money(outstanding);
    if(overdueEl) overdueEl.textContent=String(overdue.length);
    if(paidPct) paidPct.textContent=committed?`${Math.round(paid/committed*100)}%`:'0%';

    const health=document.querySelector('[data-budget-health]');
    if(health){
      if(overdue.length){
        const overdueValue=overdue.reduce((s,x)=>s+Math.max(0,Number(x.actual||x.planned||0)-Number(x.paid||0)),0);
        health.className='budget-health alert';
        health.innerHTML=`<strong>${overdue.length} overdue payment${overdue.length===1?'':'s'}</strong><span>${money(overdueValue)} is currently overdue.</span>`;
      }else if(outstanding>0){
        health.className='budget-health good';
        health.innerHTML=`<strong>Payments are on track</strong><span>${money(outstanding)} remains to be paid across your recorded costs.</span>`;
      }else{
        health.className='budget-health good';
        health.innerHTML='<strong>No outstanding payments</strong><span>Your recorded wedding costs are fully paid.</span>';
      }
    }

    const next=document.querySelector('[data-next-payment]');
    if(next){
      if(dueSoon.length){
        const x=dueSoon[0], remaining=Math.max(0,Number(x.actual||x.planned||0)-Number(x.paid||0));
        next.innerHTML=`<span>Next payment</span><strong>${esc(x.name)}</strong><small>${esc(x.due_date)} · ${money(remaining)} remaining</small>`;
      }else next.innerHTML='<span>Next payment</span><strong>Nothing scheduled</strong><small>Add a due date to an expense to track it here.</small>';
    }

    const exportBtn=document.querySelector('[data-export-budget]');
    if(exportBtn) exportBtn.onclick=()=>{
      const head=['Category','Expense','Supplier','Estimated','Actual','Paid','Outstanding','Due date','Status','Notes'];
      const body=rows.map(x=>[x.category||'',x.name||'',x.supplier||'',x.planned||0,x.actual||0,x.paid||0,Math.max(0,Number(x.actual||x.planned||0)-Number(x.paid||0)),x.due_date||'',x.payment_status||'',x.notes||'']);
      const csv=[head,...body].map(r=>r.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\n');
      const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),a=document.createElement('a');
      a.href=URL.createObjectURL(blob);a.download='ceremli-budget.csv';a.click();URL.revokeObjectURL(a.href);
    };

    // Keep status and amount logically in sync when creating/editing an expense.
    const form=document.querySelector('[data-budget-form]');
    if(form){
      const status=form.elements.payment_status, actual=form.elements.actual, planned=form.elements.planned, paidInput=form.elements.paid;
      const sync=()=>{
        const cost=Number(actual.value||planned.value||0), p=Number(paidInput.value||0);
        if(cost>0&&p>=cost) status.value='paid';
        else if(p>0&&status.value==='not_paid') status.value='deposit';
        else if(p===0&&status.value==='deposit') status.value='not_paid';
      };
      paidInput?.addEventListener('input',sync);actual?.addEventListener('input',sync);planned?.addEventListener('input',sync);
      status?.addEventListener('change',()=>{
        const cost=Number(actual.value||planned.value||0);
        if(status.value==='paid'&&cost>0) paidInput.value=String(cost);
      });
    }
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>setTimeout(ready,100));
  else setTimeout(ready,100);
})();
