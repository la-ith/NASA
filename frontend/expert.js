const root=document.getElementById("expert-app");
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let expertKey="";
const observationPhotoUrls=[];
async function api(path,options={}){
  const response=await fetch(`/api/v2/expert/${path}`,{...options,headers:{"X-Expert-Key":expertKey,...(options.headers||{})}});
  const body=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(body.detail||`Request failed (${response.status})`);
  return body;
}
function login(error=""){
  root.innerHTML=`<section class="auth-wrap"><p class="eyebrow">PRIVATE TEAM ACCESS</p><h1>Agronomist inbox</h1><p class="lead">Enter your team's inbox key to view and answer farmer requests.</p>${error?`<div class="errors" role="alert">${esc(error)}</div>`:""}<form id="expert-login" class="auth-form"><label for="expert-key">Inbox key</label><input id="expert-key" type="password" autocomplete="current-password" required><button class="primary full-button" type="submit">Open inbox</button></form><p class="hint">The key stays in memory for this page and is sent only to this Field Shift server.</p></section>`;
  document.getElementById("expert-login").onsubmit=async e=>{e.preventDefault();expertKey=document.getElementById("expert-key").value;try{await api("queue");await loadQueue();}catch(err){expertKey="";login(err.message);}};
}
async function loadQueue(message=""){
  observationPhotoUrls.splice(0).forEach(url=>URL.revokeObjectURL(url));
  root.innerHTML=`<div class="loading-card"><span class="loader"></span><p>Loading open requests…</p></div>`;
  try{
    const data=await api("queue");
    root.innerHTML=`<div class="expert-console-top"><div><p class="eyebrow">PRIVATE TEAM ACCESS</p><h1>Open farmer requests</h1><p class="lead">Review field context, then send a reply that will appear in the farmer’s Field Shift inbox.</p></div><button class="quiet-button" id="expert-signout">Sign out</button></div>${message?`<div class="notice-card" role="status">${esc(message)}</div>`:""}${data.requests.length?`<div class="expert-queue">${data.requests.map(requestCard).join("")}</div>`:`<section class="empty-state"><h2>All caught up</h2><p>There are no open farmer requests.</p></section>`}`;
    root.querySelectorAll('[data-observation-photo]').forEach(async img=>{try{const response=await fetch(`/api/v2/expert/queue/${encodeURIComponent(img.dataset.observationPhoto)}/observation-photo`,{headers:{'X-Expert-Key':expertKey}});if(!response.ok)return;const url=URL.createObjectURL(await response.blob());observationPhotoUrls.push(url);img.src=url;}catch{}});
    document.getElementById("expert-signout").onclick=()=>{expertKey="";login();};
    root.querySelectorAll("[data-reply]").forEach(form=>form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector("button");button.disabled=true;try{await api(`queue/${encodeURIComponent(form.dataset.reply)}/reply`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:form.querySelector("textarea").value.trim()})});await loadQueue("Reply sent to the farmer.");}catch(err){form.querySelector(".errors").hidden=false;form.querySelector(".errors").textContent=err.message;button.disabled=false;}});
  }catch(err){expertKey="";login(err.message);}
}
function requestCard(r){
  const details=r.details||{};
  const context=[details.area_acres?`${details.area_acres} acres`:null,details.soil_texture&&details.soil_texture!=="unknown"?`farmer-reported ${details.soil_texture} soil`:null,details.drainage&&details.drainage!=="unknown"?`${details.drainage} drainage`:null,details.slope&&details.slope!=="unknown"?`${details.slope} slope`:null,details.water_source&&details.water_source!=="unknown"?`water source: ${details.water_source}`:null].filter(Boolean).join(" · ");
  const observation=r.observation;
  return `<article class="expert-request-card"><div class="expert-thread-head"><div><p class="eyebrow">${esc(r.state||"Location not saved")} · ${esc(r.farmer_name)}</p><h2>${esc(r.field_name||"Field question")}</h2></div><span class="state-pill">${esc(new Date(r.created_utc).toLocaleString())}</span></div><p><strong>Current crop:</strong> ${esc(r.crop||"unknown")} · <strong>Water:</strong> ${esc(r.irrigation||"unknown")}</p><p><strong>Recent crops:</strong> ${esc((r.history||[]).map(x=>`${x.year}: ${x.crop}`).join(" · ")||"Not provided")}</p>${context?`<p><strong>Field context:</strong> ${esc(context)}</p>`:""}${details.notes?`<p><strong>Farmer notes:</strong> ${esc(details.notes)}</p>`:""}${observation?`<div class="expert-question"><strong>Private field note · ${esc(observation.observed_on)}</strong><p>${esc(observation.category.replace('_','/'))} · ${esc(observation.crop)}</p><p>${esc(observation.note)}</p>${observation.photo_available?`<img class="expert-observation-photo" data-observation-photo="${esc(r.request_id)}" alt="Photo attached to the farmer’s field note">`:""}</div>`:""}${r.analysis_summary?`<div class="expert-question"><strong>Analysis overview</strong><p>${esc(r.analysis_summary)}</p><div class="expert-risk-grid">${(r.risk_assessment||[]).map(x=>`<span><strong>${esc(x.crop)}</strong> · water-stress exposure ${x.percentage==null?"not available":`${esc(x.percentage)}%`}<small>${esc(x.primary_contributing_factor||"")}</small></span>`).join("")}</div></div>`:""}<div class="expert-question"><strong>Question</strong><p>${esc(r.message)}</p></div><form data-reply="${esc(r.request_id)}" class="expert-reply-form"><label>Reply to the farmer</label><textarea minlength="10" maxlength="5000" rows="4" required placeholder="Write a clear, practical response. Distinguish professional judgment from the Field Shift model results."></textarea><div class="errors" hidden></div><button class="primary" type="submit">Send reply</button></form></article>`;
}
login();
