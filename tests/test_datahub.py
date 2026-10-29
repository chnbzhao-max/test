import unittest
from datetime import date
from unittest.mock import Mock

from westminster_leads.datahub import DatahubExtractor, normalize


def application(reference='26/TEST/FULL', **extra):
    return dict(lpa_name='Westminster', lpa_app_no=reference, description='Roof replacement',
                valid_date='22/10/2026', decision_date=None, site_number=12, street_name='Test Road', **extra)


def page(records, total=2):
    return {'timed_out': False, '_shards': {'failed': 0},
            'hits': {'total': {'value': total, 'relation': 'eq'},
                     'hits': [{'_id': r['lpa_app_no'], '_source': r} for r in records]}}


class DatahubTests(unittest.TestCase):
    def test_pagination_and_normalization(self):
        extractor = DatahubExtractor(page_size=1, pause=lambda _: None)
        extractor.request = Mock(side_effect=[page([application()]), page([application('26/SECOND/FULL')])])
        records = list(extractor.collect(4, end=date(2026, 10, 29)))
        self.assertEqual(len(records), 2)
        self.assertTrue(extractor.stats['complete'])
        self.assertEqual(extractor.stats['api_total'], 2)
        self.assertEqual(records[0]['provenance'], 'london_datahub')
        self.assertEqual(records[0]['date_valid'], '22/10/2026')
        self.assertNotIn('date_received', records[0])
        self.assertNotIn('agent', records[0])

    def test_duplicate_fails(self):
        extractor = DatahubExtractor(page_size=1, pause=lambda _: None)
        extractor.request = Mock(side_effect=[page([application()]), page([application()])])
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            list(extractor.collect(4, end=date(2026, 10, 29)))
        self.assertFalse(extractor.stats['complete'])

    def test_wrong_authority_and_dates(self):
        with self.assertRaises(ValueError):
            normalize(application() | {'lpa_name': 'Camden'})
        extractor = DatahubExtractor(pause=lambda _: None)
        extractor.request = Mock(return_value=page([application() | {'valid_date': '01/01/2020'}], total=1))
        with self.assertRaisesRegex(RuntimeError, 'outside'):
            list(extractor.collect(4, end=date(2026, 10, 29)))

    def test_incomplete_and_changed_total(self):
        extractor = DatahubExtractor(page_size=1, pause=lambda _: None)
        extractor.request = Mock(side_effect=[page([application()]), page([], total=3)])
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            list(extractor.collect(4, end=date(2026, 10, 29)))
        extractor = DatahubExtractor(max_pages=1, page_size=1, pause=lambda _: None)
        extractor.request = Mock(return_value=page([application()]))
        with self.assertRaisesRegex(RuntimeError, 'page limit'):
            list(extractor.collect(4, end=date(2026, 10, 29)))


if __name__ == '__main__':
    unittest.main()
