-- ============================================================================
-- macromicetos: convertir a texto libre tres campos del formulario
--
-- Hábitat, sustrato y esfuerzo de muestreo se piden en el formulario como
-- texto (máx. 40/32 caracteres), pero las columnas heredadas eran enums del
-- diseño original. El API descartaba el texto y guardaba "Other" o NULL, y el
-- valor real solo sobrevivía en el JSON de application_state.
--
-- Pasar las columnas a TEXT conserva los valores existentes (el cast de enum a
-- texto es directo) y deja la base como única fuente de verdad.
--
-- Es idempotente: si la columna ya es texto, el ALTER no cambia nada.
-- ============================================================================

BEGIN;

ALTER TABLE ecological.location
    ALTER COLUMN habitat TYPE TEXT USING habitat::text;

ALTER TABLE ecological.occurrence
    ALTER COLUMN substrate TYPE TEXT USING substrate::text;

ALTER TABLE ecological.event
    ALTER COLUMN sampling_effort TYPE TEXT USING sampling_effort::text;

COMMIT;

-- ----------------------------------------------------------------------------
-- Verificación
-- ----------------------------------------------------------------------------
SELECT table_name, column_name, data_type
  FROM information_schema.columns
 WHERE (table_schema, table_name, column_name) IN (
       ('ecological', 'location', 'habitat'),
       ('ecological', 'occurrence', 'substrate'),
       ('ecological', 'event', 'sampling_effort'))
 ORDER BY 1, 2;
