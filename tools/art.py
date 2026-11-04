#!/usr/bin/env python3
"""Build EPIYA's vector share card and official contact card.

Uses maintained outlined logo/verified QR assets. The SVG source is the source
of truth; Sharp rasterizes it without network access. Chinese text uses the
host's licensed Hiragino Sans GB / system sans font; fonts are not redistributed.
Requires Node with sharp. This generator never creates the retired fiber art.
"""
from pathlib import Path
import argparse
import html
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
FONT = 'Hiragino Sans GB, PingFang SC, Microsoft YaHei, sans-serif'


def nested(path, x, y, width, height):
    source = path.read_text()
    viewbox = re.search(r'viewBox="([^"]+)"', source).group(1)
    inner = source[source.index('>') + 1:source.rfind('</svg>')]
    inner = re.sub(r'<(?:title|desc)\b[^>]*>.*?</(?:title|desc)>', '', inner, flags=re.S)
    inner = re.sub(r'\s+id="[^"]*"', '', inner)
    return f'<svg x="{x}" y="{y}" width="{width}" height="{height}" viewBox="{viewbox}">{inner}</svg>'


def text(x, y, content, size=24, fill='#E8EDF2', weight=400, anchor='start', tracking=0):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" letter-spacing="{tracking}" fill="{fill}">{html.escape(content)}</text>'


def background(height):
    return f'''<defs><linearGradient id="metal" x1="0" x2="1" y1="0" y2=".75"><stop offset="0" stop-color="#141922"/><stop offset=".48" stop-color="#0B0D12"/><stop offset="1" stop-color="#11161F"/></linearGradient></defs><path fill="url(#metal)" d="M0 0h1200v{height}H0z"/><rect x="32" y="32" width="1136" height="{height-64}" fill="none" stroke="#303744"/><path d="M72 166H1128" stroke="#303744"/><path d="M72 166H152" stroke="#65B8FF" stroke-width="2"/>'''


def document(height, body, title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="card-title"><title id="card-title">{title}</title>{body}</svg>\n'


def make_share():
    body = background(630) + nested(ASSETS / 'logo-light.svg', 66, 62, 320, 76)
    body += text(1128, 106, 'PRODUCTS / SOFTWARE / AI', 15, '#AEB8C7', anchor='end', tracking=1.2)
    body += text(72, 278, '把有趣的想法，', 64, weight=600)
    body += text(72, 366, '做成好用的产品。', 64, weight=600)
    body += '<path d="M792 232V409" stroke="#303744"/>'
    for index, (label, y) in enumerate([('喵喵键盘', 258), ('Relic', 325), ('Futures Alpha', 392)]):
        body += text(823, y - 2, f'0{index+1}', 14, '#65B8FF')
        body += text(875, y, label, 24)
    body += text(72, 507, '杭州壹湃科技有限公司', 22, '#AEB8C7')
    body += text(72, 551, '独立产品研发 · 软件与 AI 应用定制', 18, '#8793A6')
    body += text(1128, 550, 'epiya.cn', 25, '#E8EDF2', anchor='end')
    return document(630, body, 'EPIYA · 把有趣的想法，做成好用的产品。')


def make_contact():
    body = background(720) + nested(ASSETS / 'logo-light.svg', 66, 62, 320, 76)
    body += text(1128, 106, 'OFFICIAL CONTACT', 15, '#AEB8C7', anchor='end', tracking=1.4)
    body += text(72, 276, 'EPIYA 联系', 62, weight=600)
    body += text(74, 331, '杭州壹湃科技有限公司', 25, '#AEB8C7')
    body += text(74, 407, '42 / 创始人', 22)
    body += text(74, 455, '产品支持 · 商务合作 · 项目交流', 19, '#AEB8C7')
    body += text(72, 565, 'epiya.cn', 34)
    # Outer paper and the QR's own four-module quiet zone both remain white.
    body += '<path fill="#FFFFFF" d="M756 196h352v352H756z"/>'
    body += nested(ASSETS / 'contact-qr.svg', 772, 212, 320, 320)
    body += text(932, 590, '微信扫码，添加企业微信', 20, '#E8EDF2', anchor='middle')
    body += '<path d="M72 644H1128" stroke="#303744"/>'
    body += text(72, 681, 'EPIYA / 杭州壹湃科技有限公司', 15, '#8793A6')
    body += text(1128, 681, 'OFFICIAL WECOM', 13, '#8793A6', anchor='end', tracking=1)
    return document(720, body, 'EPIYA 官方联系名片')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--sharp-module', default='sharp')
    args = parser.parse_args()
    if not args.node:
        parser.error('Node is required: pass --node /path/to/node')
    generated = [('share', make_share())]
    if (ASSETS / 'contact-qr.svg').is_file():
        generated.append(('epiya-contact-card', make_contact()))
    raster = "const fs=require('fs'),sharp=require(process.argv[1]);(async()=>{for(const name of JSON.parse(process.argv[2]))await sharp(name+'.svg').png().toFile(name+'.png')})().catch(e=>{console.error(e.message);process.exit(1)});"
    paths = []
    for name, source in generated:
        destination = ASSETS / (name + '.svg')
        destination.write_text(source, encoding='utf-8')
        paths.append(str(ASSETS / name))
    subprocess.run([args.node, '-e', raster, args.sharp_module, json.dumps(paths)], check=True)
    (ASSETS / 'sculpture.svg').unlink(missing_ok=True)
    print('Generated: ' + ', '.join(name + '.svg / .png' for name, _ in generated))


if __name__ == '__main__':
    main()
