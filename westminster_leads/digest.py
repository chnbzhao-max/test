import html
import re
from datetime import date, datetime, timedelta
from pathlib import Path


def granted(record):
    # Status 'Decided' alone and discharge-of-condition decisions are not approvals.
    application_type = record.get('application_type', '').lower()
    if any(term in application_type for term in ('discharge', 'approval of details', 'non-material amendment', 'lawful development', 'listed building consent')) and 'full planning' not in application_type:
        return False
    decision = record.get('decision', '').lower().strip()
    return bool(re.search(r'\b(granted|grant|approved|permit|permitted)\b', decision)) and not re.search(r'\b(refus|not |discharge|condition|withdraw|pending)', decision)


def parse_date(value):
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%a %d %b %Y', '%d %b %Y', '%d %B %Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def select(records, trade=None, area='', min_confidence=.7, granted_only=True, since=None):
    selected = []
    for record, result in records:
        if not result or result.get('excluded'):
            continue
        if granted_only and not granted(record):
            continue
        if area and area.casefold() not in record.get('address', '').casefold():
            continue
        scores = result['confidence_scores']
        if trade and scores.get(trade, 0) < min_confidence:
            continue
        if not trade and not any(v >= min_confidence for v in scores.values()):
            continue
        if since:
            day = parse_date(record.get('decision_date', '') if granted_only else (record.get('date_received') or record.get('date_valid', '')))
            if day is None or day < since or day > date.today():
                continue
        selected.append((record, result))
    return selected


def render(records, trade='All trades'):
    demo = any(r.get('provenance') == 'synthetic' for r, _ in records)
    title = f'Westminster — {trade}'
    note = 'SYNTHETIC DEMO — invented applications, not real sales leads.' if demo else 'Source: Westminster City Council public planning metadata. Verify decisions and contact permissions at source.'
    if any(r.get('provenance') == 'london_datahub' for r, _ in records):
        note += ' Data source: GLA London Planning Datahub (secondary source; may lag council updates). Applicant/agent details unavailable; verify at council portal.'
    lines = [f'# {title}', '', note, '', f'{len(records)} matching leads. Planning permission does not establish a start date or a contract.', '']
    cards = []
    for r, c in records:
        lines.extend([f'## {r["reference"]}', r.get('address', ''), c['summary'],
                      f'Decision: {r.get("decision", "Unknown")} · {r.get("decision_date", "Unknown")}',
                      f'Contact route: {c["contact_route"]} — {c["contact_reason"]}',
                      f'Trades: {", ".join(c["relevant_trades"])}', f'Source: {r["source_url"]}', ''])
        # Source URLs are validated, not just escaped (javascript: is unsafe).
        url = r['source_url']
        safe_url = url if url.startswith('https://idoxpa.westminster.gov.uk/') else 'https://www.westminster.gov.uk/'
        cards.append('<article><h2>' + html.escape(r['reference']) + '</h2><p>' + html.escape(r.get('address', '')) + '</p><p>' + html.escape(c['summary']) + '</p><p>' + html.escape(r.get('decision', '') + ' · ' + r.get('decision_date', '')) + '</p><p>Trades: ' + html.escape(', '.join(c['relevant_trades'])) + '</p><p>Contact: ' + html.escape(c['contact_route'] + ' — ' + c['contact_reason']) + '</p><a rel="noreferrer" href="' + html.escape(safe_url, quote=True) + '">Verify on council portal</a></article>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>' + html.escape(title) + '</title><style>body{font:16px system-ui;background:#f3f6f8;color:#162b39;max-width:960px;margin:40px auto;padding:20px}article{background:white;border:1px solid #cbd5df;padding:24px;margin:20px 0;border-radius:12px}a{color:#075985}</style><h1>' + html.escape(title) + '</h1><p>' + html.escape(note) + '</p><p>' + str(len(records)) + ' matching leads. Verify permission and contact permissions before use.</p>' + ''.join(cards) + '</html>'
    return '\n'.join(lines), page


def write_digests(store, directory, trades, days=7, **filters):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for trade in trades:
        chosen = select(list(store.records()), trade=trade, since=date.today()-timedelta(days=days-1), **filters)
        md, page = render(chosen, trade)
        slug = re.sub(r'[^a-z0-9]+', '-', trade.lower()).strip('-')
        for ext, content in [('md', md), ('html', page)]:
            target = directory / (slug + '.' + ext)
            target.write_text(content, encoding='utf-8')
            paths.append(str(target))
    return paths
