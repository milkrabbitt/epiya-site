#!/usr/bin/env bash
# Manual, atomic rollback of one healthy deployment produced by deploy-site.sh.
# Usage on the original ECS: bash rollback-site.sh RELEASE_ID
set -euo pipefail
if [[ $# -ne 1 ]]; then echo 'Usage: rollback-site.sh RELEASE_ID' >&2; exit 2; fi
exec python3 - "$1" <<'PY'
import ctypes, datetime, fcntl, hashlib, json, os, re, subprocess, sys
from pathlib import Path

base = Path('/srv/epiya')
live = base / 'site-20261009'
release_id = sys.argv[1]
if os.geteuid() != 0 or sys.platform != 'linux' or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,70}', release_id):
    raise SystemExit('Valid release ID and root on the original Linux ECS are required')
lock = (base / '.website-deploy.lock').open('a')
fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
backup = base / 'website-releases' / release_id
receipt_path = backup / 'deployment.json'
receipt = json.loads(receipt_path.read_text())
if receipt.get('phase') != 'healthy' or receipt.get('liveRoot') != str(live):
    raise SystemExit('Receipt is not a healthy deployment for this document root; inspect it before proceeding')
if not live.is_symlink() or live.resolve() != Path(receipt['newRoot']).resolve():
    raise SystemExit('A different deployment is active; refusing to roll it back indirectly')
current_target = os.readlink(live)


def exchange(first, second):
    libc = ctypes.CDLL(None, use_errno=True)
    operation = libc.renameat2
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    if operation(-100, os.fsencode(first), -100, os.fsencode(second), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def set_link(target):
    temp = base / ('.website-manual-rollback-' + release_id)
    if temp.exists() or temp.is_symlink():
        raise RuntimeError('Temporary rollback path is occupied')
    os.symlink(target, temp)
    os.replace(temp, live)


def current_hash():
    result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--noproxy', '*', '--max-time', '20',
                             '--resolve', 'epiya.cn:443:127.0.0.1', '-H', 'Accept-Encoding: identity',
                             'https://epiya.cn/index.html'], capture_output=True)
    if result.returncode:
        raise RuntimeError('Rollback HTTPS probe failed')
    return hashlib.sha256(result.stdout).hexdigest()


previous = Path(receipt['previousRoot']) if receipt.get('previousRoot') else None
if previous and (previous != backup / 'previous-root' or not previous.is_dir()):
    raise SystemExit('Expected original document root is missing')
old_link = receipt.get('oldSymlink')
if not previous and not old_link:
    raise SystemExit('Receipt does not identify an original root')
changed = False
try:
    if previous:
        exchange(live, previous)
    else:
        set_link(old_link)
    changed = True
    if current_hash() != receipt['oldIndexSha256']:
        raise RuntimeError('Rollback HTTPS content does not match the original release')
except BaseException:
    if changed:
        if previous:
            exchange(live, previous)
        else:
            set_link(current_target)
    raise
receipt['phase'] = 'manually-rolled-back'
receipt['rolledBackAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
temp = receipt_path.with_suffix('.tmp')
temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
os.chmod(temp, 0o600)
os.replace(temp, receipt_path)
print(json.dumps({'result': 'rolled-back', 'url': 'https://epiya.cn', 'receipt': str(receipt_path), 'nginxModified': False}))
PY
