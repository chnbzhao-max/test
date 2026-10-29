# One-page technical design

PDF requirements → Westminster source adapter → SQLite source of truth → JSON and Markdown exports → prefilter → rules or explicit LLM backend → persisted classification → filtered HTML/Markdown digests → read-only dashboard.

## Extraction and persistence

Weekly bounded received and decision searches cover the requested history and catch older applications newly decided. Application reference is the primary key; changed payloads invalidate classifications. This updates changed records found in the current query windows, not arbitrary old withdrawn applications outside both windows. Periodic wider reconciliation is needed. Six-hour cached detail responses reduce traffic; use refresh to validate status changes. The parser fails closed on missing reference or description and pagination loops; partial upserts remain recoverable and the run fails visibly.

Session cookies and hidden fields are retained through a requests Session. No Essex disclaimer mechanism or browser impersonation is copied. Runtime robots rules are checked. Any terms acceptance must be reviewed separately by the operator. No document links or downloads are needed for classification.

## Taxonomy

The canonical labels and lexical triggers are in `westminster_leads/config.py`:
Scaffolding (roof/external/extension); Groundworks (excavation/foundation/drainage); Roofing (roof/loft/dormer); Kitchens & Bathrooms (explicit rooms); Electrical (rewire/solar/charging); Plumbing (boiler/heating/drainage); Skip Hire / Waste Removal (demolition/refurbishment); Architecture (new build/extension/conversion); Party-Wall Surveying (explicit party/boundary walls/basements/terraced); General Building / Refurbishment (general construction); Landscaping (garden/paving).

These are potential trade requirements, not facts. In particular external work does not always need scaffolding, and a basement does not prove a party-wall obligation. Rules intentionally label possible leads, with uncalibrated scores. A real human evaluation is required before pricing or customer delivery.

## Classification and delivery

Early exclusion handles pure trees, advertisements and environmental monitoring, retaining mixed construction proposals. LLM receives minimal metadata with untrusted-data instructions and a fixed output schema checked locally. API errors are explicit. Existing classifications are reused unless content changes or force is requested. Rules and LLM runs identify their methods; do not mix their evaluation claims.

Default digests show explicit recent grants, confidence >=0.7, with original-source attribution. Area is substring/postcode-prefix filtering. A radius search would need licensed coordinates and a distance function; it is not implemented. Dashboard runs on loopback only. It never sends email or performs outreach.

## Phase acceptance

1. Design/taxonomy implemented; live source and terms investigation outstanding.
2. Extractor implemented and fixture-tested; four weeks of real data outstanding.
3. Rules and OpenAI path implemented; live API call and ~50 independent human labels outstanding.
4. Three synthetic sample trade digests and functional local dashboard; real customer feedback outstanding.
5. Repeatable commands, scheduler, local alerts and handover implemented; production monitoring and real-data sign-off outstanding.
