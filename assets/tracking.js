/* Rastreamento de conversões: GTM, GA4, Google Ads, Meta Pixel e TikTok.
   - Consentimento (LGPD) com Google Consent Mode v2: nada de anúncio é gravado antes do aceite.
   - Guarda gclid / gbraid / wbraid / fbclid / ttclid / UTMs e repassa ao checkout.
   - Eventos padrão GA4 de e-commerce no dataLayer (servem para GTM também).
   Os IDs vêm de window.LOJA_TRACK (gerado a partir de config/loja.json). */
(function () {
  var T = window.LOJA_TRACK || {};
  var w = window, d = document;
  w.dataLayer = w.dataLayer || [];
  function gtag() { w.dataLayer.push(arguments); }
  w.gtag = w.gtag || gtag;

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  function load(src) { var s = d.createElement('script'); s.async = true; s.src = src; d.head.appendChild(s); }

  /* ---------- Consentimento ---------- */
  var consent = store('lgpd_consent'); // 'granted' | 'denied' | null
  gtag('consent', 'default', {
    ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
    analytics_storage: 'denied', functionality_storage: 'granted', security_storage: 'granted',
    wait_for_update: 500
  });
  gtag('set', 'ads_data_redaction', true);
  gtag('set', 'url_passthrough', true);
  if (consent === 'granted') grant(false);

  function grant(save) {
    gtag('consent', 'update', { ad_storage: 'granted', ad_user_data: 'granted', ad_personalization: 'granted', analytics_storage: 'granted' });
    if (save) store('lgpd_consent', 'granted');
    if (w.fbq) fbq('consent', 'grant');
    w.dataLayer.push({ event: 'consent_granted' });
  }

  /* ---------- Tags ---------- */
  if (T.gtm) {
    w.dataLayer.push({ 'gtm.start': Date.now(), event: 'gtm.js' });
    load('https://www.googletagmanager.com/gtm.js?id=' + T.gtm);
  }
  var gtagId = T.ga4 || T.ads;
  if (gtagId) {
    load('https://www.googletagmanager.com/gtag/js?id=' + gtagId);
    gtag('js', new Date());
    if (T.ga4) gtag('config', T.ga4);
    if (T.ads) gtag('config', T.ads, { allow_enhanced_conversions: true });
  }
  if (T.meta) {
    !function (f, b, e, v, n, t, s) { if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments) }; if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = []; t = b.createElement(e); t.async = !0; t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s) }(w, d, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    if (consent !== 'granted') fbq('consent', 'revoke');
    fbq('init', T.meta); fbq('track', 'PageView');
  }
  if (T.tiktok) {
    !function (w, d, t) { w.TiktokAnalyticsObject = t; var ttq = w[t] = w[t] || []; ttq.methods = ["page", "track", "identify", "instances", "debug", "on", "off", "once", "ready", "alias", "group", "enableCookie", "disableCookie", "holdConsent", "revokeConsent", "grantConsent"]; ttq.setAndDefer = function (t, e) { t[e] = function () { t.push([e].concat(Array.prototype.slice.call(arguments, 0))) } }; for (var i = 0; i < ttq.methods.length; i++)ttq.setAndDefer(ttq, ttq.methods[i]); ttq.load = function (e) { var i = "https://analytics.tiktok.com/i18n/pixel/events.js"; ttq._i = ttq._i || {}; ttq._i[e] = []; ttq._i[e]._u = i; var o = d.createElement("script"); o.async = !0; o.src = i + "?sdkid=" + e + "&lib=" + t; var a = d.getElementsByTagName("script")[0]; a.parentNode.insertBefore(o, a) }; ttq.load(T.tiktok); ttq.page() }(w, d, 'ttq');
  }

  /* ---------- Origem do clique (atribuição) ---------- */
  var KEYS = ['gclid', 'gbraid', 'wbraid', 'fbclid', 'ttclid', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];
  var qs = new URLSearchParams(location.search);
  KEYS.forEach(function (k) { var v = qs.get(k); if (v) store('attr_' + k, v); });
  if (qs.get('fbclid') && !store('attr_fbc')) store('attr_fbc', 'fb.1.' + Date.now() + '.' + qs.get('fbclid'));

  function withAttribution(url) {
    try {
      var u = new URL(url);
      KEYS.forEach(function (k) { var v = store('attr_' + k); if (v && !u.searchParams.has(k)) u.searchParams.set(k, v); });
      return u.toString();
    } catch (e) { return url; }
  }

  /* ---------- Eventos ---------- */
  function ecom(event, payload) {
    w.dataLayer.push({ ecommerce: null });
    w.dataLayer.push({ event: event, ecommerce: payload });
    if (!T.gtm && gtagId) gtag('event', event, payload);
  }
  function item(p) {
    return { item_id: p.sku, item_name: p.nome, item_brand: p.marca, item_variant: p.kit, item_category: p.categoria, price: p.preco, quantity: 1 };
  }

  var Track = {
    withAttribution: withAttribution,
    viewList: function (list) { ecom('view_item_list', { item_list_name: 'Catálogo', items: list.slice(0, 50).map(item) }); },
    viewItem: function (p) {
      ecom('view_item', { currency: 'BRL', value: p.preco, items: [item(p)] });
      if (w.fbq) fbq('track', 'ViewContent', { content_ids: [p.sku], content_type: 'product', value: p.preco, currency: 'BRL' });
      if (w.ttq) ttq.track('ViewContent', { content_id: p.sku, value: p.preco, currency: 'BRL' });
    },
    selectKit: function (p) {
      w.dataLayer.push({ event: 'select_kit', kit: p.kit, sku: p.sku, value: p.preco });
      if (!T.gtm && gtagId) gtag('event', 'select_kit', { item_id: p.sku, value: p.preco, currency: 'BRL' });
    },
    beginCheckout: function (p) {
      store('last_checkout', JSON.stringify({ sku: p.sku, valor: p.preco, nome: p.nome }));
      ecom('begin_checkout', { currency: 'BRL', value: p.preco, items: [item(p)] });
      if (T.ads && T.adsCheckout) gtag('event', 'conversion', { send_to: T.ads + '/' + T.adsCheckout, value: p.preco, currency: 'BRL' });
      if (w.fbq) fbq('track', 'InitiateCheckout', { content_ids: [p.sku], value: p.preco, currency: 'BRL', num_items: 1 });
      if (w.ttq) ttq.track('InitiateCheckout', { content_id: p.sku, value: p.preco, currency: 'BRL' });
    },
    whatsapp: function (p) {
      w.dataLayer.push({ event: 'generate_lead', method: 'whatsapp', value: p ? p.preco : 0 });
      if (!T.gtm && gtagId) gtag('event', 'generate_lead', { currency: 'BRL', value: p ? p.preco : 0 });
      if (T.ads && T.adsWhatsapp) gtag('event', 'conversion', { send_to: T.ads + '/' + T.adsWhatsapp });
      if (w.fbq) fbq('track', 'Contact');
      if (w.ttq) ttq.track('Contact');
    },
    /* Chamado na página /obrigado/. Lê os parâmetros enviados pela RXPAY. */
    purchase: function () {
      var q = new URLSearchParams(location.search);
      var last = {}; try { last = JSON.parse(store('last_checkout') || '{}'); } catch (e) { }
      var id = q.get('pedido') || q.get('order_id') || q.get('transaction_id') || q.get('id') || ('web-' + Date.now());
      var valor = parseFloat((q.get('valor') || q.get('value') || q.get('amount') || last.valor || '0').toString().replace(',', '.'));
      var sku = q.get('sku') || last.sku || '';
      if (store('purchase_' + id)) return { id: id, valor: valor, duplicado: true };
      store('purchase_' + id, '1');
      var email = q.get('email'), phone = q.get('telefone') || q.get('phone');
      if (email || phone) gtag('set', 'user_data', { email: email || undefined, phone_number: phone || undefined });
      ecom('purchase', { transaction_id: id, currency: 'BRL', value: valor, items: [{ item_id: sku, item_name: last.nome || sku, price: valor, quantity: 1 }] });
      if (T.ads && T.adsPurchase) gtag('event', 'conversion', { send_to: T.ads + '/' + T.adsPurchase, value: valor, currency: 'BRL', transaction_id: id });
      if (w.fbq) fbq('track', 'Purchase', { value: valor, currency: 'BRL', content_ids: [sku], content_type: 'product' }, { eventID: id });
      if (w.ttq) ttq.track('CompletePayment', { content_id: sku, value: valor, currency: 'BRL' });
      return { id: id, valor: valor };
    }
  };
  w.Track = Track;

  /* ---------- Aviso de cookies ---------- */
  function banner() {
    if (consent) return;
    var b = d.createElement('div');
    b.className = 'cookie';
    b.setAttribute('role', 'dialog');
    b.setAttribute('aria-label', 'Cookies');
    b.innerHTML = '<p>Usamos cookies para medir visitas e anúncios. Você escolhe se aceita. <a href="' + (w.LOJA_ROOT || '/') + 'politica-de-privacidade/">Política de privacidade</a></p>' +
      '<div><button type="button" class="btn-sec" data-c="no">Recusar</button><button type="button" class="btn" data-c="yes">Aceitar cookies</button></div>';
    b.addEventListener('click', function (e) {
      var c = e.target.getAttribute('data-c'); if (!c) return;
      if (c === 'yes') grant(true); else store('lgpd_consent', 'denied');
      consent = c; b.remove();
    });
    d.body.appendChild(b);
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', banner); else banner();
})();
