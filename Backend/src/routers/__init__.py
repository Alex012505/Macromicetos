"""Routers de la API."""
from routers import auth

# Registro central: main.py los incluye con sus prefijos.
ALL_ROUTERS = [
    auth.router
]