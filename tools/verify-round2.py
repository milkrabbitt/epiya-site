#!/usr/bin/env python3
"""Read-only release acceptance checks for EPIYA's second redesign.

Run with a Pillow-enabled Python, optionally --node /path/to/node and
--private-denylist /outside/repository/private-lines.txt. Findings never echo
private matched values. This is a static gate, not browser or payment proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from urllib.parse import unquote, urljoin, urlsplit

ORIGIN = "https://epiya.cn"
TEXT_TYPES = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".xml", ".txt", ".md", ".py", ".sh", ".webmanifest"}
IMAGE_TYPES = {".png", ".webp", ".jpg", ".jpeg", ".gif", ".avif"}
API_EXACT = {"/privacy", "/support", "/healthz", "/v1", "/upload"}
API_PREFIXES = ("/v1/", "/upload/")
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
MOBILE = re.compile(r"(?<![\dA-Za-z])(?:\+?86[ -]?)?1[3-9](?:[ -]?\d){9}(?![\dA-Za-z])")
SECRET = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})\b")
CLOSED = re.compile(r"暂未开放|尚未开放|暂不开放|待开放|未开通|尚未开通")
PRODUCT_IMAGE = re.compile(r"(?:^|/)(?:meow|relic|futures)-[^/]+\.(?:webp|png|jpe?g)$", re.I)
RETIRED_RASTER_HASHES = {
    "cff5d6e7b60b1a873331016e948a9a417759059e1277d8421d4515bfc89c5af9": "Original green-fiber social share image",
}

# Read-only browser expression. Evaluate on each real viewport and after each
# hover/theme/product/dialog action. A static pass cannot substitute for this.
BROWSER_PROBE = r"""(() => {
  const visible = el => { const s = getComputedStyle(el); return el.getClientRects().length && s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) !== 0; };
  const name = el => el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.classList.length ? '.' + [...el.classList].join('.') : '');
  const width = document.documentElement.clientWidth;
  const images = [...document.images].filter(visible).map(el => {
    const s = getComputedStyle(el), r = el.getBoundingClientRect(), w = +s.width.replace('px',''), h = +s.height.replace('px','');
    const product = /\/(meow|relic|futures)-[^/]+\.(webp|png|jpe?g)(?:\?|$)/i.test(el.currentSrc || el.src);
    const error = el.complete && !el.naturalWidth;
    const ratioError = el.naturalWidth && h ? Math.abs((w / h) / (el.naturalWidth / el.naturalHeight) - 1) : null;
    return {element:name(el),src:new URL(el.currentSrc || el.src,location.href).pathname,natural:[el.naturalWidth,el.naturalHeight],css:[w,h],bounds:[r.x,r.y,r.width,r.height],objectFit:s.objectFit,transform:s.transform,product,loaded:el.complete && !error,error,ratioError,distorted:!!(product && ratioError > .012),altPresent:el.hasAttribute('alt')};
  });
  const overflow = [...document.body.querySelectorAll('*')].filter(visible).filter(el => {
    const r=el.getBoundingClientRect(); return r.width > 0 && (r.right > width + 1 || r.left < -1) && !el.closest('dialog:not([open])');
  }).slice(0,30).map(el => {const r=el.getBoundingClientRect();return {element:name(el),left:r.left,right:r.right,width:r.width};});
  const controls = [...document.querySelectorAll('[aria-controls]')].filter(visible).map(el => ({element:name(el),expanded:el.getAttribute('aria-expanded'),targets:el.getAttribute('aria-controls').split(/\s+/).map(id=>({id,exists:!!document.getElementById(id)}))}));
  return {url:location.href,viewport:[innerWidth,innerHeight],clientWidth:width,scrollWidth:document.documentElement.scrollWidth,horizontalOverflow:document.documentElement.scrollWidth>width+1,images,overflow,controls,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,coarsePointer:matchMedia('(pointer: coarse)').matches,activeElement:name(document.activeElement),openDialogs:[...document.querySelectorAll('dialog[open]')].map(name),fonts:document.fonts?.status,scope:'Read-only rendered geometry; execute again after interactions and inspect full-page screenshots.'};
})()"""


def decoded_text(source):
    value = html.unescape(unquote(source))
    # Also inspect escaped JSON/JavaScript without executing it.
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), value)


def privacy_categories(source, private_values=()):
    value = decoded_text(source)
    categories = []
    if any(m.group().lower() != "contact@epiya.cn" for m in EMAIL.finditer(value)):
        categories.append("unapproved-email")
    if MOBILE.search(value):
        categories.append("personal-mobile-number")
    if re.search(r"(?:/Users/[^/\s]+/[^\s'\"/]+|[A-Z]:\\Users\\[^\\\s]+\\[^\s'\"]+|wxid_[A-Za-z0-9_]+)", value):
        categories.append("private-local-path-or-wechat-id")
    if SECRET.search(value):
        categories.append("credential-pattern")
    if any(item and item in value for item in private_values):
        categories.append("private-denylist-match")
    return categories


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements, self.refs, self.ids, self.visible = [], [], [], []
        self.buttons, self.active_button = [], None
        self.hidden_depth = 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a, line = dict(attrs), self.getpos()[0]
        self.elements.append((tag, a, line))
        if tag == "button":
            self.active_button = {"attrs": a, "line": line, "text": ""}
            self.buttons.append(self.active_button)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.append(a["name"])
        if tag in {"script", "style"}:
            self.hidden_depth += 1
        for key in ("src", "href", "poster", "action", "data-src", "data-full", "data-full-src"):
            if a.get(key):
                self.refs.append((a[key], f"{tag}.{key}", line))
        if a.get("srcset"):
            for item in a["srcset"].split(","):
                if item.strip():
                    self.refs.append((item.strip().split()[0], f"{tag}.srcset", line))
        if tag == "meta" and a.get("property") in {"og:image", "og:url"}:
            self.refs.append((a.get("content", ""), a["property"], line))

    def handle_endtag(self, tag):
        if tag == "button":
            self.active_button = None
        if tag in {"script", "style"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)

    def handle_data(self, data):
        if self.active_button is not None:
            self.active_button["text"] += data
        if not self.hidden_depth:
            self.visible.append(data)


def image_contract(attrs, natural, exact=False):
    """HTML attributes reserve the correct ratio before the image is loaded."""
    try:
        width, height = int(attrs.get("width", "")), int(attrs.get("height", ""))
    except (TypeError, ValueError):
        return "Missing positive integer width/height attributes"
    if width <= 0 or height <= 0:
        return "Image dimensions must be positive"
    if exact and (width, height) != natural:
        return f"Product image attributes {width}x{height} differ from file {natural[0]}x{natural[1]}"
    # Tiny icons are commonly rounded to integer CSS pixels. Allow at most
    # one pixel of proportional rounding, not arbitrary percentage scaling.
    if abs(width - height * natural[0] / natural[1]) > max(1, width * .012):
        return f"Image attributes distort the file aspect ratio ({natural[0]}x{natural[1]})"
    return None


def local_target(root, source, reference):
    url = urlsplit(urljoin(ORIGIN + "/" + source, reference))
    if url.scheme not in {"http", "https"} or url.hostname not in {"epiya.cn", "www.epiya.cn"}:
        return None, url
    if url.path in API_EXACT or url.path.startswith(API_PREFIXES):
        return None, url
    path = (root / unquote(url.path).lstrip("/")).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Reference escapes the public directory")
    return (path / "index.html" if path.is_dir() else path), url


def verify(args):
    root = args.root.resolve()
    findings, image_rows, externals, api_routes = [], [], set(), set()
    def add(level, file, check, message, line=None):
        row = {"level": level, "file": str(file), "check": check, "message": message}
        if line is not None:
            row["line"] = line
        findings.append(row)

    try:
        from PIL import Image
    except ImportError:
        Image = None
        add("error", ".", "image-decoder", "Pillow unavailable; image dimension verification was not performed")
    package_path = root / "tools/package.py"
    spec = importlib.util.spec_from_file_location("epiya_release_package", package_path)
    if not spec or not spec.loader:
        raise ValueError("tools/package.py release selector is required")
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    selected = package.selected_files(root)
    private_values = []
    if args.private_denylist:
        private_file = args.private_denylist.resolve()
        if private_file.is_relative_to(root):
            raise ValueError("Private denylist must remain outside the repository")
        private_values = [line.strip() for line in private_file.read_text().splitlines() if line.strip()]
    # Audit maintained source as well as published text. Never inspect git objects.
    source_files = {p.relative_to(root).as_posix(): p for p in root.rglob("*")
                    if p.is_file() and p.suffix.lower() in TEXT_TYPES
                    and not any(x in {".git", "node_modules", "__pycache__"} for x in p.relative_to(root).parts)}
    for name, path in source_files.items():
        if path.resolve() == Path(__file__).resolve():
            continue  # This checker intentionally contains synthetic detector fixtures.
        source = path.read_text(encoding="utf-8")
        if name.startswith("tools/test-") and name not in selected:
            # A standalone PEM header is a deliberate rejection fixture, not
            # key material. Only remove that exact quoted literal in tests;
            # complete keys, tokens, contacts and published files stay checked.
            source = re.sub(r'''b?(["'])-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\1''', "'<standalone rejection fixture>'", source)
        for category in privacy_categories(source, private_values):
            add("error", name, "privacy", category + " detected; matched value withheld")
    documents = {name: Document(path.read_text()) for name, path in selected.items() if path.suffix == ".html"}
    dimensions = {}
    if Image:
        for name, path in selected.items():
            if path.suffix.lower() in IMAGE_TYPES:
                try:
                    with Image.open(path) as im:
                        im.load()
                        dimensions[name] = im.size
                        if any(key in im.getexif() for key in (34853, 37510, 42032)):
                            add("error", name, "image-metadata", "GPS, user comment, or camera-owner EXIF must be removed")
                except Exception as exc:
                    add("error", name, "image-integrity", "Image cannot be decoded: " + type(exc).__name__)
    required = ("index.html", "products/meow/index.html", "products/relic/index.html", "products/futures-alpha/index.html",
                "downloads/index.html", "relic/pricing/index.html", "account/index.html", "about.html", "contact/index.html",
                "privacy.html", "terms.html", "meow/privacy.html", "meow/support.html", "404.html")
    for name in required:
        if name not in selected:
            add("error", name, "required-route", "Required public route missing")
    references = 0
    for name, doc in documents.items():
        for item, count in Counter(doc.ids).items():
            if count > 1:
                add("error", name, "duplicate-id", "Duplicate DOM identifier: " + item)
        for ref, kind, line in doc.refs:
            references += 1
            if ref.startswith("javascript:"):
                add("error", name, "link", "JavaScript URL is not an accessible navigation target", line)
                continue
            try:
                target, url = local_target(root, name, ref)
            except ValueError as exc:
                add("error", name, "link", str(exc), line)
                continue
            if url.scheme == "tel":
                add("error", name, "privacy", "Telephone link is not permitted by the current public contact policy", line)
            if url.scheme in {"http", "https"} and url.hostname not in {"epiya.cn", "www.epiya.cn"}:
                externals.add(url.geturl())
            if url.path in API_EXACT or url.path.startswith(API_PREFIXES):
                api_routes.add(url.path)
            if target:
                relative = target.relative_to(root).as_posix()
                if relative not in selected:
                    add("error", name, "link", f"Public target missing: {url.path}", line)
                elif url.fragment and relative in documents and unquote(url.fragment) not in documents[relative].ids:
                    add("error", name, "anchor", f"Anchor missing: {url.path}#{url.fragment}", line)
        scripts = [a for tag, a, _ in doc.elements if tag == "script"]
        for tag, a, line in doc.elements:
            for control in ("aria-controls", "aria-labelledby", "aria-describedby"):
                for identifier in a.get(control, "").split():
                    if identifier not in doc.ids:
                        add("error", name, "accessibility-hook", control + " target is absent: " + identifier, line)
            if tag == "a" and a.get("href") in {"", "#"}:
                add("error", name, "link", "Empty placeholder link", line)
            if tag == "button" and a.get("aria-expanded") and not a.get("aria-controls"):
                add("error", name, "accessibility-hook", "Expandable button does not identify its controlled region", line)
            if tag == "button" and any(k.startswith("data-") for k in a) and not scripts:
                add("error", name, "javascript-hook", "Script-dependent control has no script on its document", line)
            if tag == "dialog" and not (a.get("aria-label") or a.get("aria-labelledby")):
                add("error", name, "accessibility-hook", "Dialog needs an accessible name", line)
            if tag != "img":
                continue
            if "alt" not in a:
                add("error", name, "image-alt", "Image alt attribute is absent", line)
            target, _ = local_target(root, name, a.get("src", ""))
            if not target:
                continue
            relative = target.relative_to(root).as_posix()
            natural = dimensions.get(relative)
            if natural:
                error = image_contract(a, natural, bool(PRODUCT_IMAGE.search(relative)))
                image_rows.append({"page": name, "asset": relative, "natural": list(natural), "width": a.get("width"), "height": a.get("height")})
                if error:
                    legacy_missing = name.startswith("meow/") and error.startswith("Missing")
                    add("warning" if legacy_missing else "error", name, "image-dimensions", relative + ": " + error, line)
    # Asset URLs in stylesheets must survive the same release selection.
    for name, path in selected.items():
        if path.suffix == ".css":
            for ref in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", path.read_text()):
                target, _ = local_target(root, name, ref)
                if target and target.relative_to(root).as_posix() not in selected:
                    add("error", name, "css-asset", "CSS asset is outside the public release")
    for name, path in selected.items():
        if path.suffix.lower() in {".html", ".js", ".svg", ".css"}:
            value = path.read_text()
            if re.search(r"sculpture\.svg|fiber-canvas|sculpture-fallback", value):
                add("error", name, "retired-art", "Retired green fiber artwork is still referenced")
        if name == "assets/sculpture.svg":
            add("error", name, "retired-art", "Retired artwork remains in the public release")
        if path.suffix.lower() in IMAGE_TYPES and hashlib.sha256(path.read_bytes()).hexdigest() in RETIRED_RASTER_HASHES:
            add("error", name, "retired-art", "Retired social artwork remains in the public release")
    home = "".join(documents["index.html"].visible) if "index.html" in documents else ""
    if "把有趣的想法，做成好用的产品。" not in re.sub(r"\s+", "", home):
        add("error", "index.html", "approved-message", "Requested homepage sentence is absent")
    relic = "".join(documents["products/relic/index.html"].visible) if "products/relic/index.html" in documents else ""
    for concept, alternatives in {"profile": ("人物资料", "角色资料", "人物画像"), "style": ("语言风格", "表达风格", "语气"), "editable-memory": ("可编辑", "编辑记忆", "记忆可以编辑")}.items():
        if not any(word in relic for word in alternatives):
            add("error", "products/relic/index.html", "product-evidence", "Required visible concept absent: " + concept)
    for name in ("relic/pricing/index.html", "account/index.html"):
        doc = documents.get(name)
        if not doc:
            continue
        if not CLOSED.search("".join(doc.visible)):
            add("error", name, "commerce-closed", "Unavailable commerce/account state is not explicitly disclosed")
        for button in doc.buttons:
            a, label = button["attrs"], re.sub(r"\s+", "", button["text"])
            if re.search(r"立即购买|确认支付|立即充值|登录账户|登录并购买|创建订单|^充值$|^购买$|^支付$|^登录$", label) and "disabled" not in a and a.get("aria-disabled") != "true":
                add("error", name, "commerce-closed", "Enabled purchase/login action conflicts with the closed state", button["line"])
        for tag, a, line in doc.elements:
            if tag == "form" and not ("disabled" in a or a.get("aria-disabled") == "true"):
                add("error", name, "commerce-closed", "Active form exists while website account/purchase is closed", line)
            reference = a.get("href", "") + a.get("action", "")
            if re.search(r"(?:weixin|alipays?)://|/checkout(?:/|\?|$)|/payments?/(?:create|pay)", reference, re.I):
                add("error", name, "commerce-closed", "Active payment route exists while purchase is closed", line)
    for name, path in selected.items():
        if path.suffix in {".js", ".mjs"}:
            source = path.read_text()
            if re.search(r"(?:localStorage|sessionStorage)\s*\.\s*setItem\s*\(\s*['\"][^'\"]*(?:balance|wallet|credit|token)", source, re.I):
                add("error", name, "commerce-integrity", "Browser-local balance/credit writes are prohibited")
    try:
        releases = json.loads((root / "releases.json").read_text())
        for entry in releases:
            if entry.get("id") in {"relic", "futures"} and (entry.get("status") != "development" or entry.get("links")):
                add("error", "releases.json", "distribution", "Unreleased product is exposing a release/download link")
    except (OSError, ValueError, TypeError):
        add("error", "releases.json", "distribution", "Release configuration is invalid")
    manifest = root / "tools/sources.json"
    if manifest.is_file():
        for entry in json.loads(manifest.read_text()).get("assets", []):
            name = entry.get("output", "")
            if name not in selected:
                add("error", "tools/sources.json", "asset-provenance", "Manifest asset missing from release: " + name)
                continue
            actual_hash = hashlib.sha256(selected[name].read_bytes()).hexdigest()
            if entry.get("sha256") != actual_hash or tuple(entry.get("dimensions", [])) != dimensions.get(name):
                add("error", name, "asset-provenance", "Reviewed dimensions/hash differ from the released asset")
    else:
        add("error", "tools/sources.json", "asset-provenance", "Reviewed asset manifest is missing")
    node = args.node or shutil.which("node")
    js_files = [(name, path) for name, path in selected.items() if path.suffix in {".js", ".mjs"}]
    if js_files and not node:
        add("error", ".", "javascript-syntax", "Node unavailable; syntax checks were not performed")
    elif node:
        for name, path in js_files:
            result = subprocess.run([node, "--check", str(path)], text=True, capture_output=True)
            if result.returncode:
                add("error", name, "javascript-syntax", "Node syntax check failed; inspect source locally")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "scope": "Static source and selected release files; no network or production writes",
              "public_files": len(selected), "source_text_files": len(source_files), "html_documents": len(documents), "references": references,
              "decoded_raster_assets": len(dimensions), "image_attributes": image_rows, "external_urls_not_network_verified": sorted(externals),
              "backend_routes_not_static_files": sorted(api_routes), "private_denylist_supplied": bool(private_values),
              "errors": sum(f["level"] == "error" for f in findings), "warnings": sum(f["level"] == "warning" for f in findings), "findings": findings,
              "limits": ["Rendered CSS aspect ratios, clipping, contrast, focus, touch, motion and dialogs need real browser checks.",
                         "Image pixel privacy is established by source/visual review; this script does not perform OCR.",
                         "External availability, mailbox delivery and real payment acceptance are not asserted.",
                         "An external private denylist is required to check exact withdrawn personal names without embedding them in source."]}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("public_files", "html_documents", "references", "decoded_raster_assets", "errors", "warnings")}, ensure_ascii=False))
    for finding in findings:
        print(f"{finding['level'].upper()} {finding['file']} [{finding['check']}] {finding['message']}")
    return int(bool(report["errors"]))


class ContractTests(unittest.TestCase):
    def test_exact_product_dimensions_reject_one_pixel_error(self):
        self.assertIsNotNone(image_contract({"width": "660", "height": "1434"}, (660, 1435), True))

    def test_aspect_ratio_rejects_previous_tall_narrow_regression(self):
        self.assertIsNotNone(image_contract({"width": "215", "height": "1434"}, (660, 1434)))

    def test_proportional_nonproduct_icon_is_valid(self):
        self.assertIsNone(image_contract({"width": "20", "height": "20"}, (80, 80)))

    def test_encoded_email_is_detected_without_returning_the_value(self):
        categories = privacy_categories("name&#64;example.com")
        self.assertEqual(categories, ["unapproved-email"])

    def test_official_email_and_filing_numbers_are_not_personal_contacts(self):
        self.assertEqual(privacy_categories("contact@epiya.cn 浙公网安备33011302001543号 浙ICP备2026086186号-1"), [])

    def test_denied_text_is_never_echoed(self):
        self.assertEqual(privacy_categories("synthetic withdrawn name", ["withdrawn name"]), ["private-denylist-match"])

    def test_source_script_text_is_not_visible_state(self):
        doc = Document('<p>待开放</p><script>"Open checkout"</script>')
        self.assertEqual("".join(doc.visible), "待开放")

    def test_refs_include_zoom_and_social_images(self):
        doc = Document('<img src="/a.webp" data-full="/b.webp"><meta property="og:image" content="/c.png">')
        self.assertEqual({r[0] for r in doc.refs}, {"/a.webp", "/b.webp", "/c.png"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--node")
    parser.add_argument("--private-denylist", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--browser-probe", action="store_true", help="Print a read-only DOM geometry expression for real browser evaluation")
    args = parser.parse_args()
    if args.browser_probe:
        print(BROWSER_PROBE)
        return 0
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests))
        return int(not result.wasSuccessful())
    return verify(args)


if __name__ == "__main__":
    sys.exit(main())
