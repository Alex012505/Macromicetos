# Contrato integrado frontend ↔ FastAPI

Los contratos de los formularios están implementados en `Backend/src/routers/application.py` y `Backend/src/services/application.py`. Ya no es necesario definir endpoints pendientes para usar el aplicativo local.

## Configuración

Sin `frontend/.env`, el cliente usa `/api`; Vite reenvía las peticiones a `http://127.0.0.1:8000`. El backend sí requiere `Backend/.env` con su conexión PostgreSQL y clave JWT. Las rutas predeterminadas coinciden con el backend incluido:

| Variable | Valor |
| --- | --- |
| `VITE_LOGIN_PATH` | `/auth/login-json` |
| `VITE_ME_PATH` | `/auth/me` |
| `VITE_OCCURRENCES_LIST_PATH` | `/occurrences` |
| `VITE_CURATE_PATH` | `/occurrences/{id}/curation` |
| `VITE_USERS_PATH` | `/users` |
| `VITE_USER_UPDATE_PATH` | `/users/{id}` |
| `VITE_RECORD_BUNDLE_PATH` | `/record-bundles/{id}` |
| `VITE_TAXON_BUNDLE_PATH` | `/taxon-bundles/{id}` |
| `VITE_MEDIA_BUNDLE_PATH` | `/occurrences/{id}/media-bundle` |

Si conservas un `.env` antiguo con estos valores vacíos, actualízalo a partir de `.env.example`. `VITE_REFRESH_PATH` permanece vacío: no hay endpoint de renovación y la sesión termina al expirar.

## Autenticación y autorización

`POST /auth/login-json` recibe `{email,password}` y devuelve `access_token`, `token_type` y `user`. El cliente consulta además `GET /auth/me` con el Bearer token. El backend valida firma, expiración y rol vigente. Cambiar el rol invalida los tokens anteriores de la cuenta.

No hay selectores de identidad ni roles simulados. El registro público crea `viewer`; solo administración puede asignar `analyst`, `curator` o `admin`. La API impide retirar el último administrador. Las contraseñas se guardan con Argon2 y los tokens del navegador están únicamente en memoria.

Una cuenta `analyst` no puede asignar otra persona como propietaria: el servidor toma su identidad autenticada, incluso si se manipula el payload. `admin` puede asignar un investigador válido. `created_by_id` permanece separado del propietario.

## Fichas y hallazgos completos

Los adaptadores en `src/lib/record-contract.mjs` producen snake_case. Las fichas usan PUT JSON con `taxon`, `morphology`, `sources`, `knowledge` y `participants`. Los hallazgos usan PUT multipart: `payload` contiene `owner_id`, `location`, `event`, `occurrence`, `morphology`, `measurements`, `participants` y `multimedia`.

Se conservan IDs estables durante reintentos. El backend guarda las entidades y las colecciones en una transacción. Una edición vuelve a poner el hallazgo en revisión; repetir el mismo PUT sin cambios no duplica fotos ni entidades.

La persistencia utiliza los modelos científicos originales y una tabla adicional `application_state` para propiedad y colecciones que no estaban representadas en el ORM original. Fuentes, entrevistas, medidas libres, participantes y créditos se conservan sin pérdida en esa tabla. Las entrevistas y los correos se omiten para perfiles sin autorización.

Los GET de fichas y hallazgos devuelven las colecciones completas autorizadas. El evento contiene `location`, y el hallazgo contiene `multimedia`, `morphology`, `measurements`, `owner_id`, `created_by_id`, `status` y `review_note`. El frontend calcula mapas, filtros, métricas y exportaciones a partir de estos datos.

## Fotografías

La carga completa envía un archivo `file_<media_id>` por entrada de `multimedia`. El endpoint `PUT /occurrences/{id}/media-bundle` conserva metadatos y créditos. También existe `POST /occurrences/{id}/photos` para carga simple mediante campos `files`; no tiene el antiguo prefijo `/multimedia`.

Se admiten JPG, PNG y WebP reales, 10 MB por archivo, hasta 10 por lote. El backend comprueba el contenido con Pillow, asigna rutas UUID seguras y limpia los archivos nuevos si falla la operación. No usa el nombre suministrado como ruta. La respuesta incluye `source_url`, no rutas del sistema de archivos. La galería y el PDF utilizan esa URL. Las fotos del catálogo se sirven públicamente; los datos sensibles de entrevistas no se publican con ellas.

## Curaduría

`PATCH /occurrences/{id}/curation` recibe `{status,review_note}`. `status` es `verified` o `rejected`; un rechazo exige una explicación de al menos diez caracteres. Solo `curator` y `admin` pueden decidir. Se registra el historial en `curaduria.curation_decision`.

## Ejecución y comprobación

Desde la raíz:

```powershell
node scripts/dev.mjs
npm --prefix frontend run test:integration
```

El segundo comando utiliza una base y cuentas desechables, y prueba el cliente TypeScript real contra FastAPI por HTTP. No necesita un backend previamente iniciado ni credenciales reales.

Para ejecutar las pruebas sobre PostgreSQL real usa `.\Backend\.venv\Scripts\python.exe Backend/tests/check_postgres.py`: crea dos bases desechables independientes y prueba el backend y el cliente real sin modificar la base del aplicativo. Verificado localmente sobre PostgreSQL 18.

En producción despliega FastAPI por separado y configura `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS` y la URL HTTPS pública del frontend. Consulta [Backend/README.md](../../Backend/README.md). El ORM actual usa coordenadas numéricas y no instala PostGIS ni las vistas o triggers de un esquema SQL externo.
