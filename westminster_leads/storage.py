import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def markdown(record):
    return '\n'.join([f'# {record["reference"]}', *[
        f'\n## {key.replace("_", " ").title()}\n{value}' for key, value in record.items()
        if key != 'reference' and value]]) + '\n'


class Store:
    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'planning_leads.db')
        self.db.execute('CREATE TABLE IF NOT EXISTS applications (reference TEXT PRIMARY KEY, payload TEXT NOT NULL, classification TEXT, updated_at TEXT NOT NULL)')

    def upsert(self, record):
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
        old = self.db.execute('SELECT payload FROM applications WHERE reference=?', (record['reference'],)).fetchone()
        state = 'new' if not old else 'unchanged' if old[0] == payload else 'updated'
        if state != 'unchanged':
            with self.db:
                self.db.execute('INSERT INTO applications VALUES (?,?,NULL,?) ON CONFLICT(reference) DO UPDATE SET payload=excluded.payload, classification=NULL, updated_at=excluded.updated_at',
                                (record['reference'], payload, datetime.now(timezone.utc).isoformat()))
        # Repair missing exports even when database content has not changed.
        name = hashlib.sha256(record['reference'].encode()).hexdigest()[:20]
        for folder, suffix, content in [('raw', '.json', payload), ('markdown', '.md', markdown(record))]:
            target = self.root / folder / (name + suffix)
            target.parent.mkdir(exist_ok=True)
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

    def close(self):
        self.db.close()
