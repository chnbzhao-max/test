import tempfile
import threading
import unittest
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from bs4 import BeautifulSoup
from web_demo import date_window, handler_for
from westminster_leads.classifier import classify
from westminster_leads.digest import parse_date, select
from westminster_leads.storage import Store


def record(reference, decision_day, valid_day=None):
    return {'reference': reference, 'description': 'Roof replacement', 'decision': 'Approved', 'status': 'Decided',
            'decision_date': decision_day, 'date_valid': valid_day or decision_day,
            'source_url': 'https://idoxpa.westminster.gov.uk/online-applications/', 'provenance': 'synthetic'}


class DateSelectionTests(unittest.TestCase):
    def test_default_window_and_history_opt_in(self):
        today = date(2026, 11, 5)
        self.assertEqual(date_window({}, today), (date(2026, 10, 9), today))
        self.assertEqual(date_window({'all-dates': ['1']}, today), (None, None))

    def test_invalid_date_windows_rejected(self):
        for values in ({'from-date': ['bad']}, {'from-date': ['']},
                       {'from-date': ['2026-11-05'], 'to-date': ['2026-11-04']},
                       {'to-date': ['2026-11-06']}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                date_window(values, date(2026, 11, 5))

    def test_inclusive_boundaries_and_missing_dates(self):
        today = date.today(); lower = today-timedelta(days=5); upper = today-timedelta(days=2)
        data = [record(str(i)+'/FULL', d) for i, d in enumerate([
            (lower-timedelta(days=1)).isoformat(), lower.isoformat(), upper.isoformat(), today.isoformat(), None])]
        rows = [(r, classify(r)) for r in data]
        self.assertEqual([r['reference'] for r,c in select(rows, since=lower, until=upper)], ['1/FULL', '2/FULL'])
        with self.assertRaises(ValueError): select(rows, since=upper, until=lower)
        self.assertIsNone(parse_date(None))

    def test_all_status_uses_received_then_validated(self):
        today = date.today(); before = (today-timedelta(days=50)).isoformat()
        one = record('VALIDATED/FULL', before, today.isoformat()) | {'decision': '', 'status': 'Application Under Consideration'}
        two = record('RECEIVED/FULL', before, today.isoformat()) | {'date_received': before}
        rows = [(r, classify(r)) for r in (one,two)]
        self.assertEqual([r['reference'] for r,c in select(rows, granted_only=False, since=today, until=today)], ['VALIDATED/FULL'])


class DashboardDateHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.root = Path(cls.tmp.name)
        store = Store(cls.root)
        today = date.today()
        for r in [record('OLD/FULL', '2019-03-20'), record('EARLIER/FULL', (today-timedelta(days=4)).isoformat()),
                  record('LATEST/FULL', (today-timedelta(days=1)).isoformat())]:
            store.upsert(r); store.classify(r['reference'], classify(r))
        store.close()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(cls.root))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.base = 'http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.tmp.cleanup()

    def get(self, path):
        with urlopen(self.base+path, timeout=5) as response: return response.read().decode()

    def test_default_recent_dates_and_matching_export(self):
        soup = BeautifulSoup(self.get('/?trade=Roofing'), 'html.parser')
        self.assertEqual([node.text for node in soup.select('article h2')], ['LATEST/FULL','EARLIER/FULL'])
        self.assertEqual(soup.select_one('[name=from-date]')['value'], (date.today()-timedelta(days=27)).isoformat())
        link = next(a['href'] for a in soup.select('a[href]') if a['href'].startswith('/digest.md'))
        self.assertIn('from-date=', link); self.assertIn('trade=Roofing',link)
        exported = self.get(link)
        self.assertNotIn('OLD/FULL',exported); self.assertIn('LATEST/FULL',exported)
        self.assertIn('Decision date:', exported)

    def test_custom_range_and_all_history(self):
        query = urlencode({'from-date':'2019-03-20','to-date':'2019-03-20'})
        soup = BeautifulSoup(self.get('/?'+query), 'html.parser')
        self.assertEqual([node.text for node in soup.select('article h2')], ['OLD/FULL'])
        soup = BeautifulSoup(self.get('/?all-dates=1'), 'html.parser')
        self.assertEqual([node.text for node in soup.select('article h2')], ['LATEST/FULL','EARLIER/FULL','OLD/FULL'])
        self.assertIn('All stored dates', soup.text)

    def test_bad_range_returns_http_400(self):
        with self.assertRaises(HTTPError) as error:
            self.get('/?from-date=2026-11-05&to-date=2026-11-04')
        self.assertEqual(error.exception.code,400)


if __name__ == '__main__': unittest.main()
