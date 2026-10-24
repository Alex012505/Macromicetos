"""Local administration. Passwords are prompted, never supplied in command history."""
import argparse
import getpass
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text
from database.Base import SessionLocal, initialize_database
from models.UserWeb import UserWeb
from schemas.user_schema import UserRegisterInput
from Security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Administración local de Macromicetos")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-admin", help="Crear la primera cuenta administradora")
    create.add_argument("--email", required=True)
    create.add_argument("--first-name", required=True)
    create.add_argument("--last-name", default="")
    role = sub.add_parser("set-role", help="Asignar un rol a una cuenta existente")
    role.add_argument("--email", required=True)
    role.add_argument("--role", required=True, choices=["viewer", "analyst", "curator", "admin"])
    sub.add_parser("init-db", help="Crear tablas faltantes sin borrar datos")
    sub.add_parser("check-db", help="Comprobar conexión, tablas y privilegios sin modificar datos")
    args = parser.parse_args()
    if args.command == "check-db":
        with SessionLocal() as db:
            name, user = db.execute(text("SELECT current_database(), current_user")).one()
            privileges = db.execute(text("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user")).one()
            print(f"Motor: {db.get_bind().dialect.name}; base: {name}; usuario: {user}")
            print(f"Superusuario: {privileges[0]}; crear bases: {privileges[1]}; crear roles: {privileges[2]}")
            catalog = inspect(db.connection())
            for schema in ("public", "shared", "ecological", "curaduria"):
                print(f"{schema}: {', '.join(catalog.get_table_names(schema=schema))}")
            print(f"Usuarios del aplicativo: {db.scalar(select(func.count()).select_from(UserWeb))}")
        return
    initialize_database()
    if args.command == "init-db":
        print("Base de datos inicializada.")
        return
    with SessionLocal() as db:
        user = db.scalar(select(UserWeb).where(func.lower(UserWeb.email) == args.email.strip().lower()))
        if args.command == "create-admin":
            if user:
                parser.error("El correo ya existe. Usa set-role para asignarle un perfil.")
            password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
            if password != getpass.getpass("Repetir contraseña: "):
                parser.error("Las contraseñas no coinciden.")
            try:
                body = UserRegisterInput(email=args.email.strip(), password=password, first_name=args.first_name, last_name=args.last_name)
            except ValidationError:
                parser.error("Comprueba el correo y la longitud de la contraseña.")
            user = UserWeb(user_web_id=uuid.uuid4(), email=body.email.lower(), first_name=body.first_name.strip(),
                           last_name=body.last_name.strip() or None, password_hash=hash_password(password), role="admin")
            db.add(user)
        else:
            if not user:
                parser.error("El correo no está registrado.")
            admins = db.scalars(select(UserWeb).where(UserWeb.role == "admin")).all()
            if user.role == "admin" and args.role != "admin" and len(admins) < 2:
                parser.error("Debe permanecer al menos una cuenta administradora.")
            user.role = args.role
        db.commit()
        print(f"Cuenta {user.email}: perfil {user.role}.")


if __name__ == "__main__":
    main()
