#!/usr/bin/env python3
"""Refresh rules, audit and produce slides from already stored real data. No network."""
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    if not (root/'data/datahub/planning_leads.db').exists():
        raise SystemExit('Collect real data first: python run.py --source datahub --limit 10000 --digest-days 28')
    commands = [
        ['run.py','--source','datahub','--skip-scrape','--force','--limit','1000000','--digest-days','28'],
        ['audit_data.py'],
        ['build_presentation.py'],
    ]
    for arguments in commands:
        print('Running '+arguments[0],flush=True)
        code = subprocess.run([sys.executable,*arguments],cwd=root).returncode
        if code: raise SystemExit(code)
    print('Presentation ready: data/presentation/index.html. Datahub attribution and outstanding validation are included.')
