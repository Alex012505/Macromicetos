"""Legacy scientific routers; the application API lives in ``routers.application``."""
from routers import auth, curation, events, locations, measurements, morphology, multimedia, occurrences, taxa

ALL_ROUTERS = [
    auth.router,
    taxa.router,
    locations.router,
    events.router,
    occurrences.router,
    measurements.router,
    multimedia.router,
    morphology.router,
    curation.router,
]
