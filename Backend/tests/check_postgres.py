"""Test the API and real TypeScript client in two newly created PostgreSQL DBs.

Never resets the configured application database. Only the random databases
created by this invocation are removed, after each test process has exited.
"""
import argparse
import getpass
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from dotenv import dotenv_values
import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def main():
    parser = argparse.ArgumentParser(description="Pruebas aisladas en PostgreSQL real")
    parser.add_argument("--admin", default="postgres")
    parser.add_argument("--admin-password-file", type=Path)
    args = parser.parse_args()
    configured_url = os.environ.get("DATABASE_URL") or dotenv_values(BACKEND / ".env").get("DATABASE_URL")
    if not configured_url:
        parser.error("Configura primero PostgreSQL con Backend/setup_postgres.py.")
    target = make_url(configured_url)
    if target.get_backend_name() != "postgresql":
        parser.error("La conexión configurada no es PostgreSQL.")
    if args.admin_password_file:
        credential_path = args.admin_password_file.resolve(strict=True)
        if credential_path.parent != (BACKEND / "data").resolve():
            parser.error("El archivo privado debe estar dentro de Backend/data/.")
        admin_password = credential_path.read_text(encoding="utf-8").strip()
    else:
        admin_password = os.environ.get("MACROMICETOS_PG_TEST_ADMIN_PASSWORD") or getpass.getpass(f"Contraseña de {args.admin} (solo para crear bases de prueba): ")
    admin = psycopg2.connect(host=target.host or "127.0.0.1", port=target.port or 5432,
                             dbname="postgres", user=args.admin, password=admin_password, connect_timeout=5)
    admin.autocommit = True
    created = []
    commands = [
        ("Backend sobre PostgreSQL", [sys.executable, "-m", "pytest", "Backend/tests", "-q"]),
        ("Cliente TypeScript sobre PostgreSQL", ["node", "frontend/scripts/check-integration.mjs"]),
    ]
    try:
        for label, command in commands:
            database = "macromicetos_test_" + uuid.uuid4().hex
            assert re.fullmatch(r"macromicetos_test_[0-9a-f]{32}", database)
            assert database != target.database
            with admin.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8'").format(
                    sql.Identifier(database), sql.Identifier(target.username)))
            created.append(database)
            test_url = target.set(database=database).render_as_string(hide_password=False)
            environment = {**os.environ, "APP_ENV": "test", "MACROMICETOS_TEST_POSTGRES_URL": test_url}
            print(label + " (base temporal independiente).", flush=True)
            completed = subprocess.run(command, cwd=ROOT, env=environment)
            if completed.returncode:
                return completed.returncode
        print("Pruebas PostgreSQL correctas; la base del aplicativo no se modificó.", flush=True)
        return 0
    finally:
        try:
            for database in created:
                assert re.fullmatch(r"macromicetos_test_[0-9a-f]{32}", database)
                assert database != target.database
                with admin.cursor() as cursor:
                    cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
            if created:
                print("Bases temporales de esta ejecución eliminadas.", flush=True)
        finally:
            admin.close()


if __name__ == "__main__":
    sys.exit(main())
