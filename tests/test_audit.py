import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from audit_data import audit
from evaluate_benchmark import evaluate
from westminster_leads.classifier import classify
from westminster_leads.digest import write_digests
from westminster_leads.storage import Store


class AuditTests(unittest.TestCase):
    def test_newlines_corruption_and_label_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = {'reference': 'TEST/FULL', 'description': 'Roof replacement\r\rWith new dormer',
                 'provenance': 'london_datahub', 'decision': 'Approved', 'date_valid': date.today().isoformat(),
                 'decision_date': date.today().isoformat(), 'source_url': 'https://idoxpa.westminster.gov.uk/online-applications/'}
            store = Store(tmp)
            store.upsert(r)
            store.classify(r['reference'], classify(r))
            write_digests(store, Path(tmp)/'digests', ['Roofing', 'Scaffolding', 'Groundworks'], days=28)
            store.close()
            report = audit(tmp)
            self.assertEqual(report['issues'], [])
            labels = Path(report['review_template'])
            labels.write_text('USER REVIEW IN PROGRESS')
            audit(tmp)
            self.assertEqual(labels.read_text(), 'USER REVIEW IN PROGRESS')
            name = hashlib.sha256(r['reference'].encode()).hexdigest()[:20]
            (Path(tmp)/'raw'/(name+'.json')).write_text('{}')
            self.assertTrue(any(i['problem'] == 'JSON export mismatch' for i in audit(tmp)['issues']))

    def test_empty_or_unlabelled_not_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp);store.close()
            report = audit(tmp)
            self.assertEqual(report['records'], 0)
            self.assertFalse(report['accuracy_measured'])
        with self.assertRaisesRegex(ValueError, 'human labels'):
            evaluate([{'record': {'reference': 'TEST'}, 'trades': None, 'contact_route': None}], 'rules')


if __name__ == '__main__':
    unittest.main()
