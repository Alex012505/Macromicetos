"""Shared HTTP helpers for the application routers."""
from contextlib import contextmanager

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


@contextmanager
def mutation(db):
    """Commit the whole operation or roll back entities and new files."""
    written = []
    try:
        yield written
        db.commit()
    except Exception as error:
        db.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        if isinstance(error, IntegrityError):
            raise HTTPException(409, "Los datos entran en conflicto con un registro existente.") from error
        raise


async def multipart(request, schema):
    """Parse the ``payload`` JSON field and the ``file_<media_id>`` uploads."""
    form = await request.form(max_files=10, max_fields=100, max_part_size=2 * 1024 * 1024)
    payload = form.get("payload")
    if not isinstance(payload, str) or len(payload) > 2 * 1024 * 1024:
        raise HTTPException(422, "Falta el campo JSON payload o supera el tamaño permitido.")
    try:
        body = schema.model_validate_json(payload)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    files = {}
    for key, value in form.multi_items():
        if key == "payload":
            continue
        if not key.startswith("file_") or not hasattr(value, "read") or key[5:] in files:
            raise HTTPException(422, "Campos de archivo inválidos o duplicados.")
        files[key[5:]] = value
    if set(files) != {str(photo.media_id) for photo in body.multimedia}:
        raise HTTPException(422, "Los archivos y sus metadatos no coinciden.")
    return body, files


def find(db, model, entity_id):
    row = db.get(model, entity_id)
    if row is None:
        raise HTTPException(404, "El registro solicitado no existe.")
    return row
