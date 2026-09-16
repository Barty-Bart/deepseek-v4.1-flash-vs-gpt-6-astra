"""Check the running preview and alternate PORT without changing demo data."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
PORT = int(os.environ.get('PORT', '5181'))
ALT_PORT = int(os.environ.get('VERIFY_ALT_PORT', '5182'))


def snapshot():
    db = sqlite3.connect(ROOT / '.local' / 'northline.sqlite3')
    try:
        data = {table: db.execute(f'SELECT * FROM {table} ORDER BY id').fetchall() for table in ('bookings', 'blocks', 'admins')}
        return {'records_fingerprint': hashlib.sha256(json.dumps(data).encode()).hexdigest(),
                'secret_fingerprint': hashlib.sha256((ROOT / '.local' / 'secret_key').read_bytes()).hexdigest(),
                'bookings': len(data['bookings']), 'blocks': len(data['blocks'])}
    finally:
        db.close()


def verify():
    before = snapshot()
    report = {'primary_port': PORT, 'alternate_port': ALT_PORT, 'bookings': before['bookings'], 'blocks': before['blocks']}
    with urlopen(f'http://127.0.0.1:{PORT}/', timeout=5) as response:
        assert response.status == 200 and b'Your next good hair day.' in response.read()
    report['primary_preview'] = 'HTTP 200'
    assert stat.S_IMODE((ROOT / '.local' / 'secret_key').stat().st_mode) == 0o600
    report['secret_permissions'] = '0600'
    previous = ROOT / '.local' / 'restart-snapshot.json'
    if previous.exists():
        assert before == json.loads(previous.read_text()), 'Data or secret changed across restart'
        report['primary_restart_preserved_records_and_secret'] = True
    if ALT_PORT == PORT:
        raise ValueError('VERIFY_ALT_PORT must differ from PORT')
    log_path = REPORTS / 'alternate-port.log'
    with log_path.open('w') as log:
        process = subprocess.Popen([str(ROOT / 'start.sh')], cwd=ROOT, env={**os.environ, 'PORT': str(ALT_PORT)}, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                output = log_path.read_text()
                if f'Running on http://127.0.0.1:{ALT_PORT}' in output:
                    break
                if process.poll() is not None:
                    raise RuntimeError('The alternate preview did not start; see alternate-port.log')
                time.sleep(.1)
            else:
                raise TimeoutError('The alternate preview did not become ready in 25 seconds')
            with urlopen(f'http://127.0.0.1:{ALT_PORT}/', timeout=5) as response:
                assert response.status == 200 and b'Your next good hair day.' in response.read()
            with urlopen(f'http://127.0.0.1:{PORT}/', timeout=5) as response:
                assert response.status == 200
            report['simultaneous_previews'] = 'Both HTTP 200'
        finally:
            process.terminate()
            process.wait(timeout=5)
    assert before == snapshot(), 'Alternate startup changed demo data or secret'
    report['alternate_start_preserved_records_and_secret'] = True
    report['result'] = 'passed'
    (REPORTS / 'operation-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    verify()
