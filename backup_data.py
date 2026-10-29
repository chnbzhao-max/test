#!/usr/bin/env python3
"""Private local backup. Stop review UI before backup; never uploads data."""
import argparse
import json
import secrets
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from westminster_leads.config import ROOT
from westminster_leads.storage import Store


def backup(directory, output):
    directory=Path(directory).resolve();output=Path(output).resolve()
    if not (directory/'planning_leads.db').exists():raise ValueError('Dataset missing')
    if output == directory or directory in output.parents:raise ValueError('Backup must be outside dataset')
    if output.exists():raise FileExistsError('Refusing to overwrite an existing backup')
    output.parent.mkdir(parents=True,exist_ok=True)
    store=Store(directory)
    created=False
    try:
        store.acquire_sync_lock()
        with tempfile.TemporaryDirectory() as tmp:
            db_path=Path(tmp)/'planning_leads.db'
            target=sqlite3.connect(db_path)
            try:store.db.backup(target)
            finally:target.close()
            destination=output.open('xb')
            created=True
            with destination, ZipFile(destination,'w',compression=ZIP_DEFLATED) as archive:
                archive.write(db_path,'planning_leads.db')
                for name in ('mode.txt','raw','markdown','digests','logs','review'):
                    root=directory/name
                    if root.is_symlink():raise ValueError('Symlink in dataset; inspect before backing up')
                    paths=[root] if root.is_file() else sorted(root.rglob('*')) if root.exists() else []
                    for path in paths:
                        if path.is_symlink():raise ValueError('Symlink in dataset; inspect before backing up')
                        if path.is_file():archive.write(path,str(path.relative_to(directory)))
                archive.writestr('backup_manifest.json',json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'source':'local Datahub dataset','privacy':'Private backup; review files can contain reviewer information. Do not publish.'}))
            with ZipFile(output) as archive:
                if archive.testzip() is not None:raise RuntimeError('Backup integrity check failed')
    except Exception:
        # This path was required absent at entry; do not touch anyone's prior backup.
        if created and output.exists():output.unlink()
        raise
    finally:store.close()
    return {'backup':str(output),'bytes':output.stat().st_size,'uploaded':False}


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',type=Path,default=ROOT/'data/datahub')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    output=a.output or ROOT/'backups'/('westminster-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3)+'.zip')
    print(json.dumps(backup(a.data_dir,output),indent=2))
