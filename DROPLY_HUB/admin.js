// Admin auth and product storage helpers (client-side)
// Admin client API using server endpoints
(function(){
    async function _api(path, opts={}){
        // ensure same-origin credentials so session cookie is returned/set
        opts.credentials = opts.credentials || 'same-origin';
        console.debug('API', path, opts.method || 'GET');
        const res = await fetch(path, opts);
        let data;
        try{ data = await res.json(); }catch(e){ data = null; }
        if(!res.ok) throw data || {ok:false, msg:'Server error'};
        return data;
    }

    async function requireAuth(){
        try{
            const status = await fetch('/api/admin/status', { credentials: 'same-origin' });
            if(status.status !== 200){ window.location.href='admin.html'; }
            return true;
        }catch(e){ window.location.href='admin.html'; }
        return false;
    }

    window.Admin = {
        async login(user,pin){
            try{
                const r = await _api('/api/admin/login', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({user: document.getElementById('user').value, // STRING
                pin: document.getElementById('pin').value})});
                console.debug('login response', r);
                if(r.role === 'affiliate' && r.affiliate_id){
    sessionStorage.setItem('affiliate_id', r.affiliate_id);
}
                return {ok:true, data:r};
            }catch(e){ console.error('login error', e); return {ok:false, msg: e && e.msg ? e.msg : 'Login failed'}; }
        },
        async register(phone,pin){
            try{
                const r = await _api('/api/admin/register', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({phone,pin})});
                console.debug('register response', r);
                return {ok:true, data:r};
            }catch(e){ console.error('register error', e); return {ok:false, msg: e && e.msg ? e.msg : 'Register failed'}; }
        },
        async logout(){
            await fetch('/api/admin/logout', { credentials: 'same-origin' });
            sessionStorage.removeItem('adminAuth');
            window.location.href = 'admin.html';
        },
        // convenience wrappers for product operations
        async saveProductFormData(formData){
            const res = await fetch('/api/admin/upload', { method: 'POST', body: formData, credentials: 'same-origin' });
            let json = null;
            try{ json = await res.json(); }catch(e){ json = null; }
            // always return object with ok flag and body
            return Object.assign({ ok: res.ok }, json || {} );
        },
        async updateProductFormData(formData, id){
            formData.append('id', id);
            const res = await fetch('/api/admin/update', { method: 'POST', body: formData, credentials: 'same-origin' });
            let json = null;
            try{ json = await res.json(); }catch(e){ json = null; }
            return Object.assign({ ok: res.ok }, json || {} );
        },
        async saveProductFormData(formData){
            const res = await fetch('/api/admin/upload', { method: 'POST', body: formData, credentials: 'same-origin' });
            let json = null;
            try{ json = await res.json(); }catch(e){ json = null; }
            return Object.assign({ ok: res.ok }, json || {} );
        },
        async listProducts(){
            const res = await fetch('/api/products');
            return await res.json();
        },
        async deleteProduct(id){
            const res = await fetch('/api/admin/product/'+encodeURIComponent(id), { method: 'DELETE', credentials: 'same-origin' });
            return await res.json();
        },
        requireAuth
    };
})();
