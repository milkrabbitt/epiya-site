#!/usr/bin/env python3
"""Offline release checks using isolated fixtures; never rebuild preview HTML."""
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('site_package', Path(__file__).with_name('package.py'))
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class ProductionPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.output = self.root / 'release.tar.gz'
        for name, content in {
            'index.html': '<!doctype html><title>Production</title>',
            'CNAME': 'epiya.cn\n',
            'releases.json': '{}',
            'meow/privacy.html': '<title>Privacy</title>',
            'meow/support.html': '<title>Support</title>',
            'investment/index.html': '<title>Investment</title>',
            'assets/themes/new-skin.webp': 'fixture image bytes',
            'robots.txt': 'User-agent: *\nAllow: /\nDisallow: /v1/\nDisallow: /upload\n',
        }.items():
            self.write(name, content)

    def write(self, name, content):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def package(self):
        return PACKAGE.package(self.source, 'a' * 40, self.output)

    def test_investment_and_nested_assets_in_archive_and_manifest(self):
        self.package()
        with tarfile.open(str(self.output), 'r:gz') as archive:
            manifest = json.load(archive.extractfile('release.json'))
            rows = {row['path']: row for row in manifest['files']}
            for name in ('investment/index.html', 'assets/themes/new-skin.webp'):
                data = archive.extractfile(name).read()
                self.assertEqual(data, (self.source / name).read_bytes())
                self.assertEqual(rows[name]['size'], len(data))
                self.assertEqual(rows[name]['sha256'], PACKAGE.hashlib.sha256(data).hexdigest())

    def test_noindex_in_any_public_html_rejected_before_archive_replacement(self):
        self.output.write_bytes(b'previous release')
        self.write('investment/index.html', '<META CONTENT="follow, NOINDEX" NAME="ROBOTS"/>')
        with self.assertRaisesRegex(ValueError, 'noindex/none.*investment/index.html'):
            self.package()
        self.assertEqual(self.output.read_bytes(), b'previous release')

    def test_none_robots_directive_is_rejected(self):
        self.write('index.html', '<meta name="robots" content="none">')
        with self.assertRaisesRegex(ValueError, 'noindex/none'):
            self.package()
        self.assertFalse(self.output.exists())

    def test_global_disallow_rejected_with_case_spacing_and_comment(self):
        self.write('robots.txt', '\ufeffUser-agent: *\r\n  DISALLOW : /  # preview\r\n')
        with self.assertRaisesRegex(ValueError, 'robots.txt Disallow'):
            self.package()
        self.assertFalse(self.output.exists())

    def test_documentation_and_scoped_disallow_remain_allowed(self):
        self.write('index.html', '<title>Production</title><meta name="robots" content="index,follow">'
                   '<p>noindex is only for previews.</p><!-- <meta name="robots" content="none"> -->')
        result = self.package()
        self.assertTrue(self.output.is_file())
        self.assertEqual(result['sourceCommit'], 'a' * 40)


if __name__ == '__main__':
    unittest.main()
