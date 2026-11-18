# ruff: noqa: E501
"""The Character pack card on the Look page: choose a shared character pack (a .zip), have the host check it, install it as the
unit's picture face. Words come from ``T('char.*')`` (``i18n_character.py``); the route is
``POST /api/stackchan/unit/<id>/pictures/import-character`` (``character_pack.import_for_page``). The pack is never sent to the
unit by this card: the page's own Send button does that."""

JS_CHARACTER = r"""
/* ---- look: install a character pack ---- */
{const prevLook=BUILDERS.look;BUILDERS.look=async(p,u)=>{await prevLook(p,u);
 const id=u.device_id,box=h('div',{class:'hint',role:'status','aria-live':'polite'}),
  inp=h('input',{type:'file',accept:'.zip,application/zip','aria-label':T('char.choose')});
 const go=h('button',{class:'btn',type:'button',onclick:async()=>{const f=inp.files&&inp.files[0];
   if(!f){box.textContent=T('char.choose');return}
   if(f.size>8*1024*1024){box.textContent=T('char.too_big');return}
   box.textContent=T('char.checking');
   let b64;try{const buf=new Uint8Array(await f.arrayBuffer());let s='';for(let i=0;i<buf.length;i+=32768)s+=String.fromCharCode.apply(null,buf.subarray(i,i+32768));b64=btoa(s)}catch(e){box.textContent=T('char.unreadable');return}
   const r=await api(unitPath(id,'pictures/import-character'),{b64});
   if(!r.ok){box.replaceChildren(h('b',{},T('char.problems')),...(r.d.problems||[r.d.error||T('net_error')]).map(x=>h('div',{},x)));return}
   box.textContent=T('char.done');toast(T('char.done'));BUILT.look=false}},T('char.import'));
 p.append(card(T('char.title'),T('char.help'),inp,h('div',{class:'btns'},go),box))}}
"""
