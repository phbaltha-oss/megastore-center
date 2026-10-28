(function () {
  var brl = function (v) { return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); };
  var T = window.Track || { withAttribution: function (u) { return u; } };
  var LOJA = window.LOJA || {};

  /* ---------- Catálogo ---------- */
  var shelves = document.querySelectorAll('.shelf');
  var input = document.getElementById('busca');
  if (shelves.length && input) {
    var count = document.getElementById('count');
    var best = document.getElementById('mais-vendidos');
    var norm = function (s) { return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); };
    function apply() {
      var q = norm(input.value.trim()), n = 0, seen = {};
      if (best) best.hidden = !!q;
      shelves.forEach(function (s) {
        if (s === best) return;
        s.classList.toggle('searching', !!q);
        var vis = 0;
        s.querySelectorAll('.prod').forEach(function (c) {
          var ok = !q || norm(c.dataset.busca).indexOf(q) > -1;
          c.hidden = !ok; if (ok) { vis++; if (!seen[c.dataset.sku]) { seen[c.dataset.sku] = 1; n++; } }
        });
        s.hidden = !vis;
      });
      count.textContent = !q ? '' : (n === 0 ? 'Nenhum produto encontrado. Tente outro nome.' : (n === 1 ? '1 produto encontrado' : n + ' produtos encontrados'));
    }
    input.addEventListener('input', apply);
    var q0 = new URLSearchParams(location.search).get('q'); if (q0) input.value = q0;
    apply();
    var cards = Array.prototype.slice.call(document.querySelectorAll('.shelf .prod'));
    if (T.viewList) T.viewList(cards.slice(0, 40).map(function (c) { return { sku: c.dataset.sku, nome: c.dataset.nome, marca: c.dataset.marca, preco: +c.dataset.preco, kit: '1', categoria: c.dataset.cat }; }));
  }

  /* ---------- Produto ---------- */
  var dataEl = document.getElementById('produto-dados');
  if (dataEl) {
    var P = JSON.parse(dataEl.textContent);
    // Caminhos absolutos: a URL muda ao trocar de kit (history.replaceState), e caminhos relativos quebrariam as fotos.
    var abs = function (s) { try { return new URL(s, location.href).href; } catch (e) { return s; } };
    P.variacoes.forEach(function (v) { v.imagens = v.imagens.map(abs); if (v.url) v.url = abs(v.url); });
    var priceEl = document.getElementById('preco'), unitEl = document.getElementById('preco-unit');
    var buy = document.getElementById('comprar'), titleEl = document.getElementById('kit-titulo');
    var main = document.getElementById('foto'), thumbs = document.getElementById('thumbs');
    var current;

    function payload(v) { return { sku: v.sku, nome: v.titulo, marca: P.marca, preco: v.preco, kit: String(v.qtd), categoria: P.tipo }; }
    function gallery(v) {
      thumbs.innerHTML = '';
      v.imagens.forEach(function (src, i) {
        var b = document.createElement('button'); b.type = 'button';
        b.setAttribute('aria-label', 'Ver foto ' + (i + 1));
        b.setAttribute('aria-current', i === 0 ? 'true' : 'false');
        b.innerHTML = '<img src="' + src + '" alt="" loading="lazy" referrerpolicy="no-referrer">';
        b.addEventListener('click', function () {
          main.src = src; thumbs.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-current', 'false'); });
          b.setAttribute('aria-current', 'true');
        });
        thumbs.appendChild(b);
      });
      main.src = v.imagens[0]; main.alt = v.titulo;
    }
    function select(q, silent) {
      current = P.variacoes.filter(function (v) { return v.qtd === q; })[0] || P.variacoes[0];
      priceEl.textContent = brl(current.preco);
      unitEl.textContent = current.qtd === 1 ? '1 ' + P.unidade : brl(current.preco / current.qtd) + ' por ' + P.unidade + ' · ' + current.qtd + ' ' + P.unidade_plural;
      titleEl.textContent = current.titulo;
      gallery(current);
      if (!silent && current.url) history.replaceState(null, '', current.url);
      if (!silent && T.selectKit) T.selectKit(payload(current));
    }
    document.querySelectorAll('input[name="kit"]').forEach(function (r) {
      r.addEventListener('change', function () { select(+r.value); });
    });
    var r0 = document.querySelector('input[name="kit"]:checked');
    select(r0 ? +r0.value : 1, true);
    if (T.viewItem) T.viewItem(payload(current));

    buy.addEventListener('click', function () {
      var link = (LOJA.checkout || {})[current.sku];
      if (link) {
        if (T.beginCheckout) T.beginCheckout(payload(current));
        setTimeout(function () { location.href = T.withAttribution(link); }, 250);
      } else {
        if (T.whatsapp) T.whatsapp(payload(current));
        var msg = 'Olá! Quero comprar: ' + current.titulo + ' (' + brl(current.preco) + ') – código ' + current.sku;
        if (LOJA.whatsapp) window.open('https://wa.me/' + LOJA.whatsapp + '?text=' + encodeURIComponent(msg), '_blank', 'noopener');
        else location.href = 'mailto:' + LOJA.email + '?subject=' + encodeURIComponent('Pedido: ' + current.titulo) + '&body=' + encodeURIComponent(msg);
      }
    });
  }

  /* ---------- WhatsApp ---------- */
  document.querySelectorAll('[data-wa]').forEach(function (a) {
    a.addEventListener('click', function () { if (T.whatsapp) T.whatsapp(null); });
  });

  /* ---------- Obrigado ---------- */
  var ok = document.getElementById('obrigado');
  if (ok && T.purchase) {
    var r = T.purchase();
    if (r && r.id) ok.querySelector('[data-pedido]').textContent = r.id;
  }
})();
