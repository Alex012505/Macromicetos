-- ============================================================================
-- macromicetos: crear las capas bibliográfica y socioecológica
--
-- Ejecutar conectado a la base "macromicetos".
-- Se puede ejecutar como macromicetos_app: es dueño de la base y tiene CREATE.
-- No requiere postgres, ni PostGIS, ni pgcrypto (PostgreSQL 13+ trae
-- gen_random_uuid() nativo).
--
-- Es idempotente: no borra datos ni recrea objetos existentes.
--
-- Las tablas son las mismas del diseño original (create_macromycetes_db_v3.sql),
-- con una sola diferencia: socioecological.ethno_source incluye state_province,
-- porque el formulario web lo envía y el diseño original no lo tenía.
-- ============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS bibliographic;
CREATE SCHEMA IF NOT EXISTS socioecological;

-- ----------------------------------------------------------------------------
-- 0. Utilidad: crear un enum solo si no existe
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.ensure_enum(
    p_schema text,
    p_name   text,
    p_values text[]
) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM pg_type t
          JOIN pg_namespace n ON n.oid = t.typnamespace
         WHERE n.nspname = p_schema AND t.typname = p_name
    ) THEN
        RETURN;
    END IF;

    EXECUTE format(
        'CREATE TYPE %I.%I AS ENUM (%s)',
        p_schema,
        p_name,
        (SELECT string_agg(quote_literal(v), ', ' ORDER BY ord)
           FROM unnest(p_values) WITH ORDINALITY AS u(v, ord))
    );
END $$;

-- ----------------------------------------------------------------------------
-- 1. Tipos del esquema bibliographic
-- ----------------------------------------------------------------------------
SELECT public.ensure_enum('bibliographic', 'source_type_enum', ARRAY[
    'article', 'book', 'book_chapter', 'thesis', 'report',
    'dataset', 'preprint', 'conference_paper', 'field_guide', 'website', 'other']);

-- El formulario ya ofrecía "Sitio web": se añade al enum si la base lo creó
-- antes de existir ese valor. IF NOT EXISTS lo hace idempotente.
ALTER TYPE bibliographic.source_type_enum ADD VALUE IF NOT EXISTS 'website';

SELECT public.ensure_enum('bibliographic', 'region_scope_enum', ARRAY[
    'global', 'latam', 'colombia', 'andes', 'orinoco', 'amazonia', 'other']);

SELECT public.ensure_enum('bibliographic', 'quality_level_enum', ARRAY[
    'high', 'medium', 'low']);

SELECT public.ensure_enum('bibliographic', 'mention_type_enum', ARRAY[
    'taxonomy', 'ecology', 'use', 'chemistry', 'distribution',
    'morphology', 'phylogeny', 'biocontrol']);

SELECT public.ensure_enum('bibliographic', 'evidence_strength_enum', ARRAY[
    'strong', 'moderate', 'weak', 'anecdotal']);

SELECT public.ensure_enum('bibliographic', 'sci_use_category_enum', ARRAY[
    'edible', 'medicinal', 'antimicrobial', 'antioxidant', 'enzyme',
    'bioremediation', 'agriculture', 'biocontrol', 'dye', 'ritual',
    'mythological', 'other']);

SELECT public.ensure_enum('bibliographic', 'evidence_type_enum', ARRAY[
    'in_vitro', 'in_vivo', 'clinical', 'observational', 'review', 'meta_analysis']);

-- ----------------------------------------------------------------------------
-- 2. Tipos del esquema socioecological
-- ----------------------------------------------------------------------------
SELECT public.ensure_enum('socioecological', 'consent_type_enum', ARRAY[
    'verbal', 'written']);

SELECT public.ensure_enum('socioecological', 'anonymity_level_enum', ARRAY[
    'anonymous', 'pseudonym', 'identified']);

SELECT public.ensure_enum('socioecological', 'occupation_enum', ARRAY[
    'farmer', 'fisher', 'indigenous_knowledge_holder', 'rancher',
    'forester', 'student', 'teacher', 'other']);

SELECT public.ensure_enum('socioecological', 'age_range_enum', ARRAY[
    '12-17', '18-25', '26-40', '41-60', '60+']);

SELECT public.ensure_enum('socioecological', 'gender_enum', ARRAY[
    'male', 'female', 'non_binary', 'prefer_not_to_say']);

SELECT public.ensure_enum('socioecological', 'learning_source_enum', ARRAY[
    'family', 'community', 'personal_experience', 'books',
    'workshops', 'internet', 'other']);

SELECT public.ensure_enum('socioecological', 'ethno_use_category_enum', ARRAY[
    'edible', 'medicinal', 'ritual', 'dye', 'soil_improvement',
    'biological_control', 'animal_feed', 'other']);

SELECT public.ensure_enum('socioecological', 'importance_enum', ARRAY[
    'high', 'medium', 'low']);

SELECT public.ensure_enum('socioecological', 'cultural_identity_enum', ARRAY[
    'yes', 'no', 'partial']);

-- ----------------------------------------------------------------------------
-- 3. Función de auditoría para updated_at
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END $$;

-- ============================================================================
-- 4. CAPA BIBLIOGRÁFICA
-- ============================================================================

CREATE TABLE IF NOT EXISTS bibliographic.scientific_source (
    source_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type          bibliographic.source_type_enum NOT NULL,
    citation_apa         TEXT,
    pub_year             SMALLINT    CHECK (pub_year BETWEEN 1753 AND 2100),
    title                TEXT        NOT NULL,
    authors              TEXT,
    journal_or_publisher TEXT,
    doi                  TEXT,
    url                  TEXT,
    region_scope         bibliographic.region_scope_enum,
    quality_level        bibliographic.quality_level_enum,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_doi UNIQUE (doi)
);

COMMENT ON TABLE bibliographic.scientific_source IS
    'Una fila por referencia bibliográfica. Las demás tablas bibliográficas la referencian.';

CREATE TABLE IF NOT EXISTS bibliographic.scientific_taxon_link (
    taxon_source_link_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    taxon_id             UUID        NOT NULL
                                     REFERENCES shared.taxon_ref(taxon_id)
                                     ON DELETE CASCADE ON UPDATE CASCADE,
    source_id            UUID        NOT NULL
                                     REFERENCES bibliographic.scientific_source(source_id)
                                     ON DELETE CASCADE ON UPDATE CASCADE,
    mention_type         bibliographic.mention_type_enum NOT NULL,
    evidence_strength    bibliographic.evidence_strength_enum,
    location_in_source   TEXT,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_taxon_source_mention UNIQUE (taxon_id, source_id, mention_type)
);

COMMENT ON TABLE bibliographic.scientific_taxon_link IS
    'Muchos-a-muchos entre taxones y fuentes. Una fila por (taxón, fuente, tipo de mención).';

CREATE TABLE IF NOT EXISTS bibliographic.scientific_use (
    sci_use_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    taxon_id        UUID        NOT NULL
                                REFERENCES shared.taxon_ref(taxon_id)
                                ON DELETE CASCADE ON UPDATE CASCADE,
    source_id       UUID        NOT NULL
                                REFERENCES bibliographic.scientific_source(source_id)
                                ON DELETE CASCADE ON UPDATE CASCADE,
    use_category    bibliographic.sci_use_category_enum NOT NULL,
    evidence_type   bibliographic.evidence_type_enum,
    claimed_effect  TEXT,
    method_summary  TEXT,
    key_result      TEXT,
    safety_notes    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE bibliographic.scientific_use IS
    'Afirmaciones de uso estructuradas extraídas de la literatura.';

CREATE TABLE IF NOT EXISTS bibliographic.scientific_ecology (
    sci_eco_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    taxon_id           UUID        NOT NULL
                                   REFERENCES shared.taxon_ref(taxon_id)
                                   ON DELETE CASCADE ON UPDATE CASCADE,
    source_id          UUID        NOT NULL
                                   REFERENCES bibliographic.scientific_source(source_id)
                                   ON DELETE CASCADE ON UPDATE CASCADE,
    habitat_reported   TEXT,
    substrate_reported TEXT,
    seasonality        TEXT,
    region_reported    TEXT,
    notes              TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE bibliographic.scientific_ecology IS
    'Observaciones ecológicas estructuradas extraídas de la literatura.';

-- Índices
CREATE INDEX IF NOT EXISTS idx_source_pub_year          ON bibliographic.scientific_source (pub_year);
CREATE INDEX IF NOT EXISTS idx_source_type              ON bibliographic.scientific_source (source_type);
CREATE INDEX IF NOT EXISTS idx_taxon_link_taxon_id      ON bibliographic.scientific_taxon_link (taxon_id);
CREATE INDEX IF NOT EXISTS idx_taxon_link_source_id     ON bibliographic.scientific_taxon_link (source_id);
CREATE INDEX IF NOT EXISTS idx_sci_use_taxon_id         ON bibliographic.scientific_use (taxon_id);
CREATE INDEX IF NOT EXISTS idx_sci_use_source_id        ON bibliographic.scientific_use (source_id);
CREATE INDEX IF NOT EXISTS idx_sci_use_category         ON bibliographic.scientific_use (use_category);
CREATE INDEX IF NOT EXISTS idx_sci_eco_taxon_id         ON bibliographic.scientific_ecology (taxon_id);
CREATE INDEX IF NOT EXISTS idx_sci_eco_source_id        ON bibliographic.scientific_ecology (source_id);

-- Triggers updated_at
DROP TRIGGER IF EXISTS trg_sci_source_updated_at ON bibliographic.scientific_source;
CREATE TRIGGER trg_sci_source_updated_at
    BEFORE UPDATE ON bibliographic.scientific_source
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_sci_use_updated_at ON bibliographic.scientific_use;
CREATE TRIGGER trg_sci_use_updated_at
    BEFORE UPDATE ON bibliographic.scientific_use
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_sci_eco_updated_at ON bibliographic.scientific_ecology;
CREATE TRIGGER trg_sci_eco_updated_at
    BEFORE UPDATE ON bibliographic.scientific_ecology
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================================
-- 5. CAPA SOCIOECOLÓGICA
-- ============================================================================

CREATE TABLE IF NOT EXISTS socioecological.ethno_source (
    ethno_source_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_date   TIMESTAMPTZ NOT NULL DEFAULT now(),
    interviewer      TEXT        NOT NULL,
    consent_given    BOOLEAN     NOT NULL,
    consent_type     socioecological.consent_type_enum,
    anonymity_level  socioecological.anonymity_level_enum NOT NULL DEFAULT 'anonymous',
    state_province   TEXT,
    municipality     TEXT,
    village          TEXT,
    occupation       socioecological.occupation_enum,
    age_range        socioecological.age_range_enum,
    gender           socioecological.gender_enum,
    remarks          TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE socioecological.ethno_source IS
    'Una fila por sesión de entrevista: consentimiento, anonimato y contexto sociodemográfico.';

CREATE TABLE IF NOT EXISTS socioecological.ethno_taxon_knowledge (
    ethno_know_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ethno_source_id    UUID        NOT NULL
                                   REFERENCES socioecological.ethno_source(ethno_source_id)
                                   ON DELETE RESTRICT ON UPDATE CASCADE,
    taxon_id           UUID
                                   REFERENCES shared.taxon_ref(taxon_id)
                                   ON DELETE SET NULL ON UPDATE CASCADE,
    knows_fungi        BOOLEAN,
    local_name         TEXT,
    learning_source    socioecological.learning_source_enum,
    recognition_cues   TEXT,
    found_in_places    TEXT,
    seasonality        TEXT,
    months             TEXT,
    safety_practices   TEXT,
    myths_stories      TEXT,
    cultural_identity  socioecological.cultural_identity_enum,
    recommendations    TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_ethno_know_source_taxon UNIQUE (ethno_source_id, taxon_id)
);

COMMENT ON TABLE socioecological.ethno_taxon_knowledge IS
    'Puente entrevista-taxón. Una fila por par (persona, especie).';

CREATE TABLE IF NOT EXISTS socioecological.ethno_use (
    ethno_use_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ethno_know_id       UUID        NOT NULL
                                    REFERENCES socioecological.ethno_taxon_knowledge(ethno_know_id)
                                    ON DELETE CASCADE ON UPDATE CASCADE,
    taxon_id            UUID
                                    REFERENCES shared.taxon_ref(taxon_id)
                                    ON DELETE SET NULL ON UPDATE CASCADE,
    uses_fungi          BOOLEAN,
    use_category        socioecological.ethno_use_category_enum NOT NULL,
    preparation_method  TEXT,
    ailment             TEXT,
    dosage              TEXT,
    contraindications   TEXT,
    importance          socioecological.importance_enum,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- La tabla pudo crearse antes de existir taxon_id; se añade sin romper datos.
ALTER TABLE socioecological.ethno_use
    ADD COLUMN IF NOT EXISTS taxon_id UUID
    REFERENCES shared.taxon_ref(taxon_id) ON DELETE SET NULL ON UPDATE CASCADE;

COMMENT ON TABLE socioecological.ethno_use IS
    'Una fila por uso reportado. Un taxón puede ser comestible, medicinal y ritual a la vez.';

COMMENT ON COLUMN socioecological.ethno_use.taxon_id IS
    'FK redundante a taxon_ref para consultas directas por especie.';

-- Índices
CREATE INDEX IF NOT EXISTS idx_ethno_know_source_id  ON socioecological.ethno_taxon_knowledge (ethno_source_id);
CREATE INDEX IF NOT EXISTS idx_ethno_know_taxon_id   ON socioecological.ethno_taxon_knowledge (taxon_id);
CREATE INDEX IF NOT EXISTS idx_ethno_use_know_id     ON socioecological.ethno_use (ethno_know_id);
CREATE INDEX IF NOT EXISTS idx_ethno_use_taxon_id    ON socioecological.ethno_use (taxon_id);
CREATE INDEX IF NOT EXISTS idx_ethno_use_category    ON socioecological.ethno_use (use_category);

-- Triggers updated_at
DROP TRIGGER IF EXISTS trg_ethno_source_updated_at ON socioecological.ethno_source;
CREATE TRIGGER trg_ethno_source_updated_at
    BEFORE UPDATE ON socioecological.ethno_source
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_ethno_know_updated_at ON socioecological.ethno_taxon_knowledge;
CREATE TRIGGER trg_ethno_know_updated_at
    BEFORE UPDATE ON socioecological.ethno_taxon_knowledge
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_ethno_use_updated_at ON socioecological.ethno_use;
CREATE TRIGGER trg_ethno_use_updated_at
    BEFORE UPDATE ON socioecological.ethno_use
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================================
-- 6. PARTICIPANTES (shared.party)
-- ============================================================================

CREATE TABLE IF NOT EXISTS shared.party (
    party_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    given_name    TEXT        NOT NULL,
    family_name   TEXT,
    display_name  TEXT        NOT NULL
                              GENERATED ALWAYS AS
                              (given_name || ' ' || COALESCE(family_name, '')) STORED,
    orcid         TEXT,
    affiliation   TEXT,
    contact_email TEXT,
    is_verified   BOOLEAN     NOT NULL DEFAULT false,
    is_active     BOOLEAN     NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_party_orcid UNIQUE (orcid),
    CONSTRAINT party_orcid_check
        CHECK (orcid ~ '^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$'),
    CONSTRAINT party_contact_email_check
        CHECK (contact_email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$')
);

COMMENT ON TABLE shared.party IS
    'Personas e instituciones. display_name es una columna generada.';

CREATE TABLE IF NOT EXISTS shared.taxon_party (
    taxon_id   UUID        NOT NULL
                           REFERENCES shared.taxon_ref(taxon_id)
                           ON DELETE CASCADE ON UPDATE CASCADE,
    party_id   UUID        NOT NULL
                           REFERENCES shared.party(party_id)
                           ON DELETE RESTRICT ON UPDATE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_taxon_party PRIMARY KEY (taxon_id, party_id)
);

CREATE INDEX IF NOT EXISTS idx_taxon_party_party_id ON shared.taxon_party (party_id);

DROP TRIGGER IF EXISTS trg_party_updated_at ON shared.party;
CREATE TRIGGER trg_party_updated_at
    BEFORE UPDATE ON shared.party
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ----------------------------------------------------------------------------
-- 7. Limpieza de la utilidad temporal
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.ensure_enum(text, text, text[]);

COMMIT;

-- ============================================================================
-- 8. Verificación
-- ============================================================================
SELECT table_schema, table_name
  FROM information_schema.tables
 WHERE table_schema IN ('bibliographic', 'socioecological')
 ORDER BY 1, 2;

SELECT n.nspname AS esquema, t.typname AS enum, count(e.enumlabel) AS valores
  FROM pg_type t
  JOIN pg_namespace n ON n.oid = t.typnamespace
  JOIN pg_enum e ON e.enumtypid = t.oid
 WHERE n.nspname IN ('bibliographic', 'socioecological')
 GROUP BY 1, 2
 ORDER BY 1, 2;
