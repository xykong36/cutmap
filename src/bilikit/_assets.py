"""浏览页的 CSS / JS（内联，产物为单文件，无外部依赖）"""

CSS = """
:root { --bg:#fff; --fg:#1a1a1a; --sub:#666; --card:#f6f6f7; --line:#e3e3e6; --accent:#0b84ff; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#141416; --fg:#eaeaec; --sub:#9a9aa0; --card:#1d1d20; --line:#2c2c31; --accent:#4da3ff; }
}
:root[data-theme="dark"] {
  --bg:#141416; --fg:#eaeaec; --sub:#9a9aa0; --card:#1d1d20; --line:#2c2c31; --accent:#4da3ff;
}
:root[data-theme="light"] {
  --bg:#fff; --fg:#1a1a1a; --sub:#666; --card:#f6f6f7; --line:#e3e3e6; --accent:#0b84ff;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif; }
header { position:sticky; top:0; z-index:20; background:var(--bg);
  border-bottom:1px solid var(--line); padding:12px 20px 0; }
.top { display:flex; gap:14px; align-items:flex-start; }
#player { width:340px; flex:none; border-radius:8px; background:#000; }
.info { flex:1; min-width:0; }
h1 { margin:0 0 4px; font-size:16px; font-weight:650; }
.meta { color:var(--sub); font-size:13px; }
.tools { margin-top:10px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
input[type=search] { flex:1; min-width:180px; padding:7px 11px; font-size:14px;
  border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--fg); }
button { padding:7px 11px; font-size:13px; border:1px solid var(--line); border-radius:8px;
  background:var(--card); color:var(--fg); cursor:pointer; }
button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.count { color:var(--sub); font-size:13px; white-space:nowrap; }
/* Tab */
.tabs { display:flex; gap:2px; margin-top:12px; }
.tab { padding:9px 18px; font-size:14px; font-weight:600; cursor:pointer;
  border:none; background:none; color:var(--sub); border-bottom:2px solid transparent;
  border-radius:0; }
.tab:hover { color:var(--fg); }
.tab.active { color:var(--accent); border-bottom-color:var(--accent); }
.tab .n { font-weight:400; font-size:12px; opacity:.75; margin-left:5px; }
/* 网格 */
.pane { display:none; }
.pane.active { display:grid; }
.pane { gap:16px; padding:18px 20px 40px; }
#pane-frames { grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); }
#pane-broll  { grid-template-columns:repeat(auto-fill,minmax(360px,1fr)); }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; }
.card img, .card video { width:100%; display:block; background:#000; cursor:pointer; }
.body { padding:9px 11px 11px; }
.tc { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:5px; }
.seek { color:var(--accent); font-weight:600; font-size:13px; cursor:pointer;
  font-variant-numeric:tabular-nums; background:none; border:none; padding:0; }
.seek:hover { text-decoration:underline; }
.tag { color:var(--sub); font-size:12px; }
.sub { font-size:14px; word-break:break-word; cursor:pointer; }
.sub.clipped .rest { display:none; }
.sub .more { color:var(--accent); font-size:13px; margin-left:2px; }
.sub:not(.clipped) .more { display:none; }
.sub .none { color:var(--sub); font-size:13px; }
mark { background:#ffd54a; color:#000; border-radius:2px; }
.hidden { display:none !important; }
.empty { padding:60px 20px; text-align:center; color:var(--sub); }
"""

JS = """
const player=document.getElementById('player');
const q=document.getElementById('q');
const count=document.getElementById('count');
const autoBtn=document.getElementById('auto');
let autoPlay=true, active='frames';

/* ---- 播放器跳转 ---- */
function seek(t){
  player.currentTime=t; player.play().catch(()=>{});
  window.scrollTo({top:0,behavior:'smooth'});
}
document.addEventListener('click',e=>{
  const el=e.target.closest('[data-t]');
  if(el){ e.preventDefault(); seek(parseFloat(el.dataset.t)); }
});

/* ---- 字幕折叠 ---- */
document.addEventListener('click',e=>{
  const s=e.target.closest('.sub');
  if(s && !e.target.closest('[data-t]')) s.classList.toggle('clipped');
});

/* ---- Tab 切换 ---- */
document.querySelectorAll('.tab').forEach(t=>{
  t.onclick=()=>{
    active=t.dataset.pane;
    document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t));
    document.querySelectorAll('.pane').forEach(p=>
      p.classList.toggle('active',p.id==='pane-'+active));
    autoBtn.classList.toggle('hidden', active!=='broll');
    // 切走时暂停所有片段，避免后台解码
    if(active!=='broll') document.querySelectorAll('video.clip').forEach(v=>v.pause());
    else syncPlay();
    render();
    window.scrollTo({top:0});
  };
});

/* ---- B-roll 只播视口内 ---- */
const io=new IntersectionObserver(es=>es.forEach(e=>{
  const v=e.target.querySelector('video.clip'); if(!v) return;
  if(e.isIntersecting && autoPlay && active==='broll') v.play().catch(()=>{}); else v.pause();
}),{rootMargin:'120px'});
document.querySelectorAll('#pane-broll .card').forEach(c=>io.observe(c));
function syncPlay(){
  document.querySelectorAll('#pane-broll .card').forEach(c=>{
    const v=c.querySelector('video.clip'); if(!v) return;
    const r=c.getBoundingClientRect();
    const vis=r.top<innerHeight+120 && r.bottom>-120;
    (autoPlay && vis && active==='broll') ? v.play().catch(()=>{}) : v.pause();
  });
}
if(autoBtn) autoBtn.onclick=()=>{
  autoPlay=!autoPlay;
  autoBtn.classList.toggle('on',autoPlay);
  autoBtn.textContent='自动播放：'+(autoPlay?'开':'关');
  syncPlay();
};

/* ---- 搜索 ---- */
function esc(s){return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}
function paint(el,raw,kw){
  const n=parseInt(el.dataset.clip||'48');
  const hit=s=> kw? esc(s).split(esc(kw)).join('<mark>'+esc(kw)+'</mark>') : esc(s);
  if(!raw){ el.innerHTML='<span class="none">（无字幕）</span>'; el.classList.remove('clipped'); return; }
  if(raw.length<=n){ el.innerHTML=hit(raw); el.classList.remove('clipped'); return; }
  el.innerHTML=hit(raw.slice(0,n))+'<span class="rest">'+hit(raw.slice(n))+
               '</span><span class="more">…展开</span>';
  el.classList.add('clipped');
}
function render(){
  const kw=q.value.trim();
  const cards=[...document.querySelectorAll('#pane-'+active+' .card')];
  let n=0;
  cards.forEach(c=>{
    const el=c.querySelector('.sub'); if(!el) return;
    const raw=el.dataset.raw||'';
    if(!kw || raw.includes(kw)){ paint(el,raw,kw); c.classList.remove('hidden'); n++; }
    else c.classList.add('hidden');
  });
  count.textContent = kw ? n+' / '+cards.length : cards.length+(active==='broll'?' 个片段':' 个画面');
  if(active==='broll') syncPlay();
}
q.addEventListener('input',render);
render();
"""
