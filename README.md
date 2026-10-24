# Macromicetos

Aplicativo para registrar, consultar y revisar hallazgos de macromicetos. Usa React, FastAPI y PostgreSQL.

## 1. Abrir el programa

En PowerShell:

```powershell
cd E:\Macromicetos
node scripts/dev.mjs
```

Abre [Macromicetos](http://127.0.0.1:5173/Macromicetos/) e inicia sesión.

Deja la consola abierta mientras lo usas. Para detenerlo, pulsa **Ctrl+C**. Si ya está funcionando, abre el enlace sin ejecutar otra instancia.

## 2. Crear usuarios y asignarles un perfil

Cada persona debe tener su propia cuenta:

1. En la pantalla de acceso, pulsa **Crear una cuenta de visitante**.
2. Completa nombre, apellido, correo y contraseña.
3. Entra con tu cuenta **administradora** y abre **Gestión de usuarios**.
4. Busca la cuenta nueva, pulsa **Editar rol**, elige el perfil y pulsa **Guardar perfil**.
5. La persona debe iniciar sesión nuevamente para usar sus nuevos permisos.

Todas las cuentas nuevas empiezan como visitantes. Solo un administrador puede cambiar su perfil.

| Perfil que muestra la web | Nombre interno | Qué puede hacer |
| --- | --- | --- |
| Visitante | `viewer` | Consultar catálogo, fichas, mapa y fotografías. |
| Investigador | `analyst` | Crear fichas y hallazgos; editar sus propios registros. |
| Curador | `curator` | Revisar hallazgos, verificarlos o solicitar ajustes. |
| Administrador | `admin` | Gestionar registros, usuarios y perfiles. |

### Si todavía no tienes un administrador

Desde la raíz del proyecto, reemplaza el correo y el nombre:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/manage.py create-admin --email "tu@correo.com" --first-name "Tu nombre"
```

La consola pedirá una contraseña de al menos ocho caracteres y su confirmación. No se ven caracteres al escribirla; es normal.

Si ese correo **ya está registrado**, usa este comando en lugar de crear otra cuenta:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/manage.py set-role --email "tu@correo.com" --role admin
```

También puedes asignar `analyst`, `curator` o `viewer` con el mismo comando. El correo debe pertenecer a una cuenta existente. No se permite retirar el rol al último administrador.

## 3. Probar con datos artificiales

Los hallazgos **PRUEBA-WEB-01** y **PRUEBA-WEB-02** se reservan para pruebas. Están marcados como artificiales, usan una ficha ficticia llamada *Prueba artificialis* y fotografías ilustrativas. **No son datos científicos ni evidencia de especies en la región.**

Las pruebas web crean tres cuentas ficticias: visitante, investigador y curador. Sus correos y contraseñas se guardan únicamente en tu equipo, en `Backend/data/web-test-accounts.json`. Puedes usarlas para recorrer los perfiles. El administrador temporal de la prueba se elimina al terminar.

Para probar el flujo:

1. Entra como investigador y abre **Registros de campo**.
2. Crea o edita un hallazgo y añade una fotografía.
3. Entra como curador y abre **Curaduría**.
4. Verifica el hallazgo o solicita ajustes con un comentario.
5. Entra como visitante y comprueba que puede consultar, pero no modificar.

## 4. Comprobar la base de datos

Abre [Estado del backend](http://127.0.0.1:8000/health). Debe responder:

```json
{"status":"ok","database":"postgresql"}
```

Para comprobar también el nombre de la base, las tablas y el usuario de conexión:

```powershell
.\Backend\.venv\Scripts\python.exe Backend/manage.py check-db
```

Los datos están en PostgreSQL; las fotos, en `Backend/data/images/`. Se conservan al reiniciar. La conexión privada está en `Backend/.env`. No compartas ese archivo ni la carpeta `Backend/data/`.

## 5. Ejecutar las pruebas

Desde la raíz, en otra consola:

```powershell
npm --prefix frontend test
.\Backend\.venv\Scripts\python.exe Backend/tests/check_postgres.py
npm --prefix frontend run test:web:local
npm --prefix frontend run build
```

- `test`: comprueba el código del frontend.
- `check_postgres.py`: pide la contraseña de PostgreSQL y usa bases temporales, sin cambiar los datos del aplicativo.
- `test:web:local`: necesita el aplicativo iniciado y Chrome instalado. Prueba la web real y **crea o reutiliza las cuentas ficticias y los dos hallazgos artificiales en tu base local**. No usar en producción.
- `build`: comprueba TypeScript y genera el frontend para publicación.

## Instalación en otro equipo y documentación técnica

Consulta [la guía del backend](Backend/README.md) para instalar dependencias y configurar PostgreSQL. La configuración inicial se realiza una sola vez; no repitas `setup_postgres.py` para arrancar el programa.

- [Frontend](frontend/README.md).
- [Contrato de integración](frontend/docs/INTEGRACION_FASTAPI.md).
- [Perfiles y permisos](frontend/docs/PERFILES_Y_VISTAS.md).

GitHub Pages aloja solo el frontend: el backend y PostgreSQL necesitan su propio servidor.
