import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../app.js',import.meta.url),'utf8');
test('stale coverage success and failure cannot overwrite active selection',async()=>{
  const fn=source.slice(source.indexOf('async function chooseLocation('),source.indexOf('async function saveField('));
  let responses=[];
  const elements={lat:{value:''},lon:{value:''},'location-result':{innerHTML:''}};
  const c=vm.createContext({fieldLocationToken:0,document:{getElementById:id=>elements[id]},putMarker(){},coverageLabel:String,esc:String,API:'/api/v2',
    getJSON:()=>new Promise((resolve,reject)=>responses.push({resolve,reject}))});
  vm.runInContext(fn,c);
  const old=c.chooseLocation(38,-99),latest=c.chooseLocation(41,-93);
  const result=name=>({in_scope:true,state:{name},products:{}});
  responses[1].resolve(result('Iowa'));await latest;
  responses[0].resolve(result('Kansas'));await old;
  assert.match(elements['location-result'].innerHTML,/Iowa/);assert.equal(elements.lat.value,41);
  const failing=c.chooseLocation(39,-97),last=c.chooseLocation(42,-94);
  responses[3].resolve(result('Latest'));await last;
  responses[2].reject(new Error('stale error'));await failing;
  assert.match(elements['location-result'].innerHTML,/Latest/);
});
test('results render actual model metrics and distinguish absent soil output',()=>{
  const sample=JSON.parse(fs.readFileSync(new URL('../../data/fixtures/showcase_ks_hays.json',import.meta.url),'utf8'));
  const c=vm.createContext({esc:String});
  vm.runInContext(source.slice(source.indexOf('function metricValue('),source.indexOf('function renderAnalysis(')),c);
  vm.runInContext(source.slice(source.indexOf('function seasonChart('),source.indexOf('function recoverAccount(')),c);
  assert.match(c.metricValue(sample.strategies[0],'rainfed_deficit'),/371.7 mm per season/);
  assert.equal(c.metricValue({result:null},'rainfed_deficit'),'Not available');
  const chart=c.seasonChart(sample);
  assert.match(chart,/2001/);assert.match(chart,/2025/);assert.match(chart,/503|496.83/);
  assert.doesNotMatch(chart,/NaN|undefined/);
});
test('pending analysis is never displayed after account ownership changes',async()=>{
  const fn=source.slice(source.indexOf('async function startAnalysis('),source.indexOf('function metricValue('));
  let finish;let shown=false;
  const c=vm.createContext({busy:false,authVersion:1,currentAnalysis:null,chatSession:null,API:'/api/v2',
    catalog:{crops:[{id:'maize_grain'}]},esc:String,panel:{innerHTML:''},setMapVisible(){},
    document:{getElementById:()=>({textContent:''})},
    getJSON:async url=>url.endsWith('/analyses')?{status_url:'/job'}:new Promise(resolve=>{finish=resolve;}),
    renderAnalysis(){shown=true;},setTimeout});
  vm.runInContext(fn,c);
  const run=c.startAnalysis({name:'test',crop:'maize_grain',history:[],lat:38,lon:-99,irrigation:'unknown'});
  await new Promise(resolve=>setTimeout(resolve,0));c.authVersion=2;
  finish({state:'succeeded',analysis_url:'/private-old-account'});await run;
  assert.equal(shown,false);assert.equal(c.currentAnalysis,null);
});
