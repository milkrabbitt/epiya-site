# -*- coding: utf-8 -*-
"""Public OPC and investment copy for the Round 4 visual preview.

These fragments are presentation content only. They do not open a fundraising
transaction, disclose financing terms, or change product distribution status.
"""

OPC_SOURCE = (
    "https://hzdaily.hangzhou.com.cn/hzrb/2026/07/02/"
    "article_detail_1_20260702A079.html"
)
INVESTMENT_CONTACT = "/contact/?topic=investment#contact-card"


def _eyebrow(first, second):
    return f'<p class="eyebrow"><span>{first}</span><span>{second}</span></p>'


def _link(url, text):
    return f'<a class="text-link" href="{url}">{text} <span aria-hidden="true">↗</span></a>'


def _button(url, text):
    return f'<a class="button secondary" href="{url}">{text}<span aria-hidden="true">↗</span></a>'


opc_home = (
    '<section class="wrap section-space opc-section" id="working-method" '
    'aria-labelledby="opc-home-title">'
    + _eyebrow('OUR WAY OF WORKING', 'FOUNDER × AI')
    + '<div class="opc-intro"><h2 id="opc-home-title">创始人主导，<br>与 AI 一起把细节做下去。</h2>'
    '<div><p>在 EPIYA，42 负责产品方向与关键判断，AI 参与设计、开发、测试和日常工作。'
    '从一个具体需求开始，用可以使用的版本检验想法。</p>'
    + _link('/about.html#opc', '了解我们的 OPC 工作方式')
    + '</div></div>'
    '<ol class="opc-diagram" aria-label="EPIYA 的工作方式">'
    '<li class="opc-step"><span class="item-number">01</span><h3>定义问题</h3>'
    '<p>找到真实使用场景，确定这一版最需要解决的事。</p></li>'
    '<li class="opc-step"><span class="item-number">02</span><h3>协作实现</h3>'
    '<p>用 AI 辅助设计、代码实现与检查，逐步做成可运行版本。</p></li>'
    '<li class="opc-step"><span class="item-number">03</span><h3>使用与修正</h3>'
    '<p>回到实际体验，核对功能与细节，再决定下一步。</p></li>'
    '</ol></section>'
)


investment_home = (
    '<section class="wrap investment-note" aria-labelledby="investment-home-title">'
    + _eyebrow('IN CONVERSATION', 'INVESTMENT')
    + '<div><h2 id="investment-home-title">一起讨论，更长远的可能。</h2>'
    '<p>EPIYA 开放投资交流。欢迎关注 AI 应用与软件产品的伙伴，了解我们的产品进展与后续方向。</p></div>'
    + _link('/investment/', '投资交流')
    + '</section>'
)


investment_body = (
    '<section class="page-intro wrap" aria-labelledby="investment-title">'
    + _eyebrow('INVESTMENT', 'EPIYA / HANGZHOU')
    + '<h1 id="investment-title">开放投资交流。</h1>'
    '<p class="intro-text">EPIYA 欢迎关注 AI 应用与软件产品的投资伙伴交流。'
    '从已经做出的产品开始，聊聊公司的方向、下一阶段的投入与长期合作。</p>'
    '<div class="actions">'
    + _button(INVESTMENT_CONTACT, '联系 42 · 投资洽谈')
    + _button('/products.html', '先看看产品')
    + '</div></section>'
    '<section class="wrap section-space investment-grid" aria-labelledby="investment-company-title">'
    '<div>'
    + _eyebrow('01', 'THE COMPANY')
    + '<h2 id="investment-company-title">由产品，<br>开始认识 EPIYA。</h2></div>'
    '<div class="prose"><p>杭州壹湃科技有限公司以 EPIYA 为品牌，由创始人 42 主导产品开发。'
    '我们开发喵喵键盘、Relic 与 Futures Alpha，也提供小程序、App 和 AI 应用定制。</p>'
    '<p>三个产品分别从日常表达、角色对话和期货研究的具体需求出发。'
    '它们处于不同阶段，官网分别展示真实界面、已实现的功能和可用入口。</p>'
    '<p>这里讨论的是对 EPIYA 公司的投资与合作。Futures Alpha 是开发中的研究软件，'
    '本页不提供期货交易、资管或投资收益承诺。</p>'
    + _link('/about.html', '认识创始人 42')
    + '</div></section>'
    '<section class="wrap section-space" aria-labelledby="investment-progress-title">'
    '<div class="section-head">'
    + _eyebrow('02', 'PRODUCT PROGRESS')
    + '<div><h2 id="investment-progress-title">当前进展，逐项说明。</h2>'
    '<p>可以直接查看产品界面与使用说明。各渠道的最新可用入口集中在下载中心。</p></div></div>'
    '<dl class="investor-facts">'
    '<div><dt><a href="/products/meow/">喵喵键盘 <span aria-hidden="true">↗</span></a></dt>'
    '<dd><span class="status">App Store 已上架</span>'
    '<p>iOS 中文键盘，结合日常输入、喵化预览、猫猫颜文字与主题。</p></dd></div>'
    '<div><dt><a href="/products/relic/">Relic <span aria-hidden="true">↗</span></a></dt>'
    '<dd><span class="status muted">内部 / 开发测试</span>'
    '<p>从经授权的素材蒸馏角色，提取表达习惯，整理角色资料与可编辑记忆。</p></dd></div>'
    '<div><dt><a href="/products/futures-alpha/">Futures Alpha <span aria-hidden="true">↗</span></a></dt>'
    '<dd><span class="status muted">开发中</span>'
    '<p>连接行情、策略条件、风险约束与模拟复盘，当前没有正式公开安装包。</p></dd></div>'
    '</dl><div class="actions">'
    + _button('/downloads/', '查看实际分发状态')
    + '</div></section>'
    '<section class="wrap section-space investment-grid" aria-labelledby="investment-next-title">'
    '<div>'
    + _eyebrow('03', 'THE NEXT CONVERSATION')
    + '<h2 id="investment-next-title">希望进一步讨论什么。</h2></div>'
    '<div class="prose"><p>下一阶段，我们希望围绕产品持续开发、实际使用反馈与稳定交付展开讨论，'
    '明确最值得优先投入的方向。</p>'
    '<ul><li>产品重点：哪些使用场景最值得继续打磨，怎样判断产品真正有用。</li>'
    '<li>研发与交付：需要补齐哪些工程能力，怎样持续维护和迭代。</li>'
    '<li>商业化与合作：怎样连接合适的用户、渠道与长期伙伴。</li></ul>'
    '<p>以上是交流方向，具体计划、合作安排和投资条件在进一步沟通后确定。</p>'
    '</div></section>'
    '<section class="wrap investment-note" aria-labelledby="investment-contact-title">'
    + _eyebrow('LET’S TALK', '42 / EPIYA')
    + '<div><h2 id="investment-contact-title">从一次具体的交流开始。</h2>'
    '<p>通过企业微信联系 42，可以说明你的机构或背景、关注的产品与希望交流的问题。</p></div>'
    + _link(INVESTMENT_CONTACT, '企业微信 · 投资洽谈')
    + '</section>'
)


about_opc = (
    '<section class="wrap section-space opc-section" id="opc" aria-labelledby="opc-about-title">'
    + _eyebrow('OUR APPROACH', 'OPC / AI COLLABORATION')
    + '<div class="opc-intro"><h2 id="opc-about-title">一个清楚的方向，<br>一套持续协作的方式。</h2>'
    '<div class="prose"><p>OPC 是 One Person Company。在 AI 协同创业的语境里，'
    '它强调由核心创始人负责方向与判断，让 AI 参与执行，形成精干、灵活的工作方式。</p>'
    '<p>在 EPIYA，42 定义产品需求、决定优先级并承担交付责任；AI 辅助设计、开发、测试和日常工作。'
    '每个版本仍需要回到真实使用场景，检查是否解决了原来的问题。</p>'
    f'<a class="text-link opc-source" href="{OPC_SOURCE}" target="_blank" rel="noopener noreferrer">'
    '了解 AI＋OPC 的背景 <span aria-hidden="true">↗</span></a>'
    '</div></div>'
    '<ol class="opc-diagram" aria-label="从想法到产品的协作流程">'
    '<li class="opc-step"><span class="item-number">方向</span><h3>人来做判断</h3>'
    '<p>理解需求，选择投入方向，确定产品与使用体验。</p></li>'
    '<li class="opc-step"><span class="item-number">执行</span><h3>与 AI 协作</h3>'
    '<p>拆解任务，辅助实现与检查，把反馈带回下一版。</p></li>'
    '<li class="opc-step"><span class="item-number">交付</span><h3>用实际结果确认</h3>'
    '<p>核对功能、分发和维护状态，让产品进展可被看见。</p></li>'
    '</ol></section>'
)
