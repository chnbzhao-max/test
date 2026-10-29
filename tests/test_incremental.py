import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from run import main
from westminster_leads.storage import Store
from westminster_leads.datahub import DatahubExtractor
from westminster_leads.classifier import classify

NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def raw(ref='OLD/FULL', **extra):
    return dict(lpa_name='Westminster', lpa_app_no=ref, description='Roof replacement',
                valid_date='01/01/2020', decision_date='01/01/2020',
                last_updated='2026-10-29T11:00:00Z', last_synced='2026-10-29T11:30:00Z') | extra


def page(sources=(), total=None):
    return {'hits': {'total': {'relation': 'eq', 'value': len(sources) if total is None else total},
                     'hits': [{'_id': s['lpa_app_no'], '_source': s} for s in sources]}}


class IncrementalTests(unittest.TestCase):
    def test_older_application_updates_and_empty_scan(self):
        extractor = DatahubExtractor(pause=lambda _: None)
        extractor.request = Mock(return_value=page([raw()]))
        rows = list(extractor.collect_updates(NOW-timedelta(hours=2), NOW))
        self.assertEqual(rows[0]['date_valid'], '01/01/2020')
        self.assertTrue(extractor.stats['complete'])
        query = extractor.request.call_args.args[0]
        self.assertNotIn('valid_date', json.dumps(query))
        self.assertIn('last_synced', json.dumps(query))
        extractor.request = Mock(return_value=page())
        self.assertEqual(list(extractor.collect_updates(NOW-timedelta(hours=2), NOW)), [])
        self.assertEqual(extractor.request.call_count, 1)
        self.assertTrue(extractor.stats['complete'])

    def test_dense_window_splits_and_deduplicates_across_fields(self):
        extractor = DatahubExtractor(max_pages=1, page_size=1, pause=lambda _: None)
        # One record matches last_updated in left half and last_synced in right half.
        item = raw()
        item['last_updated'] = '2026-10-29T10:30:00Z'
        extractor.request = Mock(side_effect=[page(total=2), page([item]), page([item])])
        rows = list(extractor.collect_updates(NOW-timedelta(hours=2), NOW))
        self.assertEqual(len(rows), 1)
        self.assertEqual(extractor.stats['windows'], 2)
        self.assertEqual(extractor.stats['api_total'], 2)
        self.assertEqual(extractor.stats['unique_records'], 1)

    def test_out_of_window_timestamp_fails(self):
        extractor = DatahubExtractor(pause=lambda _: None)
        item = raw(); item['last_updated'] = item['last_synced'] = '2020-01-01T00:00:00Z'
        extractor.request = Mock(return_value=page([item]))
        with self.assertRaisesRegex(RuntimeError, 'outside'):
            list(extractor.collect_updates(NOW-timedelta(hours=2), NOW))
        self.assertFalse(extractor.stats['complete'])

    def test_metadata_only_preserves_classification_and_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Store(tmp)
            record = {'reference': 'OLD/FULL', 'description': 'Roof replacement', 'source_last_synced': 'old'}
            s.upsert(record); s.classify(record['reference'], classify(record))
            self.assertEqual(s.upsert(record | {'source_last_synced': 'new'}), 'updated')
            self.assertIsNotNone(list(s.records())[0][1])
            paths = list((Path(tmp)/'raw').glob('*.json'))
            before = paths[0].stat().st_mtime_ns
            s.upsert(record | {'source_last_synced': 'new'})
            self.assertEqual(before, paths[0].stat().st_mtime_ns)
            s.upsert(record | {'decision': 'Refused'})
            self.assertIsNone(list(s.records())[0][1]); s.close()

    def test_checkpoint_success_failure_and_no_scrape(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ['--source', 'datahub', '--data-dir', tmp]
            with patch('run.DatahubExtractor.collect', return_value=iter([])):
                self.assertEqual(main(args), 0)
            s = Store(tmp); initial = s.sync_state(); s.close()
            self.assertIsNotNone(initial)
            with patch('run.DatahubExtractor.collect_updates', side_effect=RuntimeError('failure')):
                self.assertEqual(main(args), 1)
            s = Store(tmp); self.assertEqual(s.sync_state(), initial); s.close()
            with patch('run.DatahubExtractor.collect_updates') as updates:
                self.assertEqual(main(args+['--skip-scrape']), 0)
                updates.assert_not_called()
            s = Store(tmp); self.assertEqual(s.sync_state(), initial); s.close()
            with patch('run.DatahubExtractor.collect_updates', return_value=iter([])) as updates:
                self.assertEqual(main(args), 0)
                lower, upper = updates.call_args.args
                self.assertEqual(lower, datetime.fromisoformat(initial['completed_until'])-timedelta(hours=2))
            s = Store(tmp); self.assertNotEqual(s.sync_state()['completed_until'], initial['completed_until']); s.close()

    def test_full_refresh_keeps_existing_cursor_and_downstream_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ['--source', 'datahub', '--data-dir', tmp]
            s = Store(tmp); old = {'completed_until': NOW.isoformat(), 'bootstrap_weeks': 4}; s.save_sync_state(old); s.close()
            with patch('run.DatahubExtractor.collect', return_value=iter([])), patch('run.DatahubExtractor.collect_updates') as updates:
                self.assertEqual(main(args+['--full-refresh']), 0)
                updates.assert_not_called()
            s = Store(tmp); self.assertEqual(s.sync_state(), old); s.close()
        with tempfile.TemporaryDirectory() as tmp:
            with patch('run.DatahubExtractor.collect', return_value=iter([])), patch('run.write_digests', side_effect=OSError('disk full')):
                self.assertEqual(main(['--source', 'datahub', '--data-dir', tmp]), 1)
            s = Store(tmp); self.assertIsNone(s.sync_state()); s.close()

    def test_partial_download_failure_retries_without_advancing(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = {'completed_until': (datetime.now(timezone.utc)-timedelta(days=1)).isoformat(), 'bootstrap_weeks': 4}
            record = {'reference': 'OLD/FULL', 'description': 'Roof replacement', 'decision': 'Approved', 'provenance': 'london_datahub'}
            s = Store(tmp); s.save_sync_state(old); s.upsert(record); s.classify(record['reference'], classify(record)); s.close()
            changed = record | {'decision': 'Refused'}
            def partial(*args):
                yield changed
                raise RuntimeError('second page failed')
            args = ['--source', 'datahub', '--data-dir', tmp]
            with patch('run.DatahubExtractor.collect_updates', side_effect=partial):
                self.assertEqual(main(args), 1)
            s = Store(tmp)
            self.assertEqual(s.sync_state(), old)
            rows = list(s.records())
            self.assertEqual(rows[0][0]['decision'], 'Refused')
            self.assertIsNone(rows[0][1])
            s.close()
            with patch('run.DatahubExtractor.collect_updates', return_value=iter([changed])):
                self.assertEqual(main(args), 0)
            s = Store(tmp)
            self.assertEqual(len(list(s.records())), 1)
            self.assertIsNotNone(list(s.records())[0][1]); s.close()

    def test_dataset_lock_released_after_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Store(tmp), Store(tmp)
            one.acquire_sync_lock()
            with self.assertRaises(RuntimeError):
                two.acquire_sync_lock()
            one.close();two.acquire_sync_lock();two.close()


if __name__ == '__main__':
    unittest.main()
