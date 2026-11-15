const nav = document.querySelector('.site-nav');
const coverageSection = document.getElementById('coverage');
if (coverageSection && !document.getElementById('farmer-tools')) {
  coverageSection.insertAdjacentHTML('beforebegin', `<section class="farmer-tools section-shell" id="farmer-tools">
    <div class="farmer-tools-heading"><p class="eyebrow">BUILT AROUND A FARMER’S NEXT QUESTION</p><h2>From a field location<br><em>to a clearer next step.</em></h2><p>Field Shift brings the evidence into one practical flow. You can skip details you do not know and stay in control of the final decision.</p></div>
    <div class="farmer-tools-grid">
      <article><span class="farmer-tool-number">01</span><h3>Set up your field</h3><p>Choose a place on the U.S. map, tell us what you grow, and add any land details you know. Optional questions include field size, soil feel, drainage, slope, and water source.</p></article>
      <article><span class="farmer-tool-number">02</span><h3>See the evidence</h3><p>Check nearby NASA weather and mapped USDA soil coverage. Explore map layers and their dates, units, spatial coverage, and missing-data areas.</p></article>
      <article><span class="farmer-tool-number">03</span><h3>Compare three crop options</h3><p>Review past-season water results side by side, with a relative score and its main modeled factor. The score compares these options; it is not a crop-failure probability.</p></article>
      <article><span class="farmer-tool-number">04</span><h3>Choose what to do next</h3><p>Ask the assistant to explain a result, keep private field notes, send a note to an agronomist, and export a professional report for discussion.</p></article>
    </div>
    <div class="farmer-tools-footer"><p><strong>The model informs the conversation.</strong> It does not replace field observation, local expertise, or the farmer’s judgment.</p><a class="btn btn-small" href="/workspace/">Explore your field <span>↗</span></a></div>
  </section>`);
}
if (nav && !nav.querySelector('[href="#farmer-tools"]')) nav.insertAdjacentHTML('beforeend', '<a href="#farmer-tools">For farmers</a>');
document.querySelector('.mobile-nav-toggle')?.addEventListener('click', event => {
  const open = event.currentTarget.getAttribute('aria-expanded') !== 'true';
  event.currentTarget.setAttribute('aria-expanded', String(open)); nav?.classList.toggle('open', open);
});
document.querySelectorAll('[data-auth]').forEach(button => button.onclick = () => location.assign('/workspace/?signin=1'));
nav?.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{nav.classList.remove('open');document.querySelector('.mobile-nav-toggle')?.setAttribute('aria-expanded','false');}));
let example;
const note = document.getElementById('example-note');
function showCrop(id) {
  document.querySelectorAll('[data-crop]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.crop === id)));
  const summary = example?.strategies.find(s => s.crop === id)?.result?.summary;
  if (!summary) return;
  const values = ['rainfed_deficit', 'irrigated_net_irrigation'].map(key => summary[key]?.spread?.median);
  document.querySelectorAll('#example-metrics strong').forEach((el, i) => { el.replaceChildren(document.createTextNode(values[i] == null ? '— ' : `${Math.round(values[i])} `)); const unit = document.createElement('small'); unit.textContent = 'mm'; el.append(unit); });
  note.textContent = 'Median per past season · 2001–2025 · Saved source data';
}
document.querySelectorAll('[data-crop]').forEach(button => button.onclick = () => showCrop(button.dataset.crop));
fetch('/api/v2/showcase').then(r => { if (!r.ok) throw Error(); return r.json(); }).then(r => { example = r; showCrop('maize_grain'); }).catch(() => { note.textContent = 'Saved example unavailable. Open the workspace to try again.'; });

let boundaries;
function drawRegion(region = 'lower48') {
  if (!boundaries) return;
  const canvas = document.getElementById('coverage-canvas'); if (!canvas) return;
  const names = { lower48: 'contiguous United States', alaska: 'Alaska', hawaii: 'Hawaii' };
  canvas.setAttribute('aria-label', `Coverage geography: ${names[region]}`);
  document.querySelectorAll('[data-region]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.region === region)));
  const features = boundaries.features.filter(f => {
    const code = f.properties.stusps || f.properties.STUSPS || f.properties.code || f.properties.state;
    return region === 'alaska' ? code === 'AK' : region === 'hawaii' ? code === 'HI' : !['AK','HI'].includes(code);
  });
  const polygons = features.flatMap(f => f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates : [f.geometry.coordinates]);
  const coords = polygons.flat(2).map(([x,y]) => [region === 'alaska' && x > 0 ? x - 360 : x, y]);
  if (!coords.length) return;
  const xs = coords.map(p => p[0]), ys = coords.map(p => p[1]);
  const bounds = [Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
  const aspect = Math.cos((bounds[1]+bounds[3])/2*Math.PI/180);
  const scale = Math.min(740/((bounds[2]-bounds[0])*aspect),390/(bounds[3]-bounds[1]));
  const dx = (800-(bounds[2]-bounds[0])*aspect*scale)/2, dy = (450-(bounds[3]-bounds[1])*scale)/2;
  const ctx = canvas.getContext('2d'); ctx.clearRect(0,0,800,450);
  ctx.fillStyle = '#bac9a3'; ctx.strokeStyle = '#f5f7ee'; ctx.lineWidth = 1.4;
  for (const rings of polygons) {
    ctx.beginPath();
    for (const ring of rings) ring.forEach(([lon,lat],i) => {
      if (region === 'alaska' && lon > 0) lon -= 360;
      const x = dx+(lon-bounds[0])*aspect*scale, y = dy+(bounds[3]-lat)*scale;
      if (!i) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    });
    ctx.closePath(); ctx.fill('evenodd'); ctx.stroke();
  }
}
document.querySelectorAll('[data-region]').forEach(button => button.onclick = () => drawRegion(button.dataset.region));
fetch('/api/v2/boundaries').then(r=>r.json()).then(r=>{boundaries=r;drawRegion();}).catch(()=>{const c=document.getElementById('coverage-canvas');if(c)c.setAttribute('aria-label','Coverage geography unavailable. The workspace checks all 50 US states.');});
