"""Write safe aggregate evidence to GitHub's own workflow summary."""
import json
import os
from pathlib import Path

if __name__ == '__main__':
    target = os.environ.get('GITHUB_STEP_SUMMARY')
    if not target: raise SystemExit('Run this inside GitHub Actions')
    path = Path('data/datahub/logs/last_run.json')
    lines = ['# Westminster sync', '']
    if path.exists():
        report = json.loads(path.read_text())
        for key in ('date','sync_mode','new','updated','unchanged','classified','pending_classification','failures'):
            lines.append(f'- {key}: {report.get(key, "unknown")}')
    else:
        lines.append('No pipeline report was produced; inspect the failed step.')
    lines += ['', 'Secondary Datahub source; rule scores are not measured accuracy. Download report/digests from this run. GitHub workflow failure notifications depend on your notification settings.']
    with Path(target).open('a') as stream: stream.write('\n'.join(lines)+'\n')
