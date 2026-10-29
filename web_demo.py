#!/usr/bin/env python3
"""Loopback-only, read-only demonstration. No emailing or automatic outreach."""
import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from westminster_leads.config import ROOT, TAXONOMY
from westminster_leads.digest import render, select
from westminster_leads.storage import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    directory = ROOT/'data'/('live' if args.live else 'demo')
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
                confidence = float(q.get('confidence', ['0.7'])[0])
                if not 0 <= confidence <= 1 or trade and trade not in TAXONOMY:
                    raise ValueError()
            except ValueError:
                self.send_error(400, 'Invalid filter')
                return
            store = Store(directory)
            try:
                records = select(list(store.records()), trade=trade, area=q.get('area', [''])[0], min_confidence=confidence,
                                 granted_only=q.get('status', ['granted'])[0] != 'all')
            finally:
                store.close()
            md, page = render(records, trade or 'All trades')
            if url.path == '/digest.md':
                content, mime = md, 'text/markdown'
            else:
                options = '<option value="">All trades</option>'+''.join('<option'+(' selected' if t == trade else '')+'>'+html.escape(t)+'</option>' for t in TAXONOMY)
                controls = '<form><label>Trade <select name="trade">'+options+'</select></label> <label>Area/postcode prefix <input name="area" value="'+html.escape(q.get('area', [''])[0], quote=True)+'"></label> <label>Status <select name="status"><option value="granted">Granted only</option><option value="all"'+(' selected' if q.get('status') == ['all'] else '')+'>All statuses</option></select></label> <label>Min score <input type="number" name="confidence" min="0" max="1" step="0.05" value="'+str(confidence)+'"></label> <button>Filter</button></form><p><a href="/digest.md'+html.escape('?' + url.query, quote=True)+'">Export filtered Markdown</a></p>'
                content, mime = page.replace('<h1>', controls+'<h1>', 1), 'text/html'
            body = content.encode()
            self.send_response(200)
            self.send_header('Content-Type', mime+'; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

    print(f'Dashboard running on loopback port {args.port}; mode={"live" if args.live else "synthetic"}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
