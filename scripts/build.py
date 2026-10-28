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
CHECK = json.load(open(os.path.join(ROOT, 'config/checkout.json'), encoding='utf-8')).get('links', {})
PRODS = json.load(open(os.path.join(ROOT, 'data/produtos.json'), encoding='utf-8'))
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
    cache = {}
    ok = fail = 0
    for p in PRODS:
        for v in p['variacoes']:
            lim = 5 if v['qtd'] == 1 else 2
            novas = []
            for i, u in enumerate(v['imagens']):
                if i >= lim or not u.startswith('http'):
                    novas.append(u); continue
                if u in cache:
                    novas.append(cache[u]); continue
                nome = 'img/' + hashlib.md5(u.encode()).hexdigest()[:16] + '.jpg'
                dest = os.path.join(OUT, nome)
                try:
                    if not os.path.exists(dest):
                        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
                        data = urllib.request.urlopen(req, timeout=20).read()
                        open(dest, 'wb').write(data)
                        if Image:
                            im = Image.open(dest).convert('RGB')
                            im.thumbnail((900, 900))
                            im.save(dest, 'JPEG', quality=82, optimize=True)
                    cache[u] = nome; novas.append(nome); ok += 1
                except Exception as e:
                    cache[u] = u; novas.append(u); fail += 1
            v['imagens'] = novas
    print(f'imagens: {ok} baixadas, {fail} mantidas como link externo')

# ---------------------------------------------------------------- layout
def track_js():
    return json.dumps({
        'gtm': TR.get('google_tag_manager', ''), 'ga4': TR.get('google_analytics_4', ''),
        'ads': TR.get('google_ads_id', ''), 'adsPurchase': TR.get('google_ads_label_compra', ''),
        'adsCheckout': TR.get('google_ads_label_checkout', ''), 'adsWhatsapp': TR.get('google_ads_label_whatsapp', ''),
        'meta': TR.get('meta_pixel', ''), 'tiktok': TR.get('tiktok_pixel', '')})

def layout(title, body, root, desc='', canonical='', extra_head='', noindex=False):
    v = []
    if TR.get('google_site_verification'): v.append(f'<meta name="google-site-verification" content="{E(TR["google_site_verification"])}">')
    if TR.get('meta_domain_verification'): v.append(f'<meta name="facebook-domain-verification" content="{E(TR["meta_domain_verification"])}">')
    gtm_ns = f'<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={E(TR["google_tag_manager"])}" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>' if TR.get('google_tag_manager') else ''
    loja_js = json.dumps({'whatsapp': WA, 'email': LOJA.get('email', ''), 'checkout': CHECK})
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
<meta property="og:site_name" content="{E(LOJA['nome_loja'])}">
<meta property="og:locale" content="pt_BR">
{''.join(v)}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/style.css">
<script>window.LOJA_ROOT={json.dumps(root)};window.LOJA_TRACK={track_js()};window.LOJA={loja_js};</script>
<script src="{root}assets/tracking.js"></script>
{extra_head}
</head>
<body>
{gtm_ns}
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
<header class="top"><div class="wrap">
<a class="logo" href="{root}">{E(LOJA['nome_loja'])}</a>
<nav aria-label="Principal"><a href="{root}">Produtos</a><a href="{root}entrega/">Entrega</a><a href="{root}trocas-e-devolucoes/">Trocas</a><a href="{root}contato/">Contato</a></nav>
</div></header>
<div class="strip"><div class="wrap"><span>{E(LOJA['frete'])}</span><span>Pagamento por {E(LOJA['formas_pagamento'].split(',')[0])}, cartão ou boleto</span><span>CNPJ {E(LOJA['cnpj'])}</span></div></div>
<main id="conteudo">
{body}
</main>
<footer class="foot"><div class="wrap">
<div><h3>{E(LOJA['nome_loja'])}</h3><p>{E(LOJA['razao_social'])}<br>CNPJ {E(LOJA['cnpj'])}<br>{E(LOJA['endereco'])}</p>
<p>Atendimento: {E(LOJA['horario_atendimento'])}<br><a href="mailto:{E(LOJA['email'])}">{E(LOJA['email'])}</a>{' · ' + E(LOJA['telefone']) if LOJA.get('telefone') else ''}</p></div>
<div><h3>Compra</h3><ul><li><a href="{root}entrega/">Prazos e entrega</a></li><li><a href="{root}pagamento/">Formas de pagamento</a></li><li><a href="{root}trocas-e-devolucoes/">Trocas e devoluções</a></li></ul></div>
<div><h3>A loja</h3><ul><li><a href="{root}sobre/">Quem somos</a></li><li><a href="{root}contato/">Contato</a></li><li><a href="{root}politica-de-privacidade/">Privacidade</a></li><li><a href="{root}termos-de-uso/">Termos de uso</a></li></ul></div>
<p class="legal">Suplementos alimentares não são medicamentos e não se destinam a diagnosticar, tratar, curar ou prevenir doenças. Consulte um médico ou nutricionista antes de consumir. Imagens ilustrativas; confira sempre o rótulo. © {YEAR} {E(LOJA['razao_social'])}.</p>
</div></footer>
{f'<a class="wa" data-wa href="https://wa.me/{WA}" target="_blank" rel="noopener">Atendimento no WhatsApp</a>' if WA else ''}
<script src="{root}assets/app.js"></script>
</body></html>'''

# ---------------------------------------------------------------- páginas de produto
def kit_path(p, q): return f"produto/{p['id']}/" if q == 1 else f"produto/{p['id']}/kit-{q}/"

def kit_jars(q): return '<span class="jars" aria-hidden="true">' + '<span class="jar"></span>' * q + '</span>'

def product_page(p, q):
    root = '../../' if q == 1 else '../../../'
    u = p['unidade']; up = PL[u]
    vs = p['variacoes']; sel = next(v for v in vs if v['qtd'] == q)
    p1 = vs[0]['preco']
    kits = []
    for v in vs:
        pu = v['preco'] / v['qtd']
        save = round((1 - pu / p1) * 100) if v['qtd'] > 1 else 0
        kits.append(f'''<div class="kit"><input type="radio" name="kit" id="k{v['qtd']}" value="{v['qtd']}" {'checked' if v['qtd']==q else ''}>
<label for="k{v['qtd']}">{kit_jars(v['qtd'])}<span class="q">{v['qtd']} {u if v['qtd']==1 else up}</span><span class="pu">{brl(pu)} cada</span>{f'<span class="save">-{save}%</span>' if save >= 3 else ''}</label></div>''')
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
               'shippingDetails': {'@type': 'OfferShippingDetails', 'shippingRate': {'@type': 'MonetaryAmount', 'value': '0', 'currency': 'BRL'},
                                   'shippingDestination': {'@type': 'DefinedRegion', 'addressCountry': 'BR'}},
               'hasMerchantReturnPolicy': {'@type': 'MerchantReturnPolicy', 'applicableCountry': 'BR', 'returnPolicyCategory': 'https://schema.org/MerchantReturnFiniteReturnWindow',
                                           'merchantReturnDays': LOJA.get('prazo_devolucao_dias', 7), 'returnMethod': 'https://schema.org/ReturnByMail', 'returnFees': 'https://schema.org/FreeReturn'}}
              for v in vs]
    ld = {'@context': 'https://schema.org', '@type': 'Product', 'name': sel['titulo'], 'sku': sel['sku'],
          'brand': {'@type': 'Brand', 'name': p['marca']}, 'image': [img(x, BASE + '/') for x in sel['imagens'][:3]],
          'description': D['apresentacao'], 'offers': offers}
    facts = [('Apresentação', FORMA[p['forma']]), ('Conteúdo', f"{p['conteudo']} por {u}" if p['conteudo'] else '—'), ('Marca', p['marca']), ('Condição', 'Novo, lacrado')]
    body = f'''<div class="wrap">
<p class="crumbs"><a href="{root}">Produtos</a> / {E(p['nome'])}</p>
<div class="pp">
<div><div class="gal-main"><img id="foto" src="{E(imgs[0])}" alt="{E(sel['titulo'])}" referrerpolicy="no-referrer"></div><div class="thumbs" id="thumbs">{thumbs}</div></div>
<div>
<p class="brand">{E(p['marca'])}</p>
<h1 id="kit-titulo">{E(sel['titulo'])}</h1>
<p class="price" id="preco">{brl(sel['preco'])}</p>
<p class="unit" id="preco-unit">{'1 ' + u if q == 1 else brl(sel['preco']/q) + ' por ' + u + ' · ' + str(q) + ' ' + up}</p>
<fieldset class="kits"><legend>Escolha a quantidade</legend><div class="kit-list">{''.join(kits)}</div></fieldset>
<button class="btn" id="comprar" type="button">Comprar agora</button>
<p class="buy-note">{E(LOJA['frete'])}. {E(LOJA['prazo_envio'])}. Pagamento processado com segurança pela RXPAY.</p>
<ul class="facts">{''.join(f'<li><span>{a}</span><b>{E(b)}</b></li>' for a, b in facts)}</ul>
</div></div>
<div class="info">
<section><h2>Sobre o produto</h2><p>{E(D['apresentacao'])}</p><p>{E(D['kits'])}</p></section>
<section><h2>Composição</h2><p>{E(D['composicao'])}</p></section>
<section><h2>Modo de uso</h2><p>{E(D['modo_de_uso'])}</p></section>
<section><h2>Advertências</h2><ul>{''.join(f'<li>{E(a)}</li>' for a in D['advertencias'])}</ul></section>
<section><p class="notice">{'Este produto é um suplemento alimentar e não é medicamento. Não se destina a diagnosticar, tratar, curar ou prevenir doenças. Resultados variam de pessoa para pessoa.' if p['tipo']=='suplemento' else 'Produto cosmético de uso externo. Resultados variam de pessoa para pessoa.'}</p></section>
</div></div>
<script type="application/json" id="produto-dados">{json.dumps(js, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'''
    canonical = url
    return layout(f"{sel['titulo']} | {LOJA['nome_loja']}", body, root, desc=D['apresentacao'], canonical=canonical,
                  extra_head=f'<meta property="og:image" content="{E(img(sel["imagens"][0], BASE + "/"))}">')

# ---------------------------------------------------------------- catálogo
def home():
    root = ''
    cards = []
    for p in PRODS:
        v1 = p['variacoes'][0]
        cards.append(f'''<a class="prod" href="{kit_path(p,1)}" data-busca="{E(p['nome']+' '+p['marca']+' '+' '.join(p['componentes']))}" data-tipo="{p['tipo']}" data-sku="{v1['sku']}" data-nome="{E(p['nome'])}" data-marca="{E(p['marca'])}" data-preco="{v1['preco']}">
<span class="ph"><img src="{E(img(v1['imagens'][0], root))}" alt="{E(p['nome'])}" loading="lazy" referrerpolicy="no-referrer"></span>
<span class="bd"><h3>{E(p['nome'])}</h3><span class="meta">{E(FORMA[p['forma']])}{' · ' + E(p['conteudo']) if p['conteudo'] else ''}</span>
<span class="from">1 {p['unidade']} <b>{brl(v1['preco'])}</b></span></span></a>''')
    body = f'''<div class="wrap">
<section class="intro"><h1>Encontre seu suplemento</h1>
<p>{len(PRODS)} produtos em kits de 1 a 5 unidades. Quanto maior o kit, menor o preço por unidade.</p>
<div class="finder"><label class="skip" for="busca">Buscar produto</label><input id="busca" type="search" placeholder="Busque pelo nome ou ingrediente" autocomplete="off">
<div class="chips" role="group" aria-label="Filtrar por tipo"><button class="chip" type="button" data-tipo="todos" aria-pressed="true">Todos</button><button class="chip" type="button" data-tipo="suplemento" aria-pressed="false">Suplementos</button><button class="chip" type="button" data-tipo="cosmetico" aria-pressed="false">Cosméticos</button></div></div>
<p class="count" id="count" aria-live="polite"></p></section>
<div class="grid" id="grid">{''.join(cards)}</div></div>'''
    ld = {'@context': 'https://schema.org', '@type': 'Organization', 'name': LOJA['nome_loja'], 'legalName': LOJA['razao_social'],
          'url': BASE + '/', 'email': LOJA['email'], 'telephone': LOJA['telefone'], 'taxID': LOJA['cnpj'],
          'address': {'@type': 'PostalAddress', 'streetAddress': LOJA['endereco'], 'addressCountry': 'BR'}}
    write('index.html', layout(f"{LOJA['nome_loja']} | Suplementos e cuidados diários", body, root, canonical=BASE + '/',
                               extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'))

# ---------------------------------------------------------------- páginas institucionais
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
                  ('g:product_type', 'Suplementos alimentares' if p['tipo'] == 'suplemento' else 'Cosméticos'),
                  ('g:is_bundle', 'yes' if v['qtd'] > 1 else 'no'), ('g:custom_label_0', 'kit-' + str(v['qtd'])),
                  ('g:age_group', 'adult')]
            if v['qtd'] > 1: f.append(('g:multipack', str(v['qtd'])))
            if p.get('adulto'): f.append(('g:adult', 'yes'))
            f.append(('g:shipping', None))
            parts = []
            for k, val in f:
                if k == 'g:shipping':
                    parts.append('<g:shipping><g:country>BR</g:country><g:service>Padrão</g:service><g:price>0.00 BRL</g:price></g:shipping>')
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
    urls = [BASE + '/'] + [f'{BASE}/{s}/' for s in ['sobre', 'contato', 'entrega', 'pagamento', 'trocas-e-devolucoes', 'politica-de-privacidade', 'termos-de-uso']]
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
    if '--imagens' in sys.argv:
        baixar_imagens()
    home(); pages()
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
