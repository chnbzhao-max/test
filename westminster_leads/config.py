from pathlib import Path

BASE = 'https://idoxpa.westminster.gov.uk/online-applications/'
ROOT = Path(__file__).resolve().parent.parent
# The source documents say ten categories but also list Plumbing: preserve all eleven.
TAXONOMY = {
    'Scaffolding': r'\b(scaffold|roof|extension|external alteration|facade|façade)',
    'Groundworks': r'\b(basement|foundation|excavat|drainage|new building|erection)',
    'Roofing': r'\b(roof|loft|dormer)',
    'Kitchens & Bathrooms': r'\b(kitchen|bathroom|toilet)',
    'Electrical': r'\b(rewir|electrical|solar|photovoltaic|charging point)',
    'Plumbing': r'\b(plumb|boiler|heating|water supply|drainage)',
    'Skip Hire / Waste Removal': r'\b(demoli|extension|excavat|refurbish|strip.out)',
    'Architecture': r'\b(extension|new building|erection|conversion|redevelop)',
    'Party-Wall Surveying': r'\b(party.wall|boundary wall|basement|terraced)',
    'General Building / Refurbishment': r'\b(refurbish|extension|conversion|alteration|erection|redevelop)',
    'Landscaping': r'\b(landscap|garden|paving|driveway|hardstanding)',
}
