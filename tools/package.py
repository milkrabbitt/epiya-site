#!/usr/bin/env python3
"""Build a byte-identical static EPIYA archive from a pinned source tree.

Only public paths are selected. release.json is generated inside the archive;
the source tree is never modified. Gzip uses canonical stored DEFLATE blocks,
making its bytes independent of the host OS, filesystem metadata, Python gzip
header defaults, and zlib version. Already compressed image assets dominate
this site, so avoiding an additional compression dependency is inexpensive.
"""
import argparse
import binascii
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import tarfile
import tempfile

DATE = '2026-11-03'
ROOT_FILES = {
    '.nojekyll', '404.html', 'CNAME', 'about.html', 'changelog.html', 'index.html',
    'legacy.css', 'privacy.html', 'products.html', 'releases.json', 'robots.txt',
    'sitemap.xml', 'style.css', 'terms.html',
}
PUBLIC_DIRECTORIES = {'assets', 'meow', 'products', 'downloads', 'relic', 'account', 'contact', 'support'}
STATIC_SUFFIXES = {
    '.html', '.css', '.js', '.mjs', '.json', '.svg', '.png', '.webp', '.jpg',
    '.jpeg', '.gif', '.ico', '.avif', '.webm', '.mp4', '.woff', '.woff2',
    '.ttf', '.otf', '.txt', '.xml', '.webmanifest', '.pdf',
}
PRIVATE_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.sqlite', '.sqlite3', '.db', '.log', '.mobileprovision', '.trace', '.eml'}
TEXT_SUFFIXES = {'.html', '.css', '.js', '.mjs', '.json', '.svg', '.txt', '.xml', '.webmanifest'}
MAX_BYTES = 150 * 1024 * 1024
SECRET_PATTERNS = [
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})\b'),
    re.compile(rb'''(?:api[_-]?key|client[_-]?secret|merchant[_-]?secret|access[_-]?token|private[_-]?key)\s*["']?\s*[:=]\s*["']([A-Za-z0-9_+/.=-]{20,})["']''', re.I),
    re.compile(rb'/Users/apple/'),
]


def selected_files(source):
    selected = {}
    for name in ROOT_FILES:
        path = source / name
        if path.is_symlink():
            raise ValueError('Public source symlinks are prohibited: ' + name)
        if path.is_file():
            selected[name] = path
    for directory in sorted(PUBLIC_DIRECTORIES):
        start = source / directory
        if start.is_symlink():
            raise ValueError('Public directory symlinks are prohibited: ' + directory)
        if not start.exists():
            continue
        if not start.is_dir():
            raise ValueError('Expected a public directory: ' + directory)
        for path in start.rglob('*'):
            relative = path.relative_to(source)
            if any(part.startswith('.') or part.lower().startswith('readme') or part in {'tools', 'node_modules', '__pycache__'} for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError('Public source symlinks are prohibited: ' + str(relative))
            if not path.is_file():
                continue
            if path.suffix.lower() in PRIVATE_SUFFIXES or path.suffix.lower() not in STATIC_SUFFIXES:
                continue
            selected[relative.as_posix()] = path
    for name in ['index.html', 'CNAME', 'releases.json', 'meow/privacy.html', 'meow/support.html']:
        if name not in selected:
            raise ValueError('Required public file missing: ' + name)
    if selected['CNAME'].read_text().strip() != 'epiya.cn':
        raise ValueError('CNAME must retain epiya.cn')
    return selected


def info(name, size=0, directory=False):
    member = tarfile.TarInfo(name + '/' if directory else name)
    member.uid = member.gid = member.mtime = 0
    member.uname = member.gname = ''
    member.mode = 0o755 if directory else 0o644
    member.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    member.size = 0 if directory else size
    return member


def write_gzip(tar_stream, destination):
    # RFC 1952: MTIME=0, no optional filename, XFL=0, OS=255 (unknown).
    destination.write(b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff')
    crc = size = 0
    block = tar_stream.read(65535)
    while True:
        following = tar_stream.read(65535)
        final = not following
        length = len(block)
        # RFC 1951 stored block: BFINAL, BTYPE=00, byte padding, LEN, NLEN.
        destination.write(bytes([1 if final else 0]))
        destination.write(struct.pack('<HH', length, length ^ 0xffff))
        destination.write(block)
        crc = binascii.crc32(block, crc)
        size += length
        if final:
            break
        block = following
    destination.write(struct.pack('<II', crc & 0xffffffff, size & 0xffffffff))


def package(source, commit, output):
    source = source.resolve()
    if not source.is_dir():
        raise ValueError('Source must be an existing directory')
    if not re.fullmatch(r'[a-fA-F0-9]{40}', commit):
        raise ValueError('--commit must be the complete 40-character source commit SHA')
    commit = commit.lower()
    files = selected_files(source)
    entries = {}
    manifest = []
    total = 0
    # Read each selected file exactly once; manifest and tar therefore describe
    # the same byte snapshot even if another process edits the checkout later.
    for name, path in sorted(files.items()):
        data = path.read_bytes()
        total += len(data)
        if total > MAX_BYTES:
            raise ValueError('Public release exceeds 150 MiB')
        if path.suffix.lower() in TEXT_SUFFIXES and any(pattern.search(data) for pattern in SECRET_PATTERNS):
            raise ValueError('Potential private value in public file (value omitted): ' + name)
        entries[name] = data
        manifest.append({'path': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    release = {'sourceCommit': commit, 'date': DATE, 'files': manifest}
    entries['release.json'] = (json.dumps(release, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    if total + len(entries['release.json']) > MAX_BYTES:
        raise ValueError('Public release and manifest exceed 150 MiB')
    directories = set()
    for name in entries:
        for parent in Path(name).parents:
            if str(parent) != '.':
                directories.add(parent.as_posix())
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as tar_stream:
            with tarfile.open(fileobj=tar_stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for name in sorted(set(entries) | directories):
                    if name in directories:
                        archive.addfile(info(name, directory=True))
                    else:
                        archive.addfile(info(name, len(entries[name])), io.BytesIO(entries[name]))
            tar_stream.seek(0)
            with tempfile.NamedTemporaryFile(prefix='.' + output.name + '.', dir=output.parent, delete=False) as destination:
                temporary_name = destination.name
                write_gzip(tar_stream, destination)
                destination.flush()
                os.fsync(destination.fileno())
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, output)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    digest = hashlib.sha256()
    with output.open('rb') as archive:
        for block in iter(lambda: archive.read(1024 * 1024), b''):
            digest.update(block)
    return {'archive': str(output), 'sha256': digest.hexdigest(), 'size': output.stat().st_size,
            'sourceCommit': commit, 'date': DATE, 'files': len(entries), 'gzip': 'canonical-stored-deflate'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = package(args.source, args.commit, args.output)
    except (ValueError, OSError, tarfile.TarError) as error:
        parser.exit(1, 'Packaging failed: ' + str(error) + '\n')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
