-- ============================================================================
-- Macromycets: compatibilidad con la aplicación Macromicetos
--
-- Ejecutar conectado a la base "Macromycets" con el usuario postgres
-- (pgAdmin: clic derecho sobre Macromycets > Query Tool).
--
-- Es idempotente: se puede ejecutar varias veces sin efectos secundarios.
-- No borra datos ni recrea tablas existentes.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 0. Precondición: esta base ya debe tener las tablas de la aplicación.
--    Si se reconstruyó solo con create_macromycetes_db_v3.sql, faltan
--    public.user_web, curaduria.* y ecological.morphology_fact.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('public.user_web') IS NULL THEN
        RAISE EXCEPTION
            'Falta public.user_web. Ejecuta primero el script que crea las tablas '
            'de la aplicación (user_web, curaduria.curation_decision, '
            'ecological.morphology_fact).';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 1. Permisos de conexión y de esquema
--
-- Se concede USAGE, no CREATE: la aplicación no debe poder crear esquemas ni
-- tipos duplicados dentro de una base que ya tiene su propio diseño.
-- ----------------------------------------------------------------------------
GRANT CONNECT ON DATABASE "Macromycets" TO macromicetos_app;

GRANT USAGE ON SCHEMA
    public, shared, ecological, curaduria, socioecological, bibliographic
    TO macromicetos_app;

-- ----------------------------------------------------------------------------
-- 2. Tipos enum
--
-- PostgreSQL no tiene "GRANT ... ON ALL TYPES", así que se recorre el catálogo.
-- Sin USAGE sobre el tipo, cualquier SELECT/INSERT que lo use falla con
-- "permiso denegado al tipo".
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT n.nspname AS sch, t.typname AS typ
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typtype = 'e'
          AND n.nspname IN ('public', 'shared', 'ecological',
                            'curaduria', 'socioecological', 'bibliographic')
    LOOP
        EXECUTE format('GRANT USAGE ON TYPE %I.%I TO macromicetos_app', r.sch, r.typ);
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 3. public.application_state
--
-- Es la única tabla que la aplicación necesita y que Macromycets no tiene.
-- Guarda propiedad (owner_id / created_by_id) y las colecciones extendidas
-- que aún no están normalizadas: sources, knowledge, participants,
-- measurements, credits y snapshots.
--
-- Misma definición que en la base macromicetos.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.application_state (
    entity_type   varchar(24) NOT NULL,
    entity_id     uuid        NOT NULL,
    owner_id      uuid,
    created_by_id uuid,
    payload       json        NOT NULL DEFAULT '{}'::json,
    CONSTRAINT application_state_pkey PRIMARY KEY (entity_type, entity_id),
    CONSTRAINT application_state_owner_id_fkey
        FOREIGN KEY (owner_id) REFERENCES public.user_web (user_web_id),
    CONSTRAINT application_state_created_by_id_fkey
        FOREIGN KEY (created_by_id) REFERENCES public.user_web (user_web_id)
);

CREATE INDEX IF NOT EXISTS idx_application_state_owner
    ON public.application_state (owner_id);

-- ----------------------------------------------------------------------------
-- 4. Permisos sobre datos y funciones
-- ----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA
    public, shared, ecological, curaduria, socioecological, bibliographic
    TO macromicetos_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA
    public, shared, ecological, curaduria, socioecological, bibliographic
    TO macromicetos_app;

-- Los triggers (set_updated_at, sync_location_geog, purge_on_delete) se
-- ejecutan con los privilegios de quien hace el INSERT/UPDATE.
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA
    public, shared, ecological, curaduria, socioecological, bibliographic
    TO macromicetos_app;

-- Para tablas y secuencias que se creen en el futuro desde esta sesión.
ALTER DEFAULT PRIVILEGES IN SCHEMA
    public, shared, ecological, curaduria, socioecological, bibliographic
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO macromicetos_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA
    public, shared, ecological, curaduria, socioecological, bibliographic
    GRANT USAGE, SELECT ON SEQUENCES TO macromicetos_app;

-- ----------------------------------------------------------------------------
-- 5. Ajustes de compatibilidad
--
-- Macromycets fue diseñada para un pipeline de datos, con reglas más estrictas
-- que las que el formulario web puede garantizar. Estas son las que chocan.
-- ----------------------------------------------------------------------------

-- 5.1 País: el formulario pide un código ISO de dos letras y guarda "CO".
--     La restricción original solo acepta el nombre completo "Colombia".
ALTER TABLE ecological.location
    DROP CONSTRAINT IF EXISTS location_country_check;
ALTER TABLE ecological.location
    ADD CONSTRAINT location_country_check
    CHECK (country = 'Colombia' OR country ~ '^[A-Z]{2}$');

-- 5.2 Incertidumbre de 0 m es un valor válido en el formulario.
ALTER TABLE ecological.location
    DROP CONSTRAINT IF EXISTS location_coordinate_uncertainty_m_check;
ALTER TABLE ecological.location
    ADD CONSTRAINT location_coordinate_uncertainty_m_check
    CHECK (coordinate_uncertainty_m IS NULL OR coordinate_uncertainty_m >= 0);

-- 5.3 Claves naturales que la aplicación no puede garantizar.
--
-- El formulario crea ubicaciones y eventos con identificadores propios del
-- cliente, así que dos usuarios pueden registrar el mismo sitio o la misma
-- salida sin saberlo. Con estas restricciones activas el INSERT falla con un
-- error 500 en lugar de guardar.
--
-- Si prefieres conservarlas, el backend debe detectar el conflicto y reutilizar
-- la fila existente. Eso es una mejora posterior, no un requisito para arrancar.
ALTER TABLE ecological.location
    DROP CONSTRAINT IF EXISTS uq_location_natural_key;

ALTER TABLE ecological.event
    DROP CONSTRAINT IF EXISTS uq_event_site_date;

ALTER TABLE ecological.multimedia
    DROP CONSTRAINT IF EXISTS uq_multimedia_occurrence_type_file;

-- La app ya deduplica fotografías por sha256_hash, que sigue siendo UNIQUE.

-- 5.4 El historial de curaduría puede tener dos decisiones en el mismo instante
--     (por ejemplo, una operación masiva). La unicidad por marca de tiempo es
--     frágil y no aporta integridad real.
ALTER TABLE curaduria.curation_decision
    DROP CONSTRAINT IF EXISTS uq_decision_persot;

-- ----------------------------------------------------------------------------
-- 6. search_path del rol
--
-- En Macromycets los enums viven en shared/ecological/curaduria/..., pero el
-- ORM los declara sin esquema. Con este search_path se resuelven solos, sin
-- cambiar los modelos ni calificar cada columna.
-- ----------------------------------------------------------------------------
ALTER ROLE macromicetos_app IN DATABASE "Macromycets"
    SET search_path = public, shared, ecological, curaduria, socioecological, bibliographic;

COMMIT;

-- ============================================================================
-- 7. Verificación
-- Todas las columnas deben devolver true.
-- ============================================================================
SELECT
    has_database_privilege('macromicetos_app', 'Macromycets', 'CONNECT')  AS connect_ok,
    has_schema_privilege('macromicetos_app', 'shared', 'USAGE')           AS shared_ok,
    has_schema_privilege('macromicetos_app', 'ecological', 'USAGE')       AS ecological_ok,
    has_schema_privilege('macromicetos_app', 'curaduria', 'USAGE')        AS curaduria_ok,
    has_schema_privilege('macromicetos_app', 'socioecological', 'USAGE')  AS socioeco_ok,
    has_schema_privilege('macromicetos_app', 'bibliographic', 'USAGE')    AS biblio_ok,
    has_table_privilege('macromicetos_app', 'public.application_state', 'SELECT') AS app_state_ok,
    has_table_privilege('macromicetos_app', 'shared.taxon_ref', 'INSERT') AS taxon_write_ok,
    to_regtype('shared.taxon_rank_enum') IS NOT NULL                     AS enum_ok,
    EXISTS (
        SELECT 1
          FROM pg_db_role_setting s
          JOIN pg_roles r    ON r.oid = s.setrole
          JOIN pg_database d ON d.oid = s.setdatabase
         WHERE r.rolname = 'macromicetos_app'
           AND d.datname = 'Macromycets'
           AND array_to_string(s.setconfig, ' ') LIKE '%search_path=public,shared%'
    )                                                                     AS search_path_ok;
