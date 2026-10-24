'use strict';
const statusNode = document.querySelector('#status');
const pageOptions = new URLSearchParams(location.search);
const fragment = new URLSearchParams(location.hash.slice(1));
const tokenHash = fragment.get('token_hash') || pageOptions.get('token_hash');
let recoveryAccessToken = fragment.get('type') === 'recovery' ? fragment.get('access_token') : null;
const confirmationLinkOpened = fragment.has('access_token') && !recoveryAccessToken;
const emailLinkError = fragment.has('error') || pageOptions.has('error');
history.replaceState(null, '', location.pathname);
async function post(path, payload, csrf) {
  const response = await fetch(path, {method:'POST', credentials:'same-origin',
    headers:{'Content-Type':'application/json', ...(csrf ? {'x-scene-csrf':csrf} : {})}, body:JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check the form and try again.');
  return data;
}
document.querySelector('#verify-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const data = await post('/api/auth/verify', tokenHash ? {token_hash:tokenHash} : {token:document.querySelector('#code').value.trim()});
    document.querySelector('#verify-form').hidden = true;
    if (data.recovery) {
      document.querySelector('#password-form').hidden = false;
      statusNode.textContent = 'Code verified. Choose your new password.';
    } else statusNode.textContent = 'Email verified. Return to Scene to finish your business setup.';
  } catch (error) { statusNode.textContent = error.message; }
});
if (tokenHash) document.querySelector('#code').required = false;
document.querySelector('#password-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const password=document.querySelector('#password').value;
    if(recoveryAccessToken){
      await post('/api/auth/reset-password',{access_token:recoveryAccessToken,password});
      recoveryAccessToken=null;
    }else{
      const response=await fetch('/api/auth/recovery-session',{credentials:'same-origin'});
      const session=await response.json();
      if(!response.ok)throw new Error('Recovery session expired. Request a new code.');
      await post('/api/auth/complete-recovery',{password},session.csrf);
    }
    document.querySelector('#password').value = '';
    document.querySelector('#password-form').hidden = true;
    statusNode.textContent = 'Password changed. Return to Scene and sign in again.';
  } catch (error) { statusNode.textContent = error.message; }
});

if(pageOptions.has('recover')) {
  document.querySelector('#recover-form').hidden=false;
  document.querySelector('#verify-form').hidden=true;
}
document.querySelector('#recover-form').addEventListener('submit',async event=>{
  event.preventDefault();
  try {
    await post('/api/auth/recover',{email:document.querySelector('#recover-email').value.trim()});
    document.querySelector('#recover-form').hidden=true;
    document.querySelector('#verify-form').hidden=false;
    statusNode.textContent='If eligible, check your email and enter the code in this browser.';
  } catch(error) {statusNode.textContent=error.message;}
});

if(pageOptions.has('onboard')) {
  document.querySelector('#onboard-form').hidden=false;
  document.querySelector('#verify-form').hidden=true;
  statusNode.textContent='Finish setting up your verified account.';
}
document.querySelector('#onboard-form').addEventListener('submit',async event=>{
  event.preventDefault();
  try {
    const response=await fetch('/api/me',{credentials:'same-origin'});
    const session=await response.json();
    if(!response.ok) throw new Error('Sign in again to finish setup.');
    await post('/api/organizations',{name:document.querySelector('#business-name').value.trim(),industry:document.querySelector('#business-industry').value},session.csrf);
    location.assign('/');
  } catch(error) {statusNode.textContent=error.message;}
});

// Supabase's default email links return an implicit session in the fragment.
// Keep it only in memory, remove it from history, and let the backend verify it.
if(recoveryAccessToken){
  document.querySelector('#recover-form').hidden=true;
  document.querySelector('#verify-form').hidden=true;
  document.querySelector('#password-form').hidden=false;
  statusNode.textContent='Choose a new password. The server will verify your recovery link when you save.';
}else if(confirmationLinkOpened){
  document.querySelector('#verify-form').hidden=true;
  statusNode.textContent='Your email link has opened. Sign in to continue; Scene will check your verified email before creating a session.';
  const back=document.querySelector('a[href="/"]');if(back){back.href='/?signin=1';back.textContent='Sign in to Scene';}
}
if(emailLinkError){
  recoveryAccessToken=null;
  document.querySelector('#verify-form').hidden=true;
  document.querySelector('#password-form').hidden=true;
  statusNode.textContent='This email link is invalid or expired. Return to Scene and request a new link.';
}
