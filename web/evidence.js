(() => {
  const button=document.getElementById('replay-native');
  if(!button)return;
  const output=document.getElementById('native-replay-result');
  button.addEventListener('click',async()=>{
    button.disabled=true;output.textContent='Reading the recorded result and selected requirements…';
    try{
      const [recordResponse,artifactResponse]=await Promise.all([fetch('recorded-native-evidence.json'),fetch('recorded-native-result.json')]);
      if(!recordResponse.ok||!artifactResponse.ok)throw new Error('Recorded evidence is unavailable.');
      const record=await recordResponse.json(),bytes=await artifactResponse.arrayBuffer();
      if(!crypto?.subtle)throw new Error('This browser cannot verify the artifact digest.');
      const digest=await crypto.subtle.digest('SHA-256',bytes),hex=Array.from(new Uint8Array(digest),n=>n.toString(16).padStart(2,'0')).join('');
      if(hex!==record.artifact_sha256||bytes.byteLength!==record.artifact_bytes)throw new Error('The result bytes do not match the recorded snapshot.');
      const artifact=JSON.parse(new TextDecoder().decode(bytes));
      const matches=record.checks.map(check=>{let observed=artifact;for(const field of check.field.split('.'))observed=observed?.[field];return Object.is(observed,check.expected);});
      const passed=matches.filter(Boolean).length;
      output.textContent=`${passed}/${matches.length} selected artifact checks ${passed===matches.length?'match':'do not all match'}. SHA-256 and ${bytes.byteLength} bytes match the retained snapshot. This is historical artifact replay, not a new native audit.`;
    }catch(error){output.textContent='No replay pass issued. '+error.message;}
    finally{button.disabled=false;}
  });
})();
