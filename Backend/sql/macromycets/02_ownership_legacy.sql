-- ============================================================================
-- Macromycets: asignar propietario a los registros heredados
--
-- Ejecutar DESPUÉS de 01_compatibilidad_app.sql, conectado a "Macromycets".
--
-- Por qué: la aplicación decide quién puede editar con public.application_state.
-- Los taxones, hallazgos y fotografías que ya existían en Macromycets no tienen
-- fila allí, así que aparecerían sin dueño y solo un admin podría modificarlos.
--
-- Este script NO toca los datos científicos: solo crea las filas de estado que
-- faltan, con el payload vacío, para que los registros sean editables.
--
-- Es idempotente: omite las entidades que ya tienen estado.
-- ============================================================================

BEGIN;

DO $$
DECLARE
    admin_id uuid;
    created  int;
BEGIN
    SELECT user_web_id
      INTO admin_id
      FROM public.user_web
     WHERE role = 'admin'
     ORDER BY user_web_id
     LIMIT 1;

    IF admin_id IS NULL THEN
        RAISE EXCEPTION
            'No hay ninguna cuenta con rol admin en public.user_web. '
            'Crea una primero con: python manage.py create-admin --email ... --first-name ...';
    END IF;

    INSERT INTO public.application_state
        (entity_type, entity_id, owner_id, created_by_id, payload)
    SELECT 'taxon_ref', t.taxon_id, admin_id, admin_id, '{}'::json
      FROM shared.taxon_ref t
     WHERE NOT EXISTS (
        SELECT 1 FROM public.application_state s
         WHERE s.entity_type = 'taxon_ref' AND s.entity_id = t.taxon_id
     );

    GET DIAGNOSTICS created = ROW_COUNT;
    RAISE NOTICE 'taxon_ref: % registros heredados ahora tienen dueño', created;

    INSERT INTO public.application_state
        (entity_type, entity_id, owner_id, created_by_id, payload)
    SELECT 'occurrence', o.occurrence_id, admin_id, admin_id, '{}'::json
      FROM ecological.occurrence o
     WHERE NOT EXISTS (
        SELECT 1 FROM public.application_state s
         WHERE s.entity_type = 'occurrence' AND s.entity_id = o.occurrence_id
     );

    GET DIAGNOSTICS created = ROW_COUNT;
    RAISE NOTICE 'occurrence: % registros heredados ahora tienen dueño', created;

    INSERT INTO public.application_state
        (entity_type, entity_id, owner_id, created_by_id, payload)
    SELECT 'multimedia', m.media_id, admin_id, admin_id, '{}'::json
      FROM ecological.multimedia m
     WHERE NOT EXISTS (
        SELECT 1 FROM public.application_state s
         WHERE s.entity_type = 'multimedia' AND s.entity_id = m.media_id
     );

    GET DIAGNOSTICS created = ROW_COUNT;
    RAISE NOTICE 'multimedia: % registros heredados ahora tienen dueño', created;
END $$;

COMMIT;

-- ============================================================================
-- Verificación: no debe quedar ninguna entidad sin estado.
-- Las tres columnas "sin_dueno" deben devolver 0.
-- ============================================================================
SELECT 'taxon_ref' AS entidad,
       (SELECT count(*) FROM shared.taxon_ref) AS total,
       (SELECT count(*) FROM shared.taxon_ref t
         WHERE NOT EXISTS (SELECT 1 FROM public.application_state s
                            WHERE s.entity_type = 'taxon_ref'
                              AND s.entity_id = t.taxon_id)) AS sin_dueno
UNION ALL
SELECT 'occurrence',
       (SELECT count(*) FROM ecological.occurrence),
       (SELECT count(*) FROM ecological.occurrence o
         WHERE NOT EXISTS (SELECT 1 FROM public.application_state s
                            WHERE s.entity_type = 'occurrence'
                              AND s.entity_id = o.occurrence_id))
UNION ALL
SELECT 'multimedia',
       (SELECT count(*) FROM ecological.multimedia),
       (SELECT count(*) FROM ecological.multimedia m
         WHERE NOT EXISTS (SELECT 1 FROM public.application_state s
                            WHERE s.entity_type = 'multimedia'
                              AND s.entity_id = m.media_id));
