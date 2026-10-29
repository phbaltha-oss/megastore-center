(function () {
  var brl = function (v) { return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); };
  var T = window.Track || { withAttribution: function (u) { return u; } };
  var LOJA = window.LOJA || {};

  var norm = function (s) { return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); };

  /* ---------- Destaques (hero) ---------- */
  var hero = document.querySelector('.hero');
  if (hero) {
    var slides = hero.querySelectorAll('.slide'), dots = hero.querySelectorAll('.dots button'), cur = 0, timer;
    var go = function (i) {
      cur = (i + slides.length) % slides.length;
      slides.forEach(function (s, j) { s.classList.toggle('on', j === cur); });
      dots.forEach(function (d, j) { d.setAttribute('aria-current', j === cur ? 'true' : 'false'); });
    };
    var auto = function () { clearInterval(timer); if (!matchMedia('(prefers-reduced-motion: reduce)').matches) timer = setInterval(function () { go(cur + 1); }, 6000); };
    hero.querySelector('.prev').addEventListener('click', function () { go(cur - 1); auto(); });
    hero.querySelector('.next').addEventListener('click', function () { go(cur + 1); auto(); });
    dots.forEach(function (d, j) { d.addEventListener('click', function () { go(j); auto(); }); });
    hero.addEventListener('mouseenter', function () { clearInterval(timer); });
    hero.addEventListener('mouseleave', auto);
    auto();
  }

  /* ---------- Carrosséis ---------- */
  document.querySelectorAll('.car').forEach(function (c) {
    var t = c.querySelector('.car-track'), prev = c.querySelector('.prev'), next = c.querySelector('.next');
    var upd = function () { prev.disabled = t.scrollLeft < 8; next.disabled = t.scrollLeft + t.clientWidth >= t.scrollWidth - 8; };
    prev.addEventListener('click', function () { t.scrollBy({ left: -t.clientWidth * 0.9 }); });
    next.addEventListener('click', function () { t.scrollBy({ left: t.clientWidth * 0.9 }); });
    t.addEventListener('scroll', upd, { passive: true }); window.addEventListener('resize', upd); upd();
    c._upd = upd;
  });

  /* ---------- Chips de filtro (por categoria ou apresentação) ---------- */
  document.querySelectorAll('.fchips').forEach(function (g) {
    var scope = g.closest('.shelf') || document;
    var list = scope.querySelector('.car-track') || document.getElementById('lista');
    g.addEventListener('click', function (e) {
      var b = e.target.closest('.fchip'); if (!b) return;
      g.querySelectorAll('.fchip').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      var f = b.dataset.f;
      list.querySelectorAll('.prod').forEach(function (p) { p.hidden = !!f && p.dataset.cat !== f && p.dataset.forma !== f; });
      list.scrollLeft = 0;
      var car = list.closest('.car'); if (car && car._upd) car._upd();
    });
  });

  /* ---------- Busca ---------- */
  var q0 = new URLSearchParams(location.search).get('q') || '';
  var qIn = document.getElementById('q'); if (qIn && q0) qIn.value = q0;
  var lista = document.querySelector('.grid.searchable');
  if (lista) {
    var count = document.getElementById('count'), h1 = document.querySelector('.list-head h1');
    var apply = function (q) {
      var nq = norm(q.trim()), n = 0;
      lista.querySelectorAll('.prod').forEach(function (c) { var ok = !nq || norm(c.dataset.busca).indexOf(nq) > -1; c.hidden = !ok; if (ok) n++; });
      if (nq) { h1.innerHTML = '<span>Busca:</span> ' + q.replace(/[<>&"]/g, ''); count.textContent = n === 0 ? 'Nenhum produto encontrado. Tente outro nome.' : (n === 1 ? '1 produto encontrado' : n + ' produtos encontrados'); }
      else count.textContent = '';
    };
    apply(q0);
    if (qIn) qIn.addEventListener('input', function () { apply(qIn.value); });
  }

  var cards = Array.prototype.slice.call(document.querySelectorAll('.prod'));
  if (cards.length && T.viewList) T.viewList(cards.slice(0, 40).map(function (c) { return { sku: c.dataset.sku, nome: c.dataset.nome, marca: c.dataset.marca, preco: +c.dataset.preco, kit: '1', categoria: c.dataset.cat }; }));

  /* fecha o menu de categorias ao clicar fora */
  document.addEventListener('click', function (e) { document.querySelectorAll('details.dd[open]').forEach(function (d) { if (!d.contains(e.target)) d.open = false; }); });

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
      var ks = document.getElementById('kit-sel'); if (ks) ks.textContent = current.qtd + ' ' + (current.qtd === 1 ? P.unidade : P.unidade_plural);
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
