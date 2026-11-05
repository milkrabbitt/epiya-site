# -*- coding: utf-8 -*-
"""Public product scenes. No accounts, payments or real chat material."""


def _button(href, text, secondary=False):
    return '<a class="button {}" href="{}">{}<span aria-hidden="true">↗</span></a>'.format('secondary' if secondary else 'primary', href, text)


def _photo(file, width, height, alt, caption, cls=''):
    return ('<figure class="ps-photo ' + cls + '"><a class="ps-photo-link" href="/assets/' + file + '" data-lightbox '
            'data-caption="' + caption + '" aria-label="查看大图：' + alt + '"><img src="/assets/' + file + '" '
            'width="' + str(width) + '" height="' + str(height) + '" alt="' + alt + '" loading="eager" decoding="async">'
            '<span class="ps-enlarge" aria-hidden="true">＋</span></a><figcaption>' + caption + '</figcaption></figure>')


products_intro = '''<section class="ps-products-intro" aria-labelledby="ps-products-title">
  <div class="wrap ps-products-heading"><p class="eyebrow"><span>PRODUCTS</span><span>BUILT BY EPIYA</span></p>
  <div class="ps-heading-line"><h1 id="ps-products-title">正在做的产品。</h1><p>从一句话的语气，到角色的记忆，<br>再到交易前的判断。</p></div></div>
  <div class="wrap ps-gallery ps-reactive">
    <div class="ps-gallery-label" aria-hidden="true"><span>EPIYA — PRODUCT COLLECTION</span><span>01 / 02 / 03</span></div>
    <div class="ps-gallery-rail" aria-hidden="true"></div>
    <a class="ps-product-bay ps-bay-meow" href="/products/meow/" aria-label="了解喵喵键盘">
      <div class="ps-bay-art"><div class="ps-bay-backplate" aria-hidden="true"></div><img class="ps-mini-phone" src="/assets/meow-cream.webp" width="660" height="1434" alt="喵喵键盘奶油橘猫真实界面" loading="eager" decoding="async"></div>
      <div class="ps-bay-caption"><span class="ps-bay-number">01 / EXPRESSION</span><h2>喵喵键盘 <span aria-hidden="true">↗</span></h2><p>App Store 已上架</p></div>
    </a>
    <a class="ps-product-bay ps-bay-relic" href="/products/relic/" aria-label="了解 Relic 角色蒸馏">
      <div class="ps-bay-art"><div class="ps-bay-backplate" aria-hidden="true"></div><img class="ps-mini-phone" src="/assets/relic-persona.webp" width="660" height="1435" alt="Relic 开发版角色资料真实界面，合成资料" loading="eager" decoding="async"></div>
      <div class="ps-bay-caption"><span class="ps-bay-number">02 / DISTILLATION</span><h2>Relic <span aria-hidden="true">↗</span></h2><p>内部 / 开发测试</p></div>
    </a>
    <a class="ps-product-bay ps-bay-futures" href="/products/futures-alpha/" aria-label="了解 Futures Alpha 研究工作台">
      <div class="ps-bay-art"><div class="ps-bay-backplate" aria-hidden="true"></div><div class="ps-mini-screen"><img src="/assets/futures-market.webp" width="1480" height="920" alt="Futures Alpha 开发版行情工作台，dry-run 观察，非实盘交易" loading="eager" decoding="async"></div></div>
      <div class="ps-bay-caption"><span class="ps-bay-number">03 / RESEARCH</span><h2>Futures Alpha <span aria-hidden="true">↗</span></h2><p>桌面软件 · 开发中</p></div>
    </a>
    <p class="ps-gallery-note">真实产品界面 · Relic 使用合成资料 · Futures Alpha 为 dry-run 行情观察</p>
  </div>
</section>'''


relic_intro = '''<section class="ps-relic-intro" aria-labelledby="ps-relic-title">
  <div class="wrap ps-relic-heading"><p class="eyebrow"><span>RELIC</span><span>CHARACTER DISTILLATION</span></p>
    <div class="ps-heading-line"><h1 id="ps-relic-title">蒸馏你的好友。</h1><p>从经授权的聊天素材中，提取熟悉的口头禅、表达习惯与记忆线索，创建可以继续对话的 AI 角色。</p></div>
    <div class="ps-relic-actions"><div class="actions">''' + _button('#distill', '看看如何蒸馏') + _button('/downloads/#relic', '查看分发状态', True) + '''</div><span class="ps-release-state"><i aria-hidden="true"></i>内部 / 开发测试</span></div>
  </div>
  <div class="wrap ps-memory-bench ps-reactive">
    <div class="ps-bench-topline"><span>RELIC / MEMORY WORKBENCH</span><span>素材 → 蒸馏 → AI 角色</span></div>
    <div class="ps-material-stack">
      <span class="ps-stage-kicker">01 / MATERIAL</span>
      <div class="ps-source-sheet"><div class="ps-sheet-heading"><span>一段熟悉的聊天</span><small>合成示意</small></div>
        <p class="ps-source-line">今天有点累。</p><p class="ps-source-line ps-source-reply">先歇一会儿，<br>我在呢。</p>
        <p class="ps-source-line">那明天再说？</p><p class="ps-source-line ps-source-reply">好呀，慢慢来。</p>
        <div class="ps-sheet-footer">由你选择与确认素材范围</div>
      </div>
    </div>
    <div class="ps-distill-core"><span class="ps-stage-kicker">02 / DISTILL</span><div class="ps-chip" aria-hidden="true"><span class="ps-chip-label">RELIC</span><span class="ps-chip-subtitle">VOICE / MEMORY</span><i></i><b></b></div><div class="ps-extract-tags"><span>口头禅</span><span>表达习惯</span><span>记忆线索</span></div><p>预览，再调整。</p></div>
    <div class="ps-character-output"><span class="ps-stage-kicker">03 / CHARACTER</span>''' + _photo('relic-persona.webp', 660, 1435, 'Relic 人物资料与语言风格界面', '开发版 build20 · 真实界面，合成资料', 'ps-relic-phone') + '''</div>
    <p class="ps-bench-caption">左侧聊天与中间提取过程为网页合成示意。Relic 创建的是 AI 角色，不承诺完整复制真人。</p>
  </div>
</section>'''


_steps = [
    ('导入素材', '先选择，你想留下的片段。',
     '导入有权使用的 TXT、CSV、JSON，或直接粘贴文本。客户端也提供一次性电脑上传授权，由你选择素材与导入范围。',
     '<div class="ps-file"><span class="ps-file-icon" aria-hidden="true">TXT</span><div><strong>一起散步的聊天.txt</strong><small>合成素材示意</small></div><span aria-hidden="true">↙</span></div><div class="ps-document"><span class="ps-document-label">素材片段</span><p><b>你</b>今天有点累，想出去走走。</p><p><b>林</b>走吧，老地方等你。慢慢来。</p><p><b>你</b>还是河边那条路？</p><p><b>林</b>嗯，我在呢。</p></div>', '由你导入，网页不会读取微信聊天记录。'),
    ('确认人物', '确认这一次，要蒸馏谁。',
     '区分对话双方，核对人物与素材范围。补充角色资料，把不希望纳入的内容排除在外。',
     '<div class="ps-person"><span class="ps-person-avatar" aria-hidden="true">林</span><div><strong>林</strong><span>本次角色 · 合成示例</span></div><span class="ps-confirmed">已选择</span></div><dl class="ps-profile"><div><dt>素材人物</dt><dd>林</dd></div><div><dt>对话另一方</dt><dd>你</dd></div><div><dt>保留范围</dt><dd>表达习惯、已确认的资料</dd></div></dl><div class="ps-preview-note">确认人物关系，再继续蒸馏。</div>', '示意中的人物、姓名和聊天均为合成。'),
    ('蒸馏与预览', '看看，哪些细节让你觉得熟悉。',
     '预览蒸馏出的语言风格、口癖和角色资料。你可以修改设定，检查并编辑人工记忆，再决定如何继续。',
     '<div class="ps-extraction"><span>表达习惯</span><strong>短句 · 温和 · 直接回应</strong><span>常用语</span><div class="ps-extract-tags"><span>“慢慢来”</span><span>“我在呢”</span></div><span>待确认的记忆线索</span><p>你们提到过河边散步的路线。</p></div><div class="ps-preview-note">资料与记忆由你检查、编辑。</div>', '这是合成结果示意，不是实时模型输出。'),
    ('开始对话', '让熟悉的语气，有下一句。',
     '与创建的 AI 角色继续对话。角色资料与可编辑记忆参与后续交流，你仍然可以回来调整。',
     '<div class="ps-chat-header"><span class="ps-person-avatar" aria-hidden="true">林</span><div><strong>林</strong><small>AI 角色 · 合成对话</small></div></div><div class="ps-chat-log"><p class="ps-source-line">今天也想出去走走。</p><p class="ps-source-line ps-source-reply">走吧，河边怎么样？<br>慢慢来，我在呢。</p></div><div class="ps-preview-note">保持 AI 身份清楚，记忆可查看与编辑。</div>', 'AI 生成内容可能不准确，不代表特定真人。'),
]
_tabs = ''.join('<button type="button" id="ps-step-tab-{}" class="ps-step-tab" role="tab" aria-controls="ps-step-panel-{}" aria-selected="{}" tabindex="{}"><span>0{}</span><strong>{}</strong></button>'.format(i, i, 'true' if i == 0 else 'false', '0' if i == 0 else '-1', i + 1, row[0]) for i, row in enumerate(_steps))
_panels = ''.join('<section class="ps-step-panel" id="ps-step-panel-{}" role="tabpanel" aria-labelledby="ps-step-tab-{}" tabindex="0"><div class="ps-step-copy"><span class="ps-stage-kicker">0{} / {}</span><h3>{}</h3><p>{}</p><span class="ps-demo-label">网页合成示意 · 非实时蒸馏</span></div><div class="ps-step-demo"><div class="ps-demo-content">{}</div><p class="ps-demo-footnote">{}</p></div></section>'.format(i, i, i + 1, row[0], row[1], row[2], row[3], row[4]) for i, row in enumerate(_steps))
relic_distill = '''<section class="ps-distill-section" id="distill" aria-labelledby="ps-distill-title"><div class="wrap">
  <div class="ps-distill-heading"><p class="eyebrow"><span>01</span><span>DISTILL A CHARACTER</span></p><h2 id="ps-distill-title">“一键蒸馏好友”，<br>从你选择的素材开始。</h2><p>把一段段对话，整理成可以预览、调整的角色资料与表达风格。</p></div>
  <div class="ps-distill" data-ps-distill><div class="ps-step-tabs" role="tablist" aria-label="了解角色蒸馏的四个步骤" hidden>''' + _tabs + '''</div><div class="ps-step-panels">''' + _panels + '''</div></div>
  <p class="ps-distill-boundary">只能导入你有权使用的资料。网站与小程序不能直接读取任意微信好友的全部聊天记录。</p>
</div></section>'''


futures_intro = '''<section class="ps-futures-intro" aria-labelledby="ps-futures-title"><div class="wrap">
  <p class="eyebrow"><span>FUTURES ALPHA</span><span>RESEARCH WORKSPACE</span></p>
  <div class="ps-heading-line"><h1 id="ps-futures-title">从行情到判断，<br>每一步都看得清。</h1><div><p>把行情、策略条件、风险控制、模拟执行与复盘放在同一个工作流程里。为自己的期货研究需求开发，目前仍在打磨。</p><span class="ps-release-state"><i aria-hidden="true"></i>桌面软件 · 开发中</span></div></div>
  <div class="actions">''' + _button('#workflow', '了解工作流程') + _button('/downloads/#futures', '查看开发状态', True) + '''</div>
  <div class="ps-research-instrument ps-reactive"><div class="ps-instrument-label"><span>FUTURES ALPHA</span><small>行情研究工作台</small></div><ol class="ps-research-path"><li><span>01</span>行情观察</li><li><span>02</span>触发依据</li><li><span>03</span>风险控制</li><li><span>04</span>模拟复盘</li></ol><div class="ps-instrument-foot"><span>RESEARCH / REASON / RISK / REVIEW</span><span>下方为真实开发界面 ↓</span></div></div>
</div></section>'''
