# Perfiles, vistas y acciones

La aplicación es un registro académico de macromicetos. La identidad del grupo presente en las referencias originales no se utiliza como marca de la plataforma.

## Matriz de alcance

| Vista o acción | Visitante | Investigador | Curador | Administrador |
| --- | --- | --- | --- | --- |
| Dashboard de consulta | Sí | Sí, con métricas propias | Sí, con cola pendiente | Sí |
| Catálogo y búsqueda | Consulta | Consulta y alta de especie | Consulta | Consulta y alta de especie |
| Ficha, mapa y galería | Consulta | Consulta | Consulta | Consulta |
| Nuevo registro de campo | No | Sí | No | Sí |
| Editar observación | No | Solo propia | No | Todas |
| Vincular fotografías | No | Solo a sus observaciones | No | A cualquier observación |
| Registros de campo | No | Sus registros | No | Todos los registros |
| Curaduría y verificación | No | No | Sí | Sí |
| Solicitar ajustes | No | No | Sí, con comentario | Sí, con comentario |
| Usuarios y roles | No | No | No | Sí |


## Vistas de inicio

- Visitante: consulta de especies, registros disponibles, fotografías y mapa. No tiene acceso directo de escritura.
- Investigador: datos propios, pendientes propios, nuevo hallazgo y sección de sus registros. Otras observaciones siguen siendo consultables desde catálogo y mapa.
- Curador: pendientes de revisión y acceso directo a curaduría. No crea ni edita observaciones de campo.
- Administrador: visión global, registro, curaduría, usuarios y roles.

La restricción de edición a registros propios concreta el alcance del investigador para esta implementación. El wireframe indica registro/edición para investigador y administrador, sin definir propiedad de registros; por ello se adoptó el mínimo privilegio y se explicita aquí para que el equipo pueda confirmarlo.

## Identificación de propiedad

Cada observación necesita `owner_id`, `created_by_id` o `user_id` en la respuesta del backend para identificar al propietario. El investigador solo puede editar si este identificador coincide con el usuario autenticado. El campo de texto `identified_by` no se usa como autorización: dos personas podrían compartir nombre.

La propiedad de un registro nuevo debe asignarla FastAPI a partir de la sesión autenticada. El frontend no manda un rol ni un propietario elegible por el usuario en el payload de creación. Si el contrato no entrega propietario, la interfaz no ofrece edición al investigador para ese registro. El administrador conserva edición global.

## Demostración

El selector de perfiles simula una sesión por rol para revisar sus vistas; no es un mecanismo real de autenticación ni de elevación de privilegios. Se utilizan las cuentas ficticias Laura Martínez (investigador), Andrés Rojas (curador), Camila Torres (administrador) y un visitante académico. Las observaciones de ejemplo tienen propietarios asociados.

El módulo de usuarios permite cambiar roles en la demostración. La interfaz evita quitar el último administrador. Las operaciones reales de edición se habilitan solo al configurar `VITE_USER_UPDATE_PATH`; FastAPI debe aplicar la misma protección.

## Validación obligatoria del servidor

La interfaz oculta controles, restringe rutas directas y revisa permisos antes de guardar. Estas medidas mejoran la experiencia; la seguridad efectiva depende de que FastAPI compruebe identidad, rol y propiedad en cada endpoint.

La versión expositiva no incluye un módulo de conexión e integración. La configuración técnica del backend permanece en el código, la documentación y los archivos de entorno.
