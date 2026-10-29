#!/usr/bin/env python3
"""Audit stored metadata/exports and prepare an unlabelled human review pack."""
import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from westminster_leads.config import ROOT, TAXONOMY
from westminster_leads.digest import parse_date, select
from westminster_leads.storage import Store


def audit(directory, weeks=4, review_size=50):
    directory = Path(directory)
    if not (directory/'planning_leads.db').exists():
        raise ValueError('Dataset missing; run the pipeline first')
    store = Store(directory)
    try:
        rows = list(store.records())
    finally:
        store.close()
    end = date.today()
    start = end-timedelta(days=7*weeks-1)
    issues = []
    refs = set()
    missing = Counter()
    source_conflicts = []
    outside_window = []
    for r, c in rows:
        reference = r['reference']
        if reference in refs:
            issues.append({'reference': reference, 'problem': 'duplicate reference'})
        refs.add(reference)
        for field in ('description', 'address', 'date_valid', 'decision_date', 'source_last_synced'):
            if not r.get(field):
                missing[field] += 1
        if r.get('provenance') != 'london_datahub' or reference.startswith('DEMO-'):
            issues.append({'reference': reference, 'problem': 'unexpected source'})
        if 'under consideration' in r.get('status', '').lower() and r.get('decision', '').lower() in ('approved', 'granted'):
            source_conflicts.append({'reference': reference, 'status': r['status'], 'decision': r['decision'], 'excluded_from_approval_digest': True})
        days = [parse_date(r.get(k, '')) for k in ('date_valid', 'decision_date')]
        if not any(day and start <= day <= end for day in days):
            outside_window.append(reference)
        if not c:
            issues.append({'reference': reference, 'problem': 'unclassified'})
        name = hashlib.sha256(reference.encode()).hexdigest()[:20]
        raw_path = directory/'raw'/(name+'.json')
        md_path = directory/'markdown'/(name+'.md')
        if not raw_path.exists() or json.loads(raw_path.read_text()) != r:
            issues.append({'reference': reference, 'problem': 'JSON export mismatch'})
        if not md_path.exists() or reference not in md_path.read_text() or r['description'].replace('\r\n', '\n').replace('\r', '\n') not in md_path.read_text():
            issues.append({'reference': reference, 'problem': 'Markdown export incomplete'})
    counts = {}
    # Digest consistency check, not independent evidence that selection policy is correct.
    for trade in ('Roofing', 'Scaffolding', 'Groundworks'):
        selected = select(rows, trade=trade, since=start)
        expected = {r['reference'] for r, _ in selected}
        path = directory/'digests'/(trade.lower()+'.md')
        exported = re.findall(r'^## (.+)$', path.read_text(), re.M) if path.exists() else []
        if set(exported) != expected or len(exported) != len(set(exported)):
            issues.append({'trade': trade, 'problem': 'digest references differ from current selection; regenerate with matching --digest-days'})
        for r, _ in selected:
            if r.get('decision', '').lower() not in ('approved', 'granted', 'permitted', 'grant', 'permit'):
                issues.append({'reference': r['reference'], 'problem': 'unexpected decision in approval digest'})
            if r['reference'].endswith(('/LBC', '/NMA', '/ADV', '/TCA', '/TPO', '/ADFULL', '/ADLBC')):
                issues.append({'reference': r['reference'], 'problem': 'nonprimary reference in approval digest'})
        counts[trade] = len(selected)
    # Deterministic type-stratified review selection. Predictions are stored separately
    # to allow blind human labels. This is an audit sample, not prevalence estimation.
    rng = random.Random(20261029)
    buckets = defaultdict(list)
    for r, c in rows:
        buckets[r.get('application_type', 'unknown')].append((r, c))
    for bucket in buckets.values():
        bucket.sort(key=lambda item: item[0]['reference'])
        rng.shuffle(bucket)
    chosen = []
    while len(chosen) < min(review_size, len(rows)):
        for key in sorted(buckets):
            if buckets[key] and len(chosen) < review_size:
                chosen.append(buckets[key].pop())
    target = directory/'review'
    target.mkdir(exist_ok=True)
    labels = [{'record': r, 'trades': None, 'contact_route': None, 'reviewer_note': ''} for r, _ in chosen]
    labels_path = target/'human_labels_template.json'
    # Never overwrite labels or predictions from an earlier human-review round.
    if not labels_path.exists():
        labels_path.write_text(json.dumps(labels, indent=2, ensure_ascii=False))
        (target/'predictions_at_sampling.json').write_text(json.dumps([{'reference': r['reference'], 'classification': c} for r, c in chosen], indent=2, ensure_ascii=False))
    report = {'as_of': end.isoformat(), 'window': {'start': start.isoformat(), 'end': end.isoformat(), 'basis': 'validated OR decided'},
              'records': len(rows), 'unique_references': len(refs), 'issues': issues,
              'source_counts': dict(Counter(r.get('provenance') for r, _ in rows)),
              'excluded': sum(bool(c and c.get('excluded')) for _, c in rows),
              'source_conflicts': source_conflicts, 'missing_fields': dict(missing), 'outside_requested_window': outside_window,
              'approval_digest_counts': counts, 'review_template': str(labels_path),
              'accuracy_measured': False,
              'limitations': ['Datahub secondary source; council cross-check outstanding', 'Keyword classification not independently human evaluated',
                              'Missing decision dates may be normal for pending applications',
                              'Older retained records outside the rolling window are reported separately, not automatically corrupt']}
    (directory/'logs').mkdir(exist_ok=True)
    (directory/'logs'/'audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--data-dir', type=Path, default=ROOT/'data'/'datahub')
    p.add_argument('--weeks', type=int, default=4)
    p.add_argument('--review-size', type=int, default=50)
    args = p.parse_args()
    if args.weeks < 1 or args.review_size < 1:
        p.error('weeks and review-size must be positive')
    result = audit(args.data_dir, args.weeks, args.review_size)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(1 if result['issues'] or not result['records'] else 0)
