// Fetch products from server and render into .product-grid
(async function(){
    const grid = document.querySelector('.product-grid');
    if(!grid) return;
    try{
        const res = await fetch('/api/products');
        if(!res.ok) return;
        const products = await res.json();
        if(!products || products.length===0) return;
        grid.innerHTML = products.map(p=>{
            const img = (p.images && p.images.length>0) ? p.images[0] : 'https://via.placeholder.com/600x400?text=No+Image';
            const priceHtml = p.original_price && p.original_price>p.price ? `₹${p.price} <span>₹${p.original_price}</span>` : `₹${p.price}`;
            return `
                <a href="product.html?id=${p.id}" class="product-card">
                    <div class="card-image">
                        ${p.tags && p.tags.includes('trending') ? '<span class="tag">Trending</span>' : ''}
                        <img src="${img}" alt="${p.title}">
                    </div>
                    <div class="card-info">
                        <h4>${p.title}</h4>
                        <div class="price">${priceHtml}</div>
                    </div>
                </a>
            `;
        }).join('\n');
    }catch(e){ console.error('Could not load products', e); }
})();
