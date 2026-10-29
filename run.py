#!/usr/bin/env python3
import argparse
import json
import logging
from datetime import date
from pathlib import Path

from westminster_leads.classifier import classify
from westminster_leads.config import ROOT, TAXONOMY
from westminster_leads.demo import examples
from westminster_leads.datahub import DatahubExtractor
from westminster_leads.digest import write_digests
from westminster_leads.extractor import Extractor
from westminster_leads.storage import Store


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def main(argv=None):
    p = argparse.ArgumentParser(description='Westminster planning leads: extract → classify → digest')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--demo', action='store_true', help='Invented fixtures, isolated from live data')
    mode.add_argument('--skip-scrape', action='store_true')
    p.add_argument('--source', choices=['portal', 'datahub'], default='portal', help='Datahub uses validated/decided dates and lacks applicant contacts')
    p.add_argument('--terms-reviewed', action='store_true', help='Confirm council terms have been reviewed for intended use; required for live scraping')
    p.add_argument('--weeks', type=positive, default=4)
    p.add_argument('--max-pages', type=positive, default=30)
    p.add_argument('--backend', choices=['rules', 'openai'], default='rules')
    p.add_argument('--model', default='gpt-4o-mini')
    p.add_argument('--limit', type=positive, default=100)
    p.add_argument('--force', action='store_true')
    p.add_argument('--refresh', action='store_true')
    p.add_argument('--data-dir', type=Path)
    p.add_argument('--trades', default='Roofing,Scaffolding,Groundworks')
    p.add_argument('--area', default='')
    p.add_argument('--min-confidence', type=float, default=.7)
    p.add_argument('--all-statuses', action='store_true')
    p.add_argument('--digest-days', type=positive, default=7)
    a = p.parse_args(argv)
    trades = a.trades.split(',')
    if any(t not in TAXONOMY for t in trades) or not 0 <= a.min_confidence <= 1:
        p.error('Invalid trade or confidence threshold')
    if not (a.demo or a.skip_scrape or a.terms_reviewed or a.source == 'datahub'):
        p.error('Live scraping requires review of council terms first; see docs/DISCOVERY.md and --terms-reviewed')
    directory = a.data_dir or ROOT / 'data' / ('demo' if a.demo else 'datahub' if a.source == 'datahub' else 'live')
    directory.mkdir(parents=True, exist_ok=True)
    # Never mix fixture data and production leads, even with a custom directory.
    marker = directory / 'mode.txt'
    expected = 'synthetic' if a.demo else 'london_datahub' if a.source == 'datahub' else 'live'
    if marker.exists() and marker.read_text() != expected:
        p.error('Data directory belongs to another mode; use a separate directory')
    marker.write_text(expected)
    logs = directory / 'logs'
    logs.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(logs/'pipeline.log')], force=True)
    report = {'date': date.today().isoformat(), 'mode': expected, 'backend': a.backend, 'new': 0, 'updated': 0, 'unchanged': 0, 'classified': 0, 'excluded': 0, 'failures': 0, 'usage': {}, 'estimated_cost_usd': 0 if a.backend == 'rules' else None}
    store = Store(directory)
    try:
        if not a.skip_scrape:
            extractor = DatahubExtractor(max_pages=a.max_pages) if a.source == 'datahub' else Extractor(directory/'cache', a.max_pages, a.refresh)
            records = examples() if a.demo else extractor.collect(a.weeks)
            for record in records:
                report[store.upsert(record)] += 1
            if not a.demo and a.source == 'datahub':
                report['extraction'] = extractor.stats
        for record, previous in list(store.records()):
            if report['classified'] >= a.limit:
                break
            if previous and not a.force:
                continue
            result = classify(record, a.backend, a.model)
            store.classify(record['reference'], result)
            report['classified'] += 1
            report['excluded'] += int(result.get('excluded', False))
            for key, value in result.get('usage', {}).items():
                if isinstance(value, int):
                    report['usage'][key] = report['usage'].get(key, 0) + value
            cost = result.get('estimated_cost_usd')
            if cost is not None:
                report['estimated_cost_usd'] = (report['estimated_cost_usd'] or 0) + cost
        report['digests'] = write_digests(store, directory/'digests', trades, days=a.digest_days,
                                         area=a.area, min_confidence=a.min_confidence, granted_only=not a.all_statuses)
        report['pending_classification'] = sum(c is None for _, c in store.records())
    except Exception as error:
        report['failures'] += 1
        report['error_type'] = type(error).__name__
        if not a.demo and a.source == 'datahub' and not a.skip_scrape:
            report['extraction'] = extractor.stats
        # Avoid dumping HTTP bodies, API keys, or arbitrary server output into logs.
        logging.error('Pipeline failed (%s). Check source access, terms and adapter; see HANDOVER.md.', type(error).__name__)
    finally:
        store.close()
        (logs/'last_run.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        if report['failures']:
            with (logs/'alerts.log').open('a') as f:
                f.write(json.dumps(report)+'\n')
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
