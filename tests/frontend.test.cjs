// Exercise guest submission behavior without a browser or external dependencies.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

function guestApp(industry, fetch, nodes={}) {
  const source = fs.readFileSync('static/app.js', 'utf8');
  const start = source.lastIndexOf(' initialize().catch(');
  assert.ok(start > 0);
  const storage=new Map();
  const context = vm.createContext({
    sessionStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)},
    crypto: webcrypto,
    fetch,
    document: {getElementById: id => nodes[id]||({})},
  });
  vm.runInContext(source.slice(0, start) + `
    renderGuest=()=>{};toast=()=>{};beginGuestStatusPolling=()=>{};
    globalThis.guestTest={state,sendCart,sendGuestRequest,submitGuestMessage};
  })();`, context);
  const app = context.guestTest;
  app.storage=storage;
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
  assert.match(body.message,/Contact \(reply consent\): guest@example.invalid/);
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
