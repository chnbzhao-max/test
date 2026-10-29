"""Conservative Idox adapter. Live Westminster selectors await source verification."""
import hashlib
import json
import logging
import random
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .config import BASE

LOG = logging.getLogger(__name__)
FIELDS = {
    'application reference': 'reference', 'reference': 'reference',
    'application received': 'date_received', 'date received': 'date_received',
    'application validated': 'date_valid', 'date validated': 'date_valid',
    'application type': 'application_type', 'proposal': 'description',
    'address': 'address', 'status': 'status', 'decision': 'decision',
    'decision issued date': 'decision_date', 'decision date': 'decision_date',
    'applicant name': 'applicant', 'applicant address': 'applicant_address',
    'agent name': 'agent', 'agent address': 'agent_address',
}


def parse_detail(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    record = {'council': 'Westminster', 'source_url': url, 'provenance': 'live'}
    for row in soup.select('tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) >= 2:
            label = ' '.join(cells[0].stripped_strings).strip(': ').lower()
            if label in FIELDS:
                record[FIELDS[label]] = ' '.join(cells[1].stripped_strings)
    if not record.get('reference') or not record.get('description'):
        raise ValueError('Detail page missing reference/proposal; portal may have changed or blocked access')
    return record


def result_links(html, current):
    soup = BeautifulSoup(html, 'html.parser')
    details = list(dict.fromkeys(urljoin(current, a['href']) for a in soup.select('a[href]')
                                if 'applicationDetails.do' in a['href']))
    next_link = soup.select_one('a.next, a[rel="next"]')
    if not next_link:
        next_link = next((a for a in soup.select('a[href]') if a.get_text(strip=True).lower() in ('next', 'next >', 'next »')), None)
    return details, urljoin(current, next_link['href']) if next_link else None


class Extractor:
    def __init__(self, cache, max_pages=30, refresh=False):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'WestminsterPlanningLeadsPrototype/0.1 (public metadata research; rate limited)'
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.max_pages = max_pages
        self.refresh = refresh
        self.last_request = 0
        self.robots = None

    def request(self, url, data=None, cache=True):
        url = urljoin(BASE, url)
        if urlsplit(url).netloc != urlsplit(BASE).netloc:
            raise ValueError('Refusing request outside council portal')
        if self.robots is not None and not self.robots.can_fetch(self.session.headers['User-Agent'], url):
            raise RuntimeError('robots.txt disallows this URL')
        key = hashlib.sha256((url + json.dumps(data, sort_keys=True)).encode()).hexdigest()
        path = self.cache / (key + '.json')
        if cache and not self.refresh and path.exists():
            saved = json.loads(path.read_text())
            if time.time() - saved['saved_at'] < 21600:
                return saved['html'], saved['url']
        for attempt in range(3):
            time.sleep(max(0, self.last_request + random.uniform(1, 3) - time.monotonic()))
            self.last_request = time.monotonic()
            response = self.session.request('POST' if data is not None else 'GET', url, data=data, timeout=30)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                wait = response.headers.get('Retry-After', '')
                time.sleep(min(int(wait), 120) if wait.isdigit() else 2 ** (attempt + 1))
                continue
            response.raise_for_status()
            html = response.text
            if urlsplit(response.url).netloc != urlsplit(BASE).netloc:
                raise RuntimeError('Unexpected redirect outside portal')
            if any(x in html.lower() for x in ('captcha', 'access denied', 'verify you are human')):
                raise RuntimeError('Portal access challenge; stop and inspect, do not bypass')
            if cache:
                path.write_text(json.dumps({'saved_at': time.time(), 'html': html, 'url': response.url}))
            return html, response.url
        raise RuntimeError('Request retries exhausted')

    def check_policy(self):
        robots_url = urljoin(BASE, '/robots.txt')
        # Fetch explicitly so unavailable policy is not silently treated as approval.
        response = self.session.get(robots_url, timeout=30)
        self.last_request = time.monotonic()
        if response.status_code == 404:
            text = ''
        else:
            response.raise_for_status()
            text = response.text
            if '<html' in text.lower():
                raise RuntimeError('robots.txt returned HTML; policy could not be verified')
        self.robots = RobotFileParser()
        self.robots.parse(text.splitlines())
        (self.cache / 'robots.txt').write_text(text)

    def search(self, start, end, determined=False):
        html, current = self.request('search.do?action=advanced', cache=False)
        soup = BeautifulSoup(html, 'html.parser')
        form = soup.select_one('form#advancedSearchForm') or next((f for f in soup.select('form') if f.select_one('[name="date(applicationReceivedStart)"]')), None)
        if not form:
            raise RuntimeError('Idox advanced search form not found; live adapter needs verification')
        data = {e['name']: e.get('value', '') for e in form.select('input[name]') if e.get('type') == 'hidden'}
        kind = 'applicationDecision' if determined else 'applicationReceived'
        for side, day in [('Start', start), ('End', end)]:
            data[f'date({kind}{side})'] = day.strftime('%d/%m/%Y')
        data['searchType'] = 'Application'
        html, current = self.request(urljoin(current, form.get('action') or 'advancedSearchResults.do?action=firstPage'), data=data, cache=False)
        seen_pages, seen_refs = set(), set()
        for _ in range(self.max_pages):
            signature = hashlib.sha256(html.encode()).hexdigest()
            if signature in seen_pages:
                raise RuntimeError('Repeated results page detected; refusing pagination loop')
            seen_pages.add(signature)
            links, next_url = result_links(html, current)
            if not links:
                if 'no results' in html.lower() or 'no applications found' in html.lower():
                    return
                raise RuntimeError('No application links or recognised empty-results message')
            for link in links:
                detail, final = self.request(link)
                record = parse_detail(detail, final)
                if record['reference'] not in seen_refs:
                    seen_refs.add(record['reference'])
                    yield record
            if not next_url:
                return
            html, current = self.request(next_url, cache=False)
        raise RuntimeError('Page limit reached with more results outstanding; increase --max-pages or narrow date range')

    def collect(self, weeks=4, end=None):
        end = end or date.today()
        self.check_policy()
        # Small weekly windows reduce result truncation; both received and decided.
        for n in range(weeks):
            finish = end - timedelta(days=7*n)
            start = finish - timedelta(days=6)
            for determined in (False, True):
                yield from self.search(start, finish, determined)
