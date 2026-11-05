'use strict';
const $ = id => document.getElementById(id);
let nonce, configured = false, prepared = null, wavBlob = null, recording = null, audioUrl = null, draft = null;
async function api(path, body) {
  const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json','X-Preview-Nonce':nonce},body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Review unavailable');
  return result;
}
function say(message) { $('status').textContent = message; }
function stale() {
  if (prepared) {
    say('Inputs changed. Prior evidence is retained, but prepare a fresh review before reuse.');
    $('checks').textContent='STALE · Inputs changed. Prepare a fresh review to check this version.';
    $('route').textContent='Current review depth has not been prepared.';
    $('advice').textContent='Prior model advice, if any, is stale. It remains in the session records.';
  }
  prepared = null; $('audit').disabled = true; $('escalate').disabled = true;
}
function buttons() {
  $('audit').disabled = !configured || !prepared || !$('upload-ok').checked;
  $('escalate').disabled = $('audit').disabled;
  $('transcribe').disabled = !configured || !wavBlob || !$('upload-ok').checked;
}
for (const id of ['request','requirements','artifact','cap','exposure','floor','irreversible','external','observed','ambiguous','confirmed']) {
  $(id).addEventListener('input', () => { stale(); if (['request','requirements'].includes(id)) $('confirmed').checked = false;
    if(id==='request' && draft?.origin==='typed') draft=null; });
}
$('upload-ok').addEventListener('change', buttons);
function selectedAudio(blob) {
  wavBlob = blob;
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = URL.createObjectURL(blob); $('audio').src = audioUrl; $('audio').hidden = false;
  $('audio-status').textContent = `${blob.size.toLocaleString()} local bytes selected. Not sent.`; buttons();
}
$('audio-file').addEventListener('change', event => { const file=event.target.files[0]; if(file) selectedAudio(file); });
$('record').addEventListener('click', async () => {
  let stream, ctx;
  try {
    $('record').disabled=true;
    stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1},video:false});
    ctx = new AudioContext(); const source=ctx.createMediaStreamSource(stream);
    const processor=ctx.createScriptProcessor(4096,1,1); const mute=ctx.createGain(); mute.gain.value=0;
    const chunks=[]; processor.onaudioprocess=e=>chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    source.connect(processor); processor.connect(mute); mute.connect(ctx.destination);
    recording={stream,ctx,source,processor,mute,chunks,timer:setTimeout(()=>stopRecording(),30000)};
    $('record').disabled=true; $('stop').disabled=false; say('Recording locally. Automatic stop after 30 seconds.');
  } catch (_) {
    stream?.getTracks().forEach(track=>track.stop());
    if(ctx && ctx.state!=='closed') await ctx.close().catch(()=>{});
    $('record').disabled=false;
    say('Microphone unavailable or permission denied. Type your request or select a WAV file.');
  }
});
async function stopRecording() {
  if(!recording) return; const r=recording; recording=null; clearTimeout(r.timer);
  r.processor.disconnect(); r.source.disconnect(); r.mute.disconnect(); r.stream.getTracks().forEach(track=>track.stop());
  const sourceRate=r.ctx.sampleRate; await r.ctx.close();
  const length=r.chunks.reduce((n,c)=>n+c.length,0); const samples=new Float32Array(length);
  let offset=0; for(const c of r.chunks){samples.set(c,offset);offset+=c.length;}
  const count=Math.floor(length*16000/sourceRate); const buffer=new ArrayBuffer(44+count*2);const v=new DataView(buffer);
  function tag(o,s){for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i));}
  tag(0,'RIFF');v.setUint32(4,36+count*2,true);tag(8,'WAVE');tag(12,'fmt ');v.setUint32(16,16,true);
  v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);v.setUint32(28,32000,true);
  v.setUint16(32,2,true);v.setUint16(34,16,true);tag(36,'data');v.setUint32(40,count*2,true);
  for(let i=0;i<count;i++){const p=i*sourceRate/16000;const a=Math.floor(p);const f=p-a;
    const s=Math.max(-1,Math.min(1,(samples[a]||0)*(1-f)+(samples[a+1]||0)*f));v.setInt16(44+i*2,s<0?s*32768:s*32767,true);}
  selectedAudio(new Blob([buffer],{type:'audio/wav'}));$('record').disabled=false;$('stop').disabled=true;
  say('Recording stopped. Review the audio. Transcription requires configured Meta access and explicit upload permission.');
}
$('stop').addEventListener('click', stopRecording);
$('transcribe').addEventListener('click', async () => {
  try { if(!wavBlob || wavBlob.size>3000000) throw new Error('Select a WAV recording under 3 MB.');
    const bytes=new Uint8Array(await wavBlob.arrayBuffer());let raw='';for(let i=0;i<bytes.length;i+=8192)raw+=String.fromCharCode(...bytes.subarray(i,i+8192));
    const r=await api('/api/transcribe',{audio_base64:btoa(raw),allow_upload:$('upload-ok').checked});
    draft=r;$('request').value=r.transcript;$('confirmed').checked=false;stale();say('Meta returned a transcript. Edit it and confirm the checklist before any review.');
  }catch(e){say(e.message);}
});
$('correct').addEventListener('click', () => {
  try {const artifact=JSON.parse($('artifact').value);artifact.total_minor=artifact.expenses.reduce((n,x)=>n+x.amount_minor,0);
    $('artifact').value=JSON.stringify(artifact,null,2);stale();say('Sample total corrected locally. Prepare a fresh review; previous failures remain in history.');
  }catch(_){say('The sample JSON must contain an expenses array.');}
});
$('prepare').addEventListener('click', async () => {
  try {
    if(!$('confirmed').checked) throw new Error('Review and confirm the request and checklist first.');
    if(!draft) draft=await api('/api/intake',{request:$('request').value});
    const risk={caller_floor:$('floor').value,exposure_minor:Number($('exposure').value),irreversible:$('irreversible').checked,
      external_effect:$('external').checked,outcome_observed:$('observed').checked,ambiguous:$('ambiguous').checked};
    const r=await api('/api/prepare',{request:$('request').value,draft_sha256:draft.transcript_sha256,confirmed:true,
      requirements:$('requirements').value.split('\n').filter(x=>x.trim()),artifact:$('artifact').value,cap_minor:Number($('cap').value),risk});
    prepared=r;
    $('checks').textContent=r.deterministic_checks.map(x=>`${x.passed?'Confirmed':'Failed'} · ${x.check}\nObserved: ${x.observed}; expected: ${x.expected}`).join('\n\n');
    $('route').textContent=`${r.route.tier.toUpperCase()} review · ${r.route.model}\n${r.route.reasons.join('\n')}\nIllustrative policy. No insurance coverage. Overall acceptance unresolved.`;
    $('audit').textContent=r.route.model==='muse-wonder-1.0'?'Run dedicated Muse Wonder audit':'Run dedicated Muse Spark audit';
    $('advice').textContent='No model call has been made for this version.';
    $('records').textContent=JSON.stringify(r,null,2);buttons();say('Local checks executed against this version. No model call or external action was made.');
  }catch(e){say(e.message);}
});
async function audit(escalate) {
  try { const r=await api('/api/audit',{bundle_sha256:prepared.bundle.bundle_sha256,allow_upload:$('upload-ok').checked,escalate});
    $('advice').textContent=`ADVISORY ONLY · ${r.review_tier} review\n`+r.advice.findings.map(x=>`${x.requirement_id}: ${x.assessment}\n${x.explanation}\nEvidence: ${x.evidence_ids.join(', ')||'none'}`).join('\n\n');
    $('records').textContent=JSON.stringify(r,null,2);say('Model advice received. It cannot approve delivery, prove source truth or grant insurance.');
  }catch(e){say(e.message);}
}
$('audit').addEventListener('click',()=>audit(false));$('escalate').addEventListener('click',()=>audit(true));
$('export').addEventListener('click',async()=>{try{const r=await api('/api/export',{});const a=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}));a.href=url;a.download='stardive-review-session.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){say(e.message);}});
fetch('/api/status').then(r=>r.json()).then(r=>{nonce=r.nonce;configured=r.live_configured;
  $('mode').textContent=configured?'Live Meta enabled · explicit uploads only':'Offline · Meta not configured';buttons();}).catch(()=>say('Local service unavailable. Start the Python preview server.'));
