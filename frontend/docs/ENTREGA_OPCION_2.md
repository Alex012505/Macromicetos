# Entrega · Opción 2: Frontend e integración

Fecha: 3 de octubre de 2026. Proyecto: Registro académico de macromicetos de la Orinoquía colombiana.

## Objetivo de la entrega

Implementar las interfaces principales a partir del wireframe, mejorar su apariencia y dejar una conexión lógica con la API FastAPI del equipo. El usuario confirmó verde bosque, blanco y ámbar, y posteriormente añadió morado sutil, y aclaró que el backend todavía no está disponible.

## Correspondencia con las tres tareas

| Tarea | Resultado | Estado |
| --- | --- | --- |
| Configuración inicial y maquetación | Aplicación React/TypeScript/Vite organizada, navegación por roles, dashboard, catálogo, mapa, ficha, multimedia, registro y curaduría. | Implementado y compilado. |
| Ajustar colores y mejorar interfaces | Paleta aprobada centralizada, componentes consistentes, tipografía, fotografía de referencia, estados visuales, interacción y adaptación a escritorio/móvil. | Implementado; revisado en navegador. |
| Conectar frontend con backend | Cliente HTTP, adaptadores de modelos, login/registro, Bearer, refresco configurable, carga multipart y configuración de entorno/proxy. Contratos faltantes documentados. | Preparado; conexión a FastAPI real pendiente. |

## Mejoras sobre el wireframe

- Se conserva la navegación y sus límites por rol.
- Las barras de contenido del wireframe se convierten en fichas, tablas, filtros y estados con significado.
- Las métricas se calculan con los datos disponibles, sin cifras fijas presentadas como datos en vivo.
- El catálogo permite búsqueda, filtrado, ordenación, tarjetas/lista y páginas.
- El mapa usa coordenadas y cartografía reales; en demo los puntos están identificados como ficticios.
- La ficha concentra información en cinco secciones y enlaza observaciones editables.
- El registro se divide en pasos, con validaciones y revisión inicial en demo.
- La curaduría verifica registros o solicita ajustes explicados.
- Los estados vacíos, errores de red, carga, notificaciones y permisos se comunican en la interfaz.
- Los diálogos soportan teclado y foco, las imágenes tienen texto alternativo y el diseño considera movimiento reducido.

## Límites explícitos

No se implementó base de datos ni servidor FastAPI porque corresponde a opción 1. No se afirma integración extremo a extremo. Las extensiones de curaduría, usuarios, eventos y lista de ocurrencias necesitan un acuerdo de contrato. La gestión de usuarios permite editar roles en demostración; la operación real queda deshabilitada hasta configurar el contrato del backend. No hay sincronización GBIF, streaming ni clasificación por IA en esta entrega.

## Archivos para el equipo

- `README.md`: instalación y ejecución del frontend.
- `.env.example`: URL y activación de modo API.
- `docs/INTEGRACION_FASTAPI.md`: endpoints existentes, extensiones propuestas, payloads, CORS y pendientes.
- `docs/VALIDACION.md`: evidencia de compilación, pruebas y recorrido de interfaz.
- `docs/PERFILES_Y_VISTAS.md`: matriz de permisos, vistas por perfil y reglas de propiedad.
- `src/lib/api.ts`: único punto de adaptación del contrato del servidor.
- `src/styles.css`: variables de color y diseño.

## Guion breve de demostración

1. Mostrar la vista general y explicar que son datos ilustrativos.
2. Buscar Trametes en catálogo, abrir su ficha y recorrer las secciones.
3. Filtrar el mapa por departamento y verificación.
4. Crear un hallazgo como investigador y encontrarlo en la cola de curaduría.
5. Solicitar ajustes con comentario o verificar desde el rol curador.
6. Cambiar a visitante y mostrar el acceso de solo lectura.
7. Revisar la administración de usuarios y explicar el alcance de cada perfil.

La versión expositiva no muestra controles técnicos de conexión. El contrato y la configuración de FastAPI se conservan en archivos para el equipo de desarrollo.
