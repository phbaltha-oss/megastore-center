#!/usr/bin/env python3
"""Gera o site estático da loja a partir de data/produtos.json e config/*.json.

Uso:  python scripts/build.py              -> gera em _site/
      python scripts/build.py --imagens    -> também baixa e otimiza as fotos (usado no GitHub Actions)
"""
import json, os, sys, shutil, html, re, hashlib, datetime
from xml.sax.saxutils import escape as xesc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_site')
E = lambda s: html.escape(str(s), quote=True)

LOJA = json.load(open(os.path.join(ROOT, 'config/loja.json'), encoding='utf-8'))
import base64
_CK = json.load(open(os.path.join(ROOT, 'config/checkout.json'), encoding='utf-8'))
CHECK = dict(_CK.get('links', {}))
# formato compacto da RXPAY: {"produto": {"ref": "...", "ofertas": {"1": "id", ...}}}
for _pid, _d in _CK.get('rxpay', {}).items():
    for _q, _oid in _d.get('ofertas', {}).items():
        CHECK.setdefault(f'{_pid}-k{_q}', 'https://go.rxpay.com.br/?id=' + base64.b64encode(f"{_d['ref']}:{_oid}".encode()).decode())
PRODS = json.load(open(os.path.join(ROOT, 'data/produtos.json'), encoding='utf-8'))
CATS = json.load(open(os.path.join(ROOT, 'config/categorias.json'), encoding='utf-8'))
PRODS.sort(key=lambda p: (-p.get('vendas', 0), p['nome'].lower()))
# ordem da vitrine: produtos liberados para o Google e mais vendidos primeiro
PRODS.sort(key=lambda p: (not p.get('incluir_google_shopping'), -p.get('vendas', 0), p['nome'].lower()))
# fotos: "ml:" é atalho para o CDN do Mercado Livre; kit sem fotos próprias usa as do pote único
for _p in PRODS:
    for _v in _p['variacoes']:
        _v['imagens'] = [('https://http2.mlstatic.com/D_NQ_NP_' + u[3:]) if u.startswith('ml:') else u for u in _v['imagens']] or list(_p['variacoes'][0]['imagens'])
TR = LOJA.get('rastreamento', {})
BASE = (LOJA.get('dominio_proprio') and 'https://' + LOJA['dominio_proprio'].strip('/')) or LOJA['url_site'].rstrip('/')
WA = re.sub(r'\D', '', LOJA.get('whatsapp', ''))
PL = {'pote': 'potes', 'frasco': 'frascos', 'unidade': 'unidades'}
FORMA = {'capsulas': 'Cápsulas', 'liquido': 'Líquido', 'po': 'Pó', 'cosmetico': 'Uso externo', 'outro': '—'}
YEAR = datetime.date.today().year
FRETE = float(LOJA.get('valor_frete', 0) or 0)  # frete único cobrado do cliente (0 = grátis)

def brl(v): return ('R$ %.2f' % v).replace('.', ',')
def money(v): return '%.2f BRL' % v

def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(content)

def img(src, root):
    return src if src.startswith('http') else root + src

# ---------------------------------------------------------------- imagens
def baixar_imagens():
    """Baixa as fotos do catálogo, reduz para 900 px e grava em _site/img.
    Limita a galeria para manter o site leve no GitHub Pages."""
    import urllib.request
    try:
        from PIL import Image
    except ImportError:
        Image = None
    os.makedirs(os.path.join(OUT, 'img'), exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor
    def fetch_one(u):
        nome = 'img/' + hashlib.md5(u.encode()).hexdigest()[:16] + '.jpg'
        dest = os.path.join(OUT, nome)
        try:
            if not os.path.exists(dest):
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
                data = urllib.request.urlopen(req, timeout=20).read()
                open(dest, 'wb').write(data)
                if Image:
                    im = Image.open(dest).convert('RGB'); im.thumbnail((900, 900)); im.save(dest, 'JPEG', quality=82, optimize=True)
            return u, nome
        except Exception:
            return u, u
    wanted = []
    for p in PRODS:
        for v in p['variacoes']:
            lim = 5 if v['qtd'] == 1 else 2
            wanted += [u for u in v['imagens'][:lim] if u.startswith('http')]
    with ThreadPoolExecutor(16) as ex:
        cache = dict(ex.map(fetch_one, sorted(set(wanted))))
    ok = sum(1 for k, v in cache.items() if k != v); fail = len(cache) - ok
    for p in PRODS:
        for v in p['variacoes']:
            lim = 5 if v['qtd'] == 1 else 2
            v['imagens'] = [cache.get(u, u) for u in v['imagens']]
    print(f'imagens: {ok} baixadas, {fail} mantidas como link externo')

# ---------------------------------------------------------------- layout
def track_js():
    return json.dumps({
        'gtm': TR.get('google_tag_manager', ''), 'ga4': TR.get('google_analytics_4', ''),
        'ads': TR.get('google_ads_id', ''), 'adsPurchase': TR.get('google_ads_label_compra', ''),
        'adsCheckout': TR.get('google_ads_label_checkout', ''), 'adsWhatsapp': TR.get('google_ads_label_whatsapp', ''),
        'meta': TR.get('meta_pixel', ''), 'tiktok': TR.get('tiktok_pixel', '')})

ICONS = {
 'truck': '<path d="M3 6h11v9H3zM14 9h4l3 3v3h-7z"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/>',
 'box': '<path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>',
 'card': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/>',
 'shield': '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
 'chat': '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 10h8M8 13h5"/>',
 'doc': '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h7"/>',
 'back': '<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 010 10h-3"/>',
 'search': '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
 'menu': '<path d="M4 7h16M4 12h16M4 17h16"/>',
 'mail': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
}
def ico(n, cls='ico'): return f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[n]}</svg>'

CAT_EMO = {'emagrecimento': '🔥', 'creatinas': '💪', 'energia': '⚡', 'articulacoes': '🦴', 'memoria-sono': '🧠', 'masculina': '🧔',
           'feminina': '🌸', 'cabelo-pele': '✨', 'metabolismo': '⚖️', 'visao': '👁️', 'digestao': '🌿', 'vitaminas': '🍊',
           'bem-estar': '💚', 'cosmeticos': '🧴'}
CAT_BG = ['#E3F4EA', '#FFF1D6', '#E6EEFB', '#FBE6EC', '#EEE7FA', '#E1F3F4', '#F6EEDF']
OBJ = [('articulacoes', 'Articulações'), ('energia', 'Energia'), ('feminina', 'Mulher'), ('masculina', 'Homem'), ('cabelo-pele', 'Pele e cabelo'),
       ('memoria-sono', 'Foco e memória'), ('visao', 'Visão'), ('digestao', 'Intestino'), ('emagrecimento', 'Emagrecimento'), ('vitaminas', 'Imunidade')]
NAV = ['emagrecimento', 'energia', 'articulacoes', 'memoria-sono', 'masculina', 'feminina', 'cabelo-pele', 'vitaminas']

def ccount(k): return sum(1 for p in PRODS if p.get('categoria') == k)

def layout(title, body, root, desc='', canonical='', extra_head='', noindex=False):
    v = []
    if TR.get('google_site_verification'): v.append(f'<meta name="google-site-verification" content="{E(TR["google_site_verification"])}">')
    if TR.get('meta_domain_verification'): v.append(f'<meta name="facebook-domain-verification" content="{E(TR["meta_domain_verification"])}">')
    gtm_ns = f'<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={E(TR["google_tag_manager"])}" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>' if TR.get('google_tag_manager') else ''
    loja_js = json.dumps({'whatsapp': WA, 'email': LOJA.get('email', ''), 'checkout': CHECK})
    nome = LOJA['nome_loja']; a, _, b = nome.partition(' ')
    msgs = [LOJA['frete'], 'Entrega em até 12 dias úteis para todo o Brasil', 'Kits de 2 a 5 unidades com desconto progressivo',
            'Cartão em até 12x, Pix ou boleto', 'Compra 100% segura', 'Atendimento ' + LOJA['horario_atendimento'].lower()]
    ann = ''.join(f'<span>{E(m)}</span>' for m in msgs)
    cats_dd = ''.join(f'<li><a href="{root}categoria/{k}/"><span aria-hidden="true">{CAT_EMO.get(k, "")}</span> {E(n)} <small>{ccount(k)}</small></a></li>' for k, n in CATS.items() if ccount(k))
    navl = ''.join(f'<a href="{root}categoria/{k}/">{E(CATS[k].split(" e ")[0].split(",")[0])}</a>' for k in NAV)
    return f'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc or LOJA['slogan'])}">
{'<meta name="robots" content="noindex">' if noindex else ''}
{f'<link rel="canonical" href="{E(canonical)}">' if canonical else ''}
<meta property="og:title" content="{E(title)}">
<meta property="og:site_name" content="{E(nome)}">
<meta property="og:locale" content="pt_BR">
<meta name="theme-color" content="#0B3B2E">
{''.join(v)}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/style.css">
<script>window.LOJA_ROOT={json.dumps(root)};window.LOJA_TRACK={track_js()};window.LOJA={loja_js};</script>
<script src="{root}assets/tracking.js"></script>
{extra_head}
</head>
<body>
{gtm_ns}
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
<div class="ann" aria-label="Vantagens"><div class="ann-track">{ann}{ann.replace('<span>', '<span aria-hidden="true">')}</div></div>
<header class="hd">
<div class="wrap hd-row">
<a class="logo" href="{root}" aria-label="{E(nome)} – início"><span>{E(a)}</span><b>{E(b)}</b></a>
<form class="search" action="{root}busca/" role="search"><label class="skip" for="q">Buscar produtos</label><input id="q" name="q" type="search" placeholder="O que você procura hoje?" autocomplete="off"><button type="submit">{ico('search')}<span>Buscar</span></button></form>
<div class="hd-help">{ico('mail')}<div><a href="{root}contato/">Atendimento</a><small>{E(LOJA['horario_atendimento'])}</small></div></div>
</div>
<nav class="nv" aria-label="Categorias"><div class="wrap nv-row">
<details class="dd"><summary>{ico('menu')} Categorias</summary><ul>{cats_dd}</ul></details>
{navl}<a href="{root}#mais-vendidos" class="hl">Mais vendidos</a>
</div></nav>
</header>
<main id="conteudo">
{body}
</main>
<footer class="ft">
<div class="wrap ft-grid">
<div><a class="logo" href="{root}"><span>{E(a)}</span><b>{E(b)}</b></a><p>{E(LOJA['slogan'])}.</p>
<p class="ft-h">Formas de pagamento</p><div class="pay"><span>Pix</span><span>Visa</span><span>Mastercard</span><span>Elo</span><span>Boleto</span></div></div>
<div><p class="ft-h">Institucional</p><ul><li><a href="{root}sobre/">Quem somos</a></li><li><a href="{root}contato/">Fale conosco</a></li><li><a href="{root}#mais-vendidos">Mais vendidos</a></li><li><a href="{root}busca/">Todos os produtos</a></li></ul></div>
<div><p class="ft-h">Ajuda</p><ul><li><a href="{root}entrega/">Prazos e entrega</a></li><li><a href="{root}pagamento/">Formas de pagamento</a></li><li><a href="{root}trocas-e-devolucoes/">Trocas e devoluções</a></li></ul></div>
<div><p class="ft-h">Políticas</p><ul><li><a href="{root}politica-de-privacidade/">Privacidade</a></li><li><a href="{root}termos-de-uso/">Termos de uso</a></li><li><a href="{root}trocas-e-devolucoes/">Direito de arrependimento</a></li></ul>
<p class="ft-h">Atendimento</p><p>{E(LOJA['horario_atendimento'])}<br><a href="mailto:{E(LOJA['email'])}">{E(LOJA['email'])}</a>{'<br>' + E(LOJA['telefone']) if LOJA.get('telefone') else ''}</p></div>
</div>
<div class="ft-legal"><div class="wrap"><p>Suplementos alimentares não são medicamentos e não se destinam a diagnosticar, tratar, curar ou prevenir doenças. Consulte um médico ou nutricionista antes de consumir. Imagens ilustrativas; confira sempre o rótulo.</p>
<p>© {YEAR} {E(nome)} · {E(LOJA['razao_social'])} · CNPJ {E(LOJA['cnpj'])} · {E(LOJA['endereco'])}</p></div></div>
</footer>
{f'<a class="wa" data-wa href="https://wa.me/{WA}" target="_blank" rel="noopener">Atendimento no WhatsApp</a>' if WA else ''}
<script src="{root}assets/app.js"></script>
</body></html>'''

# ---------------------------------------------------------------- páginas de produto
def kit_path(p, q): return f"produto/{p['id']}/" if q == 1 else f"produto/{p['id']}/kit-{q}/"

def unid(p, q): return f"{q} {p['unidade'] if q == 1 else PL[p['unidade']]}"

def save_pct(p, v):
    p1 = p['variacoes'][0]['preco']
    return round((1 - v['preco'] / (p1 * v['qtd'])) * 100) if v['qtd'] > 1 else 0

def product_page(p, q):
    root = '../../' if q == 1 else '../../../'
    u = p['unidade']; up = PL[u]
    vs = p['variacoes']; sel = next(v for v in vs if v['qtd'] == q)
    p1 = vs[0]['preco']
    best = max(vs, key=lambda v: save_pct(p, v))
    kits = []
    for v in vs:
        s = save_pct(p, v); qq = v['qtd']
        kits.append(f'''<label class="kr" data-q="{qq}"><input type="radio" name="kit" value="{qq}" {'checked' if qq == q else ''}>
<span class="kr-dot" aria-hidden="true"></span>
<span class="kr-l"><b>{unid(p, qq).upper()}</b><small>{brl(v['preco']/qq)} por {u}</small></span>
<span class="kr-r">{f'<s title="{qq} × {brl(p1)} comprando 1 {u} por vez">{brl(p1*qq)}</s>' if s >= 3 else ''}<b>{brl(v['preco'])}</b>{f'<em>{s}% OFF</em>' if s >= 3 else ''}</span>
{'<i class="kr-tag">Maior economia</i>' if v is best and s >= 3 else ''}</label>''')
    D = p['descricao']
    imgs = [img(x, root) for x in sel['imagens']] or ['']
    thumbs = ''.join(f'<button type="button" aria-label="Ver foto {i+1}" aria-current="{"true" if i==0 else "false"}"><img src="{E(s)}" alt="" loading="lazy" referrerpolicy="no-referrer"></button>' for i, s in enumerate(imgs))
    js = {'id': p['id'], 'marca': p['marca'], 'tipo': p['tipo'], 'unidade': u, 'unidade_plural': up,
          'variacoes': [{'qtd': v['qtd'], 'preco': v['preco'], 'sku': v['sku'], 'titulo': v['titulo'],
                         'imagens': [img(x, root) for x in v['imagens']], 'url': root + kit_path(p, v['qtd'])} for v in vs]}
    url = BASE + '/' + kit_path(p, q)
    offers = [{'@type': 'Offer', 'sku': v['sku'], 'name': v['titulo'], 'price': '%.2f' % v['preco'], 'priceCurrency': 'BRL',
               'availability': 'https://schema.org/InStock', 'itemCondition': 'https://schema.org/NewCondition',
               'url': BASE + '/' + kit_path(p, v['qtd']),
               'shippingDetails': {'@type': 'OfferShippingDetails', 'shippingRate': {'@type': 'MonetaryAmount', 'value': '%.2f' % FRETE, 'currency': 'BRL'},
                                   'shippingDestination': {'@type': 'DefinedRegion', 'addressCountry': 'BR'}},
               'hasMerchantReturnPolicy': {'@type': 'MerchantReturnPolicy', 'applicableCountry': 'BR', 'returnPolicyCategory': 'https://schema.org/MerchantReturnFiniteReturnWindow',
                                           'merchantReturnDays': LOJA.get('prazo_devolucao_dias', 7), 'returnMethod': 'https://schema.org/ReturnByMail', 'returnFees': 'https://schema.org/FreeReturn'}}
              for v in vs]
    ld = {'@context': 'https://schema.org', '@type': 'Product', 'name': sel['titulo'], 'sku': sel['sku'],
          'brand': {'@type': 'Brand', 'name': p['marca']}, 'image': [img(x, BASE + '/') for x in sel['imagens'][:3]],
          'description': D['apresentacao'], 'offers': offers}
    facts = [('Apresentação', FORMA[p['forma']]), ('Conteúdo', f"{p['conteudo']} por {u}" if p['conteudo'] else '—'), ('Marca', p['marca']), ('Condição', 'Novo, lacrado')]
    cat = p.get('categoria', 'bem-estar')
    aviso = ('Este produto é um suplemento alimentar e não é medicamento. Não se destina a diagnosticar, tratar, curar ou prevenir doenças. Resultados variam de pessoa para pessoa.'
             if p['tipo'] == 'suplemento' else 'Produto cosmético de uso externo. Resultados variam de pessoa para pessoa.')
    steps = [('Escolha o seu kit', f'Kits de 2 a 5 {up} saem mais em conta por {u} e garantem a sua rotina por mais tempo.'),
             ('Use como indicado', D['modo_de_uso']),
             ('Guarde bem', 'Mantenha em local seco e fresco, longe da luz e do alcance de crianças. Confira sempre o rótulo.')]
    tiles = ''.join(f'''<a class="kt{' on' if v['qtd']==q else ''}" href="{root}{kit_path(p, v['qtd'])}"><span class="kt-q">{v['qtd']}</span><span>{unid(p, v['qtd'])}</span><b>{brl(v['preco'])}</b><small>{brl(v['preco']/v['qtd'])} por {u}</small>{f'<em>{save_pct(p, v)}% OFF</em>' if save_pct(p, v) >= 3 else ''}</a>''' for v in vs)
    body = f'''<div class="wrap">
<nav class="crumbs" aria-label="Você está em"><a href="{root}">Início</a> › <a href="{root}categoria/{cat}/">{E(CATS.get(cat, ''))}</a> › <span>{E(p['nome'])}</span></nav>
<div class="pp">
<div class="gal"><div class="gal-main"><img id="foto" src="{E(imgs[0])}" alt="{E(sel['titulo'])}" referrerpolicy="no-referrer"></div><div class="thumbs" id="thumbs">{thumbs}</div></div>
<div class="buy">
<p class="brand">{E(p['marca'])}</p>
<h1 id="kit-titulo">{E(sel['titulo'])}</h1>
<p class="sub">{E(FORMA[p['forma']])}{' · ' + E(p['conteudo']) + ' por ' + u if p['conteudo'] else ''}</p>
<fieldset class="kitbox"><legend>Leve mais, pague menos!</legend><p class="kitbox-sub">Selecionado: <b id="kit-sel">{unid(p, q)}</b></p>
{''.join(kits)}</fieldset>
<div class="total"><span>Total</span><b id="preco">{brl(sel['preco'])}</b></div>
<p class="unit" id="preco-unit">{'1 ' + u if q == 1 else brl(sel['preco']/q) + ' por ' + u + ' · ' + str(q) + ' ' + up}</p>
<button class="btn btn-buy" id="comprar" type="button">Comprar</button>
<p class="buy-note">Cartão em até 12x, Pix ou boleto · {E(LOJA['frete'])}</p>
<ul class="trust"><li>{ico('shield')}<span><b>Compra segura</b>Pagamento pela RXPAY</span></li><li>{ico('doc')}<span><b>Nota fiscal</b>Em todos os pedidos</span></li><li>{ico('back')}<span><b>{LOJA.get('prazo_devolucao_dias', 7)} dias</b>Para desistir da compra</span></li></ul>
</div></div>
<section class="card-sec"><h2>Descrição</h2><p>{E(D['apresentacao'])}</p><p>{E(D['kits'])}</p>
<ul class="facts">{''.join(f'<li><span>{a}</span><b>{E(b)}</b></li>' for a, b in facts)}</ul></section>
<section class="know"><div><p class="eyebrow">Conheça o produto</p><h2>{E(p['nome'])}</h2><p>{E(D['composicao'])}</p></div><div class="know-img"><img src="{E(imgs[min(1, len(imgs)-1)])}" alt="" loading="lazy" referrerpolicy="no-referrer"></div></section>
<section class="howto"><h2 class="th"><span>Como</span> usar</h2><ol>{''.join(f'<li><span class="n">{i+1}</span><b>{E(t)}</b><p>{E(d)}</p></li>' for i, (t, d) in enumerate(steps))}</ol></section>
<section class="card-sec"><h2>Advertências</h2><ul>{''.join(f'<li>{E(a)}</li>' for a in D['advertencias'])}</ul><p class="notice">{aviso}</p></section>
<section class="kits-sec"><h2 class="th"><span>Escolha</span> o seu kit</h2><div class="kt-row">{tiles}</div></section>
</div>
<script type="application/json" id="produto-dados">{json.dumps(js, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'''
    return layout(f"{sel['titulo']} | {LOJA['nome_loja']}", body, root, desc=D['apresentacao'], canonical=url,
                  extra_head=f'<meta property="og:image" content="{E(img(sel["imagens"][0], BASE + "/"))}">')

# ---------------------------------------------------------------- catálogo
def card(p, root, extra=''):
    v1 = p['variacoes'][0]; v5 = p['variacoes'][-1]
    s = save_pct(p, v5); top = p.get('mais_vendido')
    return f'''<a class="prod" href="{root}{kit_path(p,1)}" data-busca="{E(p['nome']+' '+p['marca']+' '+' '.join(p['componentes'])+' '+CATS.get(p.get('categoria',''),''))}" data-cat="{p.get('categoria','')}" data-forma="{p['forma']}" data-sku="{v1['sku']}" data-nome="{E(p['nome'])}" data-marca="{E(p['marca'])}" data-preco="{v1['preco']}"{extra}>
<div class="ph">{f'<span class="b-off">Até {s}% OFF</span>' if s >= 3 else ''}{f'<span class="b-top">TOP {top}</span>' if top else ''}<img src="{E(img(v1['imagens'][0], root))}" alt="{E(p['nome'])}" loading="lazy" referrerpolicy="no-referrer"></div>
<div class="bd"><h3>{E(p['nome'])}</h3>
<p class="pr"><small>1 {p['unidade']} por</small><b>{brl(v1['preco'])}</b></p>
<p class="kit5">Kit com {v5['qtd']}: <b>{brl(v5['preco'])}</b></p>
<span class="btn btn-card">Comprar</span></div></a>'''

def shelf(sid, title, ps, root, chips=None, more='', emo='', limit=16):
    ch = ''
    if chips:
        ch = '<div class="fchips" role="group" aria-label="Filtrar">' + '<button type="button" class="fchip" aria-pressed="true" data-f="">Todos</button>' + \
             ''.join(f'<button type="button" class="fchip" aria-pressed="false" data-f="{k}">{E(n)}</button>' for k, n in chips) + '</div>'
    h = f'<span class="emo" aria-hidden="true">{emo}</span>' if emo else ''
    t1, _, t2 = title.partition(' ')
    return f'''<section class="shelf" id="{sid}"><div class="sh-head"><h2 class="th">{h}<span>{E(t1)}</span> {E(t2)}</h2>{f'<a class="more" href="{more}">Ver todos ›</a>' if more else ''}</div>{ch}
<div class="car"><button type="button" class="car-b prev" aria-label="Anteriores">‹</button><div class="car-track">{''.join(card(p, root) for p in ps[:limit])}</div><button type="button" class="car-b next" aria-label="Próximos">›</button></div></section>'''

def benefits():
    b = [(('truck', 'Frete fixo', brl(FRETE) + ' para todo o Brasil') if FRETE else ('truck', 'Frete grátis', 'Para todo o Brasil')), ('box', 'Kits com desconto', 'De 2 a 5 unidades'), ('card', 'Até 12x', 'No cartão de crédito'),
         ('shield', 'Compra segura', 'Pagamento protegido'), ('chat', 'Atendimento', 'Seg. a sex., 9h às 18h')]
    return '<section class="bens">' + ''.join(f'<div class="ben"><span class="ben-i">{ico(i)}</span><span><b>{t}</b><small>{s}</small></span></div>' for i, t, s in b) + '</section>'

def home():
    root = ''
    top = sorted([p for p in PRODS if p.get('mais_vendido')], key=lambda p: p['mais_vendido'])
    slides = []
    for i, p in enumerate(top[:4]):
        v1 = p['variacoes'][0]; v5 = p['variacoes'][-1]
        slides.append(f'''<div class="slide{' on' if i == 0 else ''}" role="group" aria-roledescription="slide" aria-label="{i+1} de {min(4, len(top))}">
<div class="sl-txt"><span class="pill">Destaque</span><h2>{E(p['nome'])}</h2><p>{E(p['descricao']['apresentacao'][:150].rsplit(' ', 1)[0])}…</p>
<p class="sl-price">Leve mais e pague menos: <b>kit com {v5['qtd']} por {brl(v5['preco'])}</b></p><a class="btn btn-hero" href="{kit_path(p, 1)}">Ver produto</a></div>
<div class="sl-img"><img src="{E(img(v1['imagens'][0], root))}" alt="{E(p['nome'])}" {'' if i == 0 else 'loading="lazy"'} referrerpolicy="no-referrer"></div></div>''')
    hero = f'''<section class="hero" aria-roledescription="carrossel" aria-label="Destaques">{''.join(slides)}
<button type="button" class="hero-b prev" aria-label="Anterior">‹</button><button type="button" class="hero-b next" aria-label="Próximo">›</button>
<div class="dots">{''.join(f'<button type="button" aria-label="Destaque {i+1}" aria-current="{"true" if i == 0 else "false"}"></button>' for i in range(len(slides)))}</div></section>'''
    cats = [(k, n) for k, n in CATS.items() if ccount(k)]
    def first_img(k):
        p = next(p for p in PRODS if p.get('categoria') == k)
        return img(p['variacoes'][0]['imagens'][0], root)
    ccards = ''.join(f'''<a class="cc" href="categoria/{k}/"><span class="cc-i" style="background:{CAT_BG[i % len(CAT_BG)]}"><img src="{E(first_img(k))}" alt="" loading="lazy" referrerpolicy="no-referrer"></span><b>{E(n)}</b><small>{ccount(k)} produtos</small></a>''' for i, (k, n) in enumerate(cats))
    top_cats = []
    for p in top:
        c = p.get('categoria')
        if c not in [x for x, _ in top_cats]: top_cats.append((c, CATS[c].split(' e ')[0].split(',')[0]))
    best = shelf('mais-vendidos', 'Os mais vendidos', top, root, chips=top_cats, emo='🏆')
    promos = f'''<section class="promos"><a class="promo p1" href="#mais-vendidos"><small>Leve mais, pague menos</small><b>Kits de 2 a 5 unidades</b><span>Até 25% de desconto por unidade</span></a>
<a class="promo p2" href="entrega/"><small>Para todo o Brasil</small><b>{E(LOJA['frete'])}</b><span>Entrega em até 12 dias úteis</span></a></section>'''
    secs = []
    for k, n in cats:
        ps = [p for p in PRODS if p.get('categoria') == k and not p.get('mais_vendido')] or [p for p in PRODS if p.get('categoria') == k]
        formas = [f for f in FORMA if f != 'outro' and sum(1 for p in ps[:16] if p['forma'] == f) and len({p['forma'] for p in ps[:16]}) > 1]
        secs.append(shelf(k, n, ps, root, chips=[(f, FORMA[f]) for f in formas] or None, more=f'categoria/{k}/', emo=CAT_EMO.get(k, '')))
    mid = len(secs) // 2
    obj = ''.join(f'<a class="obj" href="categoria/{k}/"><span aria-hidden="true">{CAT_EMO[k]}</span><b>{E(n)}</b></a>' for k, n in OBJ if ccount(k))
    objs = f'<section class="objs"><div class="sh-head"><h2 class="th"><span>Compre</span> por objetivo</h2></div><div class="obj-row">{obj}</div></section>'
    cta = f'''<section class="cta"><div><small>Compra protegida do início ao fim</small><b>Pix, cartão em até 12x ou boleto</b><p>Pagamento processado pela RXPAY, nota fiscal em todos os pedidos e {LOJA.get('prazo_devolucao_dias', 7)} dias para desistir da compra.</p></div><a class="btn btn-hero" href="pagamento/">Saiba mais</a></section>'''
    body = f'''<div class="wrap">
{hero}
{benefits()}
<section class="cats"><div class="sh-head"><h2 class="th"><span>Compre</span> por categoria</h2><a class="more" href="busca/">Ver todos ›</a></div><div class="cc-row">{ccards}</div></section>
{best}
{promos}
{''.join(secs[:mid])}
{objs}
{''.join(secs[mid:])}
{cta}
</div>'''
    ld = {'@context': 'https://schema.org', '@type': 'Organization', 'name': LOJA['nome_loja'], 'legalName': LOJA['razao_social'],
          'url': BASE + '/', 'email': LOJA['email'], 'telephone': LOJA['telefone'], 'taxID': LOJA['cnpj'],
          'address': {'@type': 'PostalAddress', 'streetAddress': LOJA['endereco'], 'addressCountry': 'BR'}}
    write('index.html', layout(f"{LOJA['nome_loja']} | Suplementos e cuidados diários", body, root, canonical=BASE + '/',
                               extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'))

def grid_page(root, title, ps, crumbs, chips_html='', intro='', search=False):
    return f'''<div class="wrap"><nav class="crumbs" aria-label="Você está em"><a href="{root}">Início</a> › {crumbs}</nav>
<section class="list-head"><h1 class="th">{title}</h1>{f'<p>{intro}</p>' if intro else ''}{chips_html}<p class="count" id="count" aria-live="polite"></p></section>
<div class="grid{' searchable' if search else ''}" id="lista">{''.join(card(p, root) for p in ps)}</div></div>'''

def category_pages():
    root = '../../'
    for k, n in CATS.items():
        ps = [p for p in PRODS if p.get('categoria') == k]
        if not ps: continue
        formas = [f for f in FORMA if f != 'outro' and any(p['forma'] == f for p in ps)]
        ch = ''
        if len(formas) > 1:
            ch = '<div class="fchips" role="group" aria-label="Filtrar"><button type="button" class="fchip" aria-pressed="true" data-f="">Todos</button>' + \
                 ''.join(f'<button type="button" class="fchip" aria-pressed="false" data-f="{f}">{FORMA[f]}</button>' for f in formas) + '</div>'
        others = ''.join(f'<a class="chip" href="../{x}/">{CAT_EMO.get(x, "")} {E(m)}</a>' for x, m in CATS.items() if x != k and ccount(x))
        body = grid_page(root, f'<span class="emo" aria-hidden="true">{CAT_EMO.get(k, "")}</span>{E(n)}', ps, E(n), ch, f'{len(ps)} produtos em kits de 1 a 5 unidades. Quanto maior o kit, menor o preço por unidade.')
        body += f'<div class="wrap other-cats"><h2 class="th"><span>Outras</span> categorias</h2><nav class="chips">{others}</nav></div>'
        write(f'categoria/{k}/index.html', layout(f"{n} | {LOJA['nome_loja']}", body, root, desc=f"{n}: {len(ps)} produtos em kits de 1 a 5 unidades na {LOJA['nome_loja']}.", canonical=f'{BASE}/categoria/{k}/'))
    root = '../'
    body = grid_page(root, '<span>Todos</span> os produtos', PRODS, 'Busca', '', f'{len(PRODS)} produtos. Use a busca no topo para filtrar pelo nome, ingrediente ou categoria.', search=True)
    write('busca/index.html', layout(f"Buscar produtos | {LOJA['nome_loja']}", body, root, canonical=f'{BASE}/busca/'))


def pages():
    L = LOJA; dias = L.get('prazo_devolucao_dias', 7)
    contato = f'''<dl><dt>Empresa</dt><dd>{E(L['razao_social'])}</dd><dt>CNPJ</dt><dd>{E(L['cnpj'])}</dd><dt>Endereço</dt><dd>{E(L['endereco'])}</dd>
<dt>E-mail</dt><dd><a href="mailto:{E(L['email'])}">{E(L['email'])}</a></dd>{f"<dt>Telefone</dt><dd>{E(L['telefone'])}</dd>" if L.get('telefone') else ''}
{f'<dt>WhatsApp</dt><dd><a data-wa href="https://wa.me/{WA}" target="_blank" rel="noopener">Conversar no WhatsApp</a></dd>' if WA else ''}<dt>Horário</dt><dd>{E(L['horario_atendimento'])}</dd></dl>'''
    P = {
     'sobre': ('Quem somos', f'''<p>A {E(L['nome_loja'])} é uma loja on-line de suplementos alimentares e produtos de cuidado pessoal, operada por {E(L['razao_social'])}, CNPJ {E(L['cnpj'])}.</p>
<p>Vendemos produtos novos e lacrados, enviados na embalagem original do fabricante, com rótulo, lote e validade. As informações de cada produto seguem o que consta no rótulo; quando houver diferença, vale o rótulo.</p>
<p>Suplementos alimentares complementam a alimentação e não substituem medicamentos nem acompanhamento profissional. Se você tem alguma condição de saúde, usa medicamentos, está grávida ou amamentando, fale com seu médico ou nutricionista antes de consumir.</p><h2>Fale com a gente</h2>{contato}'''),
     'contato': ('Contato', f'<p>Respondemos em até 1 dia útil.</p>{contato}'),
     'entrega': ('Prazos e entrega', f'''<p><b>{E(L['frete'])}.</b></p><ul><li>{E(L['prazo_envio'])}.</li><li>Prazo de entrega: {E(L['prazo_entrega'])}, contado a partir da postagem.</li><li>Enviamos o código de rastreio por e-mail ou WhatsApp assim que o pedido é postado.</li><li>Entregamos em todo o território brasileiro.</li></ul>
<h2>Problemas na entrega</h2><p>Se o pedido não chegar no prazo ou chegar avariado, fale com a gente pelo contato abaixo. Reenviamos o produto ou devolvemos o valor pago.</p>{contato}'''),
     'pagamento': ('Formas de pagamento', f'''<p>{E(L['formas_pagamento'])}.</p><ul><li><b>Pix:</b> aprovação em poucos minutos.</li><li><b>Cartão de crédito:</b> as condições de parcelamento aparecem no checkout antes da confirmação.</li><li><b>Boleto:</b> aprovação em até 3 dias úteis após o pagamento.</li></ul>
<p>O pagamento é feito em ambiente seguro da RXPAY. Nós não armazenamos dados de cartão.</p>'''),
     'trocas-e-devolucoes': ('Trocas e devoluções', f'''<h2>Direito de arrependimento</h2><p>Você pode desistir da compra em até {dias} dias corridos após receber o pedido, conforme o artigo 49 do Código de Defesa do Consumidor. Devolvemos 100% do valor pago, incluindo o frete, pelo mesmo meio de pagamento.</p>
<h2>Produto com defeito ou divergente</h2><p>Se o produto chegar violado, avariado, vencido ou diferente do pedido, avise em até 30 dias. Enviamos um novo ou devolvemos o valor, à sua escolha.</p>
<h2>Como solicitar</h2><ol><li>Fale com a gente pelo e-mail ou WhatsApp informando o número do pedido.</li><li>Enviamos as instruções e o código de postagem reversa sem custo.</li><li>O reembolso é feito em até 10 dias úteis após recebermos o produto. No cartão, o estorno aparece em até 2 faturas.</li></ol>
<p>Por segurança alimentar, produtos abertos só são aceitos de volta em caso de defeito.</p>{contato}'''),
     'politica-de-privacidade': ('Política de privacidade', f'''<p>Esta política explica como {E(L['razao_social'])} (CNPJ {E(L['cnpj'])}) trata dados pessoais, conforme a Lei Geral de Proteção de Dados (Lei 13.709/2018).</p>
<h2>Dados que coletamos</h2><ul><li>Dados do pedido: nome, CPF, e-mail, telefone e endereço, informados no checkout para entrega e emissão de nota fiscal.</li><li>Dados de navegação: páginas visitadas, dispositivo e origem da visita, por meio de cookies, somente após o seu aceite.</li></ul>
<h2>Para que usamos</h2><ul><li>Processar e entregar pedidos e prestar atendimento.</li><li>Cumprir obrigações legais e fiscais.</li><li>Medir o desempenho do site e de anúncios (Google Analytics, Google Ads, Meta e TikTok), apenas com consentimento.</li></ul>
<h2>Compartilhamento</h2><p>Compartilhamos dados apenas com quem precisa deles para concluir sua compra: processador de pagamento (RXPAY), transportadoras e plataformas de medição, quando autorizadas. Não vendemos dados pessoais.</p>
<h2>Cookies</h2><p>Na primeira visita, você escolhe se aceita cookies de medição e publicidade. Para mudar a escolha, limpe os dados do site no seu navegador.</p>
<h2>Seus direitos</h2><p>Você pode pedir acesso, correção, portabilidade ou exclusão dos seus dados pelo e-mail <a href="mailto:{E(L['email'])}">{E(L['email'])}</a>.</p>'''),
     'termos-de-uso': ('Termos de uso', f'''<p>Ao comprar em {E(L['nome_loja'])}, você concorda com estes termos.</p><ul><li>Os preços e a disponibilidade podem mudar sem aviso; vale o valor exibido no momento da compra.</li><li>As fotos são ilustrativas. As informações de composição e uso que valem são as do rótulo do produto.</li>
<li>Os suplementos vendidos não são medicamentos e não se destinam a diagnosticar, tratar, curar ou prevenir doenças.</li><li>Vendemos apenas para maiores de 18 anos.</li><li>Trocas e devoluções seguem a nossa <a href="../trocas-e-devolucoes/">política de trocas</a> e o Código de Defesa do Consumidor.</li></ul>
<p>Empresa responsável: {E(L['razao_social'])}, CNPJ {E(L['cnpj'])}, {E(L['endereco'])}.</p>'''),
    }
    for slug_, (t, c) in P.items():
        write(f'{slug_}/index.html', layout(f"{t} | {L['nome_loja']}", f'<div class="wrap page prose"><h1>{t}</h1>{c}</div>', '../', canonical=f'{BASE}/{slug_}/'))
    ob = f'''<div class="wrap page prose" id="obrigado"><h1>Pedido recebido</h1><p>Obrigado pela compra. Número do pedido: <b data-pedido>—</b>.</p>
<p>Você vai receber a confirmação e o código de rastreio por e-mail ou WhatsApp. {E(L['prazo_envio'])}.</p><p><a class="btn-sec" href="../">Voltar para a loja</a></p></div>'''
    write('obrigado/index.html', layout(f"Pedido recebido | {L['nome_loja']}", ob, '../', noindex=True))
    write('404.html', layout('Página não encontrada', f'<div class="wrap page prose"><h1>Esta página não existe</h1><p>O produto pode ter mudado de endereço. <a href="{BASE}/">Veja todos os produtos</a>.</p></div>', BASE + '/', noindex=True))

# ---------------------------------------------------------------- feeds, sitemap
GCAT_SUP = 'Health & Beauty > Health Care > Fitness & Nutrition > Vitamins & Supplements'
GCAT_COS = 'Health & Beauty > Personal Care > Cosmetics > Skin Care'

def feed():
    items = []
    for p in PRODS:
        if not p.get('incluir_google_shopping'):
            continue
        for v in p['variacoes']:
            imgs = [img(x, BASE + '/') for x in v['imagens']]
            desc = ' '.join([p['descricao']['apresentacao'], p['descricao']['composicao'], p['descricao']['kits'], 'Não é medicamento.' if p['tipo'] == 'suplemento' else ''])
            f = [('g:id', v['sku']), ('g:title', v['titulo'][:150]), ('g:description', desc[:5000]),
                 ('g:link', BASE + '/' + kit_path(p, v['qtd'])), ('g:image_link', imgs[0])]
            f += [('g:additional_image_link', x) for x in imgs[1:10]]
            f += [('g:availability', 'in_stock'), ('g:price', money(v['preco'])), ('g:condition', 'new'),
                  ('g:brand', p['marca']), ('g:identifier_exists', 'no'), ('g:mpn', v['sku']),
                  ('g:item_group_id', p['id']), ('g:google_product_category', GCAT_SUP if p['tipo'] == 'suplemento' else GCAT_COS),
                  ('g:product_type', ('Suplementos alimentares' if p['tipo'] == 'suplemento' else 'Cosméticos') + ' > ' + CATS.get(p.get('categoria', ''), 'Bem-estar geral')),
                  ('g:custom_label_2', p.get('categoria', '')),
                  ('g:is_bundle', 'yes' if v['qtd'] > 1 else 'no'), ('g:custom_label_0', 'kit-' + str(v['qtd'])),
                  ('g:age_group', 'adult')]
            if v['qtd'] > 1: f.append(('g:multipack', str(v['qtd'])))
            if p.get('adulto'): f.append(('g:adult', 'yes'))
            f.append(('g:shipping', None))
            parts = []
            for k, val in f:
                if k == 'g:shipping':
                    parts.append('<g:shipping><g:country>BR</g:country><g:service>Padrão</g:service><g:price>' + ('%.2f' % FRETE) + ' BRL</g:price></g:shipping>')
                else:
                    parts.append(f'<{k}>{xesc(str(val))}</{k}>')
            items.append('<item>' + ''.join(parts) + '</item>')
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0"><channel><title>{xesc(LOJA['nome_loja'])}</title><link>{BASE}/</link><description>Feed de produtos</description>
{chr(10).join(items)}
</channel></rss>'''
    write('feeds/google-merchant.xml', xml)
    return len(items)

def sitemap():
    urls = [BASE + '/'] + [f'{BASE}/categoria/{k}/' for k in CATS] + [f'{BASE}/{s}/' for s in ['sobre', 'contato', 'entrega', 'pagamento', 'trocas-e-devolucoes', 'politica-de-privacidade', 'termos-de-uso']]
    for p in PRODS:
        urls += [BASE + '/' + kit_path(p, v['qtd']) for v in p['variacoes']]
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{xesc(u)}</loc></url>' for u in urls) + '</urlset>')
    write('robots.txt', f'User-agent: *\nAllow: /\nDisallow: /obrigado/\nSitemap: {BASE}/sitemap.xml\n')

# ---------------------------------------------------------------- main
def main():
    if os.path.exists(OUT):
        for n in os.listdir(OUT):
            if n == 'img': continue
            fp = os.path.join(OUT, n)
            shutil.rmtree(fp) if os.path.isdir(fp) else os.remove(fp)
    os.makedirs(OUT, exist_ok=True)
    shutil.copytree(os.path.join(ROOT, 'assets'), os.path.join(OUT, 'assets'))
    # Paginas de venda avulsas (ex.: assets/zerohair) tambem em /<nome>/
    zh = os.path.join(ROOT, 'assets', 'zerohair')
    if os.path.isdir(zh):
        shutil.copytree(zh, os.path.join(OUT, 'zerohair'))
    if '--imagens' in sys.argv:
        baixar_imagens()
    home(); category_pages(); pages()
    n = 0
    for p in PRODS:
        for v in p['variacoes']:
            write(kit_path(p, v['qtd']) + 'index.html', product_page(p, v['qtd'])); n += 1
    nf = feed(); sitemap()
    open(os.path.join(OUT, '.nojekyll'), 'w').close()
    if LOJA.get('dominio_proprio'):
        open(os.path.join(OUT, 'CNAME'), 'w').write(LOJA['dominio_proprio'].strip())
    pend = [k for k, v in LOJA.items() if isinstance(v, str) and '[PREENCHER]' in v]
    sem_link = sum(1 for p in PRODS for v in p['variacoes'] if v['sku'] not in CHECK)
    print(f'OK: {len(PRODS)} produtos, {n} páginas de kit, {nf} itens no feed do Google.')
    if pend: print('ATENÇÃO: preencha em config/loja.json ->', ', '.join(pend))
    if sem_link: print(f'ATENÇÃO: {sem_link} SKUs sem link da RXPAY em config/checkout.json (botão abre WhatsApp).')

if __name__ == '__main__':
    main()
