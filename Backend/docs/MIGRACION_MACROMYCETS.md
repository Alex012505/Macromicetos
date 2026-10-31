# Migrar la aplicación a la base `Macromycets`

Estado: **pendiente de ejecución**. La base activa sigue siendo `macromicetos`.

---

## 1. Diagnóstico

`Macromycets` se creó con `create_macromycetes_db_v3.sql` (pipeline de datos) y
luego se le añadieron las tablas de la aplicación. Comparando el esquema real
con los modelos del ORM:

| Objeto | Estado en `Macromycets` | ¿Bloquea? |
| --- | --- | --- |
| `public.application_state` | **No existe** | Sí: sin ella no hay propiedad ni colecciones extendidas |
| Permisos del rol `macromicetos_app` | Sin `USAGE` en `shared`, `ecological`, `curaduria`, `socioecological`, `bibliographic` | Sí: la app no puede leer nada |
| Enums en otros esquemas | `shared.taxon_rank_enum`, `ecological.*`, `curaduria.*` | Sí, sin `search_path` |
| `shared.taxon_ref` | Columnas idénticas | No |
| `ecological.location` | Columnas idénticas + `geog` (PostGIS) | No (el ORM lo ignora) |
| `ecological.event` | Columnas idénticas | No |
| `ecological.occurrence` | Columnas idénticas | No |
| `ecological.multimedia` | Columnas idénticas | No |
| `ecological.measurement_or_fact` | Columnas idénticas | No |
| `ecological.morphology_fact` | Columnas idénticas | No |
| `curaduria.curation_decision` | Columnas idénticas | No |
| `public.user_web` | Columnas extra: `party_id`, `is_active`, `last_login_at`, `created_at`, `updated_at` | No, pero la app las ignora |
| `user_role_enum` | Incluye `field_collector` | Sí al leer esas filas |

### Restricciones que la aplicación no puede cumplir

Estas son las incompatibilidades reales, además de los permisos:

| Restricción | Qué hace la app | Efecto |
| --- | --- | --- |
| `location_country_check: country = 'Colombia'` | Guarda el código ISO `CO` | **Todo insert de ubicación falla** |
| `uq_location_natural_key (locality, municipality, state_province)` | Crea ubicaciones con UUID propio | Dos usuarios con el mismo sitio → error 500 |
| `uq_event_site_date (location_id, event_date, recorded_by)` | Crea un evento por formulario | Dos salidas el mismo día → error 500 |
| `uq_multimedia_occurrence_type_file` | Deduplica solo por `sha256_hash` | Nombre repetido → error 500 |
| `uq_decision_persot (entity_type, entity_id, created_at)` | Inserta historial con `now()` | Dos decisiones en el mismo instante → error 500 |
| `location_coordinate_uncertainty_m_check > 0` | Acepta `0` | Error si el usuario escribe 0 |
| `taxon_ref_kingdom_check: kingdom = 'Fungi'` | El campo Reino es editable | Error si escriben otro reino |
| `user_web` sin `UNIQUE(email)` | Valida en código | Carrera teórica al registrar |

---

## 2. Pasos para activar `Macromycets`

### 2.1 Ejecutar los scripts (como `postgres`)

En pgAdmin, conectado a **Macromycets**:

1. `Backend/sql/macromycets/01_compatibilidad_app.sql`
   - Permisos, `application_state`, ajustes de restricciones y `search_path`.
2. `Backend/sql/macromycets/02_ownership_legacy.sql`
   - Asigna dueño a los taxones, hallazgos y fotos heredados.
   - Requiere que exista al menos una cuenta `admin` en `public.user_web`.

Ambos son idempotentes y terminan con una consulta de verificación.

### 2.2 Cambiar la cadena de conexión

En `Backend/.env`:

```env
DATABASE_URL="postgresql+psycopg2://macromicetos_app:...@127.0.0.1:5432/Macromycets"
```

### 2.3 Verificar

```powershell
cd Backend
.\.venv\Scripts\python.exe manage.py check-db
```

Debe mostrar `base: Macromycets` y los seis esquemas con sus tablas.

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Las pruebas usan una base desechable, así que no tocan `Macromycets`.

### 2.4 Volver atrás

Restaurar la línea anterior de `.env` (base `macromicetos`). No hay cambios
destructivos en `Macromycets`: el script solo añade permisos, una tabla y
relaja restricciones.

---

## 3. Cambios ya aplicados en el código

| Archivo | Cambio |
| --- | --- |
| `src/database/Base.py` | `search_path` en la conexión PostgreSQL y creación de esquemas solo si faltan |
| `src/database/Base.py` | `initialize_database()` resuelve enums con `to_regtype` antes de crearlos (evita duplicarlos en `public`) |
| `src/models/UserWeb.py` | `user_role_enum` incluye `field_collector` |
| `manage.py` | `check-db` lista también `socioecological` y `bibliographic` |

Verificado: `12 passed` y `check-db` sigue funcionando contra `macromicetos`.

### Cambios pendientes (recomendados, no bloqueantes)

1. **`is_active`**: la app no lo lee. Una cuenta desactivada en `Macromycets`
   podría iniciar sesión. Hay que mapearlo en `UserWeb` y comprobarlo en
   `routers/auth.py`.
2. **`party_id`**: los usuarios heredados no están vinculados a `shared.party`.
   Solo importa al normalizar participantes.
3. **`field_collector`**: existe en el enum pero no en `ROLES_AUTORIZADOS`, así
   que se comporta como `viewer` (solo lectura). Definir si debe escribir.
4. **País**: si algún día se registran países distintos de Colombia, hay que
   cambiar el `CHECK` o validar en la API.
5. **Unicidad de correo**: añadir
   `CREATE UNIQUE INDEX ... ON public.user_web (lower(email))` tras comprobar
   que no hay duplicados heredados.
6. **Contraseñas heredadas**: `Security.py` solo verifica Argon2. Si los hashes
   de `Macromycets` son de otro esquema (bcrypt, md5), esos usuarios no podrán
   iniciar sesión. Comprobar con
   `SELECT left(password_hash, 10), count(*) FROM public.user_web GROUP BY 1;`
   y, si hace falta, restablecer las contraseñas o añadir el esquema a
   `CryptContext`.
7. **`field_collector`**: el frontend lo muestra como `viewer` y el backend lo
   trata como solo lectura. Si debe escribir, añadirlo a `ROLES_AUTORIZADOS`.

---

## 4. Normalizar bibliografía y entrevistas

Hoy ambas capas viven en `public.application_state.payload` como JSON. Las
tablas normalizadas ya existen en `Macromycets` y están vacías o con datos del
pipeline. Para que los formularios escriban ahí:

### 4.1 Modelos nuevos

```
src/models/Party.py                  -> shared.party (Party) y shared.taxon_party (TaxonParty)
src/models/EthnoSource.py            -> socioecological.ethno_source
src/models/EthnoTaxonKnowledge.py    -> socioecological.ethno_taxon_knowledge
src/models/EthnoUse.py               -> socioecological.ethno_use
src/models/ScientificSource.py       -> bibliographic.scientific_source
src/models/ScientificTaxonLink.py    -> bibliographic.scientific_taxon_link
src/models/ScientificUse.py          -> bibliographic.scientific_use
src/models/ScientificEcology.py      -> bibliographic.scientific_ecology
```

Todos con `create_type=False` en los enums y `__table_args__ = {"schema": ...}`,
igual que los modelos actuales. Están registrados en `src/models/__init__.py`.

`shared.party.display_name` es una columna `GENERATED ALWAYS AS ... STORED`:
el modelo la declara con `Computed` y nunca se inserta desde Python.

### 4.2 Contratos tipados

En `schemas/bundles.py`, `sources`, `knowledge` y `participants` ya no son
`list[dict]`:

```python
# schemas/bibliographic_schema.py
class SourceData(BaseModel):
    source_id: uuid.UUID | None = None
    source_type: SourceType | None = None       # Literal con el enum de la BD
    title: str | None = None
    authors: str | None = None
    year: int | None = Field(None, ge=1753, le=2100)   # en la tabla es pub_year
    doi: str | None = None
    # citation_apa, journal_or_publisher, url, region_scope, quality_level, notes

# schemas/socioecological_schema.py
class EthnoSurveyData(BaseModel):
    source: EthnoSourceData          # ethno_source
    knowledge: EthnoKnowledgeData    # ethno_taxon_knowledge
    uses: list[EthnoUseData]         # ethno_use

# schemas/party_schema.py
class ParticipantData(BaseModel):
    party: PartyData
    party_role: str | None = None
    scope: Literal["taxon", "occurrence", "event"] | None = None
    is_primary: bool | None = False

class TaxonBundle(BaseModel):
    ...
    sources: list[SourceData]
    knowledge: list[EthnoSurveyData]
    participants: list[ParticipantData]
```

Ventaja: los errores de enum se detectan con un 422 claro en vez de un error
de PostgreSQL. Los nombres del contrato se mantienen (`year`, `knowledge_id`,
`use_id`) para no tocar el frontend; la traducción a columnas (`pub_year`,
`ethno_know_id`, `ethno_use_id`) ocurre en la capa de servicio.

`source_type_enum` ganó el valor `website`, que el formulario ya ofrecía y que
aparece en los datos guardados. El script lo añade con
`ALTER TYPE ... ADD VALUE IF NOT EXISTS 'website'`.

### 4.3 Mapeo campo del formulario → columna

**Bibliografía**

| Formulario | Destino |
| --- | --- |
| `sources[].id` | `bibliographic.scientific_source.source_id` |
| `sourceType` | `source_type` |
| `title` | `title` |
| `authors` | `authors` |
| `year` | `pub_year` |
| `doi` | `doi` |
| — | `scientific_taxon_link(taxon_id, source_id, mention_type)` |

**Entrevistas**

| Formulario | Destino |
| --- | --- |
| `knowledge[].source.id` | `socioecological.ethno_source.ethno_source_id` |
| `interviewDate` | `interview_date` |
| `interviewer` | `interviewer` |
| `consentGiven` | `consent_given` |
| `consentType` | `consent_type` |
| `anonymityLevel` | `anonymity_level` |
| `municipality`, `village` | `municipality`, `village` |
| `occupation`, `ageRange`, `gender` | `occupation`, `age_range`, `gender` |
| `stateProvince` | `state_province` (ya existe en la tabla) |
| `remarks` | `remarks` |
| `knowledge[].knowledge.*` | `ethno_taxon_knowledge.*` |
| `knowledgeId` | `ethno_know_id` |
| `uses[].id` | `ethno_use.ethno_use_id` |
| `uses[].useCategory` | `ethno_use.use_category` |
| `uses[].recommendations` | `ethno_taxon_knowledge.recommendations` (no está en `ethno_use`) |
| — | `ethno_use.taxon_id`: FK redundante a `shared.taxon_ref` para consultar por especie; se copia desde `ethno_taxon_knowledge.taxon_id` |

**Participantes**

| Formulario | Destino |
| --- | --- |
| `participants[].party.*` | `shared.party` |
| `scope = taxon` | `shared.taxon_party` (sin rol) |
| `scope = occurrence` | `shared.occurrence_party` (`party_role`, `is_primary`) |
| `scope = event` | `shared.event_party` (`party_role`, `is_primary`) |
| `credits` de una foto | `shared.media_party` (`credit_role`, `is_primary`) |

### 4.4 Flujo de escritura

`save_taxon()` deja de escribir `sources`/`knowledge`/`participants` en el JSON:

```text
PUT /taxon-bundles/{id}
  ├─ shared.taxon_ref                    upsert
  ├─ bibliographic.scientific_source     upsert por source_id (y por doi)
  ├─ bibliographic.scientific_taxon_link replace por taxon_id
  ├─ socioecological.ethno_source        upsert por ethno_source_id
  ├─ socioecological.ethno_taxon_knowledge replace por (ethno_source_id, taxon_id)
  ├─ socioecological.ethno_use           replace por ethno_know_id
  ├─ shared.party                        upsert por party_id
  ├─ shared.taxon_party                  replace por taxon_id
  └─ ecological.morphology_fact          replace por taxon_id

PUT /record-bundles/{id}
  ├─ ecological.location                 upsert
  ├─ ecological.event                    upsert
  ├─ ecological.occurrence               upsert
  ├─ shared.party                        upsert por party_id
  ├─ shared.occurrence_party             replace por occurrence_id
  ├─ shared.event_party                  replace por event_id
  ├─ ecological.morphology_fact          replace por occurrence_id
  └─ ecological.multimedia + shared.media_party (fotos)

PUT /record-bundles/{id} (multimedia)
  ├─ ecological.multimedia               insert por media_id
  ├─ public.application_state            propiedad (payload vacío)
  └─ shared.media_party                  replace por media_id
```

Todo dentro de la misma transacción (`mutation()`), igual que hoy.

Detalles de la implementación (`services/application.py`):

- `scientific_source` es compartida entre taxones: no se borra, solo se retira
  el vínculo `taxonomy` del taxón que ya no la usa. Los vínculos importados
  (`ecology`, `use`, `distribution`...) se conservan.
- La clave natural de `ethno_taxon_knowledge` es `(ethno_source_id, taxon_id)`.
  Si el cliente manda un `knowledge_id` libre se respeta; si ya pertenece a otro
  par se genera uno nuevo. Lo mismo con `use_id`.
- `ethno_source` tampoco se borra: una sesión de entrevista puede cubrir varios
  taxones.
- `uses[].recommendations` se guarda en
  `ethno_taxon_knowledge.recommendations` (el formulario ya lo envía a nivel de
  entrevista). Si un cliente antiguo lo manda por uso, se concatenan los textos.
- `source_type` ausente se guarda como `other`, porque la columna es NOT NULL.
- `display_name` de `shared.party` nunca se escribe: lo genera PostgreSQL.
- Los participantes de un hallazgo se reparten por `scope`: `event` va a
  `shared.event_party` y el resto a `shared.occurrence_party`. Las filas vacías
  que el formulario deja al pulsar "añadir" se ignoran.
- Los créditos de una foto se guardan en `shared.media_party`; `PhotoData.credits`
  ya es `list[PhotoCredit]`, no `list[dict]`.
- El formulario envía `photo_type` como `habitus`/`pileus`; la columna guarda el
  valor del enum (`voucher`/`cap`) y la respuesta lo traduce de vuelta.
- `habitat`, `substrate` y `sampling_effort` pasaron de enum a TEXT
  (`03_campos_texto_libre.sql`): el formulario los pide como texto libre y antes
  el API los descartaba guardando `Other`/NULL.

`complete()` invierte el proceso: joins desde `taxon_ref`/`occurrence` hacia las
tablas laterales y arma la misma respuesta (`sources`, `knowledge`,
`participants`, `multimedia[].credits`), de modo que el frontend no cambia. Si
las tablas no tienen filas, cae al JSON antiguo de `application_state`; por eso
las fichas guardadas antes de esta versión se siguen viendo igual.

### 4.5 Qué queda en `application_state`

Solo lo que no tiene tabla propia:

| Ficha | `payload` |
| --- | --- |
| `taxon_ref` | `snapshot` (huella para detectar cambios) y `morphology_snapshot` |
| `occurrence` | `snapshot` y `measurements` |
| `multimedia` | `{}` (la fila existe para guardar `owner_id`/`created_by_id`) |

Las medidas libres siguen en el JSON porque
`ecological.measurement_or_fact` solo admite el enum de microclima y un valor
numérico, mientras el formulario acepta texto como `"5–8"` o `"24 °C"`.
Ubicación, evento, sustrato y participantes ya no se duplican allí.

### 4.6 Reglas de negocio que la BD impone

| Regla | Consecuencia |
| --- | --- |
| `scientific_source.doi` UNIQUE | La API responde 409 antes de insertar |
| `scientific_taxon_link (taxon_id, source_id, mention_type)` UNIQUE | Solo se crea el vínculo `taxonomy` si el par no tenía ninguno |
| `ethno_taxon_knowledge (ethno_source_id, taxon_id)` UNIQUE | La API responde 422 si la misma entrevista se repite para el taxón |
| `ethno_source.consent_given NOT NULL` | Ya se valida en `save_taxon` |
| `ethno_source` no guarda el nombre | La persona entrevistada no se modela; solo el entrevistador del equipo |
| `ethno_use.use_category NOT NULL` | El formulario usa un `select`; la API responde 422 si falta |
| `scientific_source.source_type NOT NULL` | `select` con los valores del enum; si falta, se guarda `other` |
| `shared.party.orcid` y `contact_email` con CHECK | El contrato Pydantic los valida con las mismas expresiones |

### 4.6 Migración de los datos actuales

Script único (`scripts/migrate_state_to_normalized.py`), idempotente:

1. Por cada `application_state` de tipo `taxon_ref`:
   - `payload.sources` → `scientific_source` + `scientific_taxon_link`.
   - `payload.knowledge` → `ethno_source` + `ethno_taxon_knowledge` + `ethno_use`.
   - `payload.participants` → `shared.party` + `taxon_party`.
2. Por cada `occurrence`: `payload.participants` → `occurrence_party`.
3. Por cada `multimedia`: `payload.credits` → `media_party`.
4. Mantener el JSON como respaldo durante una versión; `complete()` puede leer
   de las tablas y caer al JSON si no hay filas.

Conviene migrar también los datos heredados de `Macromycets` que ya estén en
`bibliographic.*` y `socioecological.*` (si los hay), para no duplicarlos.

### 4.7 Orden recomendado

1. Ejecutar los scripts de compatibilidad y cambiar `.env`.
2. Validar la app con el JSON (sin normalizar).
3. Añadir modelos y contratos tipados. *(Hecho: los 9 modelos están en
   `Backend/src/models/` y los contratos en `schemas/party_schema.py`,
   `schemas/bibliographic_schema.py` y `schemas/socioecological_schema.py`,
   conectados a `schemas/bundles.py`. Los enums nuevos se declaran con
   `schema="bibliographic"` / `schema="socioecological"` y
   `create_type=False`.)*
4. Implementar escritura y lectura normalizada con *fallback* al JSON.
   *(Hecho: `save_taxon()` escribe en `bibliographic.*`, `socioecological.*` y
   `shared.party`; `complete()` lee de ahí y solo usa el JSON para fichas
   antiguas. El JSON conserva `snapshot` y `morphology_snapshot`.)*
5. Migrar los datos existentes. *(No hace falta para `macromicetos`: la única
   ficha con fuentes en el JSON se normaliza sola al volver a guardarla.)*
6. Retirar el JSON cuando la lectura normalizada esté probada.

---

## 5. Nota sobre reconstruir desde `create_macromycetes_db_v3.sql`

Ese script **no crea** `public.user_web`, `public.application_state`,
`curaduria.*`, `ecological.morphology_fact` ni las tablas `*_party`. La base
`Macromycets` actual sí las tiene porque se añadieron después. Si algún día se
reconstruye desde cero, hay que ejecutar también los scripts que crean esos
objetos; de lo contrario la aplicación no arranca.
