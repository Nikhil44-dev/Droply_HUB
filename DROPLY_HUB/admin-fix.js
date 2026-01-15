// Attach robust handlers for login/register forms to avoid null .value errors
(function(){
    function attach(){
        const msg = document.getElementById('message');
        const loginForm = document.getElementById('loginForm');
        if(loginForm && !loginForm.__fixed){
            loginForm.__fixed = true;
            loginForm.addEventListener('submit', async function(e){
    e.preventDefault();

    const userEl = document.getElementById('user');
    const pinEl  = document.getElementById('pin');

    const affiliateId = userEl.value.trim(); // 🔑 यही AFF001 है
    const pin = pinEl.value.trim();

    if(!affiliateId || !pin){
        msg.textContent = 'Fill all fields';
        return;
    }

    const res = await Admin.login(affiliateId, pin);
    const data = res.data || res;

    if(data.ok && data.role === 'affiliate'){
        // ✅ EXACT user input hi save ho raha
        sessionStorage.setItem('affiliate_id', affiliateId);
        window.location.href = data.redirect;
    } 
    else if(data.ok && data.role === 'admin'){
        window.location.href = data.redirect;
    } 
    else {
        msg.textContent = data.msg || 'Login failed';
    }
});

        }

        const regForm = document.getElementById('regForm');
        if(regForm && !regForm.__fixed){
            regForm.__fixed = true;
            regForm.addEventListener('submit', async function(e){
                e.preventDefault();
                if(msg) msg.textContent='';
                const phoneEl = document.getElementById('rphone');
                const pinEl = document.getElementById('rpin');
                const pin2El = document.getElementById('rpin2');
                if(!phoneEl || !pinEl || !pin2El){ if(msg) msg.textContent='Form fields missing. Reload page.'; return; }
                const p = phoneEl.value.trim();
                const pin = pinEl.value.trim();
                const pin2 = pin2El.value.trim();
                if(pin !== pin2){ if(msg) msg.textContent='PINs do not match'; if(msg) msg.className='error'; return; }
                try{
                    const res = await Admin.register(p,pin);
                    if(res && res.ok){ window.location.href='admin_dashboard.html'; }
                    else { if(msg) msg.textContent = res.msg || 'Register failed'; if(msg) msg.className='error'; }
                }catch(err){ if(msg) msg.textContent = err && err.msg ? err.msg : 'Register error'; if(msg) msg.className='error'; }
            });
        }
    }

    document.addEventListener('DOMContentLoaded', ()=>{
        attach();
        // also poll briefly in case UI is dynamically rendered
        const id = setInterval(()=>{ attach(); }, 250);
        setTimeout(()=> clearInterval(id), 4000);
    });
})();
