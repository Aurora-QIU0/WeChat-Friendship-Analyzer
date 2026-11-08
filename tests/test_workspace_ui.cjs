// State transitions in the local UI; fictional data and no browser/network.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

function workspace() {
  const elements = new Map();
  function element() { return {value:'',checked:false,disabled:false,textContent:'',children:[],style:{},files:[],append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},addEventListener(){},focus(){},click(){}}; }
  const get = id => {if(!elements.has(id))elements.set(id,element());return elements.get(id);};
  let blob;
  const context=vm.createContext({document:{getElementById:get,createElement:element},window:{addEventListener(){}},
    crypto:webcrypto,Blob,URL:{createObjectURL(b){blob=b;return 'blob:example';},revokeObjectURL(){}},
    setTimeout(fn){fn();},Option:function(text,value){this.textContent=text;this.value=value;},
    fetch:async()=>({ok:true,json:async()=>({token:'fictional',prompts:['base prompt','short','voice']})})});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),context);
  get('category').value='user';get('source').value='fictional user statement';get('prompt-version').value='0';
  return {get,context,blob:()=>blob,run:code=>vm.runInContext(code,context)};
}

test('candidates are excluded, confirmation includes, edits invalidate',async()=>{
  const w=workspace();await new Promise(resolve=>setImmediate(resolve));
  w.get('memory-content').value='fictional preference';w.get('add-memory').onclick();
  w.get('reviewed').checked=true;w.get('generate').onclick();
  assert.equal(w.get('prompt').value,'base prompt');
  w.get('memories').children[0].children[2].onclick();
  assert.equal(w.get('reviewed').checked,false);
  w.get('reviewed').checked=true;w.get('generate').onclick();
  assert.match(w.get('prompt').value,/fictional preference/);
  w.get('memories').children[0].children[3].onclick();
  w.get('memory-content').value='edited preference';w.get('add-memory').onclick();
  assert.equal(w.get('copy').disabled,true);
  assert.equal(w.run('memories[0].user_confirmed'),false);
  assert.equal(w.run('memories[0].revision'),3);
});

test('canonical JSON roundtrip re-confirms and rejects duplicate IDs',async()=>{
  const w=workspace();w.get('memory-content').value='fictional preference';w.get('add-memory').onclick();
  w.get('memories').children[0].children[2].onclick();w.get('export-memory').onclick();
  const serialized=await w.blob().text(), data=JSON.parse(serialized);
  assert.equal(data.schema_version,'1.0');assert.equal(data.records[0].confirmed,true);
  assert.match(data.records[0].id,/^memory-[a-z0-9-]+$/);
  assert.equal(data.records[0].content.summary,'fictional preference');
  w.get('clear').onclick();w.get('import-memory').files=[{size:serialized.length,text:async()=>serialized}];
  await w.get('import-memory').onchange();assert.equal(w.run('memories.length'),1);
  assert.equal(w.run('memories[0].user_confirmed'),false);
  await w.get('import-memory').onchange();assert.equal(w.run('memories.length'),1);
  assert.match(w.get('persona-status').textContent,/重复/);
});

test('short term expires and is excluded; deletion removes draft',async()=>{
  const w=workspace();await new Promise(resolve=>setImmediate(resolve));
  w.get('category').value='short_term';w.get('memory-content').value='temporary fictional context';w.get('add-memory').onclick();
  w.get('memories').children[0].children[2].onclick();w.get('reviewed').checked=true;w.get('generate').onclick();
  assert.equal(w.get('prompt').value,'base prompt');
  w.get('export-memory').onclick();const data=JSON.parse(await w.blob().text());
  assert.ok(Date.parse(data.records[0].expires_at)>Date.now());
  w.get('memories').children[0].children[4].onclick();assert.equal(w.run('memories.length'),0);
});

test('private text is rendered through textContent, not HTML',()=>{
  const w=workspace();w.run(`rows=[{sender:'fictional',content:'<img src=x onerror=alert(1)>',quote_content:'<script>bad</script>',timestamp:1,datetime:'fictional',message_type:'text'}];filterMessages();`);
  assert.equal(w.get('messages').children[0].children[1].textContent,'<img src=x onerror=alert(1)>');
  assert.equal(w.get('messages').children[0].children[2].textContent,'<script>bad</script>');
});
