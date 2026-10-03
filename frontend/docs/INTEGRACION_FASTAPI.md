# Contrato de integración frontend ↔ FastAPI

Estado: cliente preparado; backend no disponible para pruebas de extremo a extremo. Las rutas se derivan de los HTML originales en `docs/operations/DefaultApi.html` y `docs/models/`. Los documentos de arquitectura se usan como contexto, pero las rutas concretas de esta entrega corresponden al contrato de Macromicetos; no se mezclan con los servicios de salas y streaming de otros diagramas.

## 1. Rutas documentadas utilizadas

| Método | Ruta relativa a la URL base | Interfaz | Observación |
| --- | --- | --- | --- |
| POST | `/auth/login` | Inicio de sesión | JSON `{email,password}`. Falta precisar respuesta con tokens/perfil. |
| POST | `/auth/register` | Registro de cuenta | `{email,password,first_name,last_name}`. El servidor fija el rol público. |
| GET | `/taxa?search=...` | Catálogo | Lista directa o envoltura `data`, `items` o `results`. |
| GET | `/taxa/{taxon_id}` | Ficha | Contrato TaxonRef. |
| POST | `/taxa` | Crear ficha taxonómica | Campos de TaxonRef. ID asignado por el servidor. |
| GET | `/occurrences/{occurrence_id}` | Consulta de registro por ID | Perfil con taxón, evento, ubicación y multimedia. |
| POST | `/occurrences/{occurrence_id}` | Crear/editar observación según contrato | Requiere ID en la ruta, `event_id` y `taxon_id` UUID. Confirmar semántica de edición con backend. |
| POST | `/multimedia/upload` | Carga de fotografía | multipart: `file`, `occurrence_id`, `photo_type`. |

El servidor virtual SwaggerHub que aparece en los HTML es documentación y no se usa como backend real. No se enviaron datos ni credenciales a ese servidor.

## 2. Configuración local

```dotenv
VITE_DATA_MODE=api
VITE_API_BASE_URL=/api
API_PROXY_TARGET=http://127.0.0.1:8000
```

`/api/taxa` en el navegador se convierte en `http://127.0.0.1:8000/taxa`. Para un backend con prefijo `/api/v1`, define `VITE_API_BASE_URL=/api/api/v1`. Todas las variables `VITE_*` son públicas en la compilación; no incluyas secretos. Reinicia el servidor después de editar `.env`, y recompila si cambia la configuración de producción. [Referencia oficial de Vite](https://vite.dev/guide/env-and-mode.html).

Para producción, sirve `dist/` y enruta `/api` al backend con un proxy real, o define una URL absoluta HTTPS. El prefijo debe acordarse una vez; los componentes no contienen URLs fijas.

## 3. Autenticación pendiente de contrato

Respuesta propuesta de `/auth/login`:

```json
{
  "access_token": "jwt-del-servidor",
  "refresh_token": "token-opaco-opcional",
  "token_type": "bearer",
  "user": {
    "user_id": "uuid",
    "email": "persona@institucion.edu.co",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "role": "researcher"
  }
}
```

El cliente también acepta `accessToken`, `refreshToken` y `userProfile`. Roles canónicos: `readonly_user`, `researcher`, `curator`, `admin`. Si el servidor solo devuelve un mensaje, se muestra un error de contrato y no se inicia una sesión ficticia. Si entrega token sin perfil, el cliente conserva el mínimo privilegio; opcionalmente se puede configurar `VITE_ME_PATH` para consultar el perfil.

Los tokens están en memoria. Recargar requiere iniciar sesión otra vez. No existe revocación remota de logout porque el contrato no define esa ruta; cerrar sesión borra los tokens del cliente. Para revocación global el backend debe añadir una operación y acordar el contrato.

El refresco solo se activa al definir `VITE_REFRESH_PATH`. Sigue el cuerpo `{ "refreshToken": "..." }` del diagrama de autenticación entregado. Si el equipo usa `refresh_token`, adaptar ese campo en `src/lib/http.mjs`. Un 401 dispara como máximo un refresco y un reintento; peticiones simultáneas comparten el refresco. Si falla, la sesión termina. Un 403 de una operación no intenta elevar permisos.

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

`OccurrenceInput` requiere un evento existente. Los HTML actuales no declaran POST de evento ni ubicación. Por ello, en modo API el formulario solicita un UUID de evento real y un identificador de ocurrencia; no inventa eventos ni envía campos geográficos ignorados por el contrato. El backend determina el estado inicial.

Para habilitar el formulario completo de campo con coordenadas reales, acordar una operación transaccional que cree ubicación, evento y ocurrencia, o definir endpoints y devolución de sus IDs. El formulario geográfico completo funciona actualmente en el demo, con persistencia local.

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
