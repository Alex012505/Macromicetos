# Verificación del registro ampliado

Fecha: 17 de octubre de 2026. Windows, Node 20.18.0 y npm 10.8.2. Se conserva a continuación el informe histórico de la entrega anterior.

## Resultados actuales

- `npm test`: **38 pruebas correctas**, incluidas adaptación al ORM, roles, morfología controlada, coordenadas, geolocalización simulada, exportación y migración.
- `npm run build`: TypeScript y compilación de producción correctos. Vite informa de paquetes de más de 500 kB; Excel y PDF se cargan bajo demanda. Es una advertencia de tamaño, no un fallo de compilación.
- Dependencias: la instalación final informa **0 vulnerabilidades**. Se actualizó `uuid` indirecto de ExcelJS mediante un override compatible con CommonJS.
- `git diff --check`: sin errores de espacios.

## Flujos recorridos en navegador

| Comprobación | Resultado |
| --- | --- |
| Registro con foto inicial | Guardado y consulta correctos. |
| Mapa de ubicación | Pulsar un punto actualiza latitud y longitud. |
| Coordenadas incompletas | Error visible; bloquea el avance. |
| Latitud cero | Se conserva como número válido, junto a longitud negativa. |
| Diámetro sin unidad | Solicita cm o mm. |
| Datos entre pasos | Se conservan fotos, campos y medidas al avanzar y retroceder. |
| Fotos posteriores | Se añadió una segunda foto al mismo hallazgo; ambas permanecen después de recargar. |
| Edición de hallazgo | Conserva dos fotografías, morfología y medidas ambientales. |
| Hallazgo sin identificar, sin coordenadas | Se guarda y abre su propio detalle, con posibilidad de completar la identificación después. |
| Ficha taxonómica ampliada | Guarda rasgos generales, responsable, bibliografía, entrevista y uso reportado. |
| Entrevista sin consentimiento | Bloquea el guardado con mensaje. |
| Visitante | No ve edición ni pestaña socioecológica. |
| Investigador por URL directa de curaduría | Acceso denegado. |
| Curaduría | Bloquea solicitud de ajustes sin comentario; guarda una solicitud con comentario. |
| Formulario móvil, viewport 390 × 844 | Página y diálogo sin desbordamiento horizontal; pasos en dos columnas. |
| Ficha móvil | Sin desbordamiento global; pestañas desplazables. |
| Cursiva | Verificada en el estilo calculado del nombre científico, en el archivo XLSX y en las fuentes del PDF. |
| Fuente sin variante cursiva | Se habilitó la síntesis de estilo exclusivamente para nombres científicos y énfasis; verificada visualmente. |
| Cambio rápido de mapas | Se probó ampliar y cerrar el mapa y abandonar el selector de ubicación: sin nuevos errores de consola tras detener las animaciones antes del desmontaje. |

La prueba de varias fotos reveló el límite de `localStorage` y la descarga PDF rechazaba las imágenes cargadas localmente. Se corrigieron con persistencia en IndexedDB y soporte explícito para URLs de datos de imágenes rasterizadas, y se repitieron ambas pruebas con archivos reales.

## Descargas verificadas

Se descargaron archivos desde los botones de la aplicación y se inspeccionó su contenido:

- CSV del catálogo: una especie cuando se descarga desde su ficha; sin datos de imagen.
- CSV de hallazgos filtrados: una sola fila coincidente; conserva coordenadas `0, -73.64`, morfología y medidas.
- XLSX: abre como un paquete Excel válido con tres hojas, coordenadas numéricas, filtros y cursiva. No contiene `xl/media`, imágenes ni fórmulas generadas desde texto.
- PDF: cuatro páginas con datos, fotografías cargadas y de referencia, créditos y nombres científicos en cursiva. Se renderizaron y revisaron las páginas; sin superposición ni recortes. Los objetos de imagen repetidos se reutilizan.
- Se añadieron marcadores ficticios a una entrevista y un correo de participante y se comprobó que **no aparecen en CSV, XLSX ni PDF**.

Evidencias actuales:

- `evidencias/2026-10-17/formulario-movil.png`.
- `evidencias/2026-10-17/ficha-movil.png`.
- `evidencias/2026-10-17/ficha-escritorio.png`.

## Límites de la comprobación

Los recorridos de navegador son pruebas manuales asistidas, no una suite E2E automática. Los datos utilizados son ficticios y se guardaron en la demostración local. Las pruebas de geolocalización usan respuestas simuladas para posición, precisión, altitud, permiso denegado, indisponibilidad y timeout; no se capturó la ubicación física de la persona.

No hay backend implementado en este repositorio. No se verificaron autenticación, guardado ni permisos contra PostgreSQL/FastAPI reales. Los contratos ampliados y la cobertura del modelo están en [REGISTRO_COMPLETO.md](REGISTRO_COMPLETO.md). La autorización y la redacción de datos sensibles deben aplicarse en el servidor.

---

# Validación de la entrega

Fecha: 3 de octubre de 2026. Entorno: Windows, Node 20.18.0, npm 10.8.2. Backend FastAPI no disponible.

## Compilación y pruebas

`npm run build`: comprobación TypeScript y compilación de producción con Vite, correctas.

`npm test`: 14 pruebas del transporte HTTP con respuestas simuladas y 4 pruebas de permisos por perfil:

1. URL base, cuerpo JSON y token Bearer.
2. Login público sin token anterior.
3. Mensajes de validación FastAPI 422.
4. FormData sin Content-Type manual.
5. Error de red sin sustitución por datos de ejemplo.
6. Rechazo de respuestas HTML.
7. Operaciones 204 sin contenido.
8. Cierre de sesión ante 401 sin refresco configurado.
9. Un único refresco para 401 simultáneos.
10. Refresco fallido sin bucles.
11. Timeout y cancelación de la petición.
12. Cancelación solicitada por el llamador.
13. Normalización de listas y rechazo de contratos desconocidos.
14. Rechazo de URLs de imagen con esquemas activos.

Permisos: mínimo privilegio de visitante/rol desconocido, edición propia del investigador, separación de funciones del curador y administración exclusiva de usuarios y rechazo de rutas retiradas o desconocidas.

## Comprobaciones en navegador

| Flujo | Resultado |
| --- | --- |
| Dashboard de escritorio, 1440 × 1000 | Navegación, métricas, fotografías y mapa visibles. |
| Dashboard móvil, 390 × 844 | Sin desbordamiento horizontal de la página. |
| Búsqueda de Trametes | Un resultado; ficha navegable. |
| Ficha, sección Morfología | Medidas de demostración visibles. |
| Nuevo hallazgo | Formulario por pasos; guardado y aparición en cola de revisión. |
| Solicitar ajustes sin comentario | Mensaje de validación; no guarda la decisión. |
| Solicitar ajustes con comentario | Estado actualizado y notificación. |
| Rol visitante | Oculta módulos de escritura y curaduría. |
| URL directa de curaduría como visitante | Deniega la interfaz restringida. |
| Menú móvil | Apertura, selección de ruta y cierre correctos. |
| Mapa: Meta + solo verificados | Dos observaciones y dos marcadores en la demostración inicial. |
| Visor móvil | Ajustado a 380 px de altura; sin desbordamiento global. Las tablas anchas se desplazan dentro de su contenedor. |
| Fotografías locales | Ambas cargan correctamente. |
| Módulo de conexión retirado | No aparece en la navegación ni se renderiza con su antigua URL. |
| Acentos morados | Avatar, nota académica, iconos y pestañas; verde bosque como color principal. |
| Identidad académica | Sin marcas Virtus en el contenido visible de la aplicación. |
| Investigador | Cuatro observaciones propias; no ve curaduría ni usuarios. |
| Visitante | Acción de consulta, sin botón de nuevo registro. |
| Curador | Acceso a revisión y decisiones, sin creación ni módulo de registros de campo. |
| Último administrador | Impide cambiar a otro perfil la única cuenta administradora. |

Las verificaciones de UI fueron recorridas directamente en el navegador; no son una suite E2E automatizada. No se probaron login, registro, carga ni persistencia contra una base de datos real.

## Evidencias

- `evidencias/dashboard.png`: vista de escritorio.
- `evidencias/mobile.png`: vista de teléfono.

El alcance de cada perfil y las obligaciones de autorización del servidor están en `PERFILES_Y_VISTAS.md`.

La cobertura responsive revisa los tamaños indicados; no constituye una auditoría completa de accesibilidad. El mapa y las fuentes necesitan red externa, con aviso y fuentes de respaldo respectivamente.
