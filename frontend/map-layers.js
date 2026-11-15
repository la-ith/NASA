// Source imagery and computed grids remain separate; no values are inferred from colors.
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const METRICS={precipitation:'Season rainfall',et0:'Reference ET₀',etc_standard:'Crop water demand',rainfed_deficit:'Rain-fed deficit',irrigated_net_irrigation:'Net irrigation need',rainfed_stress_days:'Water-stress days'};
const CROPS={maize_grain:'Corn',soybean:'Soybean',sorghum_grain:'Grain sorghum'};
const STATES={AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming'};
function nasaLayerLabel(layer){
  if(layer.id==='imerg_rain_rate')return 'Rain rate · NASA satellite estimate';
  if(layer.id==='smap_root_zone')return 'Moisture below the surface · NASA SMAP';
  if(layer.id==='smap_surface')return 'Moisture near the surface · NASA SMAP';
  return `NASA map · ${layer.title}`;
}
function gridScope(grid){
  const states=grid.job.states;
  if(!states||states==='US50'||(Array.isArray(states)&&states.length===50))return 'U.S. overview';
  if(Array.isArray(states)&&states.length===1)return STATES[states[0]]||states[0];
  return 'Selected states';
}
export async function installLayers(map) {
  const pane=document.getElementById('map-pane'); if(!pane)return;
  const controls=document.createElement('details');controls.className='science-layer-controls';
  controls.innerHTML='<summary><span class="science-layer-heading">Map data</span><span class="science-layer-active" id="science-layer-active">Location map</span></summary><div class="science-layer-content"><label for="science-layer">Choose what to show</label><select id="science-layer"><option value="">Location map</option></select><div id="science-layer-options"></div><div id="science-legend" aria-live="polite"></div><p id="science-value" aria-live="polite"></p></div>';
  pane.append(controls);
  const select=controls.querySelector('select'),options=controls.querySelector('#science-layer-options'),legend=controls.querySelector('#science-legend'),value=controls.querySelector('#science-value');
  const activeLabel=controls.querySelector('#science-layer-active');
  let source=null,metric='rainfed_deficit',day='',requestVersion=0;
  let catalog;
  try{const response=await fetch('/api/v2/map/layers');if(!response.ok)throw Error();catalog=await response.json();}catch{legend.textContent='Map data unavailable. Field analysis still works.';return null;}
  const choices=new Map();
  for(const s of catalog.source_layers){choices.set(`nasa:${s.id}`,{type:'nasa',data:s});select.add(new Option(nasaLayerLabel(s),`nasa:${s.id}`));}
  // Prefer national complete plans; retain smaller studies with their actual extent named.
  const grids=catalog.derived_grids.filter(g=>g.schema==='grid-cog-1.0'&&g.coverage.complete);
  const chosen=new Map();
  for(const g of grids){const key=JSON.stringify(g.job);chosen.set(key,g);}
  for(const g of chosen.values()){const scope=gridScope(g);const key=`grid:${g.artifact_id}`;choices.set(key,{type:'grid',data:g});select.add(new Option(`${CROPS[g.job.crop]||g.job.crop} · ${g.job.year} · ${scope}`,key));}
  const updateActiveLabel=()=>{
    if(!activeLabel)return;
    const layerName=select.selectedOptions?.[0]?.textContent||'Location map';
    activeLabel.textContent=!source?'Location map':source.type==='grid'?`${layerName} · ${METRICS[metric]||metric}`:`${layerName} · ${day}`;
  };
  function clear(){if(map.getLayer('science-overlay'))map.removeLayer('science-overlay');if(map.getSource('science-raster'))map.removeSource('science-raster');}
  function apply(){
    // The base style can be ready while its tiles/GeoJSON are still loading.
    // Waiting for all sources here can permanently swallow a user's selection.
    if(!map.getLayer('states-line'))return;
    clear();value.textContent='';requestVersion++;
    if(!source){legend.textContent='Choose a layer to show satellite context or a modeled climate-grid scenario. Click or tap the map to inspect supported grid values.';return;}
    const data=source.data;
    let template;
    if(source.type==='nasa'){
      const supported=data.intervals.some(range=>{const [start,end]=range.split('/');return day>=start&&day<=end;});
      if(!supported){legend.textContent='This date is not available from the selected source. Choose another date.';return;}
      template=data.tiles.replace('{date}',day);
      const plainMeaning=data.id==='imerg_rain_rate'?'Satellite-estimated rain intensity for this date; it is not the season’s total rainfall.':data.id==='smap_root_zone'?'NASA SMAP model-assisted estimate of moisture 0–100 cm below the surface; it is not a soil sample.':data.id==='smap_surface'?'NASA SMAP model-assisted estimate of moisture in the top 0–5 cm; it is not a soil sample.':data.meaning;
      legend.innerHTML=`<p class="map-data-heading">${esc(plainMeaning)}</p><p>${esc(day)} · ${esc(data.unit)}</p><img src="${esc(data.legend_url)}" alt="NASA color legend, ${esc(data.unit)}"><details class="map-layer-explanation"><summary>How to read this layer</summary><p>Context imagery, not a measurement taken in your field. Transparent areas have no available data.</p></details>`;
    }else{
      template=data.tiles[metric];
      const count=data.coverage.metric_valid_cells?.[metric]??data.coverage.computed_cells;
      legend.innerHTML=`<div class="grid-gradient"></div><div class="legend-scale"><span>Lower</span><span>Higher · up to ${Math.round(data.legend_max[metric])} ${esc(data.units[metric])}</span></div><p class="map-data-heading">${esc(METRICS[metric]||metric)} · ${esc(data.units[metric])}</p><p>${esc(CROPS[data.job.crop]||data.job.crop)} · ${data.job.year} historical model</p><p>${count} of ${data.coverage.planned_cells} planned climate cells have a mapped value. Transparent areas indicate missing results.</p><details class="map-layer-explanation"><summary>About this map</summary><p>${esc(data.spatial_support)}. These are grid-cell model results, not measurements from individual fields. Field-level accuracy has not been validated.</p></details>`;
    }
    map.addSource('science-raster',{type:'raster',tiles:[`${location.origin}${template}`],tileSize:256,maxzoom:source.type==='nasa'?data.maxzoom:8,attribution:source.type==='nasa'?'NASA GIBS':'NASA POWER · USDA NRCS · Field Shift FAO-56 scenario'});
    const before=map.getLayer('states-line')?'states-line':undefined;
    map.addLayer({id:'science-overlay',type:'raster',source:'science-raster',paint:{'raster-opacity':.8,'raster-resampling':'nearest'}},before);
  }
  select.onchange=()=>{
    source=choices.get(select.value)||null;options.innerHTML='';
    if(activeLabel)activeLabel.textContent=select.selectedOptions?.[0]?.textContent||'Location map';
    if(source?.type==='nasa'){
      day=source.data.default_date;options.innerHTML=`<label for="science-date">Choose a date</label><input id="science-date" type="date" value="${esc(day)}">`;
      options.querySelector('input').onchange=e=>{day=e.target.value;updateActiveLabel();apply();};
    }else if(source){options.innerHTML=`<label for="science-metric">Choose a reading</label><select id="science-metric">${Object.entries(METRICS).map(([key,label])=>`<option value="${key}"${key===metric?' selected':''}>${label}</option>`).join('')}</select>`;options.querySelector('select').onchange=e=>{metric=e.target.value;updateActiveLabel();apply();};}
    updateActiveLabel();
    apply();
  };
  map.on('style.load',apply);
  map.on('error',event=>{if(event.sourceId==='science-raster'||String(event.error?.message).includes('/api/v2/map/')){value.textContent='This map layer could not load. Try another date or layer; your field analysis is still available.';controls.open=true;}});
  map.on('click',async e=>{
    if(source?.type!=='grid')return;
    const version=++requestVersion;const id=source.data.artifact_id;const point=e.lngLat.wrap();
    value.textContent='Reading climate-grid scenario…';
    try{const response=await fetch(`/api/v2/map/grids/${id}/${metric}/value?lon=${point.lng}&lat=${point.lat}`);if(!response.ok)throw Error();const r=await response.json();if(version===requestVersion)value.textContent=r.value==null?'No computed value at this location.':`${Number(r.value).toFixed(1)} ${r.unit} · grid-cell scenario, not a field measurement`;}catch{if(version===requestVersion)value.textContent='No value available for this location.';}
  });
  return {selectAnalysisLayer(cropId,requestedMetric){
    const matching=[...choices.entries()].filter(([,item])=>item.type==='grid'&&item.data.job.crop===cropId);
    if(!matching.length){
      select.value='';source=null;apply();
      legend.textContent='No mapped crop scenario is available for this option. The field comparison is still available in the results.';controls.open=true;
      return null;
    }
    const selected=matching[matching.length-1][1].data;
    if(requestedMetric&&selected.legend_max?.[requestedMetric]!=null)metric=requestedMetric;
    select.value=matching[matching.length-1][0];select.dispatchEvent(new Event('change'));
    return {year:selected.job.year,crop:selected.job.crop,metric,metricLabel:METRICS[metric]||metric};
  }};
}
