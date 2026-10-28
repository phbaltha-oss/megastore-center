# MegaStore Center — site no GitHub Pages

Site de e-commerce gerado a partir de `data/produtos.json` (346 produtos, kits de 1 a 5 unidades).
Cada alteração salva na branch `main` reconstrói e publica o site sozinha (aba **Actions**).

## Onde editar

| O que | Arquivo |
|---|---|
| Nome da loja, CNPJ, endereço, contatos, prazos | `config/loja.json` |
| IDs de rastreamento (GTM, GA4, Google Ads, Meta, TikTok) | `config/loja.json` → `rastreamento` |
| Links de checkout da RXPAY por SKU | `config/checkout.json` |
| Títulos, textos, preços e fotos dos produtos | `data/produtos.json` |
| Visual | `assets/style.css` |

No GitHub, abra o arquivo, clique no lápis, edite e clique em **Commit changes**.

## Conversões configuradas

- **Consentimento LGPD** com Google Consent Mode v2 (nada de anúncio antes do aceite).
- Eventos GA4 de e-commerce no `dataLayer`: `view_item_list`, `view_item`, `select_kit`, `begin_checkout`, `generate_lead` (WhatsApp) e `purchase`.
- **Google Ads**: conversões de compra, início de checkout e WhatsApp (preencha os rótulos), com conversões otimizadas.
- **Meta Pixel**: PageView, ViewContent, InitiateCheckout, Contact, Purchase (com `eventID` para deduplicar com a API de Conversões da RXPAY, se houver).
- **TikTok Pixel**: ViewContent, InitiateCheckout, Contact, CompletePayment.
- Guarda `gclid`, `gbraid`, `wbraid`, `fbclid`, `ttclid` e UTMs e repassa ao link de checkout.
- Página de compra concluída: `/obrigado/?pedido={id}&valor={valor}&sku={sku}` — configure como URL de retorno na RXPAY. Compras repetidas do mesmo pedido não são contadas duas vezes.

## Google Merchant Center

Feed: `URL_DO_SITE/feeds/google-merchant.xml` (só produtos de risco baixo e médio).
Em Merchant Center → Produtos → Feeds → Adicionar → Busca programada, cole a URL.

## Rodar localmente

```
python scripts/build.py          # gera _site/
python -m http.server -d _site
```
