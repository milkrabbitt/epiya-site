#!/usr/bin/env python3
"""Build a byte-identical static EPIYA archive from a pinned source tree.

Only public paths are selected. release.json is generated inside the archive;
the source tree is never modified. USTAR headers and gzip stored DEFLATE blocks
are written as fixed bytes, without tarfile/gzip writer defaults. Source
filesystem metadata and zlib compression are not inputs. The server must still
compare the resulting archive SHA256 with the locally verified expected hash.
"""
import argparse
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import tempfile

DATE = '2026-11-04'
ROOT_FILES = {
    '.nojekyll', '404.html', 'CNAME', 'about.html', 'changelog.html', 'index.html',
    'legacy.css', 'privacy.html', 'products.html', 'releases.json', 'robots.txt',
    'sitemap.xml', 'style.css', 'terms.html', 'services.html',
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
    if selected['CNAME'].read_text(encoding='utf-8').strip() != 'epiya.cn':
        raise ValueError('CNAME must retain epiya.cn')
    return selected


def octal(value, width):
    encoded = format(value, 'o').encode('ascii')
    if value < 0 or len(encoded) >= width:
        raise ValueError('USTAR numeric field exceeds its fixed width')
    return b'0' * (width - 1 - len(encoded)) + encoded + b'\0'


def ustar_header(name, size=0, directory=False):
    name = name + '/' if directory else name
    encoded = name.encode('utf-8')
    if b'\0' in encoded or name.startswith('/') or '..' in name.split('/'):
        raise ValueError('Unsafe USTAR entry name')
    prefix = b''
    if len(encoded) > 100:
        # Choose the final split that fits both fixed USTAR name fields.
        split = None
        for position in range(len(encoded) - 1, 0, -1):
            if encoded[position:position + 1] == b'/' and position <= 155 and 0 < len(encoded) - position - 1 <= 100:
                split = position
                break
        if split is None:
            raise ValueError('Public path does not fit fixed USTAR fields: ' + name)
        prefix, encoded = encoded[:split], encoded[split + 1:]
    header = bytearray(512)
    header[0:len(encoded)] = encoded
    header[100:108] = octal(0o755 if directory else 0o644, 8)
    header[108:116] = octal(0, 8)  # uid
    header[116:124] = octal(0, 8)  # gid
    header[124:136] = octal(0 if directory else size, 12)
    header[136:148] = octal(0, 12)  # mtime
    header[148:156] = b'        '  # checksum field is spaces while summing
    header[156:157] = b'5' if directory else b'0'
    header[257:263] = b'ustar\0'
    header[263:265] = b'00'
    # linkname, uname and gname remain NUL-filled.
    header[329:337] = octal(0, 8)  # devmajor
    header[337:345] = octal(0, 8)  # devminor
    header[345:345 + len(prefix)] = prefix
    checksum = format(sum(header), '06o').encode('ascii')
    if len(checksum) != 6:
        raise ValueError('Unexpected USTAR checksum width')
    header[148:156] = checksum + b'\0 '
    return bytes(header)


def write_tar(entries, directories, destination):
    for name in sorted(set(entries) | directories):
        if name in directories:
            destination.write(ustar_header(name, directory=True))
        else:
            data = entries[name]
            destination.write(ustar_header(name, len(data)))
            destination.write(data)
            destination.write(b'\0' * ((-len(data)) % 512))
    destination.write(b'\0' * 1024)  # two end-of-archive records
    destination.write(b'\0' * ((-destination.tell()) % 10240))


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
            write_tar(entries, directories, tar_stream)
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
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
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
    except (ValueError, OSError) as error:
        parser.exit(1, 'Packaging failed: ' + str(error) + '\n')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
