import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
test('a layer selection survives pending basemap tile loads',async()=>{
  const select={add(){},value:'grid:test'};
  const legend={innerHTML:'',textContent:''},value={textContent:''};
  const options={innerHTML:'',querySelector:()=>({})};
  const controls={className:'',innerHTML:'',querySelector:key=>({'select':select,'#science-layer-options':options,'#science-legend':legend,'#science-value':value}[key])};
  const grid={schema:'grid-cog-1.0',artifact_id:'test',job:{crop:'maize_grain',year:2020,states:'US50'},
    coverage:{complete:true,computed_cells:2,planned_cells:3,metric_valid_cells:{rainfed_deficit:2}},
    legend_max:{rainfed_deficit:500},units:{rainfed_deficit:'mm per season'},
    tiles:{rainfed_deficit:'/api/v2/map/grids/test/rainfed_deficit/{z}/{x}/{y}.png'},spatial_support:'native grid'};
  const added=[];
  const map={isStyleLoaded:()=>false,getLayer:key=>key==='states-line'?{}:null,getSource:()=>null,
    addSource:(...args)=>added.push(args),addLayer(){},on(){}};
  const context=vm.createContext({document:{createElement:()=>controls,getElementById:()=>({append(){}})},
    Option:class{},fetch:async()=>({ok:true,json:async()=>({source_layers:[],derived_grids:[grid]})}),
    location:{origin:'http://localhost'}});
  const code=fs.readFileSync(new URL('../map-layers.js',import.meta.url),'utf8').replace('export async function','async function');
  vm.runInContext(code,context);await context.installLayers(map);select.onchange();
  assert.equal(added.length,1);
  assert.match(added[0][1].tiles[0],/rainfed_deficit/);
  assert.match(legend.innerHTML,/2 of 3 planned climate cells/);
});
