# Contrato de integración frontend ↔ FastAPI

Estado: cliente preparado; backend no disponible para pruebas de extremo a extremo. Las rutas se derivan de los HTML originales en `docs/operations/DefaultApi.html` y `docs/models/`. Los documentos de arquitectura se usan como contexto, pero las rutas concretas de esta entrega corresponden al contrato de Macromicetos; no se mezclan con los servicios de salas y streaming de otros diagramas.

## 1. Referencia original de rutas

| Método | Ruta relativa a la URL base | Interfaz | Observación |
| --- | --- | --- | --- |
| POST | `/auth/login-json` | Inicio de sesión | JSON `{email,password}`; devuelve JWT con ID, rol y expiración. |
| POST | `/auth/register` | Registro de cuenta | `{email,password,first_name,last_name}`. El servidor fija el rol público. |
| GET | `/taxa?search=...` | Catálogo | Lista directa o envoltura `data`, `items` o `results`. |
| GET | `/taxa/{taxon_id}` | Ficha | Contrato TaxonRef. |
| POST | `/taxa` | Creación básica de taxón | JSON plano en snake_case: `scientific_name`, `taxon_rank`, `common_name_es`, etc. El servidor genera el ID. Las fichas con entidades adicionales requieren el contrato de ficha completa. |
| GET | `/occurrences/{occurrence_id}` | Consulta de registro por ID | Perfil con taxón, evento, ubicación y multimedia. |
| POST | `/occurrences/{occurrence_id}` | Referencia histórica de observación básica | El nuevo editor no la usa para evitar descartar ubicación, morfología y demás campos. |
| POST | `/occurrences/{occurrence_id}/photos` | Añadir fotografías | Multipart con un campo `files` por archivo; devuelve una lista de multimedia, que se incorpora al hallazgo existente. Si se configura `VITE_MEDIA_BUNDLE_PATH`, se conserva el guardado completo mediante PUT. |

El servidor virtual SwaggerHub que aparece en los HTML es documentación y no se usa como backend real. No se enviaron datos ni credenciales a ese servidor.

## 2. Configuración local

```dotenv
VITE_DATA_MODE=api
VITE_API_BASE_URL=/api
API_PROXY_TARGET=http://127.0.0.1:8000
```

`/api/taxa` en el navegador se convierte en `http://127.0.0.1:8000/taxa`. Para un backend con prefijo `/api/v1`, define `VITE_API_BASE_URL=/api/api/v1`. Todas las variables `VITE_*` son públicas en la compilación; no incluyas secretos. Reinicia el servidor después de editar `.env`, y recompila si cambia la configuración de producción. [Referencia oficial de Vite](https://vite.dev/guide/env-and-mode.html).

Para producción, sirve `dist/` y enruta `/api` al backend con un proxy real, o define una URL absoluta HTTPS. El prefijo debe acordarse una vez; los componentes no contienen URLs fijas.

## 3. Autenticación de los cuatro perfiles

Antes de abrir cualquier vista se exige correo y contraseña. El cliente no carga el conjunto de datos hasta iniciar sesión y no ofrece selectores de identidad o rol, tampoco con datos demo.

`POST /auth/login-json` recibe JSON `{email,password}`. Esta es la operación JSON existente en la rama `Backend`; `POST /auth/login` recibe un formulario OAuth2 y no se usa para enviar JSON. La ruta JSON se puede configurar mediante `VITE_LOGIN_PATH`.

Respuesta actual del backend:

```json
{
  "access_token": "jwt-firmado-por-el-servidor",
  "token_type": "Bearer"
}
```

El JWT incluye `sub` (ID de cuenta), `role` y `exp`. El cliente lee estos datos únicamente del token recibido tras un login exitoso. El rol debe ser `viewer`, `analyst`, `curator` o `admin`; un ID ausente, un rol desconocido o un token vencido impiden abrir la sesión. Leer el JWT en el navegador no verifica su firma: FastAPI debe validar firma, expiración, identidad, rol y propiedad en cada petición protegida.

Si el login incluye un perfil (`user`, `profile` o `userProfile`), se utiliza tras comprobar que pertenece al ID autenticado y tiene un rol válido. Si se configura `VITE_ME_PATH`, se consulta ese perfil con el Bearer token y su rol es el que se muestra. No se presume que esa ruta exista: la rama inspeccionada no implementa `/auth/me`. Sin perfil, se usa el ID y rol del JWT y el correo introducido para identificar la sesión.

El registro público envía solo correo, contraseña, nombre y apellido a `/auth/register`. El backend crea cuentas `viewer`; el formulario no permite solicitar permisos elevados. Los roles `analyst`, `curator` y `admin` deben asignarse en el servidor. Si falta el endpoint administrativo de roles, debe habilitarse en el backend; el cliente no lo simula.

Los tokens se mantienen en memoria, sin almacenar contraseñas ni perfiles en `localStorage`. Recargar exige un nuevo login. Cerrar sesión, recibir HTTP 401 en una petición autenticada o llegar a `exp` limpia la cuenta, los datos y los formularios privados. Al volver a enfocar la ventana se revisa la expiración. Las respuestas de una cuenta anterior no pueden cargar datos ni cerrar la sesión de una cuenta nueva.

El transporte conserva el refresco opcional mediante `VITE_REFRESH_PATH`, que sigue pendiente de implementación en el backend. La sesión de interfaz tiene como límite la expiración recibida al iniciar sesión. Un HTTP 403 se muestra como permiso denegado y no intenta elevar el rol.

## 4. Extensiones propuestas — no son rutas existentes

Las siguientes variables están vacías en `.env.example`. No se solicita ninguna de estas rutas hasta configurarla. La propuesta sirve para coordinación con opción 1.

| Variable | Ruta sugerida | Contrato propuesto |
| --- | --- | --- |
| `VITE_OCCURRENCES_LIST_PATH` | `/occurrences` | GET lista de perfiles con coordenadas y estado. |
| `VITE_CURATE_PATH` | `/occurrences/{id}/curation` | PATCH `{status,review_note}`, exclusivo curador/admin. |
| `VITE_USERS_PATH` | `/users` | GET lista de perfiles, exclusivo admin. |
| `VITE_USER_UPDATE_PATH` | `/users/{id}` | PATCH `{role}`, exclusivo admin; conservar al menos un administrador. |
| `VITE_REFRESH_PATH` | `/auth/refresh` | POST `{refreshToken}` → token nuevo. |
| `VITE_ME_PATH` | `/auth/me` | GET perfil autenticado. |

Lista de ocurrencias sugerida:

```json
{
  "items": [{
    "occurrence_id": "uuid",
    "taxon_id": "uuid",
    "event_id": "uuid",
    "identified_by": "Nombre del investigador",
    "date_identified": "2026-10-03",
    "substrate": "Madera muerta",
    "occurrence_remarks": "Notas de campo",
    "status": "pending",
    "event": {
      "event_id": "uuid",
      "event_date": "2026-10-03",
      "location": {
        "state_province": "Meta",
        "locality": "Sitio de muestreo",
        "decimal_latitude": 4.15,
        "decimal_longitude": -73.64,
        "habitat": "Bosque de galería"
      }
    },
    "multimedia": [{
      "media_id": "uuid",
      "source_url": "https://almacenamiento-del-proyecto.example/foto.jpg",
      "photo_type": "habitus",
      "license": "licencia-del-registro"
    }],
    "measurements": [{
      "measurement_type": "diametro_sombrero",
      "measurement_value": "5",
      "measurement_unit": "cm"
    }]
  }]
}
```

Estados propuestos: `pending`, `verified`, `rejected`. La documentación original no declara un campo de curaduría. Su ausencia se muestra como **Sin estado**, nunca como verificado. El frontend adapta `approved` a `verified` si la API usa ese término.

TaxonRef usa `taxonID`, `scientificName`, `commonName_es`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `species`, `taxonRemarks`. La respuesta taxonómica anidada de una ocurrencia usa algunos nombres diferentes (`taxon_id`, `scientific_name`, `common_name_es`): el adaptador admite esos alias. Las fotografías usan `source_url`, conforme al modelo multimedia original.

## 5. Eventos y geografía

`OccurrenceInput` de la referencia original requiere un evento existente y no cubre el registro ampliado. La interfaz de campo ahora recoge ubicación, evento, ocurrencia, participantes, rasgos, medidas y fotos. En modo API solo guarda mediante `VITE_RECORD_BUNDLE_PATH`; si falta, muestra un error y conserva el formulario. Los UUID del borrador y de las fotos son estables durante los reintentos. El backend determina identidad, permisos y estado inicial.

Las tres operaciones propuestas, sus cuerpos, respuestas y semántica transaccional se describen en [REGISTRO_COMPLETO.md](REGISTRO_COMPLETO.md). El formulario completo funciona en demostración con IndexedDB. La obtención de coordenadas depende del permiso del navegador y de HTTPS/localhost; mapa y coordenadas manuales permanecen como alternativas.

## 6. CORS y errores

Con el proxy Vite, las peticiones del navegador mantienen el mismo origen en desarrollo. Si se utiliza una URL absoluta del backend, habilitar los orígenes concretos del frontend mediante CORSMiddleware. Ejemplo para el equipo backend:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
```

El ejemplo corresponde a tokens Bearer; si se adopta autenticación por cookie, revisar credenciales y CSRF como parte de ese contrato. Añadir el origen HTTPS de producción cuando exista. [Documentación oficial de FastAPI sobre CORS](https://fastapi.tiangolo.com/tutorial/cors/).

El cliente muestra mensajes del backend (`detail`, `error`, `message`), incluyendo validaciones FastAPI 422. Mantiene timeout de 15 segundos, soporta cancelación y rechaza respuestas HTML/JSON mal formado. Las cargas FormData dejan que el navegador genere el boundary multipart. No se sustituyen errores reales por datos de demostración.

## 7. Validación cuando exista FastAPI

1. Configurar la URL base y activar modo API.
2. Verificar GET `/taxa`, un taxón por ID y búsqueda desde el contrato del servidor.
3. Confirmar login con token, perfil y rol; registro público sin elección de privilegio.
4. Usar IDs reales de evento/taxón para POST de ocurrencia; confirmar su consulta posterior.
5. Cargar una fotografía y comprobar `source_url` en el perfil.
6. Configurar las extensiones acordadas y comprobar mapa, lista, curaduría y usuarios.
7. Probar 401, 403, 422, servidor no disponible y timeout.
8. Confirmar RBAC en el backend, además del control de navegación de la interfaz.

Estas verificaciones de extremo a extremo permanecen pendientes; las pruebas actuales del transporte usan respuestas simuladas.

## 8. Propiedad y vistas por perfil

Consulta `PERFILES_Y_VISTAS.md`. Para delimitar la edición del investigador, la API debe incluir un identificador de propietario en cada ocurrencia: `owner_id`, `created_by_id` o `user_id`. El frontend utiliza ese dato y el ID del usuario autenticado; no convierte `identified_by` en un permiso. El backend asigna la propiedad al crear el registro y verifica propiedad/rol en edición y carga multimedia.

El administrador tiene gestión de perfiles. Su operación de actualización requiere un contrato propio, aún propuesto, configurado con `VITE_USER_UPDATE_PATH`. El registro público siempre crea una cuenta de menor privilegio.
