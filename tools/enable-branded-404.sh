#!/usr/bin/env bash
# On the original ECS only, after the new static site has passed deployment QA:
#   bash enable-branded-404.sh /etc/nginx/sites-available/ACTUAL_CONFIG RELEASE_ID
# Restore this one configuration change later:
#   bash enable-branded-404.sh --rollback /srv/epiya/nginx-404-backups/RELEASE_ID
# Does not rewrite any location, proxy_pass, or API include.
set -euo pipefail
if [[ $# -ne 2 ]]; then echo 'Usage: enable-branded-404.sh CONFIG RELEASE_ID | --rollback BACKUP_DIRECTORY' >&2; exit 2; fi
exec python3 - "$@" <<'PY'
import datetime, fcntl, hashlib, json, os, re, stat, subprocess, sys, tempfile, time
from pathlib import Path

BASE = Path('/srv/epiya')
LIVE = BASE / 'site-20261009'
INCLUDE = Path('/etc/nginx/relic-locations.conf')
PROBES = ['/privacy', '/support', '/v1/__epiya_404_probe__', '/upload']


def check(value, message):
    if not value:
        raise RuntimeError(message)


def is_within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def command(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check(result.returncode == 0, 'Command failed: ' + args[0] + ' (exit ' + str(result.returncode) + ')')
    return result.stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def get(path, timeout='20'):
    raw = command(['curl', '--silent', '--show-error', '--noproxy', '*', '--max-time', timeout, '--connect-timeout', '5',
                   '--resolve', 'epiya.cn:443:127.0.0.1', '-H', 'Accept-Encoding: identity',
                   '-w', '\n%{http_code}\n%{content_type}', 'https://epiya.cn' + path])
    body, status, content_type = raw.rsplit(b'\n', 2)
    return int(status), content_type.decode().split(';')[0], body


def verify_branded_404(expected_sha, record):
    # Nginx reload returns before every old worker has finished. Probe actual
    # responses instead of assuming that the first new connection is current.
    for attempt in range(1, 11):
        observation = {'attempt': attempt, 'status': None, 'contentType': None, 'sha256': None}
        try:
            status, content_type, body = get('/__epiya_missing_page_20261103__', timeout='2')
            observation.update({'status': status, 'contentType': content_type, 'sha256': digest(body)})
        except Exception as failure:
            observation['error'] = str(failure)
        record(observation)
        if observation['status'] == 404 and observation['contentType'] == 'text/html' and observation['sha256'] == expected_sha:
            return
        if attempt < 10:
            time.sleep(0.25)
    raise RuntimeError('Branded 404 did not match HTTP404, text/html and exact page SHA256 after 10 bounded probes')


def replace_config(path, data, metadata):
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.epiya-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temporary, metadata['mode'])
        os.chown(temporary, metadata['uid'], metadata['gid'])
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def reload_nginx():
    command(['nginx', '-t'])
    command(['systemctl', 'reload', 'nginx'])
    command(['systemctl', 'is-active', '--quiet', 'nginx'])


check(sys.platform == 'linux' and os.geteuid() == 0, 'Run as root on the existing Linux ECS')
lock = (BASE / '.website-deploy.lock').open('a')
fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
check(INCLUDE.is_file(), 'Existing Relic API include is missing; stop for inspection')
include_before = digest(INCLUDE.read_bytes())
command(['nginx', '-t'])
before_home = get('/')
before_api = {p: get(p)[:2] for p in PROBES}
check(before_home[0] == 200, 'Current HTTPS homepage is not healthy')

if sys.argv[1] == '--rollback':
    backup = Path(sys.argv[2]).resolve()
    check(is_within(backup, BASE / 'nginx-404-backups'), 'Unexpected rollback directory')
    receipt_path = backup / 'receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    check(receipt['phase'] == 'healthy', 'Only a healthy 404 change can be manually rolled back')
    config = Path(receipt['configuration']).resolve(strict=True)
    check(is_within(config, Path('/etc/nginx')), 'Unexpected configuration target')
    current = config.read_bytes()
    check(digest(current) == receipt['newSha256'], 'Configuration changed since this operation; refusing to overwrite it')
    original = (backup / 'original.conf').read_bytes()
    check(digest(original) == receipt['oldSha256'], 'Configuration backup checksum mismatch')
    try:
        replace_config(config, original, receipt['metadata'])
        reload_nginx()
        check(digest(INCLUDE.read_bytes()) == include_before, 'Relic include changed independently')
        check(get('/') == before_home, 'Homepage changed during configuration rollback')
        check({p: get(p)[:2] for p in PROBES} == before_api, 'API status/content type changed during configuration rollback')
    except BaseException:
        replace_config(config, current, receipt['metadata'])
        reload_nginx()
        raise
    receipt['phase'] = 'manually-rolled-back'
    receipt['rolledBackAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': 'rolled-back', 'receipt': str(receipt_path), 'apiIncludeModified': False}))
    sys.exit(0)

config = Path(sys.argv[1]).resolve(strict=True)
release_id = sys.argv[2]
check(is_within(config, Path('/etc/nginx')) and config.is_file(), 'Pass the actual existing /etc/nginx configuration file')
check(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,70}', release_id) is not None, 'Invalid release ID')
original = config.read_bytes()
text = original.decode('utf-8')
check(re.search(r'include\s+/etc/nginx/relic-locations\.conf\s*;', text), 'Selected file does not contain the existing Relic include')
check(not re.search(r'(?m)^\s*error_page\s+404\b', text), 'A 404 error_page already exists; do not add another')
all_config = command(['nginx', '-T']).decode('utf-8')
check(not re.search(r'(?m)^\s*proxy_intercept_errors\s+on\s*;', all_config), 'proxy_intercept_errors is enabled; scope needs manual review before adding a server-level 404')
location = re.compile(r'(?m)^(?P<indent>[ \t]*)location[ \t]+/[ \t]*\{[ \t\r\n]*try_files[ \t]+\$uri[ \t]+\$uri/[ \t]+=404;[ \t\r\n]*\}')
matches = list(location.finditer(text))
check(len(matches) == 1, 'Expected exactly one unmodified location / { try_files $uri $uri/ =404; }')
match = matches[0]
updated = (text[:match.start()] + match.group('indent') + 'error_page 404 /404.html;\n' + text[match.start():]).encode('utf-8')
check(updated.replace((match.group('indent') + 'error_page 404 /404.html;\n').encode(), b'', 1) == original, 'Unexpected configuration diff')
check((LIVE / '404.html').is_file(), 'Deploy the real branded 404 page before changing Nginx')
branded_sha = digest((LIVE / '404.html').read_bytes())
backup = BASE / 'nginx-404-backups' / release_id
check(not backup.exists(), 'Backup ID already exists; inspect its receipt before retrying')
backup.mkdir(parents=True, mode=0o700)
(backup / 'original.conf').write_bytes(original)
os.chmod(backup / 'original.conf', 0o600)
saved_stat = config.stat()
metadata = {'mode': stat.S_IMODE(saved_stat.st_mode), 'uid': saved_stat.st_uid, 'gid': saved_stat.st_gid}
receipt_path = backup / 'receipt.json'
receipt = {'phase': 'prepared', 'configuration': str(config), 'oldSha256': digest(original), 'newSha256': digest(updated),
           'apiIncludeSha256': include_before, 'metadata': metadata, 'backup': str(backup / 'original.conf'),
           'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
os.chmod(receipt_path, 0o600)
written = False
try:
    replace_config(config, updated, metadata)
    written = True
    reload_nginx()
    receipt['expected404Sha256'] = branded_sha
    receipt['404Checks'] = []
    def record_404_check(observation):
        receipt['404Checks'].append(observation)
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    verify_branded_404(branded_sha, record_404_check)
    check(get('/') == before_home, 'Homepage changed during 404 configuration')
    check({p: get(p)[:2] for p in PROBES} == before_api, 'Existing API status/content type changed')
    check(digest(INCLUDE.read_bytes()) == include_before, 'Relic include changed independently')
    receipt['phase'] = 'healthy'
    receipt['verified404Sha256'] = branded_sha
except BaseException as failure:
    receipt['error'] = str(failure)
    receipt['phase'] = 'failed-before-write'
    if written:
        try:
            replace_config(config, original, metadata)
            reload_nginx()
            receipt['phase'] = 'rolled-back'
        except BaseException as rollback_failure:
            receipt['phase'] = 'rollback-needs-attention'
            receipt['rollbackError'] = str(rollback_failure)
    raise
finally:
    receipt['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'result': 'enabled', 'receipt': str(receipt_path), 'apiIncludeModified': False, 'change': 'One server-level error_page 404 /404.html directive'}))
PY
