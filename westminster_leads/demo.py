"""Explicitly synthetic fixtures; never presented as council applications."""
from datetime import date, timedelta


def examples():
    descriptions = [
        'Roof replacement and dormer extension to a terraced house',
        'Basement excavation, drainage and refurbishment',
        'Kitchen and bathroom renovation with electrical rewiring and boiler replacement',
        'Garden landscaping and new paving',
        'Tree works to a protected tree',
        'Advertisement consent for illuminated signage',
        'Demolition and erection of a new building with solar panels',
        'Internal alterations and conversion of existing premises',
    ]
    for i, description in enumerate(descriptions):
        yield {'reference': f'DEMO-WESTMINSTER-{i+1:03}', 'description': description,
               'council': 'Westminster', 'address': f'Synthetic example {i+1}, Westminster SW1A (not a real property)',
               'date_received': (date.today()-timedelta(days=14)).isoformat(),
               'decision_date': (date.today()-timedelta(days=1)).isoformat(),
               'status': 'Decided', 'decision': 'Refused' if i == 7 else 'Granted',
               'agent': 'Synthetic demo agent — no contact details',
               'source_url': 'https://idoxpa.westminster.gov.uk/online-applications/',
               'provenance': 'synthetic'}
