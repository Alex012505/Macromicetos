# Macromicetos · Registro académico · Opción 2

Interfaz de investigación de macromicetos de la Orinoquía colombiana. React, TypeScript, Vite, Leaflet y Lucide. Diseño adaptado del wireframe entregado, con una paleta basada en [Programa Orquídeas](https://programaorquideas.minciencias.gov.co/): morado `#34207D`, verde menta `#81F3A6`, blanco `#FFFFFF` y gris. Se utilizan variantes oscuras para textos y tonos claros para superficies; el ámbar y el rojo se reservan para estados de revisión y errores.

## Ejecución

Requisito: Node.js 20.18 o superior. Validado con Node 20.18.0.

El aplicativo completo requiere también el backend y PostgreSQL configurados según el [README principal](../README.md). Para iniciar ambos servicios desde la raíz usa `node scripts/dev.mjs`. Los siguientes comandos arrancan solo la interfaz y se ejecutan dentro de `frontend/`.

```powershell
npm ci
npm run dev
```

Dirección: `http://127.0.0.1:5173/Macromicetos/`. El servidor utiliza un puerto fijo; si está ocupado, detén la instancia anterior antes de iniciar otra.

```powershell
npm run build
npm test
npm run preview
```

`build` comprueba TypeScript y genera `dist/`. `preview` sirve la compilación en el puerto que indica Vite. `dist/` necesita un servidor HTTP; no abras `index.html` directamente desde el explorador de archivos.

## Módulos e interacciones

- Vista general: métricas derivadas de los datos disponibles, últimas observaciones, mapa y accesos.
- Catálogo: búsqueda, filtro por familia, ordenación, tarjetas/lista y paginación.
- Ficha: taxonomía, morfología general y por hallazgo, ecología, geografía, multimedia, bibliografía y socioecología según permisos; rutas compartibles por hash.
- Mapa: Leaflet + OpenStreetMap, filtros por departamento, familia, fechas y verificación.
- Registros: formulario de cuatro pasos con fotografías y ubicación por dispositivo/mapa/coordenadas, creación/edición de ocurrencias, exportación CSV y Excel y consulta por ID en modo API.
- Curaduría: revisión, verificación y solicitud de ajustes con comentario obligatorio.
- Multimedia: galería, ampliación y carga inicial o posterior de varias fotos con tipo, licencia, titular y personas acreditadas.
- Fichas PDF por especie: taxonomía, rasgos, contexto de los hallazgos, bibliografía y fotografías con créditos.
- Ficha editable: taxonomía completa, morfología, responsables, fuentes y entrevistas con consentimiento y usos reportados.
- Usuarios: lectura y actualización de perfiles mediante endpoints autorizados del backend; los usuarios de los datos demo son de solo lectura.
- Autenticación: correo y contraseña para los cuatro perfiles, rol asignado por el servidor y cierre de sesión por expiración o HTTP 401. No hay selector de perfil ni acceso automático.
- Guía: uso de la plataforma, alcance de perfiles, procedencia de datos y créditos. La configuración de FastAPI se gestiona mediante archivos de entorno; no forma parte de las vistas expositivas.

## Demostración y API real

Sin `.env`, la aplicación usa la API real y muestra primero el formulario de acceso. Todos los perfiles, incluido `viewer`, deben autenticarse. El login envía JSON a `/auth/login-json`, la ruta existente en la rama `Backend`; el servidor verifica la contraseña y devuelve un JWT con `sub`, `role` y `exp`. Las cuentas nuevas son `viewer`; los permisos de `analyst`, `curator` y `admin` deben asignarse en el servidor.

El token se conserva solo en memoria. Recargar o cerrar sesión exige autenticarse otra vez. Un token inválido o vencido no abre la aplicación. El cliente consulta `/auth/me`, implementado en el backend, para obtener la cuenta y el rol vigentes.

Para trabajar con datos ilustrativos, se puede definir explícitamente `VITE_DATA_MODE=demo`. Esto cambia los datos, pero sigue exigiendo una cuenta real del backend y no permite simular identidades o elevar el rol desde el navegador.

Las observaciones, coordenadas, personas, fechas, medidas y estados son ficticios. Las fotografías descargadas son referencias de especies; no evidencian ocurrencias en la región. Los cambios se guardan en IndexedDB, únicamente en este navegador. Los datos antiguos de `localStorage` se migran al guardar. El almacenamiento es limitado: el demo acepta imágenes de hasta 2 MB y muestra errores si no puede guardarlas. El modo API nunca carga los ejemplos como sustituto ante errores.

Para usar FastAPI:

```powershell
Copy-Item '.env.example' '.env'
```

Edita el archivo:

```dotenv
VITE_DATA_MODE=api
VITE_API_BASE_URL=/api
API_PROXY_TARGET=http://127.0.0.1:8000
VITE_LOGIN_PATH=/auth/login-json
```

Reinicia Vite. Si las rutas del backend incluyen `/api/v1`, usa `VITE_API_BASE_URL=/api/api/v1`: el proxy elimina solo el primer `/api`. En producción configura una URL HTTPS absoluta o un proxy de mismo origen en el servidor que entrega `dist/`; el proxy de Vite solo sirve para desarrollo.

El backend incluido implementa el login, perfil, listado de ocurrencias, curaduría, usuarios y guardado completo de fichas, hallazgos y fotografías. Las rutas predeterminadas del frontend ya coinciden con esos endpoints. No existe renovación de tokens; la sesión finaliza al expirar. Si conservas un `.env` antiguo con rutas vacías, actualízalo desde `.env.example`. Consulta [INTEGRACION_FASTAPI.md](docs/INTEGRACION_FASTAPI.md) y [Backend/README.md](../Backend/README.md).

## Estructura

```text
frontend/
  public/                 favicon y fotografías locales
  src/
    App.tsx               navegación, permisos y vistas principales
    types.ts              modelos del frontend
    components/
      UI.tsx              estados, fotos y diálogo accesible
      Forms.tsx           autenticación
      RecordForm.tsx      hallazgo, fotos, ubicación, evento y medidas
      TaxonForm.tsx       ficha, bibliografía y entrevistas
      UploadForm.tsx      fotos adicionales y créditos
      SpeciesDetail.tsx   ficha de especie
      OccurrenceMap.tsx   mapa y marcadores
      UserManagement.tsx usuarios y asignación de perfiles
    data/demo.ts          ejemplos y almacenamiento local
    lib/api.ts            adaptador REST y configuración
    lib/http.mjs          transporte, tokens, errores y refresco
    lib/permissions.mjs   alcance de los perfiles y propiedad de registros
    styles.css            tokens, estilos y adaptación por tamaño
  tests/http.test.mjs      pruebas de contrato del transporte
  tests/permissions.test.mjs pruebas de acceso por perfil
  docs/                   entrega, integración y validación
```

## Accesibilidad y recursos externos

Controles semánticos, textos alternativos, foco visible, diálogo nativo con teclado, pestañas accesibles, navegación móvil y respeto a movimiento reducido. El mapa necesita internet para sus teselas; si fallan, los marcadores se mantienen y se informa del problema. Google Fonts necesita internet; la interfaz tiene fuentes del sistema de respaldo. Las dos fotografías y el favicon son locales.

En modo API, los tokens viven en memoria y se pierden al recargar la página. El servidor debe validar todos los permisos; ocultar controles en la interfaz no reemplaza la autorización del backend. No se guardan contraseñas ni tokens reales en `localStorage`.

Consulta la [matriz de perfiles y vistas](docs/PERFILES_Y_VISTAS.md) para conocer el alcance de visitantes, investigadores, curadores y administradores.
