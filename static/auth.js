(()=>{'use strict';
const $=id=>document.getElementById(id);
// Capture mode before scrubbing the URL; recovery/onboarding must survive cleanup.
const mode=new URLSearchParams(location.search);
let tokenHash=new URLSearchParams(location.hash.slice(1)).get('token_hash');
history.replaceState(null,'',location.pathname);
if(mode.has('recover')||mode.has('onboard'))tokenHash=null;
const busy=new Set();
const stages={
  verify:['ACCOUNT VERIFICATION','Check your inbox.','Enter the code from your email in the browser where you started registration or recovery.'],
  recover:['ACCOUNT RECOVERY','Let’s get you back in.','Enter your account email. If eligible, we’ll send a code to help you reset your password.'],
  password:['ACCOUNT RECOVERY','A fresh start.','Your code is verified. Choose a new password to secure your account.'],
  onboard:['YOUR BUSINESS WORKSPACE','Make it yours.','Your email is verified. Add your business details to create your workspace.'],
  done:['ALL SET','You’re ready.','Your account is ready for the next step.']
};
function stage(name,focus=false){
  for(const key of ['verify','recover','password','onboard']) $(key+'-form').hidden=key!==name;
  $('accountContinue').hidden=name!=='done';
  const [eyebrow,title,description]=stages[name];
  $('accountEyebrow').textContent=eyebrow;$('accountTitle').textContent=title;$('accountDescription').textContent=description;
  document.title=title+' · SCENE';
  if(focus){const form=$(name+'-form');(form?.querySelector('input:not([hidden]),select,button')||$('accountContinue')).focus();}
}
function message(text,error=false){
  $('status').textContent=text;$('status').hidden=!text;$('status').classList.toggle('is-error',error);
  if(error)$('status').focus();
}
async function request(path,payload,csrf){
  let response,data;
  try{
    response=await fetch(path,{method:payload===undefined?'GET':'POST',credentials:'same-origin',
      headers:{Accept:'application/json',...(payload===undefined?{}:{'Content-Type':'application/json'}),...(csrf?{'x-scene-csrf':csrf}:{})},
      ...(payload===undefined?{}:{body:JSON.stringify(payload)})});
  }catch{throw new Error('Cannot connect to Scene. Check your connection and try again.');}
  try{data=await response.json();}catch{throw new Error('The response could not be read. Try again shortly.');}
  if(!response.ok)throw new Error(typeof data?.detail==='string'?data.detail:'Check your details and try again.');
  return data;
}
function bind(name,task){
  const form=$(name+'-form');
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy.has(form))return;
    const button=form.querySelector('button[type="submit"]'),label=button.textContent;
    busy.add(form);button.disabled=true;button.textContent='Please wait…';form.setAttribute('aria-busy','true');message('');
    try{await task();}catch(error){message(error.message,true);}
    finally{busy.delete(form);button.disabled=false;button.textContent=label;form.setAttribute('aria-busy','false');}
  });
}
bind('verify',async()=>{
  const data=await request('/api/auth/verify',tokenHash?{token_hash:tokenHash}:{token:$('code').value.trim()});
  tokenHash=null;$('code').value='';
  if(data.recovery){stage('password',true);message('Code verified. Choose your new password.');}
  else if(data.onboarding_required&&!data.organization){stage('onboard',true);message('Email verified. Let’s set up your business.');}
  else{stage('done',true);message('Email verified. Your workspace is ready.');}
});
bind('password',async()=>{
  const session=await request('/api/auth/recovery-session');
  await request('/api/auth/complete-recovery',{password:$('password').value},session.csrf);
  $('password').value='';stage('done',true);$('accountContinue').textContent='Return to sign in →';message('Password changed. Sign in with your new password.');
});
bind('recover',async()=>{
  await request('/api/auth/recover',{email:$('recover-email').value.trim()});
  stage('verify',true);message('If eligible, check your inbox and enter the code in this browser.');
});
bind('onboard',async()=>{
  const session=await request('/api/me');
  await request('/api/organizations',{name:$('business-name').value.trim(),industry:$('business-industry').value},session.csrf);
  location.assign('/');
});
if(tokenHash){$('code').required=false;$('code-field').hidden=true;stage('verify');$('accountDescription').textContent='Your email link is ready. Continue below to verify it in this browser.';}
else stage(mode.has('recover')?'recover':mode.has('onboard')?'onboard':'verify');
})();
