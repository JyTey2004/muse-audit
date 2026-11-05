(() => {
  const $ = id => document.getElementById(id);
  const state = {cap:800, sourceFee:80, pinnedFee:80, includesDelivery:false, receipt:null, sequence:1};
  const money = n => '$' + n.toFixed(2).replace(/\.00$/, '');
  function total(){return 450 + 250 + (state.includesDelivery ? state.pinnedFee : 0);}
  function showDraft(){
    $('example-request').textContent=`Prepare a complete home-office budget including desk, chair and delivery. Keep the total within USD ${state.cap}.`;
    $('budget-rows').replaceChildren();
    for(const [label,cost] of [['Desk',450],['Chair',250],['Delivery',state.includesDelivery?state.pinnedFee:null]]){
      const row=document.createElement('tr');if(cost===null)row.className='missing-row';
      const name=document.createElement('td');name.textContent=label;
      const value=document.createElement('td');value.textContent=cost===null?'Not included':money(cost);
      row.append(name,value);$('budget-rows').append(row);
    }
    $('budget-total').textContent=money(total());
    $('draft-note').textContent=state.includesDelivery?'Corrected private copy · original budget preserved.':'Private draft · the delivery row is missing.';
    $('repair').disabled=state.includesDelivery;
  }
  function checks(){
    const sourceMatches=state.sourceFee===state.pinnedFee;
    return [
      {name:'Selected source is unchanged',status:sourceMatches?'PASS':'STALE',required:money(state.pinnedFee)+' delivery',observed:money(state.sourceFee)+' delivery'},
      {name:'Every required cost is included',status:state.includesDelivery?'PASS':'FAIL',required:'Desk, chair, delivery',observed:state.includesDelivery?'All 3 rows':'Delivery row missing'},
      {name:'Approved all-in budget is respected',status:!sourceMatches?'UNKNOWN':!state.includesDelivery?'UNKNOWN':total()<=state.cap?'PASS':'FAIL',required:'At most '+money(state.cap),observed:!state.includesDelivery?'Incomplete cost coverage':money(total())}
    ];
  }
  function rows(results){
    $('check-list').replaceChildren();
    for(const check of results){
      const row=document.createElement('div');row.className='check-row';row.dataset.status=check.status;
      const symbol=document.createElement('span');symbol.className='check-symbol';symbol.textContent=check.status==='PASS'?'✓':'!';
      const body=document.createElement('span');body.textContent=check.name;
      const details=document.createElement('small');details.textContent='Required: '+check.required+' · Observed: '+check.observed;body.append(details);
      const status=document.createElement('span');status.className='check-state';status.textContent=check.status;
      row.append(symbol,body,status);$('check-list').append(row);
    }
  }
  function invalidate(message){
    const hadRecord=state.receipt!==null;
    state.receipt=null;$('outcome-badge').textContent='Needs a new check';$('outcome-badge').className='status-badge warning';
    $('outcome-title').textContent='The evidence changed.';$('outcome-description').textContent=message;
    $('check-stamp').textContent=hadRecord?'Previous example result is no longer current':'No current verification issued';$('example-record').textContent='No current verification. Recheck the new copy; start a new task to adopt changed source facts.';
    $('check-list').replaceChildren();
  }
  async function run(){
    const inputSnapshot=JSON.stringify({cap:state.cap,sourceFee:state.sourceFee,pinnedFee:state.pinnedFee,includesDelivery:state.includesDelivery,sequence:state.sequence});
    const results=checks(),pass=results.every(c=>c.status==='PASS'),stale=results.some(c=>c.status==='STALE');
    const record={example_only:true,task:'browser-example-'+state.sequence,request:$('example-request').textContent,approved_cap_usd:state.cap,selected_delivery_usd:state.pinnedFee,current_source_delivery_usd:state.sourceFee,artifact_total_usd:total(),checks:results,outcome:pass?'SELECTED_REQUIREMENTS_FULFILLED':stale?'STALE':'BLOCKED',scope:'Only the listed browser-example checks. No live Muse verification, purchase, physical delivery or insurance.',checked_at:new Date().toISOString()};
    const canonical=JSON.stringify(record);
    if(window.crypto?.subtle){const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical));record.snapshot_sha256=Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');}
    if(inputSnapshot!==JSON.stringify({cap:state.cap,sourceFee:state.sourceFee,pinnedFee:state.pinnedFee,includesDelivery:state.includesDelivery,sequence:state.sequence})){invalidate('Task inputs changed while checking. Run a new check.');return;}
    state.receipt=record;rows(results);
    $('outcome-badge').textContent=pass?'Listed requirements fulfilled':stale?'Stale evidence':'Needs attention';
    $('outcome-badge').className='status-badge '+(pass?'pass':'warning');
    $('outcome-title').textContent=pass?'Checked. Within your request.':stale?'An old pass cannot follow new facts.':'This task is not fulfilled.';
    $('outcome-description').textContent=pass?'The complete '+money(total())+' budget satisfies the three listed checks. Unsupported questions remain outside this scope.':stale?'The source fee no longer matches the selected snapshot. Rechecking cannot silently adopt it. Start a newly agreed task to use the changed source.':!state.includesDelivery?'The draft omits delivery. Its displayed total cannot establish your complete budget.':`The full cost is ${money(total())}, above your ${money(state.cap)} cap. The cap stays unchanged.`;
    $('example-record').textContent=JSON.stringify(record,null,2);
    $('check-stamp').textContent='Example checked · '+new Intl.DateTimeFormat('en-SG',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Singapore'}).format(new Date())+' SGT';
    $('run-check').textContent='Re-run the checks ↗';
  }
  $('run-check').addEventListener('click',()=>run().catch(()=>{invalidate('Verification could not complete. No passing result is issued.');}));
  $('repair').addEventListener('click',()=>{state.includesDelivery=true;showDraft();invalidate('A new copy includes delivery. The original budget and selected source are preserved.');});
  $('source-change').addEventListener('click',()=>{state.sourceFee+=15;invalidate('The current source differs from the selected snapshot. Any earlier verification is stale.');});
  $('new-task').addEventListener('click',()=>{const raw=$('budget-cap').value.trim(),n=Number(raw);if(!raw||!Number.isInteger(n)||n<0||n>10000){$('budget-cap').setCustomValidity('Use a whole-dollar cap between 0 and 10000.');$('budget-cap').reportValidity();return;}$('budget-cap').setCustomValidity('');state.cap=n;state.pinnedFee=state.sourceFee;state.includesDelivery=false;state.sequence++;showDraft();invalidate('A new request and selected source are saved. Run the checks for this task.');});
  $('budget-cap').addEventListener('input',()=>{$('budget-cap').setCustomValidity('');});
  showDraft();
})();
