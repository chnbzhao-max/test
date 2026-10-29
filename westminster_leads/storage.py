import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def markdown(record):
    return '\n'.join([f'# {record["reference"]}', *[
        f'\n## {key.replace("_", " ").title()}\n{value}' for key, value in record.items()
        if key != 'reference' and value]]) + '\n'


class Store:
    def __init__(self, directory):
        self._sync_lock = None
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'planning_leads.db')
        self.db.execute('CREATE TABLE IF NOT EXISTS sync_state (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS applications (reference TEXT PRIMARY KEY, payload TEXT NOT NULL, classification TEXT, updated_at TEXT NOT NULL)')

    def upsert(self, record):
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
        old = self.db.execute('SELECT payload, classification FROM applications WHERE reference=?', (record['reference'],)).fetchone()
        state = 'new' if not old else 'unchanged' if old[0] == payload else 'updated'
        if state != 'unchanged':
            ignored = {'source_last_updated', 'source_last_synced'}
            old_content = {k: v for k, v in json.loads(old[0]).items() if k not in ignored} if old else None
            new_content = {k: v for k, v in record.items() if k not in ignored}
            classification = old[1] if old and old_content == new_content else None
            with self.db:
                self.db.execute('INSERT INTO applications VALUES (?,?,?,?) ON CONFLICT(reference) DO UPDATE SET payload=excluded.payload, classification=excluded.classification, updated_at=excluded.updated_at',
                                (record['reference'], payload, classification, datetime.now(timezone.utc).isoformat()))
        # Repair missing exports even when database content has not changed.
        name = hashlib.sha256(record['reference'].encode()).hexdigest()[:20]
        for folder, suffix, content in [('raw', '.json', payload), ('markdown', '.md', markdown(record))]:
            target = self.root / folder / (name + suffix)
            target.parent.mkdir(exist_ok=True)
            if target.exists() and target.read_bytes() == content.encode('utf-8'):
                continue
            temp = target.with_suffix('.tmp')
            temp.write_text(content, encoding='utf-8')
            temp.replace(target)
        return state

    def records(self):
        for payload, classification in self.db.execute('SELECT payload, classification FROM applications ORDER BY reference'):
            yield json.loads(payload), json.loads(classification) if classification else None

    def classify(self, reference, result):
        with self.db:
            self.db.execute('UPDATE applications SET classification=? WHERE reference=?', (json.dumps(result), reference))

    def acquire_sync_lock(self):
        lock = (self.root / '.sync.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if lock.tell() == 0:
                    lock.write(b'0'); lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock.close()
            raise RuntimeError('Another process is using this Datahub dataset')
        self._sync_lock = lock

    def sync_state(self):
        row = self.db.execute("SELECT value FROM sync_state WHERE name='datahub-v1'").fetchone()
        return json.loads(row[0]) if row else None

    def save_sync_state(self, state):
        with self.db:
            self.db.execute("INSERT INTO sync_state VALUES ('datahub-v1', ?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (json.dumps(state),))

    def close(self):
        self.db.close()
        if self._sync_lock is not None:
            self._sync_lock.close()
            self._sync_lock = None
