// Exercise guest submission behavior without a browser or external dependencies.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

function authPage(search, options={}) {
  const nodes=new Map();
  const location={search,hash:options.hash??'#token_hash=synthetic-test-token',pathname:'/auth/confirm'};
  const context=vm.createContext({URLSearchParams,location,fetch:options.fetch,
    history:{replaceState:(_state,_title,value)=>{const next=new URL(value,'https://scene.example');location.search=next.search;location.hash=next.hash;}},
    document:{querySelector:selector=>{
      if(!nodes.has(selector))nodes.set(selector,{hidden:selector!=='#verify-form',required:true,handlers:{},addEventListener(type,handler){this.handlers[type]=handler}});
      return nodes.get(selector);
    }}
  });
  vm.runInContext(fs.readFileSync('static/auth.js','utf8'),context);
  return {nodes,location};
}

test('password recovery opens its form after sensitive URL data is removed',()=>{
  const {nodes,location}=authPage('?recover=1');
  assert.equal(nodes.get('#recover-form').hidden,false);
  assert.equal(nodes.get('#verify-form').hidden,true);
  assert.equal(location.search,'?recover=1');assert.equal(location.hash,'');
});

test('verified account setup opens its form after URL cleanup',()=>{
  const {nodes}=authPage('?onboard=1');
  assert.equal(nodes.get('#onboard-form').hidden,false);
  assert.equal(nodes.get('#verify-form').hidden,true);
});

function guestApp(industry, fetch, nodes={}) {
  const source = fs.readFileSync('static/app.js', 'utf8');
  const start = source.lastIndexOf(' initialize().catch(');
  assert.ok(start > 0);
  const storage=new Map();
  const context = vm.createContext({
    sessionStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)},
    URLSearchParams,
    crypto: webcrypto,
    fetch,
    document: {getElementById: id => nodes[id]||({})},
  });
  vm.runInContext(source.slice(0, start) + `
    renderGuest=()=>{};toast=()=>{};beginGuestStatusPolling=()=>{};
    globalThis.guestTest={state,sendCart,sendGuestRequest,submitGuestMessage,matchingProducts,adjustGuestCart,loadRequests,renderRequests,motionBehavior,renderCatalog,renderStations,loadBusiness,onBrand,requestCard,scanTokenFromLocation};
  })();`, context);
  const app = context.guestTest;
  app.storage=storage;app.context=context;
  Object.assign(app.state, {
    guest: {industry,products:[{id:1,name:'Sample service'},{id:2,name:'Another service'}]},
    qr: 'sample-qr', cart:[{id:1,qty:1},{id:2,qty:1}],
  });
  return app;
}

for (const industry of ['restaurant','retail','barber','auto']) {
  test(`${industry} cart uses a supported request type`, async () => {
    const bodies=[];
    const app=guestApp(industry,async (_url,opts)=>{
      bodies.push(JSON.parse(opts.body));
      return {ok:true,json:async()=>({request_id:bodies.length,ticket:'sample-receipt',status:'open'})};
    });
    await app.sendCart();
    assert.equal(bodies.length,2);
    assert.ok(bodies.every(body=>body.kind===(['auto','barber'].includes(industry)?'service':'order')));
    assert.equal(app.state.cart.length,0);
    assert.equal(app.state.pending,false);
  });
}

test('partial failure retains only unsent selections',async()=>{
  const app=guestApp('auto',async (_url,opts)=>{
    const item=JSON.parse(opts.body).product_id;
    return {ok:item===1,json:async()=>item===1?{request_id:1,ticket:'sample-receipt',status:'open'}:{detail:'Try later'}};
  });
  await app.sendCart();
  assert.equal(app.state.cart.length,1);
  assert.equal(app.state.cart[0].id,2);
  assert.equal(app.state.pending,false);
});

test('in-flight submission blocks repeated cart and action clicks',async()=>{
  let resolve, calls=0;
  const app=guestApp('auto',()=>{
    calls++;
    return new Promise(done=>{resolve=done});
  });
  app.state.cart=[{id:1,qty:1}];
  const first=app.sendCart();
  await app.sendCart();
  await app.sendGuestRequest('service','Help');
  assert.equal(calls,1);
  resolve({ok:true,json:async()=>({request_id:1,ticket:'sample-receipt',status:'open'})});
  await first;
  assert.equal(app.state.pending,false);
});

test('all cart receipts remain available after multiple selections',async()=>{
  let count=0;
  const app=guestApp('restaurant',async()=>({ok:true,json:async()=>({request_id:++count,ticket:'synthetic-ticket-'+count,status:'open'})}));
  await app.sendCart();
  assert.equal(app.state.receipts.length,2);
  assert.deepEqual(Array.from(app.state.receipts,r=>r.id),[1,2]);
  assert.equal(app.state.receipt.id,2);
});

test('successful requests retain earlier private receipts',async()=>{
  let count=0;
  const app=guestApp('auto',async()=>({ok:true,json:async()=>({request_id:++count,ticket:'synthetic-ticket-'+count,status:'open'})}));
  await app.sendGuestRequest('service','Help');
  await app.sendGuestRequest('question','A synthetic question');
  assert.equal(app.state.receipts.length,2);
  assert.equal(app.state.receipts[0].ticket,'synthetic-ticket-1');
});

function inquiryFields(contact, consent) {
  const field=value=>({value,setCustomValidity(message){this.error=message},reportValidity(){}});
  const nodes={guestNote:field('Synthetic question'),guestName:field('Sample Guest'),guestContact:field(contact),guestConsent:{...field(''),checked:consent}};
  nodes.guestMessageForm={querySelector:()=>({disabled:false})};
  return nodes;
}

test('contact inquiry requires explicit consent before network submission',async()=>{
  let calls=0;
  const nodes=inquiryFields('guest@example.invalid',false);
  const app=guestApp('auto',async()=>{calls++},nodes);
  await app.submitGuestMessage({preventDefault(){}});
  assert.equal(calls,0);
  assert.match(nodes.guestConsent.error,/agree/);
});

test('consented inquiry reaches staff and stores only private receipt metadata',async()=>{
  let body;
  const app=guestApp('auto',async(_url,options)=>{
    body=JSON.parse(options.body);
    return {ok:true,json:async()=>({request_id:1,ticket:'synthetic-private-ticket',status:'open'})};
  },inquiryFields('guest@example.invalid',true));
  await app.submitGuestMessage({preventDefault(){}});
  assert.equal(body.kind,'question');
  assert.equal(body.customer_contact,'guest@example.invalid');
  assert.equal(body.customer_name,'Sample Guest');
  assert.equal(body.reply_consent,true);
  assert.equal(body.message,'Synthetic question');
  assert.ok(body.message.length<=400);
  const stored=app.storage.get('scene-receipts:sample-qr');
  assert.ok(stored.includes('synthetic-private-ticket'));
  assert.ok(!stored.includes('guest@example.invalid'));
});

test('failed inquiry preserves entered fields for correction',async()=>{
  const nodes=inquiryFields('',false);
  const app=guestApp('auto',async()=>({ok:false,json:async()=>({detail:'Try later'})}),nodes);
  await app.submitGuestMessage({preventDefault(){}});
  assert.equal(nodes.guestNote.value,'Synthetic question');
  assert.equal(app.state.receipts.length,0);
  assert.equal(app.state.pending,false);
});


test('guest catalog search combines text and category filters',()=>{
  const app=guestApp('auto',async()=>{});
  app.state.guest.products=[{id:1,name:'Exterior clean',description:'Wax finish',category:'Detailing'},{id:2,name:'Interior clean',description:'Seats',category:'Care'}];
  assert.deepEqual(Array.from(app.matchingProducts(app.state.guest,'CLEAN','Care'),p=>p.id),[2]);
  assert.deepEqual(Array.from(app.matchingProducts(app.state.guest,'wax'),p=>p.id),[1]);
  assert.equal(app.matchingProducts(app.state.guest,'missing').length,0);
});

test('cart quantities can be adjusted and removed with a maximum of 99',async()=>{
  let submitted;
  const app=guestApp('auto',async(_url,options)=>{submitted=JSON.parse(options.body);return {ok:true,json:async()=>({request_id:1,ticket:'synthetic-ticket',status:'open'})}});
  app.state.cart=[{id:1,qty:1}];
  app.adjustGuestCart(1,-1);
  assert.equal(app.state.cart.length,0);
  app.adjustGuestCart(1,1);
  app.adjustGuestCart(1,1);
  assert.equal(app.state.cart[0].qty,2);
  app.state.cart[0].qty=99;
  app.adjustGuestCart(1,1);
  assert.equal(app.state.cart[0].qty,99);
  app.state.pending=true;
  app.adjustGuestCart(1,-1);
  assert.equal(app.state.cart[0].qty,99);
  app.state.pending=false;
  await app.sendCart();
  assert.equal(submitted.quantity,99);
});

test('stale request search responses cannot overwrite newer results',async()=>{
  const pending=[];
  const app=guestApp('auto',(path)=>new Promise(resolve=>pending.push({path,resolve})));
  Object.assign(app.state,{me:{},business:{slug:'sample'},slug:'sample'});
  const first=app.loadRequests(false);
  app.state.requestSearch='new search';
  const second=app.loadRequests(false);
  assert.match(pending[1].path,/search=new\+search/);
  pending[1].resolve({ok:true,json:async()=>({requests:[{id:2}]})});
  await second;
  pending[0].resolve({ok:true,json:async()=>({requests:[{id:1}]})});
  await first;
  assert.equal(app.state.requestPage.requests[0].id,2);
});

test('lead stage filter is sent with request search',async()=>{
  let requested;
  const app=guestApp('auto',async path=>{
    requested=path;
    return {ok:true,json:async()=>({requests:[]})};
  });
  Object.assign(app.state,{me:{},business:{slug:'sample'},slug:'sample',requestLead:'qualified',requestSearch:'Sample Guest'});
  await app.loadRequests(false);
  const params=new URLSearchParams(requested.split('?')[1]);
  assert.equal(params.get('lead_status'),'qualified');
  assert.equal(params.get('search'),'Sample Guest');
});


test('request filter drafts survive a workspace rerender before Apply',()=>{
  const app=guestApp('auto',async()=>{});
  Object.assign(app.state,{business:{industry:'auto',stations:[],role:'owner'},requestLead:'',requestDraft:{search:'Draft & name',kind:'question',lead:'qualified',station:''}});
  const html=app.renderRequests();
  assert.match(html,/value="qualified" selected/);
  assert.match(html,/value="question" selected/);
  assert.match(html,/value="Draft &amp; name"/);
  assert.equal(app.state.requestLead,'');
});


test('selection notes accompany each item and clear after success',async()=>{
  const bodies=[];
  const app=guestApp('auto',async (_path,options)=>{
    bodies.push(JSON.parse(options.body));
    return {ok:true,json:async()=>({request_id:bodies.length,ticket:'synthetic-notes-receipt',status:'open'})};
  });
  app.state.cartNote='Synthetic pickup preference';
  await app.sendCart();
  assert.equal(bodies.length,2);
  assert.ok(bodies.every(body=>body.message==='Synthetic pickup preference'));
  assert.equal(app.state.cartNote,'');
  assert.ok(!app.storage.get('scene-receipts:sample-qr').includes('Synthetic pickup preference'));
});

test('failed selection keeps notes with unsent items',async()=>{
  const app=guestApp('auto',async()=>({ok:false,json:async()=>({detail:'Try later'})}));
  app.state.cartNote='Synthetic retry note';
  await app.sendCart();
  assert.equal(app.state.cartNote,'Synthetic retry note');
  assert.equal(app.state.cart.length,2);
});

test('programmatic scrolling honors reduced motion',()=>{
  const app=guestApp('auto',async()=>{});
  app.context.matchMedia=()=>({matches:true});
  assert.equal(app.motionBehavior(),'auto');
  app.context.matchMedia=()=>({matches:false});
  assert.equal(app.motionBehavior(),'smooth');
});

test('catalog edit and paused station forms escape user content',()=>{
  const app=guestApp('auto',async()=>{});
  const name='Sample \" onfocus=\"alert(1)';
  app.state.business={industry:'auto',slug:'sample',products:[{id:1,name,description:'<script>',category:'Care',price_cents:1200}],stations:[{id:1,label:name,code:'desk',token:'synthetic-token',active:0}]};
  app.state.editProduct=1;
  const catalog=app.renderCatalog(),stations=app.renderStations();
  assert.ok(!catalog.includes('<script>'));
  assert.ok(catalog.includes('&lt;script&gt;'));
  assert.ok(catalog.includes('Sample &quot; onfocus=&quot;alert(1)'));
  assert.match(stations,/QR location paused/);
  assert.ok(!stations.includes('class="qr-image"'));
  assert.ok(!stations.includes('data-station-preview='));
});


test('lost submission response blocks duplicates and keeps a tab recovery marker',async()=>{
  let calls=0;
  const app=guestApp('auto',async()=>{calls++;throw new Error('Synthetic connection interrupted')});
  app.state.cart=[{id:1,qty:1}];
  await app.sendCart();
  await app.sendCart();
  await app.sendGuestRequest('service','Help');
  assert.equal(calls,1);
  assert.equal(app.state.uncertain,true);
  assert.equal(app.storage.get('scene-uncertain:sample-qr'),'yes');
  assert.equal(app.state.cart.length,1);
  assert.match(app.state.feedback,/staff/i);
});

test('server error or unreadable response never pretends a request succeeded',async()=>{
  for(const response of [
    {ok:false,status:503,json:async()=>({detail:'Synthetic unavailable'})},
    {ok:true,status:200,json:async()=>{throw new Error('truncated')}},
    {ok:true,status:200,json:async()=>({})},
  ]){
    let calls=0;
    const app=guestApp('auto',async()=>{calls++;return response});
    await app.sendGuestRequest('service','Help');
    await app.sendGuestRequest('service','Help');
    assert.equal(calls,1);
    assert.equal(app.state.receipts.length,0);
    assert.equal(app.state.uncertain,true);
  }
});

test('confirmed validation rejection permits correction without delivery lock',async()=>{
  let calls=0;
  const app=guestApp('auto',async()=>{calls++;return {ok:false,status:400,json:async()=>({detail:'Correct this input'})}});
  await app.sendGuestRequest('question','Synthetic inquiry');
  await app.sendGuestRequest('question','Corrected inquiry');
  assert.equal(calls,2);
  assert.equal(app.state.uncertain,false);
});

test('revoked access immediately clears cached private workspace data',async()=>{
  const content={textContent:''};
  const app=guestApp('auto',async()=>({ok:false,status:404,json:async()=>({detail:'Business not found'})}),{workContent:content});
  app.state.me={csrf:'synthetic-csrf'};
  app.state.slug='sample';app.state.business={slug:'sample',requests:[{customer_contact:'private@example.invalid'}]};
  app.state.requestPage={requests:[{customer_contact:'private@example.invalid'}]};
  app.state.inviteUrl='synthetic-private-invite';
  await assert.rejects(app.loadBusiness('sample'),/Business not found/);
  assert.equal(app.state.business,null);
  assert.equal(app.state.requestPage,null);
  assert.equal(app.state.inviteUrl,'');
  assert.match(content.textContent,/access|sign in/i);
});


test('business accents retain readable header contrast',()=>{
  const app=guestApp('restaurant',async()=>{});
  const luminance=hex=>hex.slice(1).match(/../g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  for(const color of ['#000000','#ffffff','#777777','#808080','#ff0000','#00ff00','#0000ff','#c28f5a']){
    const a=luminance(color),b=luminance(app.onBrand(color));
    assert.ok((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5,color);
  }
});

test('service tickets expose one next action and a textual status',()=>{
  const app=guestApp('restaurant',async()=>{});app.state.business={role:'owner'};
  const ticket={id:12,station:'Table <01>',kind:'service',message:'Call server',created_at:1700000000};
  const start=app.requestCard({...ticket,status:'open'});
  assert.match(start,/data-next-status="in_progress"/);assert.match(start,/>Start<\/button>/);
  assert.ok(!start.includes('<select'));assert.ok(start.includes('Table &lt;01&gt;'));
  assert.match(app.requestCard({...ticket,status:'in_progress'}),/>Mark done<\/button>/);
  assert.ok(!app.requestCard({...ticket,status:'completed'}).includes('data-next-status'));
});


test('printed QR and legacy query links resolve to the same guest token',()=>{
 const app=guestApp('restaurant',async()=>{});
 assert.equal(app.scanTokenFromLocation({pathname:'/q/printed-token',search:''}),'printed-token');
 assert.equal(app.scanTokenFromLocation({pathname:'/q/printed-token/',search:''}),'printed-token');
 assert.equal(app.scanTokenFromLocation({pathname:'/',search:'?q=printed-token'}),'printed-token');
 assert.equal(app.scanTokenFromLocation({pathname:'/q/%ZZ',search:''}),null);
 assert.equal(app.scanTokenFromLocation({pathname:'/',search:''}),null);
});


test('default confirmation links remove tokens and ask for provider-verified sign-in',()=>{
 const {nodes,location}=authPage('',{hash:'#access_token=synthetic-email-session&type=signup'});
 assert.equal(location.hash,'');assert.equal(nodes.get('#verify-form').hidden,true);
 assert.match(nodes.get('#status').textContent,/Sign in to continue/);
 assert.ok(!nodes.get('#status').textContent.includes('synthetic-email-session'));
});

test('default recovery links use the backend verification endpoint and never URL storage',async()=>{
 const calls=[];
 const {nodes,location}=authPage('',{hash:'#access_token=synthetic-recovery-session&type=recovery',fetch:async(path,options)=>{calls.push({path,body:JSON.parse(options.body)});return {ok:true,json:async()=>({ok:true})}}});
 assert.equal(location.hash,'');assert.equal(nodes.get('#password-form').hidden,false);
 nodes.set('#password',{value:'SyntheticNewPassword123!'});
 await nodes.get('#password-form').handlers.submit({preventDefault(){}});
 assert.equal(calls.length,1);assert.equal(calls[0].path,'/api/auth/reset-password');
 assert.equal(calls[0].body.access_token,'synthetic-recovery-session');
 assert.equal(nodes.get('#password').value,'');assert.equal(nodes.get('#password-form').hidden,true);
});

test('expired email callbacks do not expose a password reset form',()=>{
 const {nodes,location}=authPage('',{hash:'#error=access_denied&type=recovery&access_token=synthetic-invalid'});
 assert.equal(location.hash,'');assert.equal(nodes.get('#password-form').hidden,true);
 assert.match(nodes.get('#status').textContent,/invalid or expired/);
});
