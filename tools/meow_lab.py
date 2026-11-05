"""Source-backed, clearly labelled browser demonstration of Meow Keyboard."""
from pathlib import Path
from html import escape
import json

DATA=json.loads((Path(__file__).resolve().parents[1]/'assets/meow-themes.json').read_text())
THEMES=DATA['themes']
SAMPLE='我今天很开心，你要一起玩吗？'

def picker(default='strawberry'):
    out='<div class="meow-theme-picker" data-theme-picker>'
    for name,items in [('猫咪主题',[t for t in THEMES if t['cat']]),('经典纯色',[t for t in THEMES if not t['cat']])]:
        out+=f'<div class="theme-family"><p class="theme-family-label">{name}</p><div class="theme-options" role="group" aria-label="{name}">'
        for t in items:
            dev='<small>开发版</small>' if t['release']=='development-preview' else ''
            out+=f'<button type="button" data-skin="{t["id"]}" aria-pressed="{str(t["id"]==default).lower()}"><i style="background:{t["palette"]["accent"]}" aria-hidden="true"></i><span>{t["name"]}</span>{dev}</button>'
        out+='</div></div>'
    return out+'</div><p class="theme-hint">12 款主题 · 标注“开发版”的 6 款尚未进入当前商店版本。</p>'

def keyboard(default='strawberry',expanded=False):
    out='<div class="lab-keyboard" aria-hidden="true">'
    if expanded:
        out+='<div class="lab-faces"><span>ฅ•ω•ฅ</span><span>ฅ(^•ﻌ•^ฅ)</span><span>₍^ >ヮ<^₎</span></div><div class="lab-key-preview"><img data-lab-cat src="/assets/meow-cats/'+default+'.svg" alt=""><span data-lab-mirror>本喵今天很翘尾巴，主人要一起玩嘛~</span></div>'
    for keys in ['qwertyuiop','asdfghjkl','zxcvbnm']:
        out+='<div class="lab-key-row">'+''.join('<span>'+k+'</span>' for k in keys)+'</div>'
    out+='<div class="lab-key-row bottom"><span class="special">123</span><span class="emoji">ฅ</span><span class="space">空格 <img data-lab-cat src="/assets/meow-cats/'+default+'.svg" alt=""></span><span class="special">换行</span></div></div>'
    return out

def lab(prefix='home',default='strawberry'):
    t=next(t for t in THEMES if t['id']==default);photo=t['photo'];label=escape(photo['caption'])
    options=''.join('<option value="'+item['id']+'"'+(' selected' if item['id']==default else '')+'>'+item['name']+(' · 开发版' if item['release']=='development-preview' else '')+'</option>' for item in THEMES)
    return f'''<div class="meow-lab">
      <div class="lab-toolbar" role="group" aria-label="选择产品展示方式">
        <button type="button" data-lab-view="live" aria-pressed="true" aria-controls="{prefix}-live">动手试试</button>
        <button type="button" data-lab-view="photo" aria-pressed="false" aria-controls="{prefix}-photo">真实截图</button>
      </div><label class="lab-mobile-theme" for="{prefix}-skin">换个皮肤<select id="{prefix}-skin" data-lab-select aria-label="手机预览皮肤">{options}</select></label><p class="lab-photo-note" data-photo-note hidden></p>
      <div class="lab-phone" id="{prefix}-live" data-live-panel><div class="lab-screen">
        <div class="lab-island" aria-hidden="true"></div>
        <header class="lab-brand"><span class="lab-cat" aria-hidden="true">₍^ &gt;ヮ&lt;^₎</span><h3>喵喵键盘</h3><small>网页交互演示 · 自然喵化</small></header>
        <div class="lab-input-panel"><label for="{prefix}-input">写一句你想说的话</label><textarea id="{prefix}-input" data-lab-input maxlength="120" rows="3" autocomplete="off" autocapitalize="off" spellcheck="false" aria-describedby="{prefix}-privacy" placeholder="比如：今天也想和你一起玩">{SAMPLE}</textarea><div class="lab-input-meta"><span data-lab-count>{len(SAMPLE)} / 120</span><button type="button" data-lab-clear>清空</button></div></div>
        <div class="lab-result-panel"><div class="lab-result-heading"><span id="{prefix}-result-label">喵化预览</span><button type="button" data-lab-copy>复制</button></div><p class="lab-output" data-lab-output role="status" aria-live="polite" aria-atomic="true" aria-labelledby="{prefix}-result-label">本喵今天很翘尾巴，主人要一起玩嘛~</p></div>
        <div class="lab-samples" role="group" aria-label="试一句合成样例"><button type="button" data-lab-sample="我喜欢你">我喜欢你</button><button type="button" data-lab-sample="我们去吃饭吧">我们去吃饭吧</button></div>
        {keyboard(default)}<div class="lab-home-indicator" aria-hidden="true"></div>
      </div></div>
      <div class="lab-photo" id="{prefix}-photo" data-photo-panel hidden><figure><a class="image-link" data-lightbox data-caption="{label}" href="{photo['src']}" aria-label="查看{t['name']}完整真实截图"><span class="lab-photo-window"><img data-lab-photo src="{photo['src']}" width="{photo['width']}" height="{photo['height']}" alt="{label}" loading="lazy"></span></a><figcaption data-photo-caption>{label}</figcaption><button type="button" class="lab-photo-retry" data-photo-retry hidden>重新加载截图</button></figure></div>
      <p class="lab-caption" data-lab-status role="status">{t['name']} · 网页配色与喵化演示</p>
      <p class="lab-privacy" id="{prefix}-privacy">文字只在此浏览器处理，不上传、不保存。<br>展示背景随主题联动；iOS 完整输入体验请以 App 为准。</p>
      <noscript><p class="lab-caption">开启 JavaScript 后可以输入并切换主题。<a href="{photo['src']}">先查看真实截图</a></p></noscript>
    </div>'''

def config():
    return '<script type="application/json" id="meow-theme-data">'+json.dumps(DATA,ensure_ascii=False).replace('<','\\u003c')+'</script>'
