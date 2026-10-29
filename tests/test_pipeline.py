import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from run import main
from evaluate_benchmark import evaluate
from westminster_leads.classifier import classify, validate
from westminster_leads.demo import examples
from westminster_leads.digest import granted, render, select
from westminster_leads.extractor import Extractor, parse_detail, result_links
from westminster_leads.storage import Store

# Synthetic Idox-shaped fixtures, not captured Westminster pages.
DETAIL = '<table><tr><th>Reference</th><td>TEST/01</td></tr><tr><th>Proposal</th><td>Roof replacement</td></tr><tr><th>Decision</th><td>Granted</td></tr></table>'
RESULTS = '<a href="applicationDetails.do?keyVal=ONE">Details</a><a class="next" href="pagedSearchResults.do?searchCriteria.page=2&amp;date=2026">Next</a>'


class PipelineTests(unittest.TestCase):
    def test_parse_and_pagination(self):
        record = parse_detail(DETAIL, 'https://example.test/detail')
        self.assertEqual(record['reference'], 'TEST/01')
        self.assertEqual(record['description'], 'Roof replacement')
        links, next_url = result_links(RESULTS, 'https://example.test/search')
        self.assertEqual(len(links), 1)
        self.assertIn('date=2026', next_url)
        with self.assertRaises(ValueError):
            parse_detail('<h1>Sign in</h1>', 'x')

    def test_repeated_page_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            extractor = Extractor(tmp)
            form = '<form id="advancedSearchForm" action="search.do"></form>'
            with patch.object(extractor, 'request', side_effect=[(form, 'https://example.test/'), (RESULTS, 'https://example.test/'), (DETAIL, 'https://example.test/'), (RESULTS, 'https://example.test/')]):
                with self.assertRaisesRegex(RuntimeError, 'Repeated'):
                    list(extractor.search(date.today(), date.today()))

    def test_upsert_and_invalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            record = next(examples())
            self.assertEqual(store.upsert(record), 'new')
            store.classify(record['reference'], classify(record))
            self.assertEqual(store.upsert(record), 'unchanged')
            self.assertIsNotNone(list(store.records())[0][1])
            record['decision'] = 'Refused'
            self.assertEqual(store.upsert(record), 'updated')
            self.assertIsNone(list(store.records())[0][1])
            self.assertEqual(len(list((Path(tmp)/'markdown').glob('*.md'))), 1)
            store.close()

    def test_filter_and_escaping(self):
        record = next(examples())
        result = classify(record)
        self.assertIn('Roofing', result['relevant_trades'])
        self.assertEqual(len(select([(record, result)], trade='Roofing', area='SW1A')), 1)
        for decision in ('Decided', 'Refused', 'Not approved', 'Discharge of condition approved'):
            self.assertFalse(granted(record | {'decision': decision}))
        record['description'] = '<script>alert(1)</script>'
        record['source_url'] = 'javascript:alert(1)'
        result['summary'] = record['description']
        _, page = render([(record, result)])
        self.assertNotIn('<script>', page)
        self.assertNotIn('javascript:', page)
        self.assertIn('SYNTHETIC', page)

    def test_exclusion_and_validation(self):
        self.assertTrue(classify(list(examples())[4])['excluded'])
        bad = classify(next(examples()))
        bad['confidence_scores']['Roofing'] = 2
        with self.assertRaises(ValueError):
            validate(bad)

    def test_pipeline_repeatability(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ['--demo', '--data-dir', tmp]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 0)
            report = json.loads((Path(tmp)/'logs/last_run.json').read_text())
            self.assertEqual(report['unchanged'], 8)
            self.assertEqual(report['classified'], 0)
            self.assertTrue((Path(tmp)/'digests/roofing.html').exists())
            self.assertEqual(report['pending_classification'], 0)

    def test_failure_status_and_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('run.Extractor.collect', side_effect=RuntimeError('blocked')):
                self.assertEqual(main(['--terms-reviewed', '--data-dir', tmp]), 1)
            self.assertTrue((Path(tmp)/'logs/alerts.log').exists())

    def test_evaluation(self):
        # Metric arithmetic test only: this is not a real model benchmark.
        record = next(examples())
        with patch('evaluate_benchmark.classify', return_value={'relevant_trades': ['Roofing', 'Scaffolding'], 'contact_route': 'agent'}):
            result = evaluate([{'record': record, 'trades': ['Roofing'], 'contact_route': 'agent'}], 'rules')
        self.assertEqual(result['micro']['precision'], .5)
        self.assertEqual(result['micro']['recall'], 1)
        self.assertAlmostEqual(result['micro']['f1'], 2/3)
        with self.assertRaises(ValueError):
            evaluate([], 'rules')


if __name__ == '__main__':
    unittest.main()
