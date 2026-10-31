async function api(url, opts={}){
  const res = await fetch(url, {headers:{'Content-Type':'application/json'}, ...opts});
  return res.json();
}

function el(id){return document.getElementById(id);}

const svg = el('topo-svg');
let topo = {nodes:[], links:[], towers:[], me:{}};

function render(){
  svg.innerHTML = '';
  const w=1000,h=520;
  const nodes = [...(topo.nodes||[])];
  const towers = [...(topo.towers||[])];
  const all = [...nodes, ...towers.map(t=>({id:t.name||t.id, label:t.name||t.id.slice(0,8), role:'TOWER', type:'tower', _t:true, tower_id:t.id, ip:t.ip}))];
  // position
  const centerX=w/2, centerY=h/2;
  all.forEach((n,i)=>{
    const ang = (i/all.length)*Math.PI*2;
    const r = n.type==='tower'||n.role==='TOWER'? 160 : 200;
    n.x = centerX + Math.cos(ang)*r + (Math.random()-0.5)*10;
    n.y = centerY + Math.sin(ang)*r + (Math.random()-0.5)*10;
    if(n.type==='self' || (n.label && topo.me && n.label.includes(topo.me.username))) { n.x=centerX; n.y=centerY; n.r=18; }
    else if(n.type==='tower'||n.role==='TOWER'){ n.r=16; }
    else { n.r=12; }
  });

  // links
  (topo.links||[]).forEach(lk=>{
    const s = all.find(a=>a.id===lk.source || a.label===lk.source || a.tower_id===lk.source);
    const t = all.find(a=>a.id===lk.target || a.label===lk.target || a.tower_id===lk.target);
    if(!s||!t) return;
    const line = document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1',s.x); line.setAttribute('y1',s.y);
    line.setAttribute('x2',t.x); line.setAttribute('y2',t.y);
    if(lk.type==='tower-tower'){ line.setAttribute('stroke','#a78bfa'); line.setAttribute('stroke-dasharray','6 4'); }
    else if(lk.type==='via-tower'){ line.setAttribute('stroke','#f59e0b'); line.setAttribute('stroke-dasharray','4 3'); }
    else { line.setAttribute('stroke','#38bdf8'); }
    line.setAttribute('stroke-width','2');
    svg.appendChild(line);
  });

  // nodes
  all.forEach(n=>{
    const g = document.createElementNS('http://www.w3.org/2000/svg','g');
    const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx',n.x); c.setAttribute('cy',n.y); c.setAttribute('r',n.r||12);
    if(n.type==='self'){ c.setAttribute('fill','#22d3ee'); }
    else if(n.type==='tower'||n.role==='TOWER'){ c.setAttribute('fill','#22c55e'); }
    else { c.setAttribute('fill','#38bdf8'); }
    c.setAttribute('opacity','0.9');
    const tx = document.createElementNS('http://www.w3.org/2000/svg','text');
    tx.setAttribute('x',n.x); tx.setAttribute('y',n.y + (n.r||12)+14);
    tx.setAttribute('text-anchor','middle');
    tx.setAttribute('fill','#cbd5e1');
    tx.setAttribute('font-size','11');
    tx.textContent = (n.label||n.id||'').toString().substring(0,16);
    g.appendChild(c); g.appendChild(tx); svg.appendChild(g);
  });

  // lists
  const tl = el('tower-list'); tl.innerHTML='';
  (topo.towers||[]).forEach(t=>{
    const d=document.createElement('div'); d.className='list-item';
    d.innerHTML = `<div><strong>${t.name||t.id.slice(0,8)}</strong><div class="list-sub">${t.ip||''} ${t.self?'• YOU':''}</div></div><span class="list-sub">TOWER</span>`;
    tl.appendChild(d);
  });
  const nl = el('node-list'); nl.innerHTML='';
  (topo.nodes||[]).forEach(n=>{
    const d=document.createElement('div'); d.className='list-item';
    d.innerHTML = `<div><strong>${n.label||n.id}</strong><div class="list-sub">${n.ip||''}</div></div><span class="list-sub">${n.role}</span>`;
    nl.appendChild(d);
  });
  const ll = el('link-list'); ll.innerHTML='';
  (topo.links||[]).forEach(lk=>{
    const d=document.createElement('div'); d.className='list-item';
    d.innerHTML = `<div><strong>${lk.source} → ${lk.target}</strong></div><span class="list-sub">${lk.type}</span>`;
    ll.appendChild(d);
  });
  el('map-info').textContent = `Updated ${new Date().toLocaleTimeString()} • Nodes:${all.length} Links:${(topo.links||[]).length} Towers:${(topo.towers||[]).length}`;
}

async function load(){
  topo = await api('/api/mesh/topology');
  render();
}

load(); setInterval(load, 3000);
