# ruff: noqa: E501
"""The settings page's encrypted-link card, added under the Security section's passcode card.

Shows the link state of the selected unit and the choice (required, allowed, off). Every word comes from ``T('ln.*')``
(``i18n_link.py``). The page never sees a key: the host answers with the state and the mode only."""

JS_LINK = r"""
/* ---- security: the encrypted link (TLS with a pre-shared key; the page sees only state and choice) ---- */
async function linkCard(id){
 const box=h('div',{class:'stack'});let v=null;
 const reload=async()=>{const r=await api(unitPath(id,'link'));v=r.ok?r.d:null;draw()};
 function draw(){
  if(!v){box.replaceChildren(h('p',{class:'hint'},T('ln.unknown')));return}
  const kids=[h('p',{class:'hint',role:'status'},T('ln.state')+': '+T('ln.state.'+v.state))];
  if(v.mode==='off')kids.push(h('p',{class:'hint',role:'alert'},T('ln.off_warning')));
  kids.push(seg(T('ln.choice'),['required','allowed','off'].map(m=>({v:m,t:T('ln.'+m)})),v.mode,async m=>{const r=await api(unitPath(id,'link'),{mode:m});if(r.ok&&r.d.ok!==false){toast(r.d.message||S['settings.saved']);await reload();return true}toast((r.d&&r.d.error)||T('net_error'),'bad');return false}),
   h('p',{class:'hint'},T('ln.'+v.mode+'_help')));
  box.replaceChildren(...kids)}
 await reload();
 return card(T('ln.title'),T('ln.help'),box)}
{const prevSecurity=BUILDERS.security;BUILDERS.security=async(p,u)=>{await prevSecurity(p,u);p.append(h('div',{class:'stack'},await linkCard(u.device_id)))}}
"""
