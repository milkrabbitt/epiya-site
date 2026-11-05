"""Round 6 presentation surfaces, with existing copy and functional routes retained."""
from html import escape
import re

PRODUCTS = (
    ('meow', '喵喵键盘', 'MEOW KEYBOARD', '/products/meow/', '/assets/meow-cream.webp'),
    ('relic', 'Relic', 'CHARACTER DISTILLATION', '/products/relic/', '/assets/relic-persona.webp'),
    ('futures', 'Futures Alpha', 'RESEARCH WORKSPACE', '/products/futures-alpha/', '/assets/futures-market.webp'),
)


def product_plate():
    items = ''.join('<a class="ix-studio-product ix-product-'+key+'" href="'+url+'"><span>'+str(i+1).zfill(2)+'</span><strong>'+name+'</strong><i aria-hidden="true">↗</i></a>' for i,(key,name,en,url,img) in enumerate(PRODUCTS))
    return '<div class="ix-studio-panel"><div class="ix-panel-top"><span>INDEPENDENT TECHNOLOGY</span><span>HANGZHOU</span></div><img class="ix-studio-logo" src="/assets/logo-dark.svg" alt="EPIYA" width="240" height="57"><div class="ix-studio-products">'+items+'</div><div class="ix-panel-foot"><span>EXPRESSION / MEMORY / RESEARCH</span><span aria-hidden="true">＋</span></div></div>'


def release_dock():
    items = ''
    for i,(key,name,en,url,img) in enumerate(PRODUCTS):
        w,h=(1480,920) if key=='futures' else (660,1435 if key=='relic' else 1434)
        items += '<a class="ix-release-item ix-product-'+key+'" href="#'+key+'"><span class="ix-release-index">'+str(i+1).zfill(2)+'</span><div class="ix-release-device"><img src="'+img+'" alt="'+name+' 产品界面缩略图" width="'+str(w)+'" height="'+str(h)+'" loading="eager" decoding="async"></div><strong>'+name+'</strong><span>查看分发状态 <i aria-hidden="true">↓</i></span></a>'
    return '<div class="ix-release-dock"><div class="ix-panel-top"><span>PRODUCT DIRECTORY</span><span>01—03</span></div><div class="ix-release-shelves">'+items+'</div><p class="ix-dock-note">正式版本与开发进展，分别列明。</p></div>'


def contact_plate():
    return '<div class="ix-contact-panel"><div class="ix-panel-top"><span>OPEN A CONVERSATION</span><span>EPIYA</span></div><div class="ix-envelope" aria-hidden="true"><span>@</span><i></i></div><a class="ix-contact-address" href="mailto:contact@epiya.cn">contact@epiya.cn <span aria-hidden="true">↗</span></a><p>产品支持 / 商务合作 / 投资交流</p><a class="ix-contact-jump" href="#contact-card">或通过企业微信联系 <span aria-hidden="true">↓</span></a></div>'


def enhance_body(path, body):
    """Decorate only the existing first intro; founder section is never touched."""
    surfaces = {'about.html': ('studio', product_plate), 'contact/index.html': ('contact', contact_plate), 'downloads/index.html': ('downloads', release_dock), 'investment/index.html': ('investment', product_plate)}
    if path not in surfaces:
        return body
    kind, draw = surfaces[path]
    match = re.search(r'<section class="page-intro wrap"([^>]*)>(.*?)</section>', body, re.S)
    if not match:
        raise ValueError('Expected existing page intro for '+path)
    replacement = '<section class="page-intro wrap ix-intro ix-intro-'+kind+'"'+match.group(1)+'><div class="ix-intro-copy">'+match.group(2)+'</div><div class="ix-intro-stage">'+draw()+'</div></section>'
    return body[:match.start()]+replacement+body[match.end():]
