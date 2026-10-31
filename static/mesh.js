async function api(url, opts={}){
  const res = await fetch(url, {headers:{'Content-Type':'application/json'}, ...opts});
  return res.json();
}

function el(id){return document.getElementById(id);}

async function loadTower(){
  const j = await api('/api/mesh/tower');
  const t = j.tower || {};
  const box = el('tower-status');
  if(t.is_tower){
    box.innerHTML = `<div><strong><i class="fas fa-broadcast-tower"></i> TOWER ACTIVE</strong> — ${t.tower_name} (${t.tower_id?.slice(0,8)})</div><div class="hint">Role: TOWER | IP: ${t.local_ip}:${t.port}</div>`;
  }else{
    box.innerHTML = `<div><strong>PEER MODE</strong></div><div class="hint">Not acting as base station. You can enable to relay others.</div>`;
  }
  if(t.tower_name) el('tower-name').value = t.tower_name;
}

el('tower-enable')?.addEventListener('click', async ()=>{
  const name = el('tower-name').value.trim() || undefined;
  await api('/api/mesh/tower',{method:'POST', body:JSON.stringify({enable:true,name})});
  loadTower(); loadTopoMini();
});

el('tower-disable')?.addEventListener('click', async ()=>{
  await api('/api/mesh/tower',{method:'POST', body:JSON.stringify({enable:false})});
  loadTower(); loadTopoMini();
});

async function loadFreqs(){
  const j = await api('/api/mesh/freq');
  const list = el('freq-list');
  list.innerHTML = '';
  (j.freqs||[]).forEach(f=>{
    const item = document.createElement('div');
    item.className = 'freq-item';
    item.innerHTML = `<div class="freq-meta"><span class="freq-name">${f.name}</span><span class="freq-desc">${f.desc||''} • ${f.count} member(s)</span></div><div class="freq-actions"><button class="mesh-btn small" data-act="${f.joined?'leave':'join'}" data-id="${f.id}">${f.joined?'Leave':'Join'}</button></div>`;
    list.appendChild(item);
  });
  list.querySelectorAll('button').forEach(b=>{
    b.addEventListener('click', async ()=>{
      const act = b.dataset.act;
      const id = b.dataset.id;
      await api('/api/mesh/freq',{method:'POST', body:JSON.stringify({action:act,id})});
      loadFreqs();
    });
  });
}

el('freq-create')?.addEventListener('click', ()=> el('freq-modal').classList.add('open'));
document.querySelectorAll('[data-close="freq-modal"]').forEach(b=>b.addEventListener('click',()=> el('freq-modal').classList.remove('open')));

el('freq-save')?.addEventListener('click', async ()=>{
  const name = el('freq-name').value.trim();
  const desc = el('freq-desc').value.trim();
  if(!name) return;
  await api('/api/mesh/freq',{method:'POST', body:JSON.stringify({action:'create',name,desc})});
  el('freq-modal').classList.remove('open');
  el('freq-name').value=''; el('freq-desc').value='';
  loadFreqs();
});

async function loadEmergency(){
  const j = await api('/api/mesh/emergency');
  const st = el('emergency-status');
  if(j.active){
    st.innerHTML = `<strong>ACTIVE EMERGENCY</strong> from ${j.data?.from||'?' } — "${j.data?.msg||''}"`;
  }else{
    st.innerHTML = `No active emergency`;
  }
}

el('emergency-trigger')?.addEventListener('click', async ()=>{
  const msg = el('emergency-msg').value.trim() || 'EMERGENCY BROADCAST';
  if(!confirm('Trigger EMERGENCY BROADCAST to all peers on LAN?')) return;
  await api('/api/mesh/emergency',{method:'POST', body:JSON.stringify({action:'trigger',msg})});
  el('emergency-msg').value='';
  loadEmergency();
});

el('emergency-clear')?.addEventListener('click', async ()=>{
  await api('/api/mesh/emergency',{method:'POST', body:JSON.stringify({action:'clear'})});
  loadEmergency();
});

async function loadTopoMini(){
  const j = await api('/api/mesh/topology');
  const box = el('topo-mini');
  const nodes = (j.nodes||[]).length;
  const links = (j.links||[]).length;
  const towers = (j.towers||[]).length;
  box.innerHTML = `<div><strong>Nodes:</strong> ${nodes} | <strong>Links:</strong> ${links} | <strong>Towers:</strong> ${towers}</div><div class="hint">Me: ${j.me?.username} [${j.me?.role}]</div>`;
}

el('mp-add')?.addEventListener('click', async ()=>{
  const ip = el('mp-ip').value.trim();
  const port = el('mp-port').value.trim() || '6667';
  if(!ip) return;
  await api('/api/mesh/discover-manual',{method:'POST', body:JSON.stringify({ip,port})});
  alert('Manual probe recorded. Existing discovery will attempt to reach it.');
  el('mp-ip').value='';
});

setInterval(loadEmergency, 2000);
loadTower(); loadFreqs(); loadEmergency(); loadTopoMini(); setInterval(loadTopoMini, 5000);
