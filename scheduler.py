#!/usr/bin/env python3
"""Single-worker periodic runner. Use cron instead if multi-process locking is needed."""
import argparse
import subprocess
import sys
import time
from pathlib import Path

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--interval-hours', type=float, default=84, help='Twice weekly by default')
    p.add_argument('--once', action='store_true')
    p.add_argument('pipeline_args', nargs=argparse.REMAINDER)
    a = p.parse_args()
    if a.interval_hours <= 0:
        p.error('interval must be positive')
    arguments = a.pipeline_args
    if arguments[:1] == ['--']:
        arguments = arguments[1:]
    root = Path(__file__).resolve().parent
    while True:
        result = subprocess.run([sys.executable, str(root/'run.py'), *arguments], cwd=root)
        if a.once:
            raise SystemExit(result.returncode)
        print(f'Pipeline exit={result.returncode}; next attempt in {a.interval_hours}h', flush=True)
        try:
            time.sleep(a.interval_hours*3600)
        except KeyboardInterrupt:
            break
