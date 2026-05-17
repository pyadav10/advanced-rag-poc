'use strict';
let selectedFile=null,lastTrace=null,groqKey='';

function showSection(name){
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('section-'+name).classList.add('active');
  document.getElementById('nav-'+name).classList.add('active');
  if(name==='vectordb')loadDbStats();
}
function handleDrop(e){
  e.preventDefault();
  document.getElementById('upload-zone').classList.remove('dragover');
  if(e.dataTransfer.files[0])setFile(e.dataTransfer.files[0]);
}
function handleFileSelect(inp){if(inp.files[0])setFile(inp.files[0]);}
function setFile(file){
  const ext=file.name.split('.').pop().toLowerCase();
  if(!['csv','xlsx','xls'].includes(ext)){toast('❌ Only CSV/Excel files');return;}
  selectedFile=file;
  document.getElementById('upload-title').textContent='✅ '+file.name;
  document.getElementById('upload-file-info').classList.remove('hidden');
  document.getElementById('file-details').innerHTML=
    `<b>${file.name}</b> &nbsp;·&nbsp; ${(file.size/1048576).toFixed(2)} MB &nbsp;·&nbsp; <span class="text-accent">${ext.toUpperCase()}</span>`;
}
function clearFile(){
  selectedFile=null;
  document.getElementById('upload-title').textContent='Click to browse or drag & drop';
  document.getElementById('upload-file-info').classList.add('hidden');
  document.getElementById('file-input').value='';
}
async function runPreview(){
  if(!selectedFile){toast('Upload a file first');return;}
  showSection('preview');
  document.getElementById('preview-content').innerHTML=loadingHtml('Parsing and chunking…');
  const form=new FormData();form.append('file',selectedFile);
  try{
    const d=await(await fetch('/api/preview',{method:'POST',body:form})).json();
    if(d.error){document.getElementById('preview-content').innerHTML=errHtml(d.error);return;}
    renderPreview(d);renderIngestReady(d);
  }catch(e){document.getElementById('preview-content').innerHTML=errHtml(e.message);}
}
function renderPreview(d){
  let h=`<div class="stats-grid">
    <div class="stat-card"><div class="stat-val">${d.total_rows.toLocaleString()}</div><div class="stat-label">Total Rows</div></div>
    <div class="stat-card"><div class="stat-val">${d.estimated_total_chunks.toLocaleString()}</div><div class="stat-label">Est. Chunks</div></div>
    <div class="stat-card"><div class="stat-val">${d.chunk_size}</div><div class="stat-label">Chunk Size</div></div>
    <div class="stat-card"><div class="stat-val">${d.chunk_overlap}</div><div class="stat-label">Overlap</div></div>
    <div class="stat-card"><div class="stat-val">${d.columns.length}</div><div class="stat-label">Columns</div></div>
  </div>`;
  h+=`<div class="card"><div class="card-title"><span class="dot"></span>Raw Data Preview</div>
  <div class="tbl-wrap"><table><thead><tr>${d.columns.map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>`;
  d.preview_rows.forEach(r=>{h+=`<tr>${d.columns.map(c=>`<td title="${r[c]||''}">${String(r[c]||'').substring(0,60)}</td>`).join('')}</tr>`;});
  h+=`</tbody></table></div></div>`;
  h+=`<div class="card"><div class="card-title"><span class="dot"></span>Chunking Visualization (first 3 test cases)</div>`;
  d.chunk_previews.forEach((cp,ci)=>{
    h+=`<div style="margin-bottom:18px"><div style="font-size:.8rem;color:var(--text2);margin-bottom:8px">
      <span class="tag-amber">Test Case ${ci+1}</span> · Source: <b>${cp.source_id}</b>
      · ${cp.original_char_count} chars → <span class="text-accent">${cp.chunk_count} chunks</span></div>`;
    cp.chunks.forEach((ch,ki)=>{
      h+=`<div class="chunk-card"><div class="chunk-header">
        <span class="chunk-badge">Chunk ${ki+1}/${cp.chunk_count}</span>
        <span class="meta-pill">📝 ${ch.char_count} chars</span>
        <span class="meta-pill">📖 ${ch.word_count} words</span>
        <span class="meta-pill">💬 ${ch.sentence_count} sentences</span>
        ${ch.overlap_chars>0?`<span class="overlap-tag">↔ ${ch.overlap_chars} overlap</span>`:''}
      </div><div class="chunk-text">${esc(ch.text)}</div></div>`;
    });
    h+=`</div>`;
  });
  h+=`</div>`;
  document.getElementById('preview-content').innerHTML=h;
}
function renderIngestReady(d){
  document.getElementById('ingest-content').innerHTML=`
  <div class="card"><div class="card-title"><span class="dot"></span>Ready to Ingest</div>
  <div class="stats-grid" style="margin-bottom:14px">
    <div class="stat-card"><div class="stat-val">${d.total_rows.toLocaleString()}</div><div class="stat-label">Test Cases</div></div>
    <div class="stat-card"><div class="stat-val">${d.estimated_total_chunks.toLocaleString()}</div><div class="stat-label">Est. Chunks</div></div>
  </div>
  <p style="font-size:.84rem;color:var(--text2);margin-bottom:14px">
    Chunks → embedded with <b>all-MiniLM-L6-v2</b> (384 dims) → stored in <b>Qdrant</b> local DB.
  </p>
  <button class="btn btn-primary" onclick="startIngestion()">🚀 Start Ingestion</button></div>
  <div id="ingest-progress-wrap" class="card hidden">
    <div class="card-title"><span class="dot"></span>Ingestion Progress</div>
    <div class="progress-wrap">
      <div class="progress-label"><span id="ingest-prog-label">Starting…</span><span id="ingest-prog-pct">0%</span></div>
      <div class="progress-bar"><div class="progress-fill" id="ingest-prog-fill" style="width:0%"></div></div>
    </div>
    <div class="progress-steps" id="ingest-steps"></div>
  </div>`;
}
async function startIngestion(){
  if(!selectedFile){toast('Upload a file first');return;}
  document.getElementById('ingest-progress-wrap').classList.remove('hidden');
  try{
    const resp = await fetch('/api/process_data',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({filename: selectedFile.name})
    });
    if(!resp.ok){
      let txt = '';
      try{ txt = await resp.text(); }catch(e){}
      console.error('Ingest failed', resp.status, txt);
      toast('❌ Ingest failed: '+resp.status+' '+(txt||resp.statusText));
      return;
    }
    pollProgress();
  }catch(e){toast('❌ '+e.message);}
}
function pollProgress(){
  const iv=setInterval(async()=>{
    try{
      const d=await(await fetch('/api/process_data/progress')).json();
      updateProgress(d);
      if(d.done){
        clearInterval(iv);
        if(d.error){toast('❌ '+d.error);return;}
        toast('✅ Done! '+d.result.total_chunks+' chunks stored.');
        updateSidebar(d.result);loadDbStats();
      }
    }catch(e){clearInterval(iv);}
  },800);
}
function updateProgress(data){
  const steps=data.steps||[],last=steps[steps.length-1]||{};
  let pct=0,label='Processing…';
  if(last.step==='model_load'){pct=5;label='Loading model…';}
  else if(last.step==='chunking'){pct=20;label='Chunking…';}
  else if(last.step==='chunking_progress'){pct=20+Math.round((last.processed/last.total)*30);label=`Chunking ${last.processed}/${last.total}`;}
  else if(last.step==='embedding'){pct=50;label=`Embedding ${last.total_chunks} chunks…`;}
  else if(last.step==='embedding_progress'){pct=50+Math.round((last.embedded/last.total)*35);label=`Embedding ${last.embedded}/${last.total}`;}
  else if(last.step==='storing'){pct=90;label='Writing to Qdrant…';}
  else if(last.step==='done'){pct=100;label='✅ Complete!';}
  document.getElementById('ingest-prog-fill').style.width=pct+'%';
  document.getElementById('ingest-prog-pct').textContent=pct+'%';
  document.getElementById('ingest-prog-label').textContent=label;
  document.getElementById('ingest-steps').innerHTML=steps.slice(-6).map((s,i)=>
    `<div class="progress-step ${i===steps.slice(-6).length-1?'active':''}">${JSON.stringify(s)}</div>`).join('');
}
async function loadDbStats(){
  document.getElementById('vectordb-content').innerHTML=loadingHtml('Loading Qdrant stats…');
  try{
    const d=await(await fetch('/api/db-stats')).json();
    if(d.error){document.getElementById('vectordb-content').innerHTML=errHtml(d.error);return;}
    updateSidebar(d);renderDbStats(d);
  }catch(e){document.getElementById('vectordb-content').innerHTML=errHtml(e.message);}
}
function renderDbStats(d){
  let h=`<div class="stats-grid">
    <div class="stat-card"><div class="stat-val">${d.total_test_cases?.toLocaleString()}</div><div class="stat-label">Test Cases</div></div>
    <div class="stat-card"><div class="stat-val">${d.total_chunks?.toLocaleString()}</div><div class="stat-label">Chunks</div></div>
    <div class="stat-card"><div class="stat-val">${d.avg_chunks_per_case}</div><div class="stat-label">Avg Chunks/Case</div></div>
    <div class="stat-card"><div class="stat-val">${d.embed_dim}</div><div class="stat-label">Vector Dims</div></div>
    <div class="stat-card"><div class="stat-val">${d.chunk_size}</div><div class="stat-label">Chunk Size</div></div>
    <div class="stat-card"><div class="stat-val">${d.chunk_overlap}</div><div class="stat-label">Overlap</div></div>
  </div>
  <div class="card"><div class="card-title"><span class="dot"></span>Embedding Config</div>
  <table style="font-size:.82rem"><tbody>
    <tr><td style="color:var(--text3);padding:5px 12px">Model</td><td style="padding:5px 12px">${d.embed_model}</td></tr>
    <tr><td style="color:var(--text3);padding:5px 12px">Dimensions</td><td style="padding:5px 12px">${d.embed_dim}</td></tr>
    <tr><td style="color:var(--text3);padding:5px 12px">Vector DB</td><td style="padding:5px 12px"><span class="tag-green">Qdrant (local)</span></td></tr>
    <tr><td style="color:var(--text3);padding:5px 12px">Columns</td><td style="padding:5px 12px">${(d.columns||[]).join(', ')}</td></tr>
  </tbody></table></div>
  <div class="card"><div class="card-title"><span class="dot"></span>Sample Stored Chunks</div>`;
  (d.sample_chunks||[]).slice(0,10).forEach(ch=>{
    h+=`<div class="chunk-card" style="margin-bottom:8px"><div class="chunk-header">
      <span class="chunk-badge">Chunk ${ch.chunk_index+1}</span>
      <span class="meta-pill">🆔 ${ch.source_id}</span>
      <span class="meta-pill">📝 ${ch.char_count} chars</span>
      <span class="meta-pill">📖 ${ch.word_count} words</span>
      ${ch.overlap_chars>0?`<span class="overlap-tag">↔ ${ch.overlap_chars} overlap</span>`:''}
      <span style="font-family:'JetBrains Mono',monospace;font-size:.62rem;color:var(--text3)">${ch.id}</span>
    </div><div class="chunk-text">${esc((ch.text||'').substring(0,300))}${(ch.text||'').length>300?'…':''}</div></div>`;
  });
  h+=`</div>`;
  document.getElementById('vectordb-content').innerHTML=h;
}
function updateSidebar(d){
  if(d.total_chunks)document.getElementById('sb-chunks').textContent=d.total_chunks.toLocaleString();
  if(d.total_test_cases)document.getElementById('sb-cases').textContent=d.total_test_cases.toLocaleString();
}
async function sendQuery(){
  const inp=document.getElementById('chat-input');
  const q=inp.value.trim();if(!q)return;
  inp.value='';
  document.getElementById('send-btn').disabled=true;
  appendMsg('user',q);
  const tid=appendMsg('assistant','⏳ Searching through your test cases…');
  try{
    const d=await(await fetch('/api/query',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query:q,groq_api_key:groqKey})})).json();
    removeMsg(tid);
    if(d.error){appendMsg('assistant','❌ '+d.error+(d.hint?' — '+d.hint:''));}
    else{
      lastTrace=d;
      const g=d.generation;
      let bubble=esc(g.answer);
      if(g.sources?.length)bubble+=`<div class="answer-sources">${g.sources.map(s=>`<span class="source-tag">📌 ${s}</span>`).join('')}</div>`;
      bubble+=`<div style="margin-top:10px;font-size:.73rem;color:var(--text3)">
        ⏱ ${d.elapsed_sec}s · 🧩 ${d.retrieval.total_dense_fetched} dense + ${d.retrieval.total_sparse_fetched} BM25
        → RRF ${d.retrieval.total_fused} → rerank kept ${d.reranking.total_kept} → ${g.model}</div>`;
      appendMsg('assistant',bubble,true);
      renderTrace(d);
    }
  }catch(e){removeMsg(tid);appendMsg('assistant','❌ '+e.message);}
  document.getElementById('send-btn').disabled=false;
}
function appendMsg(role,html,isHtml=false){
  const id='msg-'+Date.now(),msgs=document.getElementById('chat-messages');
  const div=document.createElement('div');
  div.className='msg '+role;div.id=id;
  div.innerHTML=`<div class="msg-avatar">${role==='user'?'👤':'🔮'}</div><div class="msg-bubble">${isHtml?html:esc(html)}</div>`;
  msgs.appendChild(div);msgs.scrollTop=msgs.scrollHeight;return id;
}
function removeMsg(id){const el=document.getElementById(id);if(el)el.remove();}
function renderTrace(data){
  const r=data.retrieval,rr=data.reranking,g=data.generation;
  const steps=[
    {n:1,t:'Query Embedding',c:`${r.embed_dim}-dim`,
     b:`<div style="font-size:.82rem;color:var(--text2);margin-bottom:8px">Query: <b>"${esc(r.query)}"</b></div>
        <div class="vec-bars">${r.embed_preview.map((v,i)=>`<div class="vec-row">
          <span class="vec-label">d${i}</span>
          <div class="vec-track"><div class="vec-fill" style="width:${Math.abs(v)*100}%;background:${v>=0?'var(--accent)':'var(--red)'}"></div></div>
          <span class="vec-val">${v>=0?'+':''}${v.toFixed(5)}</span></div>`).join('')}</div>`
    },
    {n:2,t:'Dense Retrieval (Qdrant)',c:`${r.total_dense_fetched} hits`,
     b:r.dense_hits.map(h=>`<div class="hit-card"><div class="hit-header">
       <span class="score-badge score-dense">cosine ${h.score}</span>
       <span style="font-size:.72rem;color:var(--text3)">rank #${h.rank} · ${h.metadata?.source_id||''}</span></div>
       <div class="hit-text">${esc(h.text)}</div></div>`).join('')
    },
    {n:3,t:'Sparse Retrieval (BM25)',c:`${r.total_sparse_fetched} hits`,
     b:r.sparse_hits.map(h=>`<div class="hit-card"><div class="hit-header">
       <span class="score-badge score-sparse">BM25 ${h.score.toFixed(3)}</span>
       <span style="font-size:.72rem;color:var(--text3)">rank #${h.rank}</span></div>
       <div class="hit-text">${esc(h.text)}</div></div>`).join('')
    },
    {n:4,t:'RRF Fusion',c:`top ${r.total_fused}`,
     b:r.fused_hits.map(h=>`<div class="hit-card"><div class="hit-header">
       <span class="score-badge score-rrf">RRF ${h.rrf_score.toFixed(5)}</span>
       ${h.dense_rank!=null?`<span class="score-badge score-dense">dense #${h.dense_rank}</span>`:''}
       ${h.sparse_rank!=null?`<span class="score-badge score-sparse">BM25 #${h.sparse_rank}</span>`:''}
       </div><div class="hit-text">${esc(h.text)}</div></div>`).join('')
    },
    {n:5,t:'Cross-Encoder Re-ranking',c:`${rr.total_kept} kept / ${rr.dropped.length} dropped`,
     b:`<div style="font-size:.78rem;color:var(--text3);margin-bottom:6px">✅ Kept:</div>
       ${rr.kept.map(h=>`<div class="hit-card"><div class="hit-header"><span class="score-badge score-rerank">rerank ${h.rerank_score}</span></div><div class="hit-text">${esc(h.text)}</div></div>`).join('')}
       ${rr.dropped.length?'<div style="font-size:.78rem;color:var(--text3);margin:8px 0 4px">❌ Dropped:</div>'+
         rr.dropped.map(h=>`<div class="hit-card" style="opacity:.5"><div class="hit-header"><span class="score-badge score-dropped">dropped ${h.rerank_score}</span></div><div class="hit-text">${esc(h.text)}</div></div>`).join(''):''}`
    },
    {n:6,t:`LLM Generation (${g.model})`,c:`${g.completion_tokens??'—'} tokens`,
     b:`<div class="answer-block">${esc(g.answer)}</div>
       <div style="display:flex;gap:12px;margin-top:8px;font-size:.78rem;color:var(--text3);flex-wrap:wrap">
         <span>📥 ${g.prompt_tokens??'—'} prompt tokens</span>
         <span>📤 ${g.completion_tokens??'—'} output tokens</span>
         <span>🧩 ${g.context_chunks_used} chunks used</span>
         <span>⏱ ${data.elapsed_sec}s</span></div>`
    }
  ];
  document.getElementById('trace-content').innerHTML=`<div class="trace-panel">${
    steps.map(s=>`<div class="trace-step${s.n===6?' open':''}" id="trace-${s.n}">
      <div class="trace-step-header" onclick="this.parentElement.classList.toggle('open')">
        <div class="trace-step-num">${s.n}</div>
        <div class="trace-step-title">${s.t}</div>
        <div class="trace-step-count">${s.c}</div>
        <div class="trace-chevron">›</div>
      </div>
      <div class="trace-step-body">${s.b}</div>
    </div>`).join('')}</div>`;
}
function showKeyModal(){document.getElementById('key-modal').classList.remove('hidden');}
async function saveKey(){
  const key=document.getElementById('key-input').value.trim();if(!key)return;
  groqKey=key;
  await fetch('/api/set-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
  document.getElementById('key-modal').classList.add('hidden');
  toast('✅ Groq key saved');
}
function loadingHtml(m){return`<div class="empty-state"><div class="big-icon">⏳</div>${m}</div>`;}
function errHtml(m){return`<div class="empty-state"><div class="big-icon">❌</div><b>Error:</b> ${esc(m)}</div>`;}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function toast(m){const el=document.createElement('div');el.className='toast';el.textContent=m;document.body.appendChild(el);setTimeout(()=>el.remove(),3000);}
(async()=>{try{const d=await(await fetch('/api/db-stats')).json();if(!d.error)updateSidebar(d);}catch(_){}})();
