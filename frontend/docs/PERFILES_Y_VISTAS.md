# Perfiles, vistas y acciones

La aplicación es un registro académico de macromicetos. La identidad del grupo presente en las referencias originales no se utiliza como marca de la plataforma.

## Matriz de alcance

Los valores de rol son `viewer` (Visitante), `analyst` (Investigador), `curator` (Curador) y `admin` (Administrador). Se usan sin traducción en tipos, permisos, selectores y API. Al cargar datos demo antiguos, se migran los roles anteriores conservando las cuentas y sus registros.

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

La aplicación exige autenticación de backend incluso al configurar datos de demostración. No existe selector de perfiles ni de cuentas. Las personas y observaciones demo siguen siendo datos ilustrativos; no son cuentas que permitan iniciar sesión.

Los usuarios de demostración son de solo lectura. Las operaciones reales de edición se habilitan al configurar `VITE_USER_UPDATE_PATH`; FastAPI debe autorizar al administrador y proteger la continuidad de al menos una cuenta administradora. Si se modifica el rol de la cuenta en uso, se cierra la sesión para obtener un token nuevo.

## Validación obligatoria del servidor

La interfaz oculta controles, restringe rutas directas y revisa permisos antes de guardar. Estas medidas mejoran la experiencia; la seguridad efectiva depende de que FastAPI compruebe identidad, rol y propiedad en cada endpoint.

La versión expositiva no incluye un módulo de conexión e integración. La configuración técnica del backend permanece en el código, la documentación y los archivos de entorno.


## Responsabilidad desde la sesión y catálogo durante el registro

El investigador registra siempre para su propia cuenta autenticada. «Investigador responsable» y «Registrado por» son campos de solo lectura; la asignación se valida también al guardar. Solo el administrador puede seleccionar otro investigador. El registro asignado pasa a la vista propia del investigador destinatario y conserva por separado quién lo creó.

La separación de registros se comprueba iniciando sesión con cuentas reales distintas del backend. El rol y la identidad proceden de la autenticación del servidor; no se pueden seleccionar desde el encabezado.

Investigadores y administradores pueden buscar especies ya registradas y crear una especie nueva desde el primer paso del hallazgo. La creación conserva el borrador y selecciona la nueva especie automáticamente.
