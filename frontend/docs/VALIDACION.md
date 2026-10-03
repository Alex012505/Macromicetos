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
