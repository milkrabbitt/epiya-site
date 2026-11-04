#!/usr/bin/env bash
# Prepared release script. Creates no infrastructure or Nginx configuration.
# Run on the existing ECS after static/browser QA and root verification:
#   bash deploy-site.sh /tmp/epiya-site-20261103.tar.gz ARCHIVE_SHA256 RELEASE_ID
# RELEASE_ID is epiya-20261103-<source-commit-prefix>, derived by the release owner
# from release.json; archive SHA256 is separately computed after packaging.
# Optional read-only backend probes, set explicitly from confirmed live routes:
#   EPIYA_BACKEND_HEALTH_PATHS='/v1/health,/v1/public/config' bash ...
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo 'Usage: deploy-site.sh ABSOLUTE_ARCHIVE EXPECTED_SHA256 RELEASE_ID' >&2
  exit 2
fi
command -v python3 >/dev/null
exec python3 - "$@" <<'PY'
import ctypes
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse

archive = Path(sys.argv[1])
expected_sha = sys.argv[2].lower()
release_id = sys.argv[3]
base = Path('/srv/epiya')
live = base / 'site-20261009'
domain = 'epiya.cn'
required = ['index.html', 'about.html', 'products.html', 'privacy.html',
            'meow/index.html', 'meow/privacy.html', 'meow/support.html', 'style.css', 'CNAME', 'release.json']
backend_paths = [p.strip() for p in os.environ.get('EPIYA_BACKEND_HEALTH_PATHS', '').split(',') if p.strip()]
max_unpacked = 150 * 1024 * 1024


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def command(args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        # No request URLs contain credentials; do not print raw Nginx config.
        raise RuntimeError('Command failed: ' + args[0] + ' (exit ' + str(result.returncode) + ')')
    return result.stdout


def nginx_digest():
    return hashlib.sha256(command(['nginx', '-T'])).hexdigest()


def exchange(first, second):
    libc = ctypes.CDLL(None, use_errno=True)
    operation = getattr(libc, 'renameat2', None)
    check(operation is not None, 'libc renameat2 unavailable; atomic deployment stopped')
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    if operation(-100, os.fsencode(first), -100, os.fsencode(second), 2) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def get(path, allow_error=False):
    check(path.startswith('/') and not path.startswith('//') and not any(c in path for c in ['?', '#', '\n', '\r']), 'Invalid health path')
    args = ['curl', '--silent', '--show-error', '--noproxy', '*', '--max-time', '20',
            '--connect-timeout', '5', '--proto', '=https', '--resolve', domain + ':443:127.0.0.1',
            '-H', 'Accept-Encoding: identity', '-w', '\n%{http_code}', 'https://' + domain + urllib.parse.quote(path, safe='/.-_')]
    raw = command(args)
    body, code = raw.rsplit(b'\n', 1)
    status = int(code)
    check(allow_error or status == 200, 'HTTPS health failed for ' + path + ': ' + str(status))
    return status, body


check(os.geteuid() == 0, 'Run on existing ECS as root; no local deployment is supported')
check(sys.platform == 'linux', 'This script is for the existing Linux ECS only')
check(archive.is_absolute() and archive.is_file() and not archive.is_symlink(), 'Archive must be an uploaded regular file at an absolute path')
check(re.fullmatch(r'[a-f0-9]{64}', expected_sha) is not None, 'Expected SHA256 is required')
check(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,70}', release_id) is not None, 'Invalid release ID')
check(base.is_dir() and not base.is_symlink(), 'Unexpected /srv/epiya layout')
check(live.is_dir(), 'Existing static document root missing; refusing to create a replacement site')
resolved_live = live.resolve()
check(resolved_live != base and resolved_live.is_relative_to(base), 'Existing live root resolves outside /srv/epiya')
check(sha(archive) == expected_sha, 'Uploaded archive SHA256 mismatch')
for binary in ['curl', 'nginx', 'tar']:
    check(shutil.which(binary) is not None, binary + ' is required')
for path in backend_paths:
    check(path.startswith('/v1/') or path in ['/health', '/healthz'], 'Backend health probes must be explicit known read-only health/config paths')

lock = (base / '.website-deploy.lock').open('a')
fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
backup = base / 'website-releases' / release_id
releases = base / 'releases'
check(not releases.is_symlink(), 'Releases directory cannot be a symlink')
releases.mkdir(exist_ok=True, mode=0o755)
stage = releases / release_id
check(not backup.exists() and not stage.exists(), 'Release ID already exists; inspect the previous receipt before retrying')
backup.mkdir(parents=True, mode=0o700)
stage.mkdir(mode=0o755)
receipt_path = backup / 'deployment.json'
receipt = {
    'releaseId': release_id, 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'archiveSha256': expected_sha, 'domain': domain, 'liveRoot': str(live),
    'phase': 'preparing', 'nginxModified': False, 'backendHealthPaths': backend_paths,
    'oldRootKind': 'symlink' if live.is_symlink() else 'directory',
}
switched = False
previous = None
old_symlink = os.readlink(live) if live.is_symlink() else None
nginx_before = None
old_index_sha = sha(resolved_live / 'index.html')


def save_receipt():
    temp = receipt_path.with_suffix('.tmp')
    temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    os.chmod(temp, 0o600)
    os.replace(temp, receipt_path)


def validate_archive():
    with tarfile.open(archive, 'r:*') as source:
        members = source.getmembers()
        size = 0
        seen = set()
        for member in members:
            path = PurePosixPath(member.name)
            check(not path.is_absolute() and '..' not in path.parts and '\\' not in member.name, 'Unsafe archive member path')
            check(member.isfile() or member.isdir(), 'Archive links/devices/special files are prohibited')
            if str(path) in ('', '.'):
                check(member.isdir(), 'Invalid root member')
                continue
            check(str(path) not in seen, 'Duplicate archive member')
            seen.add(str(path))
            check(not any(p in ['.git', '.aws', '.ssh', '__MACOSX'] or p.startswith('.env') for p in path.parts), 'Private repository/runtime member in archive')
            check(not any(p.startswith('.') and p not in ['.well-known', '.nojekyll'] for p in path.parts), 'Hidden source/runtime files must not be published')
            check('tools' not in path.parts, 'Build tools must not be included in the public archive')
            check(path.suffix.lower() not in ['.pem', '.key', '.p12', '.db', '.sqlite', '.mobileprovision'], 'Private/server artifact in archive')
            size += member.size
            check(member.size >= 0 and size <= max_unpacked, 'Archive exceeds static release size limit')
        check(shutil.disk_usage(base).free > size * 3 + 100 * 1024 * 1024, 'Insufficient free space for safe release and backup')
        # Manual extraction deliberately refuses links and path traversal. It
        # does not depend on Python's version-specific tar extraction filter.
        for member in members:
            relative = PurePosixPath(member.name)
            if str(relative) in ('', '.'):
                continue
            target = stage.joinpath(*relative.parts)
            check(target.resolve().is_relative_to(stage), 'Archive escaped staging directory')
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
                os.chmod(target, 0o755)
                continue
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            with source.extractfile(member) as incoming, target.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
            check(target.stat().st_size == member.size, 'Truncated archive member')
            os.chmod(target, 0o644)
    for path in required:
        check((stage / path).is_file(), 'Required retained public path missing: ' + path)
    provenance = json.loads((stage / 'release.json').read_text())
    source_commit = provenance.get('sourceCommit', '')
    check(re.fullmatch(r'[a-fA-F0-9]{40}', source_commit) is not None, 'release.json needs the complete sourceCommit SHA')
    check(release_id == 'epiya-20261103-' + source_commit[:12].lower(), 'Release ID does not match release.json sourceCommit')
    receipt['sourceCommit'] = source_commit.lower()
    # Preserve policy/help content and existing product assets. Head metadata
    # may be enriched for SEO; the legacy stylesheet itself remains unchanged.
    for old_file in list((resolved_live / 'meow').rglob('*')) + [resolved_live / 'style.css']:
        if old_file.is_file():
            relative = old_file.relative_to(resolved_live)
            check(not old_file.is_symlink(), 'Retained legacy file is a symlink')
            check((stage / relative).is_file(), 'Retained legacy file missing: ' + str(relative))
            if old_file.suffix == '.html':
                old_main = re.search(r'<main\b[^>]*>([\s\S]*?)</main>', old_file.read_text(), re.I)
                new_main = re.search(r'<main\b[^>]*>([\s\S]*?)</main>', (stage / relative).read_text(), re.I)
                check(old_main and new_main and old_main.group(1) == new_main.group(1), 'Retained product page content changed: ' + str(relative))
            else:
                check(sha(old_file) == sha(stage / relative), 'Retained legacy asset changed: ' + str(relative))
    check((stage / 'CNAME').read_text().strip() == domain, 'CNAME changed')
    homepage = (stage / 'index.html').read_text()
    for filing in ['浙ICP备2026086186号-1', '浙公网安备33011302001543号']:
        check(filing in homepage, 'Verified website filing is absent from homepage')
    # ACME challenge files, if hosted in this static root, belong to the
    # existing certificate workflow. Preserve them without changing Nginx.
    existing_well_known = resolved_live / '.well-known'
    if existing_well_known.exists():
        check(existing_well_known.is_dir() and not existing_well_known.is_symlink(), 'Unexpected .well-known layout')
        check(not any(p.is_symlink() for p in existing_well_known.rglob('*')), '.well-known symlink requires manual review')
        shutil.copytree(existing_well_known, stage / '.well-known', dirs_exist_ok=True)
    receipt['unpackedBytes'] = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())


def restore():
    if old_symlink is not None:
        replacement = base / ('.website-restore-' + release_id)
        check(not replacement.exists() and not replacement.is_symlink(), 'Rollback temporary path occupied')
        os.symlink(old_symlink, replacement)
        os.replace(replacement, live)
    else:
        exchange(live, previous)
    check(hashlib.sha256(get('/index.html')[1]).hexdigest() == old_index_sha, 'Rollback content verification failed')
    check(nginx_digest() == nginx_before, 'Nginx config changed independently during rollback')


try:
    validate_archive()
    command(['nginx', '-t'])
    nginx_before = nginx_digest()
    receipt['nginxConfigurationSha256'] = nginx_before
    baseline = {p: get(p, allow_error=True)[0] for p in backend_paths}
    receipt['backendBeforeStatus'] = baseline
    # Verify current document-root assumptions before any mutation.
    check(hashlib.sha256(get('/index.html')[1]).hexdigest() == old_index_sha, 'HTTPS currently serves another root; refusing deployment')
    if old_symlink is None:
        with tempfile.TemporaryDirectory(prefix='.website-atomic-probe-', dir=base) as probe:
            first, second = Path(probe) / 'a', Path(probe) / 'b'
            target = Path(probe) / 'target'
            first.mkdir(); target.mkdir()
            (first / 'a').write_text('a'); (target / 'b').write_text('b')
            os.symlink(target, second)
            exchange(first, second)
            check(first.is_symlink() and (first / 'b').is_file() and (second / 'a').is_file(), 'Atomic directory/symlink exchange probe failed')
    backup_tar = backup / 'original-site.tar.gz'
    command(['tar', '--numeric-owner', '-czf', str(backup_tar), '-C', str(resolved_live), '.'])
    command(['tar', '-tzf', str(backup_tar)])
    receipt['backupArchive'] = str(backup_tar)
    receipt['backupSha256'] = sha(backup_tar)
    receipt['oldIndexSha256'] = old_index_sha
    receipt['oldSymlink'] = old_symlink
    expected_pages = {str(p.relative_to(stage)): sha(p) for p in stage.rglob('*.html')}
    receipt['phase'] = 'prepared'
    save_receipt()
    replacement = base / ('.website-link-' + release_id)
    check(not replacement.exists() and not replacement.is_symlink(), 'Temporary symlink path occupied')
    os.symlink(stage, replacement)
    if old_symlink is not None:
        os.replace(replacement, live)
        switched = True
    else:
        exchange(live, replacement)
        switched = True
        previous = replacement
        previous_destination = backup / 'previous-root'
        os.replace(previous, previous_destination)
        previous = previous_destination
        receipt['previousRoot'] = str(previous)
    receipt['newRoot'] = str(stage)
    receipt['phase'] = 'switched'
    save_receipt()
    verified = []
    for path, checksum in sorted(expected_pages.items()):
        body = get('/' + path)[1]
        check(hashlib.sha256(body).hexdigest() == checksum, 'Deployed content differs from release: ' + path)
        verified.append('/' + path)
    check(hashlib.sha256(get('/')[1]).hexdigest() == expected_pages['index.html'], 'Homepage root does not serve release index')
    after = {p: get(p, allow_error=True)[0] for p in backend_paths}
    check(after == baseline, 'Backend health HTTP status changed')
    check(nginx_digest() == nginx_before, 'Nginx configuration changed independently; refusing successful receipt')
    receipt.update({'phase': 'healthy', 'verifiedHtmlPaths': verified, 'backendAfterStatus': after,
                    'finishedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    save_receipt()
    print(json.dumps({'result': 'deployed', 'url': 'https://' + domain, 'releaseId': release_id,
                      'verifiedHtmlCount': len(verified), 'receipt': str(receipt_path),
                      'backup': str(backup_tar), 'nginxModified': False}))
except BaseException as failure:
    receipt['error'] = str(failure)
    receipt['phase'] = 'failed-before-switch'
    if switched:
        try:
            restore()
            receipt['phase'] = 'rolled-back'
        except BaseException as rollback_failure:
            receipt['phase'] = 'rollback-needs-attention'
            receipt['rollbackError'] = str(rollback_failure)
    receipt['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_receipt()
    print(json.dumps({'result': receipt['phase'], 'error': str(failure), 'receipt': str(receipt_path)}), file=sys.stderr)
    sys.exit(1)
PY
