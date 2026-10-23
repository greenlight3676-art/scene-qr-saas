'use strict';
const statusNode = document.querySelector('#status');
const fragment = new URLSearchParams(location.hash.slice(1));
const tokenHash = fragment.get('token_hash');
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
    const response = await fetch('/api/auth/recovery-session', {credentials:'same-origin'});
    const session = await response.json();
    if (!response.ok) throw new Error('Recovery session expired. Request a new code.');
    await post('/api/auth/complete-recovery', {password:document.querySelector('#password').value}, session.csrf);
    document.querySelector('#password').value = '';
    document.querySelector('#password-form').hidden = true;
    statusNode.textContent = 'Password changed. Return to Scene and sign in again.';
  } catch (error) { statusNode.textContent = error.message; }
});

if(new URLSearchParams(location.search).has('recover')) {
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
