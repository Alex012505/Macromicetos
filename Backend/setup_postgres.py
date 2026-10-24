"""Interactive PostgreSQL setup; administrator credentials are never saved.

Creates a dedicated, unprivileged login and a new database, or connects to an
existing database with --existing. Refuses to overwrite .env or existing names.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import URL

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
ENV_FILE = BACKEND / ".env"


def identifier(value):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
        raise argparse.ArgumentTypeError("Usa un nombre de hasta 63 letras minúsculas, números o guiones bajos.")
    return value


def make_url(host, port, database, user, password):
    return URL.create("postgresql+psycopg2", username=user, password=password,
                      host=host, port=port, database=database).render_as_string(hide_password=False)


def main():
    parser = argparse.ArgumentParser(description="Configurar Macromicetos con PostgreSQL local")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", type=identifier, default="macromicetos")
    parser.add_argument("--user", type=identifier, default="macromicetos_app")
    parser.add_argument("--admin", default="postgres", help="Administrador que puede crear bases y roles")
    parser.add_argument("--existing", action="store_true", help="Conectar una base existente; no crear ni modificar roles")
    parser.add_argument("--admin-password-file", type=Path, help="Archivo privado local; solo para la recuperación autorizada")
    args = parser.parse_args()
    if ENV_FILE.exists():
        parser.error("Backend/.env ya existe; no se sobrescribió. Revisa esa configuración antes de continuar.")
    if os.environ.get("DATABASE_URL") or os.environ.get("SECRET_KEY"):
        parser.error("La consola ya tiene DATABASE_URL o SECRET_KEY. Usa una consola sin esas variables para evitar conexiones ambiguas.")

    if args.existing:
        print(f"Conexión existente: {args.host}:{args.port}/{args.database}, usuario {args.user}.")
        print("Se crearán las tablas faltantes del aplicativo, sin borrar datos ni alterar columnas existentes.")
        if input("¿Tienes respaldo y deseas continuar? [s/N]: ").strip().lower() != "s":
            return 0
        password = getpass.getpass(f"Contraseña de {args.user}: ")
    else:
        print(f"Se creará la base {args.database} y el usuario exclusivo {args.user} en {args.host}:{args.port}.")
        if args.admin_password_file:
            credential_path = args.admin_password_file.resolve()
            if credential_path.parent != (BACKEND / "data").resolve():
                parser.error("El archivo de recuperación debe estar dentro de Backend/data/.")
            admin_password = credential_path.read_text(encoding="utf-8").strip()
        else:
            admin_password = getpass.getpass(f"Contraseña de PostgreSQL para {args.admin} (no se guardará): ")
        connection = psycopg2.connect(host=args.host, port=args.port, dbname="postgres",
                                      user=args.admin, password=admin_password, connect_timeout=5)
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (args.database,))
                database_exists = cursor.fetchone() is not None
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (args.user,))
                role_exists = cursor.fetchone() is not None
                if database_exists or role_exists:
                    parser.error("La base o el usuario ya existe. No se modificó. Usa --existing con sus credenciales, o elige otros nombres.")
                password = secrets.token_urlsafe(36)
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION").format(
                    sql.Identifier(args.user), sql.Literal(password)))
                try:
                    cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8'").format(
                        sql.Identifier(args.database), sql.Identifier(args.user)))
                except psycopg2.Error:
                    print("No se pudo crear la base. El usuario nuevo quedó creado; un administrador debe revisar sus permisos.")
                    raise
        finally:
            connection.close()
        del admin_password
        print("Base y usuario creados. La cuenta del aplicativo no es superusuario.")

    database_url = make_url(args.host, args.port, args.database, args.user, password)
    signing_key = secrets.token_urlsafe(48)
    # Save the application credential before initialization so a failed schema
    # check never loses the newly created role's password. Do not overwrite.
    with ENV_FILE.open("x", encoding="utf-8") as stream:
        stream.write("APP_ENV=development\n")
        stream.write("DATABASE_URL=" + json.dumps(database_url) + "\n")
        stream.write("SECRET_KEY=" + json.dumps(signing_key) + "\n")
        stream.write("CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n")
        stream.write("ACCESS_TOKEN_MINUTES=60\n")
    print("Backend/.env guardado (privado, ignorado por Git).")
    initialized = subprocess.run([sys.executable, str(BACKEND / "manage.py"), "init-db"], cwd=ROOT)
    if initialized.returncode:
        print("La inicialización falló. Conserva .env y ejecuta manage.py init-db después de resolver el error; no recrees la base.")
        return initialized.returncode
    print("Conexión PostgreSQL verificada y tablas listas.")
    print("Siguiente: crea tu administrador con Backend/manage.py create-admin e inicia node scripts/dev.mjs.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except psycopg2.Error as error:
        print("No se pudo configurar PostgreSQL:", str(error).strip(), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nConfiguración cancelada.", file=sys.stderr)
        sys.exit(130)
