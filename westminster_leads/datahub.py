"""Public London Planning Datahub metadata adapter (not a council-portal bypass)."""
import json
import time
from datetime import date, datetime, timedelta

import requests

from .config import BASE

API = 'https://planningdata.london.gov.uk/api-guest/applications/_search'


def parse_day(value):
    try:
        return datetime.strptime(value, '%d/%m/%Y').date() if value else None
    except (ValueError, TypeError):
        raise ValueError('Unexpected Datahub date format')


def normalize(source):
    if (source.get('lpa_name') or '').strip().casefold() != 'westminster':
        raise ValueError('Unexpected local planning authority')
    if not source.get('lpa_app_no') or not source.get('description'):
        raise ValueError('Missing reference or description in Datahub record')
    record = {
        'reference': source['lpa_app_no'].strip(), 'council': 'Westminster',
        'description': source['description'],
        'address': ', '.join(str(source[k]).strip() for k in ('site_name', 'site_number', 'street_name', 'locality', 'postcode') if source.get(k)),
        'application_type': source.get('application_type_full') or source.get('application_type') or '',
        'status': source.get('status') or '', 'decision': source.get('decision') or '',
        'date_valid': source.get('valid_date') or '', 'decision_date': source.get('decision_date') or '',
        'postcode': source.get('postcode') or '', 'ward': source.get('ward') or '',
        'source_url': source.get('url_planning_app') or BASE,
        'provenance': 'london_datahub', 'source_record_id': source.get('id'),
        'source_last_updated': source.get('last_updated'), 'source_last_synced': source.get('last_synced'),
        'coordinates': source.get('centroid'),
        'source_note': 'GLA London Planning Datahub; verify latest decision and contact route at council. Validated date is not received date.',
    }
    return record


class DatahubExtractor:
    def __init__(self, max_pages=30, page_size=100, session=None, pause=time.sleep):
        if not 1 <= page_size <= 500 or max_pages < 1:
            raise ValueError('Invalid pagination limits')
        self.session = session or requests.Session()
        self.session.headers['User-Agent'] = 'WestminsterPlanningLeadsPrototype/0.1 (public metadata research; rate limited)'
        self.max_pages, self.page_size, self.pause = max_pages, page_size, pause
        self.stats = {}

    def request(self, query):
        for attempt in range(3):
            self.pause(2)
            r = self.session.get(API, params={'source': json.dumps(query), 'source_content_type': 'application/json'}, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                self.pause(2 ** (attempt+1))
                continue
            r.raise_for_status()
            body = r.json()
            if body.get('timed_out') or body.get('_shards', {}).get('failed', 0):
                raise RuntimeError('Incomplete Datahub response')
            return body
        raise RuntimeError('Datahub request retries exhausted')

    def collect(self, weeks=4, end=None):
        end = end or date.today()
        start = end - timedelta(days=weeks*7-1)
        ranges = [{'range': {field: {'gte': start.strftime('%d/%m/%Y'), 'lte': end.strftime('%d/%m/%Y'), 'format': 'dd/MM/yyyy'}}}
                  for field in ('valid_date', 'decision_date')]
        query = {'size': self.page_size, 'track_total_hits': True,
                 'query': {'bool': {'filter': [{'match_phrase': {'lpa_name': 'Westminster'}}], 'should': ranges, 'minimum_should_match': 1}},
                 'sort': [{'last_updated': 'desc'}]}
        seen_ids, seen_refs = set(), set()
        expected = None
        self.stats = {'source': API, 'start': start.isoformat(), 'end': end.isoformat(), 'date_basis': 'validated OR decided', 'pages': 0, 'complete': False}
        for page in range(self.max_pages):
            if page*self.page_size >= 10000:
                raise RuntimeError('Datahub result window reached; narrow the date range')
            query['from'] = page*self.page_size
            body = self.request(query)
            hits = body['hits']
            total = hits['total']
            if total['relation'] != 'eq':
                raise RuntimeError('Datahub total is not exact')
            if expected is None:
                expected = total['value']
                self.stats['api_total'] = expected
            elif expected != total['value']:
                raise RuntimeError('Datahub changed during pagination; rerun rather than claiming completeness')
            self.stats['pages'] += 1
            for hit in hits['hits']:
                record = normalize(hit['_source'])
                if hit['_id'] in seen_ids or record['reference'] in seen_refs:
                    raise RuntimeError('Duplicate Datahub record during pagination; inspect source/index changes')
                dates = [parse_day(record.get(k)) for k in ('date_valid', 'decision_date')]
                if not any(day is not None and start <= day <= end for day in dates):
                    raise RuntimeError('Datahub returned a record outside requested date range')
                seen_ids.add(hit['_id'])
                seen_refs.add(record['reference'])
                yield record
            self.stats['unique_records'] = len(seen_refs)
            if len(seen_refs) == expected:
                self.stats['complete'] = True
                return
            if not hits['hits'] or len(seen_refs) > expected:
                raise RuntimeError('Datahub record count does not match exact total')
        raise RuntimeError('Datahub page limit reached before complete retrieval')
