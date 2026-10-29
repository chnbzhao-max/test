#!/usr/bin/env python3
"""Build a shareable offline slide deck from the local dataset, not invented metrics."""
import argparse
import html
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from westminster_leads.config import ROOT
from westminster_leads.storage import Store
from westminster_leads.digest import select


def build(directory, output):
    directory = Path(directory)
    if not (directory/'planning_leads.db').exists(): raise ValueError('Collect real data before building the deck')
    store = Store(directory)
    try: rows = list(store.records()); checkpoint = store.sync_state()
    finally: store.close()
    if not rows: raise ValueError('Dataset is empty')
    since = date.today()-timedelta(days=27)
    counts = {t:len(select(rows,trade=t,since=since)) for t in ('Roofing','Scaffolding','Groundworks')}
    sources = Counter(r.get('provenance','unknown') for r,c in rows)
    excluded = sum(bool(c and c.get('excluded')) for r,c in rows)
    esc = html.escape
    table = '<table><tr><th>Trade</th><th>Current 28-day approval leads</th></tr>'+''.join('<tr><td>'+esc(t)+'</td><td>'+str(n)+'</td></tr>' for t,n in counts.items())+'</table>'
    slides = [
        ('Westminster Planning Leads', '<p class="large">A working prototype: public planning metadata → potential trade leads.</p><p>Python · SQLite · public Datahub API · rules / optional LLM</p><p>Snapshot built '+date.today().isoformat()+'. Secondary data source; no measured classification accuracy claimed.</p>'),
        ('The problem and the product', '<p>Planning registers contain useful signals, but tradespeople need a short, local, trade-specific feed.</p><ul><li>Identify relevant approvals</li><li>Explain the proposed work</li><li>Link back to the original council search</li></ul><p>Planning permission does not prove construction is about to start.</p>'),
        ('Real data, explicit provenance', '<p class="large">'+str(len(rows))+' unique applications stored</p><p>'+str(excluded)+' currently screened out by the prefilter.</p><p>Sources: '+esc(', '.join(f'{k}: {v}' for k,v in sources.items()))+'</p><p>Datahub can lag the council. Validated date is not received date. The database may retain older applications updated since initial collection.</p>'),
        ('Reliable incremental pipeline', '<p>API → bounded pagination → SQLite → JSON & Markdown → classification → digest</p><ul><li>Successful sync checkpoint stored in SQLite</li><li>Only updated/synced records requested after bootstrap</li><li>Two-hour overlap; reference-based deduplication</li><li>Failed runs keep the previous checkpoint</li><li>Timestamp-only changes preserve classifications</li></ul><p>Checkpoint present: '+('yes' if checkpoint else 'no — next collection bootstraps')+'</p>'),
        ('The lead output', table+'<p>Counts overlap across trades. Conservative primary-permission filter excludes separate LBC, amendments, condition variations and retrospective proposals.</p><p>Area and optional postcode-centred radius filtering; HTML/Markdown exports.</p>'),
        ('Validation: what is and is not proven', '<ul><li>Real API pagination and repeated-run behaviour verified</li><li>Ten-record / sixty-field import-fidelity spot-check recorded</li><li>SQLite, JSON and Markdown audit available</li><li>Regression tests cover observed classification and consent mistakes</li></ul><p class="notice">Trade accuracy is not yet measured against independent human labels. A blind human-review UI and evaluator are provided. Live LLM verification needs a securely configured API key.</p>'),
        ('Operation and next decisions', '<ul><li>GitHub Actions workflow: scheduled twice-weekly sync, state cache, downloadable digests and failure status</li><li>Private Codespaces dashboard and independent-review interface</li><li>Complete human labels; measure F1 and review errors on held-out examples</li><li>Verify commercial reuse terms and council cross-check before sale</li><li>Use durable storage and production authentication before wider deployment</li></ul><p>Workflow configuration and local tests are distinct from a successful hosted Actions run. Cache retention is not a permanent backup.</p>'),
    ]
    sections=[]
    for i,(title,body) in enumerate(slides,1):
        nav=('<a href="#slide-'+str(i-1)+'">← Previous</a>' if i>1 else '')+' '+('<a href="#slide-'+str(i+1)+'">Next →</a>' if i<len(slides) else '')
        sections.append('<section id="slide-'+str(i)+'"><div class="number">'+str(i)+' / '+str(len(slides))+'</div><h1>'+esc(title)+'</h1>'+body+'<nav>'+nav+'</nav></section>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Westminster — presentation</title><style>html{scroll-behavior:smooth}body{margin:0;background:#0b1729;color:#edf5ff;font:clamp(16px,2vw,25px)/1.5 system-ui}section{box-sizing:border-box;min-height:100vh;padding:6vh 8vw;border-bottom:1px solid #33465e;position:relative}h1{font-size:clamp(30px,4vw,56px);color:#76dcbd}li{margin:14px 0}.large{font-size:1.5em}.number,nav{color:#a5b8ce}nav a{color:#76dcbd;margin-right:24px}table{border-collapse:collapse;width:100%;max-width:900px}td,th{text-align:left;border-bottom:1px solid #42617a;padding:16px}.notice{background:#18344a;padding:20px;border-left:5px solid #ffca70}@media print{body{background:white;color:#15283a;font:16pt/1.4 sans-serif}section{min-height:0;height:190mm;break-after:page;padding:10mm;border:0}h1{color:#075985}nav{display:none}.notice{background:#edf5fa}.number{color:#456}}</style>'+''.join(sections)+'</html>'
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(page)
    return {'slides':len(slides),'records':len(rows),'approval_counts':counts,'path':str(output),'accuracy_measured':False}


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',type=Path,default=ROOT/'data/datahub')
    p.add_argument('--output',type=Path,default=ROOT/'data/presentation/index.html')
    a=p.parse_args();print(json.dumps(build(a.data_dir,a.output),indent=2))
