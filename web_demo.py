#!/usr/bin/env python3
"""Private read-only demonstration; loopback binding by default. No emailing or automatic outreach."""
import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from westminster_leads.config import ROOT, TAXONOMY
from westminster_leads.digest import render, select
from westminster_leads.storage import Store
from westminster_leads.geography import postcode_centre
import requests


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true')
    mode.add_argument('--datahub', action='store_true')
    parser.add_argument('--host', choices=['127.0.0.1','0.0.0.0'], default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    directory = ROOT/'data'/('datahub' if args.datahub else 'live' if args.live else 'demo')
    if not (directory/'planning_leads.db').exists():
        parser.error('Run run.py first to create this dataset')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            if url.path not in ('/', '/digest.md'):
                self.send_error(404)
                return
            q = parse_qs(url.query)
            trade = q.get('trade', [''])[0]
            try:
                centre_text = q.get('centre-postcode', [''])[0].strip()
                radius_text = q.get('radius-km', [''])[0].strip()
                if bool(centre_text) != bool(radius_text): raise ValueError('Provide postcode and radius together')
                radius = float(radius_text) if radius_text else None
                if radius is not None and not 0 < radius <= 100: raise ValueError('Invalid radius')
                centre = postcode_centre(centre_text) if centre_text else None
                confidence = float(q.get('confidence', ['0.7'])[0])
                if not 0 <= confidence <= 1 or trade and trade not in TAXONOMY:
                    raise ValueError()
            except requests.RequestException:
                self.send_error(502, 'Postcode lookup unavailable'); return
            except ValueError:
                self.send_error(400, 'Invalid filter')
                return
            store = Store(directory)
            try:
                records = select(list(store.records()), trade=trade, area=q.get('area', [''])[0], min_confidence=confidence,
                                 granted_only=q.get('status', ['granted'])[0] != 'all', centre=centre, radius_km=radius)
            finally:
                store.close()
            md, page = render(records, trade or 'All trades')
            if url.path == '/digest.md':
                content, mime = md, 'text/markdown'
            else:
                options = '<option value="">All trades</option>'+''.join('<option'+(' selected' if t == trade else '')+'>'+html.escape(t)+'</option>' for t in TAXONOMY)
                controls = '<form><label>Trade <select name="trade">'+options+'</select></label> <label>Area/postcode prefix <input name="area" value="'+html.escape(q.get('area', [''])[0], quote=True)+'"></label> <label>Status <select name="status"><option value="granted">Granted only</option><option value="all"'+(' selected' if q.get('status') == ['all'] else '')+'>All statuses</option></select></label> <label>Min score <input type="number" name="confidence" min="0" max="1" step="0.05" value="'+str(confidence)+'"></label> <label>Centre postcode <input name="centre-postcode" value="'+html.escape(centre_text, quote=True)+'" placeholder="SW1A 1AA"></label> <label>Radius km <input type="number" name="radius-km" min="0.1" max="100" step="0.1" value="'+html.escape(radius_text, quote=True)+'"></label> <button>Filter</button></form><p><a href="/digest.md'+html.escape('?' + url.query, quote=True)+'">Export filtered Markdown</a></p>'
                content, mime = page.replace('<!--FILTERS-->', controls, 1), 'text/html'
            body = content.encode()
            self.send_response(200)
            self.send_header('Content-Type', mime+'; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

    print(f'Dashboard running on loopback port {args.port}; mode={"london_datahub" if args.datahub else "live" if args.live else "synthetic"}', flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
