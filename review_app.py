#!/usr/bin/env python3
"""Private human-label review UI; predictions are deliberately not loaded."""
import argparse
import hashlib
import html
import json
import secrets
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from westminster_leads.config import ROOT, TAXONOMY

LOCK = threading.Lock()


def record_hash(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save_label(path, fields):
    with LOCK:
        samples = json.loads(path.read_text())
        index = int(fields['index'][0])
        if not 0 <= index < len(samples):
            raise ValueError('Invalid sample index')
        sample = samples[index]
        if fields.get('reference', [''])[0] != sample['record']['reference']:
            raise ValueError('Sample changed; reload the page')
        reviewer = fields.get('reviewer', [''])[0].strip()
        if not reviewer or len(reviewer) > 100 or fields.get('attested') != ['yes']:
            raise ValueError('Reviewer name and independent-review confirmation are required')
        trades = fields.get('trade', [])
        if len(trades) != len(set(trades)) or any(t not in TAXONOMY for t in trades):
            raise ValueError('Invalid trade labels')
        no_trades = fields.get('no_trades') == ['yes']
        if bool(trades) == no_trades:
            raise ValueError('Select trades OR explicitly select no relevant trade')
        contact = fields.get('contact', [''])[0]
        record = sample['record']
        if contact not in ('portal', 'agent', 'applicant', 'excluded'):
            raise ValueError('Invalid contact route')
        if contact in ('agent', 'applicant') and not record.get(contact):
            raise ValueError('This source does not provide that contact route')
        if contact == 'excluded' and trades:
            raise ValueError('Excluded proposals must have no relevant trades')
        sample.update(trades=trades, contact_route=None if contact == 'excluded' else contact,
                      reviewer_note=fields.get('note', [''])[0][:2000], reviewer=reviewer,
                      label_source='human', reviewed_at=datetime.now(timezone.utc).isoformat(),
                      reviewed_record_sha256=record_hash(record))
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(samples, indent=2, ensure_ascii=False))
        temp.replace(path)
        return len(samples)


def handler_for(path):
    csrf = secrets.token_urlsafe(32)
    escape = html.escape

    class Handler(BaseHTTPRequestHandler):
        last_reviewer = ''
        def send_page(self, code, content):
            body = content.encode()
            self.send_response(code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path != '/':
                self.send_error(404); return
            samples = json.loads(path.read_text())
            if not samples:
                self.send_error(400, 'Review set is empty'); return
            done = sum(s.get('label_source') == 'human' and s.get('reviewed_record_sha256') == record_hash(s['record']) for s in samples)
            try:
                default = next((i for i, s in enumerate(samples) if not s.get('reviewed_at')), 0)
                index = int(parse_qs(url.query).get('i', [str(default)])[0])
                if not 0 <= index < len(samples): raise ValueError()
            except ValueError:
                self.send_error(400, 'Invalid sample'); return
            sample = samples[index]; r = sample['record']
            selected = sample.get('trades') or []
            options = ''.join('<label><input type="checkbox" name="trade" value="'+escape(t, quote=True)+'"'+(' checked' if t in selected else '')+'>'+escape(t)+'</label>' for t in TAXONOMY)
            routes = [('portal', 'Council portal — contact details unavailable')]
            routes += [(t, t.title()) for t in ('agent', 'applicant') if r.get(t)]
            routes.append(('excluded', 'Exclude — no contact routing needed'))
            contact = sample.get('contact_route') or ('excluded' if sample.get('label_source') == 'human' else 'portal')
            route_options = ''.join('<option value="'+key+'"'+(' selected' if contact == key else '')+'>'+escape(label)+'</option>' for key, label in routes)
            body = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Independent review</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto;padding:20px;background:#f5f7fa;color:#182c3c}label{display:block;margin:10px 0}article,form{background:white;padding:24px;margin:16px 0;border:1px solid #ccd7e0;border-radius:12px}pre{white-space:pre-wrap}button{padding:12px 24px;background:#075985;color:white;border:0;border-radius:6px}input[type=text],textarea,select{padding:8px;max-width:95%}</style>'
            body += '<h1>Independent human review</h1><p>'+str(done)+' / '+str(len(samples))+' reviewed. Sample '+str(index+1)+'. Predictions are hidden; no accuracy has been measured yet.</p>'
            body += '<article><h2>'+escape(r['reference'])+'</h2><p>'+escape(r.get('application_type',''))+' · '+escape(r.get('status',''))+' · '+escape(r.get('decision',''))+'</p><pre>'+escape(r['description'])+'</pre><p>Judge potential trades from the actual proposed work, not from location words or historical work quoted in the description. Permission is not proof of construction.</p></article>'
            body += '<form method="post" action="/label"><input type="hidden" name="csrf" value="'+csrf+'"><input type="hidden" name="index" value="'+str(index)+'"><input type="hidden" name="reference" value="'+escape(r['reference'], quote=True)+'">'+options
            body += '<label><input type="checkbox" name="no_trades" value="yes"'+(' checked' if sample.get('trades') == [] else '')+'>No relevant trade (explicit negative label)</label><label>Contact route <select name="contact">'+route_options+'</select></label><label>Reviewer <input type="text" name="reviewer" required maxlength="100" value="'+escape(sample.get('reviewer',type(self).last_reviewer), quote=True)+'"></label><label>Reason / ambiguity <textarea name="note" rows="3" cols="80">'+escape(sample.get('reviewer_note',''))+'</textarea></label><label><input type="checkbox" name="attested" value="yes" required>I independently reviewed the source description without using model predictions as the answer.</label><button>Save and next</button></form>'
            body += '<p>'+(' <a href="/?i='+str(index-1)+'">Previous</a> ' if index else '')+(' <a href="/?i='+str(index+1)+'">Next without saving</a>' if index+1 < len(samples) else '')+'</p></html>'
            self.send_page(200, body)

        def do_POST(self):
            if urlsplit(self.path).path != '/label':
                self.send_error(404); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536: raise ValueError('Invalid request size')
                fields = parse_qs(self.rfile.read(length).decode(), keep_blank_values=True)
                if fields.get('csrf') != [csrf]:
                    self.send_error(403); return
                count = save_label(path, fields)
                type(self).last_reviewer = fields['reviewer'][0].strip()
                next_index = min(int(fields['index'][0])+1, count-1)
            except (ValueError, KeyError, UnicodeError) as error:
                self.send_page(400, '<p>'+escape(str(error))+'</p><a href="/">Return to review</a>'); return
            self.send_response(303); self.send_header('Location', '/?i='+str(next_index)); self.end_headers()

    return Handler


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--labels', type=Path, default=ROOT/'data/datahub/review/human_labels_template.json')
    p.add_argument('--host', choices=['127.0.0.1','0.0.0.0'], default='127.0.0.1')
    p.add_argument('--port', type=int, default=8002)
    a = p.parse_args()
    if not a.labels.exists(): p.error('Run audit_data.py first to prepare the review set')
    server = ThreadingHTTPServer((a.host,a.port), handler_for(a.labels))
    print(f'Review UI listening on port {a.port}. Keep Codespaces port visibility PRIVATE.', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
