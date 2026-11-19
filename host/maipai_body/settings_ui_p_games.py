# Placement: host dashboard (More > Games in the new look; the old builder BUILDERS.play is the spec for the calls)
"""The Games page in the new dashboard look: three rows, a fold, and three detail views."""

JS = r"""
/* ---- Games (settings_ui_p_games.py) ---- */
const GAME_LANGS=[['en','English'],['es','Espa\u00f1ol'],['fr','Fran\u00e7ais'],['de','Deutsch'],['pt','Portugu\u00eas'],['it','Italiano']];
const GAME_KINDS=['joke','riddle','trivia','story','line','object'];
const gameBest=x=>x.scores&&x.scores.length?x.scores[0]+(x.unit?' '+x.unit:''):T('games.empty');
const gameLink=(label,fn,bad)=>h('button',{type:'button',style:'border:0;background:none;color:var('+(bad?'--bad':'--ac')+');font:500 15px/1 var(--font);cursor:pointer;min-height:36px;padding:0 6px',onclick:fn},label);
const gameSelect=(label,opts,val,fn)=>{const s=h('select',{'aria-label':label,style:'border:0;background:none;color:var(--fg);font:inherit;text-align:right;max-width:60%',onchange:e=>fn(e.target.value)});for(const[v,t]of opts)s.append(h('option',{value:v,selected:v===val},t));return s};
const gameData=async()=>api(unitPath(UNIT.device_id,'games'));
DETAIL['more/games']=async v=>{add(v,...detailHead(T('Games'),'more'));
 if(!UNIT){add(v,need());return}
 const g=await gameData();
 if(!g.ok||!g.d.games){add(v,h('p',{class:'empty2'},(g.d&&g.d.error)||T('net_error')));return}
 const pn=await api('/api/stackchan/pantry');const tk=g.d.talk;
 const rows=[rowEl({label:T('Games and best scores'),icon:'game',go:()=>nav('more','games-scores')})];
 if(pn.ok&&pn.d.enabled)rows.push(rowEl({label:T('Jokes and games content'),icon:'box',go:()=>nav('more','games-content')}));
 if(tk&&tk.games&&tk.games.length)rows.push(rowEl({label:T('Talk games'),icon:'talk',go:()=>nav('more','games-talk')}));
 if(g.d.playing)add(v,h('div',{class:'ok2'},T('games.playing')));
 add(v,grp(null,...rows));
 const forget=(g.d.by_person||[]).map(x=>{const who=x.person==='Someone'?T('Someone'):x.person;
  return rowEl({label:T('Delete scores')+': '+who,icon:'info',go:async()=>{if(!(await ask(T('Delete scores')+' - '+who+'?',T('Delete scores'))))return;
   const r=await save(unitPath(UNIT.device_id,'forget-scores'),{person:x.person},true);if(r.ok){toast(r.d.message||T('Scores deleted'));render()}}})});
 const note=pn.ok&&pn.d.enabled&&pn.d.built_in&&pn.d.built_in.text?[rowEl({label:T('About this content'),icon:'info',help:pn.d.built_in.text})]:[];
 if(forget.length||note.length)add(v,moreFold(...forget,...note))};
DETAIL['more/games-scores']=async v=>{add(v,...detailHead(T('Best scores'),'more'));
 if(!UNIT){add(v,need());return}
 const g=await gameData();
 if(!g.ok||!g.d.games){add(v,h('p',{class:'empty2'},(g.d&&g.d.error)||T('net_error')));return}
 add(v,grp(null,...g.d.games.map(x=>rowEl({label:x.title,value:gameBest(x)}))));
 for(const p of g.d.by_person||[]){const who=p.person==='Someone'?T('Someone'):p.person;
  add(v,grp(who,...p.games.map(gm=>{const t=g.d.games.find(q=>q.id===gm.id)||{title:gm.id};return rowEl({label:t.title,value:gm.scores.join(', ')})})))}};
DETAIL['more/games-talk']=async v=>{add(v,...detailHead(T('Talk games'),'more'));
 if(!UNIT){add(v,need());return}
 const g=await gameData();const tk=g.ok&&g.d.talk;
 if(!tk||!tk.games||!tk.games.length){add(v,h('p',{class:'empty2'},(g.d&&g.d.error)||T('net_error')));return}
 add(v,grp(null,...tk.games.map(x=>rowEl({label:x.title,help:x.hint||tk.help||null}))))};
DETAIL['more/games-content']=async v=>{add(v,...detailHead(T('Jokes and games content'),'more'));
 const pn=await api('/api/stackchan/pantry');
 if(!pn.ok||!pn.d.enabled){add(v,h('p',{class:'empty2'},pn.ok?T('Not switched on'):((pn.d&&pn.d.error)||T('net_error'))));return}
 const f={kind:'',language:'',q:''};const list=h('div',{});const used=h('span',{class:'rv'},'');
 const load=async()=>{const r=await fetch('/api/stackchan/pantry/list',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(f)}).then(x=>x.json()).catch(()=>null);list.replaceChildren();
  if(!r||!r.rows){list.append(h('p',{class:'empty2'},T('net_error')));return}
  used.textContent=r.calls_today+'/'+r.daily_cap;
  if(!r.rows.length){list.append(h('p',{class:'empty2'},T('Nothing here yet. Press Refill now and your model will write some.')));return}
  list.append(grp(r.total+' '+T('Items'),...r.rows.slice(0,60).map(x=>rowEl({label:x.text.replace('|',' '),value:x.kind+' \u00b7 '+x.language,help:x.answer||null,
   control:h('span',{style:'display:inline-flex;gap:4px;flex:none'},
    gameLink(T('Delete'),async()=>{const d=await save('/api/stackchan/pantry/delete',{id:x.id},true);if(d.ok){toast(T('Deleted'));load()}}),
    gameLink(T('Never again'),async()=>{if(!(await ask(T('Never again')+'?',T('Never again'))))return;const d=await save('/api/stackchan/pantry/never-again',{id:x.id},true);if(d.ok){toast(T('It will not come back'));load()}},true))}))))};
 const kind=gameSelect(T('Kind'),[['',T('All kinds')],...GAME_KINDS.map(k=>[k,pretty(k)])],'',x=>{f.kind=x;load()});
 const lang=gameSelect(T('Language'),[['',T('All languages')],...GAME_LANGS],'',x=>{f.language=x;load()});
 const q=h('input',{class:'tx',type:'search','aria-label':T('Search'),placeholder:T('Search'),oninput:e=>{f.q=e.target.value;load()}});
 const refill=rowEl({label:T('Refill now'),icon:'plus',go:async()=>{if(!f.kind||!f.language){toast(T('Pick a kind and a language first'),'warn');return}
  toast(T('Asking your model. This can take a minute.'));const d=await save('/api/stackchan/pantry/refill',{kind:f.kind,language:f.language},true);
  if(!d.ok)return;if(d.d.stopped)toast(d.d.stopped,'warn');else toast(T('Added')+' '+(d.d.added||0));load()}});
 add(v,grp(null,rowEl({label:T('Kind'),control:kind}),rowEl({label:T('Language'),control:lang}),refill,rowEl({label:T('Used today'),control:used})),moreFold(rowEl({label:T('Search'),control:q})),list);
 load()};
"""
