import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../app.js',import.meta.url),'utf8');
test('stale coverage success and failure cannot overwrite active selection',async()=>{
  const fn=source.slice(source.indexOf('async function setPoint('),source.indexOf('// ---------- form'));
  let responses=[];
  const c=vm.createContext({form:{},coverage:null,coverageToken:0,
    saveForm(){},placeMarker(){},renderForm(){},API:'/api/v2',
    getJSON:()=>new Promise((resolve,reject)=>responses.push({resolve,reject}))});
  vm.runInContext(fn,c);
  const old=c.setPoint(1,2,'live'),latest=c.setPoint(3,4,'live');
  responses[1].resolve({state:'B'});await latest;
  responses[0].resolve({state:'A'});await old;
  assert.equal(c.coverage.state,'B');assert.equal(c.form.lat,3);
  const failing=c.setPoint(5,6,'live'),last=c.setPoint(7,8,'live');
  responses[3].resolve({state:'D'});await last;
  responses[2].reject(new Error('stale error'));await failing;
  assert.equal(c.coverage.state,'D');
});
