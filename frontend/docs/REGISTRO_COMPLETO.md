# Registro ampliado y correspondencia con el modelo

Actualización: 17 de octubre de 2026. Esta entrega implementa el frontend. El repositorio no contiene FastAPI ni PostgreSQL; la persistencia contra el servidor sigue pendiente de implementación y verificación.

## Cobertura de la información

| Entidad del modelo recibido | Captura y consulta en el frontend |
| --- | --- |
| `taxon_ref` | Nombre científico y común, rango, reino, división, clase, orden, familia, género, epíteto, ID externo y notas. Creación y edición de fichas propias; administración puede editar todas. |
| `location` | País, departamento, municipio, localidad, latitud/longitud WGS84, incertidumbre, elevación, hábitat y notas. Ubicación del dispositivo bajo petición, selección en mapa o coordenadas manuales. |
| `event` | Fecha de salida, tipo, código de campo, registrado por, protocolo, esfuerzo y notas. |
| `occurrence` | Taxón opcional, tipo de registro, ID externo, fecha/hora opcional, sustrato, identificador, fecha de identificación y notas. Se diferencia observación de identificación. |
| `morphology_fact` | Los 18 tipos exactos del ENUM del SQL, valor, unidad, fecha de evaluación y notas. Ámbito general del taxón o espécimen; no se repite el mismo rasgo dentro del ámbito. |
| `measurement_or_fact` | Variable, valor, unidad y ámbito de evento o espécimen. |
| `party` y tablas puente | Nombres, apellidos, nombre para créditos, ORCID, afiliación y correo; participantes de evento/ocurrencia y responsables taxonómicos. Rol y participante principal cuando corresponde. |
| `multimedia` y `media_party` | Una o varias imágenes iniciales o posteriores, tipo de vista, fotógrafo, licencia, titular y personas acreditadas con su función. Nombre de archivo y MIME se obtienen del archivo; ruta, fechas y control de calidad los gestiona el servidor. Los resultados de calidad recibidos se muestran en el detalle. |
| `scientific_source` | Tipo, título, autores, año y DOI en la ficha de especie. |
| `ethno_source` | Fecha de entrevista, entrevistador, consentimiento y tipo, anonimato, edad por rango, género, ocupación, departamento, municipio, vereda y notas. |
| `ethno_taxon_knowledge` | Conocimiento de los hongos, nombre local, aprendizaje, reconocimiento, lugares, estacionalidad, meses, seguridad, relatos e identidad cultural. |
| `ethno_use` | Categoría, importancia, preparación, afección mencionada, dosificación, contraindicaciones y recomendaciones reportadas. |

Los UUID, auditoría, credenciales, verificación y activación de personas, rutas de archivos y resultados de control de calidad no se solicitan como datos de campo. El formulario no sustituye la administración del servidor.

El diagrama PDF recibido sitúa algunas mediciones en `measurement_or_fact`. Para la morfología se sigue el SQL más específico recibido: `ecological.morphology_fact`, con `taxon_id` o `occurrence_id`. El cliente envía solo uno de esos enlaces por rasgo y deja las medidas ambientales en su entidad independiente. Esta decisión evita mezclar descripciones generales con mediciones de especímenes.

## Experiencia de registro

1. Hallazgo y fotos: taxón opcional, tipo de registro, identificación, sustrato, notas y fotografías.
2. Ubicación: dispositivo como primera opción; coordenadas manuales o mapa; información descriptiva del sitio.
3. Salida: fecha, recolector, protocolo, esfuerzo, notas y participantes.
4. Morfología y medidas: rasgos del espécimen, medidas ambientales y resumen previo al guardado.

Las fotografías se pueden añadir posteriormente desde el hallazgo, su ficha de especie o la galería. Se conserva el vínculo con el hallazgo concreto. Se admiten JPG, PNG y WebP, hasta 10 archivos por operación, con 2 MB por archivo en demo y 10 MB en API. Se comprueba que el archivo decodifique como imagen.

Los nombres científicos, géneros y epítetos se muestran en cursiva en catálogo, fichas, revisión, selectores, mapa, Excel y PDF. CSV es texto plano y no admite formato tipográfico. La presentación sigue el criterio editorial habitual de diferenciar los nombres científicos; el [prefacio del ICN](https://iapt-taxon.org/historic/Preface/P-2018.htm) explica que la tipografía es una convención editorial.

La geolocalización requiere permiso y contexto seguro. No se solicita al abrir el formulario: la persona pulsa «Usar mi ubicación». Se registra precisión e incertidumbre disponibles, se informa de denegación, falta de posición o timeout, y se descartan respuestas tardías al cambiar de modo o abandonar el paso. Ver [documentación de Geolocation](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition).

## Responsabilidad del registro y especies durante el hallazgo

El investigador responsable se toma de la cuenta autenticada. Para investigadores, «Investigador responsable» y «Registrado por» son de solo lectura; antes de guardar también se fuerzan `ownerId` y `recordedBy` desde la sesión, aunque el borrador contenga valores manipulados. Solo el administrador puede seleccionar otra cuenta investigadora. Un hallazgo asignado por administración aparece en los registros del investigador elegido, quien puede editarlo y añadir fotos.

La demostración distingue `ownerId` (cuenta responsable) de `createdById` (cuenta que creó el registro). Editar un registro no modifica su creador original. Se conservan los responsables históricos al editar, aunque su perfil haya cambiado. «Identificado por» mantiene su significado científico de atribución de la identificación taxonómica y no determina la propiedad del registro.

El acceso demo permite elegir Laura Martínez o Diego Ramírez al iniciar sesión como investigador. El selector de cuenta del encabezado permite alternarlas para comprobar vistas propias. Esta simulación no reemplaza autenticación real.

En el primer paso del hallazgo, «Buscar especie registrada» filtra por nombre científico, común, género o familia, sin distinguir mayúsculas o acentos. «Añadir especie nueva» abre el editor completo sobre el borrador actual, comprueba duplicados y selecciona automáticamente la especie creada. Las notas, ubicación, fotografías y demás campos del borrador se conservan. Cancelar la creación de la especie devuelve al hallazgo sin descartarlo.

En API, el contrato de hallazgo envía `owner_id` junto a las entidades. El servidor debe permitir asignarlo a otra cuenta únicamente a administradores y obtener la responsabilidad del token para investigadores. Debe devolver `owner_id` separado de `created_by_id`; el cliente nunca utiliza al creador administrador como propietario implícito del registro. El historial `created_by_id` debe generarlo el servidor a partir del token, no confiar en el cliente.

## Persistencia de demostración

Se usa IndexedDB, base `macromicetos-local`, almacén `datasets`, clave `current`. El mensaje de éxito se muestra después de confirmar la transacción. Esto permite guardar varias fotografías sin depender de la reducida cuota síncrona de `localStorage`.

Los conjuntos antiguos de `localStorage` se leen si no existe un conjunto en IndexedDB. Al guardar pasan al nuevo almacén sin borrar el respaldo antiguo. Se migra el diámetro de los ejemplos antiguos a morfología sin duplicarlo, y se conserva la información restante. El almacenamiento continúa sujeto a la disponibilidad y cuota del navegador; un error mantiene el formulario abierto. No hay sincronización entre equipos.

## Exportaciones

| Descarga | Contenido |
| --- | --- |
| CSV del catálogo | Una fila por taxón filtrado, aunque no tenga hallazgos: taxonomía, notas, cantidad de observaciones y morfología general. |
| CSV de registros | Una fila por hallazgo filtrado: taxonomía, ubicación, evento, identificación, notas, medidas y morfología del espécimen. |
| Excel `.xlsx` | Hojas Especies, Hallazgos y Morfología; cabeceras, filtros, primera fila fija, coordenadas numéricas y nombres científicos en cursiva. |
| Ficha PDF | Taxonomía, rasgos generales, hallazgos, contexto, medidas, fuentes y fotografías con créditos y licencias disponibles. |

CSV y Excel no incluyen imágenes, datos binarios, entrevistas ni correos de participantes. El PDF tampoco contiene entrevistas ni correos. Las celdas CSV se escapan para comillas, separadores, saltos de línea y posibles fórmulas. Las coordenadas numéricas negativas conservan su valor.

Si una fotografía del PDF no se puede cargar, se informa en la ficha y en la interfaz. Las imágenes remotas necesitan estar disponibles con permisos CORS para incorporarse al PDF. Las fotografías locales cargadas se admiten mediante URLs de datos de imágenes rasterizadas, excluyendo SVG y esquemas activos. Los créditos de las imágenes de referencia se conservan.

## Contratos de servidor propuestos

Estas operaciones **no están implementadas en el repositorio**. Sus rutas se configuran expresamente; no son una afirmación de que existan en la API original. Hasta habilitarlas, el modo API conserva los formularios y muestra que el guardado completo no está disponible. El cliente no envía los datos ampliados al endpoint básico, donde podrían ignorarse.

| Variable | Ejemplo de ruta | Método y contenido |
| --- | --- | --- |
| `VITE_RECORD_BUNDLE_PATH` | `/record-bundles/{id}` | PUT multipart: campo `payload` JSON y archivos `file_<media_id>`. |
| `VITE_TAXON_BUNDLE_PATH` | `/taxon-bundles/{id}` | PUT JSON: `taxon`, `morphology`, `sources`, `knowledge`, `participants`. |
| `VITE_MEDIA_BUNDLE_PATH` | `/occurrences/{id}/media-bundle` | PUT multipart: `payload` con ID del hallazgo y metadatos, más archivos `file_<media_id>`. |

`{id}` es obligatorio. El editor genera UUID estables para el borrador, el evento, la ubicación, entrevistas, fuentes y cada foto, y los conserva durante los reintentos. El servidor debe admitir estos IDs como claves idempotentes o devolver un contrato equivalente acordado. Las entidades y campos se adaptan explícitamente en `src/lib/record-contract.mjs`.

El `payload` de hallazgo tiene `location`, `event`, `occurrence`, `morphology`, `measurements`, `participants` y `multimedia`. Cada entrada multimedia lleva un `media_id` estable y los créditos; su archivo usa ese ID en el nombre del campo multipart. No se serializan vistas previas ni archivos dentro de JSON.

La operación de hallazgo debe guardar todo en una transacción, reemplazar los conjuntos de rasgos/medidas/participantes con los enviados y conservar las fotografías existentes. La operación de fotos adicionales añade el lote de forma atómica y no duplica `media_id` al reintentarlo. Los datos se validan antes de confirmar y los archivos se limpian si la transacción falla. Las operaciones de ficha deben hacer lo equivalente con sus colecciones y relaciones; los arrays vacíos representan la retirada deliberada de elementos en la edición.

El ORM recibido no incluye una relación explícita entre `scientific_source` y `taxon_ref`. Antes de implementar el guardado bibliográfico, el backend debe acordar esa asociación y migración. Tampoco el modelo original de taxón declara estado de curaduría o propiedad: el servidor debe exponer `owner_id` y el estado si aplica; no se infieren desde el cliente.

Las respuestas PUT deben devolver la ficha o hallazgo completo guardado, incluidas sus colecciones. Para los hallazgos se admite el objeto compuesto `{occurrence,event,location,morphology,measurements,participants,multimedia}` o el perfil de ocurrencia con `event.location`. Para taxones se admite `{taxon,morphology,sources,knowledge,participants}` o la ficha plana con colecciones. Los GET de fichas, ocurrencias y listados deben conservar esos datos para poder editarlos sin pérdida.

El servidor debe determinar identidad, propiedad y permisos a partir del token; no confiar en IDs ni estados editables. Debe redactar entrevistas y contactos en las respuestas públicas. La pestaña socioecológica solo se muestra a curaduría/administración o al autor de la ficha; esto es control de interfaz y no reemplaza la autorización del servidor.

Roles del ORM: `field_collector` se adapta a investigador, `viewer` y `analyst` a visitante, `curator` a curador y `admin` a administrador. Los datos de identidad se leen desde `party`.
