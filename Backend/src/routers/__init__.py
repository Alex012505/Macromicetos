"""Routers de la API."""
from routers import auth, taxa, locations, events, occurrences, measurements, multimedia, morphology
ALL_ROUTERS = [
    auth.router,
    taxa.router,
    locations.router,
    events.router,
    occurrences.router, measurements.router,
    multimedia.router,
    morphology.router
]