(function () {
  var brl = function (v) { return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); };
  var T = window.Track || { withAttribution: function (u) { return u; } };
  var LOJA = window.LOJA || {};

  /* ---------- Catálogo ---------- */
  var grid = document.getElementById('grid');
  if (grid) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll('.prod'));
    var input = document.getElementById('busca');
    var chips = document.querySelectorAll('.chip');
    var count = document.getElementById('count');
    var tipo = 'todos';
    var norm = function (s) { return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); };
    function apply() {
      var q = norm(input.value.trim()), n = 0;
      cards.forEach(function (c) {
        var ok = (!q || norm(c.dataset.busca).indexOf(q) > -1) && (tipo === 'todos' || c.dataset.tipo === tipo);
        c.hidden = !ok; if (ok) n++;
      });
      count.textContent = n === 1 ? '1 produto' : n + ' produtos';
    }
    input.addEventListener('input', apply);
    chips.forEach(function (ch) {
      ch.addEventListener('click', function () {
        chips.forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        ch.setAttribute('aria-pressed', 'true'); tipo = ch.dataset.tipo; apply();
      });
    });
    var q0 = new URLSearchParams(location.search).get('q'); if (q0) input.value = q0;
    apply();
    if (T.viewList) T.viewList(cards.slice(0, 40).map(function (c) { return { sku: c.dataset.sku, nome: c.dataset.nome, marca: c.dataset.marca, preco: +c.dataset.preco, kit: '1', categoria: c.dataset.tipo }; }));
  }

  /* ---------- Produto ---------- */
  var dataEl = document.getElementById('produto-dados');
  if (dataEl) {
    var P = JSON.parse(dataEl.textContent);
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
