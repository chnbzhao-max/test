import unittest
from unittest.mock import Mock
import requests
from verify_portal import verify


def response(code, text=''):
    r = requests.Response()
    r.status_code = code
    r._content = text.encode()
    return r


class PreflightTests(unittest.TestCase):
    def test_unavailable_policy_stops_before_search(self):
        session = Mock(headers={})
        session.get.side_effect = [response(200), response(503)]
        result = verify(session, pause=lambda _: None)
        self.assertEqual(session.get.call_count, 2)
        self.assertFalse(result['ready_for_extraction'])
        self.assertIn('blocked_before_search', result['result'])

    def test_robots_disallow_stops_search(self):
        session = Mock(headers={})
        session.get.side_effect = [response(200), response(200, 'User-agent: *\nDisallow: /online-applications/')]
        result = verify(session, pause=lambda _: None)
        self.assertEqual(session.get.call_count, 2)
        self.assertFalse(result['robots_allows_search'])

    def test_form_does_not_imply_extraction_ready(self):
        session = Mock(headers={})
        session.get.side_effect = [response(200, '<a href="https://idoxpa.westminster.gov.uk/online-applications/">Portal</a>'), response(404),
                                  response(200, '<form id="advancedSearchForm">'+''.join('<input name="date('+name+')">' for name in ('applicationReceivedStart', 'applicationReceivedEnd', 'applicationDecisionStart', 'applicationDecisionEnd'))+'</form>')]
        result = verify(session, pause=lambda _: None)
        self.assertTrue(result['preflight_passed'])
        self.assertFalse(result['ready_for_extraction'])
        self.assertFalse(result['terms_reviewed'])
        self.assertEqual(result['live_records_collected'], 0)


if __name__ == '__main__':
    unittest.main()
