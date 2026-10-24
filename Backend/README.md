# Backend integrado de Macromicetos

FastAPI + SQLAlchemy. Ejecutar desde la raíz del repositorio con Python 3.12+.

## Instalación y arranque

```powershell
python -m venv Backend/.venv
.\Backend\.venv\Scripts\python.exe -m pip install -r Backend/requirements-dev.txt
.\Backend\.venv\Scripts\python.exe Backend/setup_postgres.py
.\Backend\.venv\Scripts\python.exe Backend/manage.py create-admin --email TU_CORREO --first-name TU_NOMBRE
```

Necesitas PostgreSQL activo; validado localmente con PostgreSQL 18. `setup_postgres.py` solicita la contraseña del usuario `postgres`, crea una base `macromicetos` y un usuario exclusivo `macromicetos_app` sin privilegios de superusuario, guarda `Backend/.env` e inicializa las tablas. La contraseña del usuario de base y la clave JWT se generan aleatoriamente; no se imprimen. La contraseña de `postgres` no se guarda en la configuración del aplicativo.

El último comando solicita y confirma la contraseña del administrador del aplicativo, distinta de la de PostgreSQL. No existen contraseñas predeterminadas ni usuarios de la interfaz creados automáticamente. En los siguientes arranques no repitas la configuración ni la creación de cuentas.

El asistente no sobrescribe `.env` ni cambia una base o un rol ya existente. Puedes elegir nombres nuevos con `--database NOMBRE --user USUARIO`. Si quieres conectar una base existente, primero respáldala y ejecuta:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/setup_postgres.py --existing --database NOMBRE --user USUARIO
```

Esta opción solicita las credenciales de ese usuario y confirma antes de crear tablas faltantes. No modifica sus roles ni migra columnas existentes. Si ya tienes `.env`, edítalo directamente y ejecuta `Backend/manage.py init-db` en lugar de repetir el asistente.

Para ejecutar solo la API:

```powershell
.\Backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir Backend/src --host 127.0.0.1 --port 8000
```

Documentación: <http://127.0.0.1:8000/docs>. Estado: <http://127.0.0.1:8000/health>, que debe indicar `{"status":"ok","database":"postgresql"}`.

Puedes comprobar desde la consola la base, el usuario de conexión, sus privilegios y las tablas sin modificar datos:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/manage.py check-db
```

## Persistencia y configuración

El aplicativo requiere PostgreSQL y una conexión explícita en `Backend/.env`. No utiliza SQLite automáticamente si faltan credenciales. SQLite solo se permite con `APP_ENV=test` para las pruebas rápidas aisladas. Las fotos se almacenan en `Backend/data/images/`; tanto esa carpeta como `.env` están ignorados por Git.

Para configuración manual usa `Backend/.env.example`, define `DATABASE_URL` y una `SECRET_KEY` aleatoria de al menos 32 caracteres e inicializa las tablas faltantes con `manage.py init-db`. En producción configura además `APP_ENV=production` y `CORS_ORIGINS` con el origen HTTPS real del frontend. El asistente escapa correctamente los caracteres especiales de las contraseñas en la URL.

Se conservan los modelos de `shared`, `ecological` y `curaduria`. La tabla adicional `application_state` guarda propiedad, creador y colecciones ampliadas que el ORM original no representaba (fuentes, entrevistas, participantes, créditos y medidas libres), sin eliminar ni modificar columnas de las tablas existentes. Morfología, entidades principales y fotografías usan sus modelos científicos originales. Este diseño aditivo conserva las colecciones completas del formulario; su normalización relacional futura debe hacerse mediante una migración explícita.

En PostgreSQL se conservan los esquemas `shared`, `ecological` y `curaduria`; usuarios y `application_state` quedan en `public`. `init-db` crea tablas y tipos faltantes; no borra registros ni altera automáticamente columnas existentes. Respalda la base antes de aplicar cambios de esquema. El usuario propietario de la base puede inicializarla sin ser superusuario.

El ORM actual utiliza latitud/longitud numéricas y no requiere ni instala PostGIS. No se incluye el SQL original de triggers o vistas como `curaduria.current_status`; si necesitas esos endpoints heredados, debes aportar y aplicar ese esquema por separado. La API integrada del frontend no depende de esa vista.

El archivo SQLite anterior, si existe, se conserva sin uso. No hay importación automática: cambiar la URL no transfiere datos. Respalda PostgreSQL y la carpeta de fotografías por separado.

Las fotos del catálogo se sirven públicamente bajo URLs con UUID en `/media/`; no contienen entrevistas ni correos. La API de datos requiere autenticación y omite contactos/entrevistas para perfiles sin permiso. Los archivos se guardan con nombres generados, no con rutas suministradas por el cliente.

## Perfiles

- `viewer`: consulta autenticada de catálogo, hallazgos y fotos.
- `analyst`: crea fichas y hallazgos, edita los propios y agrega fotografías.
- `curator`: revisa hallazgos y puede consultar información científica sensible.
- `admin`: gestión global, asignación de responsables y administración de roles.

El registro público crea exclusivamente `viewer`. El administrador puede asignar roles en la interfaz. Para recuperación o administración local:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/manage.py set-role --email CORREO_EXISTENTE --role analyst
```

Se impide eliminar el último rol administrador. Cambiar el rol invalida los tokens anteriores de esa cuenta. El JWT se verifica en cada petición, y el servidor comprueba propiedad y rol antes de modificar datos. Las contraseñas se guardan con Argon2.

## Contrato del frontend

| Método | Ruta | Función |
| --- | --- | --- |
| POST | `/auth/register` | Crear cuenta visitante |
| POST | `/auth/login-json` | Login JSON y perfil autenticado |
| POST | `/auth/login` | Login OAuth2 con formulario |
| GET | `/auth/me` | Cuenta y rol actuales |
| GET | `/users` | Lista de usuarios, solo administrador |
| PATCH | `/users/{id}` | Cambiar rol, solo administrador |
| GET | `/taxa`, `/taxa/{id}` | Fichas completas con datos autorizados |
| POST | `/taxa` | Alta taxonómica básica en snake_case |
| PUT | `/taxon-bundles/{id}` | Ficha completa, fuentes y entrevistas |
| GET | `/occurrences`, `/occurrences/{id}` | Hallazgos completos |
| PUT | `/record-bundles/{id}` | Guardado completo del hallazgo y fotos iniciales |
| PUT | `/occurrences/{id}/media-bundle` | Fotos adicionales con metadatos y créditos |
| POST | `/occurrences/{id}/photos` | Carga simple de archivos bajo campos `files` |
| PATCH | `/occurrences/{id}/curation` | Verificar o solicitar ajustes |

Los PUT multipart reciben un campo `payload` JSON y un archivo `file_<media_id>` por fotografía. Los UUID permanecen estables para reintentos. Cada operación confirma la transacción completa o revierte entidades y archivos nuevos; no elimina fotografías preexistentes. Una foto admite JPG, PNG o WebP reales, hasta 10 MB, máximo 10 por operación. Un mismo hash no se duplica.

Los endpoints científicos originales se conservan bajo `/legacy`, restringidos a administradores para que sus escrituras básicas no eludan los controles de propiedad del aplicativo. Sus vistas SQL específicas de PostgreSQL requieren la instalación original del equipo.

## Pruebas

```powershell
.\Backend\.venv\Scripts\python.exe -m pytest Backend/tests -q
cd frontend
npm test
npm run test:integration
```

Por defecto, las pruebas rápidas crean bases SQLite y cuentas desechables dentro de `Backend/.test-data/`. No usan la base del aplicativo ni necesitan credenciales reales. La prueba de integración usa el cliente TypeScript real contra FastAPI por HTTP, con los serializadores de los formularios.

Para validar PostgreSQL real con las credenciales de aplicación configuradas:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/tests/check_postgres.py
```

Solicita una contraseña de administrador exclusivamente para crear y eliminar dos bases con nombres aleatorios `macromicetos_test_<UUID>`. Sus propietarios y las conexiones de la API usan el usuario configurado del aplicativo, no el superusuario. La base normal no se vacía ni se modifica. Localmente se verificaron las 11 pruebas del backend y el cliente TypeScript completo sobre PostgreSQL 18.

Si recuperaste el acceso local y tienes su contraseña guardada de forma privada, puedes evitar introducirla en el historial:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/tests/check_postgres.py --admin-password-file Backend/data/postgres-admin-password.txt
```

Ese archivo, si existe, es una credencial sensible excluida de Git. No lo compartas ni lo adjuntes a incidencias. No cambies `pg_hba.conf` a `trust` de forma permanente para evitar una contraseña olvidada.

### Pruebas de la interfaz local

Con el aplicativo iniciado, Chrome instalado y al menos una cuenta administradora real:

```powershell
npm --prefix frontend run test:web:local
```

Esta prueba usa Chrome con un perfil aislado, sin tus contraseñas guardadas. Opera sobre la web y PostgreSQL locales: crea o reutiliza tres cuentas ficticias y dos registros `PRUEBA-WEB-01` / `PRUEBA-WEB-02`, con una ficha ficticia `Prueba artificialis`. Cada registro incluye una imagen ilustrativa con créditos; nunca representa un muestreo real. El primero termina verificado técnicamente y el segundo en revisión. No ejecutar en producción.

El administrador temporal de QA se elimina al terminar; las tres cuentas de prueba, los dos registros y sus fotos se conservan para las pruebas manuales solicitadas. Sus credenciales quedan en `Backend/data/web-test-accounts.json`, ignorado por Git. El script no cambia cuentas reales ni sus contraseñas.

Comprueba registro, contraseñas incorrectas, cambios de rol, validaciones del formulario, fotos, edición, persistencia al recargar, CSV/Excel/PDF, curaduría, permisos, mapa y vista móvil. Después consulta directamente PostgreSQL y verifica los archivos mediante sus hashes. Capturas y resultados se guardan en `frontend/test-results/web-local/`, también excluido de Git. El fondo de OpenStreetMap necesita acceso a internet; las coordenadas y marcadores no dependen de que todas las teselas descarguen.
