-- ============================================================================
-- macromicetos: participantes de hallazgos, eventos y fotografías
--
-- Ejecutar conectado a la base "macromicetos", después de
-- 01_capas_bibliografica_socioecologica.sql (usa shared.party).
--
-- Complementa shared.taxon_party con los otros tres ámbitos que el formulario
-- ya distinguía: la salida de campo (event), el hallazgo (occurrence) y los
-- créditos de una fotografía (media).
--
-- Es idempotente: no borra datos ni recrea objetos existentes.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS shared.event_party (
    event_id   UUID        NOT NULL
                           REFERENCES ecological.event(event_id)
                           ON DELETE CASCADE ON UPDATE CASCADE,
    party_id   UUID        NOT NULL
                           REFERENCES shared.party(party_id)
                           ON DELETE RESTRICT ON UPDATE CASCADE,
    party_role TEXT,
    is_primary BOOLEAN     NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_event_party PRIMARY KEY (event_id, party_id)
);

COMMENT ON TABLE shared.event_party IS
    'Personas que participaron en una salida de campo (ecological.event).';

CREATE TABLE IF NOT EXISTS shared.occurrence_party (
    occurrence_id UUID        NOT NULL
                              REFERENCES ecological.occurrence(occurrence_id)
                              ON DELETE CASCADE ON UPDATE CASCADE,
    party_id      UUID        NOT NULL
                              REFERENCES shared.party(party_id)
                              ON DELETE RESTRICT ON UPDATE CASCADE,
    party_role    TEXT,
    is_primary    BOOLEAN     NOT NULL DEFAULT false,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_occurrence_party PRIMARY KEY (occurrence_id, party_id)
);

COMMENT ON TABLE shared.occurrence_party IS
    'Personas vinculadas a un hallazgo concreto (ecological.occurrence).';

CREATE TABLE IF NOT EXISTS shared.media_party (
    media_id   UUID        NOT NULL
                           REFERENCES ecological.multimedia(media_id)
                           ON DELETE CASCADE ON UPDATE CASCADE,
    party_id   UUID        NOT NULL
                           REFERENCES shared.party(party_id)
                           ON DELETE RESTRICT ON UPDATE CASCADE,
    party_role TEXT,
    is_primary BOOLEAN     NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_media_party PRIMARY KEY (media_id, party_id)
);

COMMENT ON TABLE shared.media_party IS
    'Créditos de una fotografía: fotógrafo, titular de derechos, proveedor.';

CREATE INDEX IF NOT EXISTS idx_event_party_party_id      ON shared.event_party (party_id);
CREATE INDEX IF NOT EXISTS idx_occurrence_party_party_id ON shared.occurrence_party (party_id);
CREATE INDEX IF NOT EXISTS idx_media_party_party_id      ON shared.media_party (party_id);

COMMIT;

-- ----------------------------------------------------------------------------
-- Verificación
-- ----------------------------------------------------------------------------
SELECT table_name
  FROM information_schema.tables
 WHERE table_schema = 'shared'
 ORDER BY 1;
