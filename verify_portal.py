#!/usr/bin/env python3
"""Read-only connectivity/structure preflight; does not approve terms or scrape records."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from westminster_leads.config import BASE

GUIDANCE = 'https://www.westminster.gov.uk/planning-building-control-and-environmental-regulations/planning-applications/search-and-comment-planning-applications-and-register-email-notifications'
AGENT = 'WestminsterPlanningLeadsPrototype/0.1 (public metadata research; rate limited)'


def verify(session=None, pause=time.sleep):
    session = session or requests.Session()
    session.headers['User-Agent'] = AGENT
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'checks': [],
              'live_records_collected': 0, 'terms_reviewed': False, 'ready_for_extraction': False}

    def get(name, url):
        pause(2)
        try:
            response = session.get(url, timeout=25)
        except requests.RequestException as error:
            report['checks'].append({'name': name, 'error': type(error).__name__})
            return None
        report['checks'].append({'name': name, 'status': response.status_code,
                                 'content_type': response.headers.get('Content-Type', '')})
        return response

    guidance = get('official_guidance', GUIDANCE)
    if guidance is not None and guidance.status_code == 200:
        soup = BeautifulSoup(guidance.text, 'html.parser')
        report['official_portal_link_confirmed'] = any(
            a['href'].startswith(('https://idoxpa.westminster.gov.uk/online-applications/',
                                  'http://idoxpa.westminster.gov.uk/online-applications/')) for a in soup.select('a[href]'))
    robots_response = get('robots', 'https://idoxpa.westminster.gov.uk/robots.txt')
    if robots_response is None or robots_response.status_code not in (200, 404):
        report['result'] = 'blocked_before_search: robots could not be read; extraction not attempted'
        return report
    if robots_response.status_code == 200 and '<html' in robots_response.text.lower():
        report['result'] = 'blocked_before_search: robots returned HTML rather than a policy'
        return report
    robots = RobotFileParser()
    robots.parse(robots_response.text.splitlines() if robots_response.status_code == 200 else [])
    search_url = BASE + 'search.do?action=advanced'
    allowed = robots.can_fetch(AGENT, search_url)
    report['robots_allows_search'] = allowed
    if not allowed:
        report['result'] = 'blocked_by_robots: search not requested'
        return report
    search = get('advanced_search', search_url)
    if search is None or search.status_code != 200:
        report['result'] = 'blocked_before_parsing: search unavailable'
        return report
    if any(x in search.text.lower() for x in ('captcha', 'access denied', 'verify you are human')):
        report['result'] = 'access_challenge: stop; no bypass attempted'
        return report
    soup = BeautifulSoup(search.text, 'html.parser')
    form = soup.select_one('form#advancedSearchForm') or next((f for f in soup.select('form') if f.select_one('[name="date(applicationReceivedStart)"]')), None)
    report['search_form_found'] = form is not None
    if form is None:
        report['result'] = 'adapter_mismatch: inspect actual public search HTML'
        return report
    # Report input names only, never hidden values, cookies, tokens or headers.
    names = {e['name'] for e in form.select('[name]')}
    required = ['date(applicationReceivedStart)', 'date(applicationReceivedEnd)',
                'date(applicationDecisionStart)', 'date(applicationDecisionEnd)']
    report['date_fields_present'] = {name: name in names for name in required}
    report['preflight_passed'] = all(report['date_fields_present'].values()) and report.get('official_portal_link_confirmed', False)
    report['result'] = ('preflight_passed: review terms, then verify one-week extraction against portal manually'
                        if report['preflight_passed'] else 'adapter_mismatch: current date fields differ from adapter')
    return report


def main():
    report = verify()
    target = Path(__file__).resolve().parent/'data'/'verification'/'preflight.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report.get('preflight_passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
