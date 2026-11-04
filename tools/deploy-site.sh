#!/usr/bin/env bash
# Existing ECS only; no Nginx, backend, DNS or certificate changes.
# Usage: bash deploy-site.sh ABS_ARCHIVE SHA256 RELEASE_ID EXPECTED_OLD_COMMIT
# RELEASE_ID must be epiya-YYYYMMDD-<12-char source commit>, from release.json.
# Fetch this script from the same pinned Git commit as tools/package.py. The
# archive hash must equal the independently packaged and reviewed local hash.
set -euo pipefail
[[ $# -eq 4 ]] || { echo 'Usage: deploy-site.sh ABS_ARCHIVE SHA256 RELEASE_ID EXPECTED_OLD_COMMIT' >&2; exit 2; }
command -v python3 >/dev/null
exec python3 - "$@" <<'PY'
import datetime, fcntl, hashlib, json, os, re, shutil, subprocess, sys, tarfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

BASE = Path('/srv/epiya')
DOMAIN = 'epiya.cn'
LIMIT = 150 * 1024 * 1024
BACKEND = ('/healthz', '/privacy', '/support', '/upload', '/policy.css', '/upload.css', '/upload.js')
REQUIRED = ('index.html', '404.html', 'about.html', 'products.html', 'privacy.html', 'terms.html',
            'meow/index.html', 'meow/privacy.html', 'meow/support.html', 'style.css', 'CNAME', 'release.json')
SUFFIXES = {'.html', '.css', '.js', '.mjs', '.json', '.svg', '.png', '.webp', '.jpg', '.jpeg',
            '.gif', '.ico', '.avif', '.webm', '.mp4', '.woff', '.woff2', '.ttf', '.otf', '.txt',
            '.xml', '.webmanifest', '.pdf'}
TEXT = {'.html', '.css', '.js', '.mjs', '.json', '.svg', '.txt', '.xml', '.webmanifest'}
SECRETS = (re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
           re.compile(rb'\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})\b'))


def check(value, message):
    if not value:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_name(name):
    path = PurePosixPath(name)
    check(not path.is_absolute() and '..' not in path.parts and '\\' not in name, 'Unsafe archive path')
    check(not any(p.startswith('.') and p not in ('.nojekyll', '.well-known') for p in path.parts), 'Hidden source path')
    check(not any(p in ('tools', 'Backend', 'Tests', 'node_modules', '__pycache__') for p in path.parts), 'Non-public source path')
    return path.as_posix()


def inventory(root):
    check(root.is_dir() and not root.is_symlink(), 'Unexpected static root')
    files = {}
    for path in sorted(root.rglob('*')):
        check(not path.is_symlink(), 'Nested static symlink requires review')
        name = safe_name(path.relative_to(root).as_posix())
        if path.is_file():
            check(name in ('CNAME', '.nojekyll') or name.startswith('.well-known/') or path.suffix.lower() in SUFFIXES, 'Non-static public file: ' + name)
            data = path.read_bytes()
            files[name] = {'sha256': sha(data), 'size': len(data)}
        else:
            check(path.is_dir(), 'Special file in static tree')
    return files


def validate_manifest(root, files):
    doc = json.loads((root / 'release.json').read_text(encoding='utf-8'))
    check(re.fullmatch('[a-f0-9]{40}', doc.get('sourceCommit', '')) is not None, 'Invalid sourceCommit')
    date = datetime.datetime.strptime(doc.get('date', ''), '%Y-%m-%d').strftime('%Y-%m-%d')
    check(date == doc['date'], 'Invalid canonical release date')
    rows = doc.get('files')
    check(isinstance(rows, list) and rows, 'Empty manifest')
    listed = {}
    for row in rows:
        name = safe_name(row['path'])
        check(name == row['path'] and name not in listed and name != 'release.json', 'Invalid or duplicate manifest path')
        listed[name] = {'sha256': row['sha256'], 'size': row['size']}
    actual = {k: v for k, v in files.items() if k != 'release.json' and not k.startswith('.well-known/')}
    check(listed == actual, 'Manifest does not match complete public file set')
    return doc


def run(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check(proc.returncode == 0, 'Command failed: ' + args[0])
    return proc.stdout


def get(path):
    check(path.startswith('/') and not path.startswith('//') and not any(c in path for c in ('?', '#', '\n', '\r')), 'Invalid read-only probe path')
    raw = run(['curl', '--silent', '--show-error', '--noproxy', '*', '--request', 'GET',
               '--max-time', '20', '--connect-timeout', '5', '--proto', '=https', '--tlsv1.2',
               '--resolve', DOMAIN + ':443:127.0.0.1', '-H', 'Accept-Encoding: identity',
               '-H', 'Cache-Control: no-cache', '-w', '\n%{http_code}',
               'https://' + DOMAIN + quote(path, safe='/.-_')])
    body, status = raw.rsplit(b'\n', 1)
    return int(status), body


def require(probe, path, checksum, statuses=(200,)):
    status, data = probe(path)
    check(status in statuses and sha(data) == checksum, 'HTTPS content/status mismatch: ' + path)
    return {'path': path, 'status': status, 'sha256': checksum}


def nginx_state():
    run(['nginx', '-t'])
    return sha(run(['nginx', '-T']))


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(str(temporary), 0o600)
    os.replace(str(temporary), str(path))


def set_link(base, live, target, release_id):
    temporary = base / ('.website-swap-' + release_id)
    check(not temporary.exists() and not temporary.is_symlink(), 'Temporary symlink already exists')
    os.symlink(str(target), str(temporary))
    os.replace(str(temporary), str(live))
    fd = os.open(str(base), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def extract(archive, stage):
    with tarfile.open(str(archive), 'r:gz') as source:
        members = source.getmembers()
        check(len(members) <= 20000, 'Too many archive entries')
        seen, total = set(), 0
        for member in members:
            name = safe_name(member.name)
            check(member.isfile() or member.isdir(), 'Links/devices/special archive members prohibited')
            if name in ('', '.'):
                check(member.isdir(), 'Invalid archive root')
                continue
            check(name not in seen, 'Duplicate normalized archive path')
            seen.add(name)
            check(not name.startswith('.well-known/'), 'Certificate workflow is preserved from current server, not archive')
            if member.isfile():
                check(name in ('CNAME', '.nojekyll') or PurePosixPath(name).suffix.lower() in SUFFIXES, 'Non-static archive file')
                check('/' + name not in BACKEND and not name.startswith(('v1/', 'v2/')), 'Archive shadows protected backend')
                total += member.size
                check(0 <= member.size <= LIMIT and total <= LIMIT, 'Static release exceeds size limit')
        for member in members:
            name = safe_name(member.name)
            if name in ('', '.'):
                continue
            target = stage / name
            check(within(target.resolve(), stage.resolve()), 'Archive escaped staging root')
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                os.chmod(str(target), 0o755)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as incoming, target.open('xb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
                check(target.stat().st_size == member.size, 'Truncated archive member')
                os.chmod(str(target), 0o644)
        for path in stage.rglob('*'):
            if path.is_dir():
                os.chmod(str(path), 0o755)


def deploy(archive, expected_sha, release_id, expected_old, base=BASE, probe=get, config=nginx_state):
    check(re.fullmatch('[a-f0-9]{64}', expected_sha) is not None, 'Invalid archive SHA256')
    check(re.fullmatch('[a-f0-9]{40}', expected_old) is not None, 'Expected current sourceCommit is required')
    check(re.fullmatch('epiya-[0-9]{8}-[a-f0-9]{12}', release_id) is not None, 'Invalid release ID')
    check(archive.is_absolute() and archive.is_file() and not archive.is_symlink(), 'Archive must be an absolute regular file')
    check(archive.stat().st_size <= LIMIT and sha(archive.read_bytes()) == expected_sha, 'Uploaded archive SHA256/size mismatch')
    check(base.is_dir() and not base.is_symlink(), 'Unexpected ECS static base')
    live, releases, backups = base / 'site-20261009', base / 'releases', base / 'website-releases'
    check(live.is_symlink(), 'Expected existing static root symlink; inspect changed deployment topology')
    check(all(p.is_dir() and not p.is_symlink() for p in (releases, backups)), 'Unexpected release/backup directories')
    old_link, old_root = os.readlink(str(live)), live.resolve()
    check(within(old_root, releases.resolve()) and old_root != releases.resolve(), 'Current root outside release directory')
    old_files = inventory(old_root)
    old_manifest = validate_manifest(old_root, old_files)
    check(old_manifest['sourceCommit'] == expected_old, 'Current sourceCommit changed; stop and review')
    stage, backup = releases / release_id, backups / release_id
    check(all(not p.exists() and not p.is_symlink() for p in (stage, backup)), 'Release ID already used; inspect receipt before retrying')
    needed = sum(v['size'] for v in old_files.values()) + LIMIT + 100 * 1024 * 1024
    check(shutil.disk_usage(str(base)).free > needed, 'Insufficient free disk for release and backup')
    old_index = old_files['index.html']['sha256']
    require(probe, '/', old_index)
    nginx_before = config()
    baseline = {}
    for path in BACKEND:
        status, body = probe(path)
        check(status == 200, 'Backend baseline failed: ' + path)
        if path == '/healthz':
            health = json.loads(body.decode('utf-8'))
            check(health.get('ok') is True and health.get('service') == 'relic', 'Relic baseline unhealthy')
        baseline[path] = {'status': status, 'sha256': sha(body)}
    backup.mkdir(mode=0o700)
    os.chmod(str(backup), 0o700)
    record = backup / 'deployment.json'
    receipt = {'releaseId': release_id, 'phase': 'preparing', 'archiveSha256': expected_sha,
               'previousCommit': expected_old, 'oldSymlink': old_link, 'oldRoot': str(old_root),
               'oldIndexSha256': old_index, 'newRoot': str(stage), 'liveRoot': str(live),
               'nginxModified': False, 'backendModified': False, 'nginxConfigurationSha256': nginx_before,
               'backendBefore': baseline, 'startedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write_json(record, receipt)
    try:
        stage.mkdir(mode=0o755)
        extract(archive, stage)
        new_files = inventory(stage)
        manifest = validate_manifest(stage, new_files)
        expected_id = 'epiya-' + manifest['date'].replace('-', '') + '-' + manifest['sourceCommit'][:12]
        check(release_id == expected_id, 'Release ID does not match canonical manifest date and commit')
        check(manifest['sourceCommit'] != expected_old, 'Refusing same-commit replacement')
        check(all(name in new_files for name in REQUIRED), 'Required website/policy paths missing')
        old_html = {name for name in old_files if name.endswith('.html')}
        check(old_html.issubset(new_files), 'Existing public HTML paths must be retained')
        check((stage / 'CNAME').read_bytes() == (old_root / 'CNAME').read_bytes() and (stage / 'CNAME').read_text().strip() == DOMAIN, 'CNAME changed')
        homepage = (stage / 'index.html').read_text(encoding='utf-8')
        for value in ('杭州壹湃科技有限公司', '浙ICP备2026086186号-1', '浙公网安备33011302001543号'):
            check(value in homepage, 'Company or filing absent from homepage')
        for name in new_files:
            if Path(name).suffix.lower() in TEXT:
                check(not any(pattern.search((stage / name).read_bytes()) for pattern in SECRETS), 'Potential secret in public text: ' + name)
        # Challenge files stay byte-identical without changing the certificate workflow.
        if (old_root / '.well-known').exists():
            check(not (stage / '.well-known').exists(), 'Archive unexpectedly supplies certificate directory')
            shutil.copytree(str(old_root / '.well-known'), str(stage / '.well-known'))
        new_files = inventory(stage)
        shutil.copytree(str(old_root), str(backup / 'previous-root'))
        check(inventory(backup / 'previous-root') == old_files, 'Backup failed full hash verification')
        write_json(backup / 'old-link.json', {'sourceCommit': expected_old, 'oldSymlink': old_link, 'files': old_files})
        check(live.is_symlink() and os.readlink(str(live)) == old_link and inventory(old_root) == old_files, 'Current release changed during preparation')
        require(probe, '/', old_index)
        check(config() == nginx_before, 'Nginx configuration changed during preparation')
        receipt.update({'phase': 'prepared', 'sourceCommit': manifest['sourceCommit'],
                        'privateBackup': str(backup / 'previous-root'), 'manifestSha256': new_files['release.json']['sha256']})
        write_json(record, receipt)
        set_link(base, live, stage, release_id)
        receipt['phase'] = 'switched'
        write_json(record, receipt)
        verified = []
        for name, item in sorted(new_files.items()):
            if name == '.nojekyll' or name.startswith('.well-known/'):
                continue
            verified.append(require(probe, '/' + name, item['sha256'], (200, 404) if name == '404.html' else (200,)))
            if name == 'index.html' or name.endswith('/index.html'):
                alias = '/' if name == 'index.html' else '/' + name[:-len('index.html')]
                verified.append(require(probe, alias, item['sha256']))
        require(probe, '/__static_missing_' + manifest['sourceCommit'][:12] + '/', new_files['404.html']['sha256'], (404,))
        for path, item in baseline.items():
            require(probe, path, item['sha256'])
        check(config() == nginx_before, 'Nginx configuration changed during deployment')
        check(live.is_symlink() and live.resolve() == stage.resolve(), 'Another release replaced this deployment')
        receipt.update({'phase': 'healthy', 'verified': verified, 'backendAfter': baseline,
                        'finishedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat()})
        write_json(record, receipt)
        return {'result': 'deployed', 'releaseId': release_id, 'sourceCommit': manifest['sourceCommit'],
                'verifiedCount': len(verified), 'url': 'https://' + DOMAIN, 'receipt': str(record),
                'nginxModified': False, 'backendModified': False}
    except BaseException as failure:
        receipt.update({'phase': 'failed-before-switch', 'error': str(failure)})
        if live.is_symlink() and live.resolve() == stage.resolve():
            try:
                set_link(base, live, old_link, release_id)
                require(probe, '/', old_index)
                for path, item in baseline.items():
                    require(probe, path, item['sha256'])
                check(config() == nginx_before, 'Nginx configuration changed independently')
                receipt['phase'] = 'rolled-back'
            except BaseException as rollback_failure:
                receipt.update({'phase': 'rollback-needs-attention', 'rollbackError': str(rollback_failure)})
        elif not live.is_symlink() or os.readlink(str(live)) != old_link:
            receipt['phase'] = 'concurrent-change-needs-attention'
        receipt['finishedAtUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(record, receipt)
        raise RuntimeError(receipt['phase'] + ': ' + str(failure) + '; receipt=' + str(record))


def main():
    check(len(sys.argv) == 5, 'Expected four deployment arguments')
    check(sys.platform == 'linux' and os.geteuid() == 0, 'Existing Linux ECS root only')
    check(shutil.which('curl') and shutil.which('nginx'), 'curl and nginx are required')
    check(BASE.is_dir() and not BASE.is_symlink(), 'Existing static base required')
    with (BASE / '.website-deploy.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = deploy(Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'result': 'failed', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
PY
