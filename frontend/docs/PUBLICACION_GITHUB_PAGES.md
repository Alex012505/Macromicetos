# Publicación del modelo expositivo en GitHub Pages

## Causa del 404

La ejecución `37104679301` del commit `5c556c8` instaló dependencias y compiló correctamente, pero falló en `Configure Pages`: GitHub respondió `Not Found` al consultar el sitio. El artefacto no se subió y el despliegue fue omitido. Crear el workflow no habilita automáticamente Pages.

## Ajuste necesario en GitHub

1. Abrir el repositorio `Alex012505/Macromicetos`.
2. Ir a **Settings → Pages → Build and deployment → Source**.
3. Seleccionar **GitHub Actions**. No elegir la carpeta `docs`: contiene la referencia de la API, no la aplicación compilada.
4. Guardar o esperar que GitHub aplique la selección.
5. Subir los archivos corregidos a `main`. Esto ejecuta el workflow. También se puede iniciar desde **Actions → Deploy frontend to GitHub Pages → Run workflow**.
6. Comprobar que los trabajos `build` y `Deploy` terminen correctamente antes de abrir el sitio.

Dirección esperada: **https://alex012505.github.io/Macromicetos/**.

## Archivos corregidos

- `frontend/src/lib/assets.mjs`: construye rutas según `import.meta.env.BASE_URL`.
- `frontend/src/data/demo.ts`: utiliza la base de Vite para las fotos y repara rutas antiguas de la demostración almacenada sin borrar registros ni fotos añadidas.
- `frontend/tests/assets.test.mjs`: comprueba rutas en localhost y Pages, migración y preservación de imágenes externas/subidas.
- `frontend/package.json`: ejecuta también las pruebas de recursos.
- `.github/workflows/deploy-pages.yml`: comprueba Pages al inicio, utiliza Node 24 y acciones checkout/setup-node v7, compila explícitamente en demo y ejecuta las pruebas antes de publicar.

`base: '/Macromicetos/'` ya era correcto y se conserva. Las rutas del favicon en HTML y del fondo fotográfico en CSS se ajustan durante la compilación de Vite. La navegación utiliza hash, por ejemplo `/Macromicetos/#/especies`, por lo que no necesita redirecciones del servidor para esas vistas.

## Instalación y verificación local

Desde la raíz del repositorio:

```powershell
cd frontend
npm ci
npm test
npm run build
npm run preview
```

En el servidor de preview, abrir `/Macromicetos/` en el puerto indicado. `frontend/dist` se genera localmente y no necesita añadirse a Git: el workflow compila y carga ese directorio.

## Alcance del hosting

GitHub Pages sirve el frontend estático. No ejecuta FastAPI ni PostgreSQL. La exposición funciona en modo demostración y guarda los cambios únicamente en ese navegador. Conectar una API real requiere desplegarla por separado y configurar HTTPS, CORS y las variables públicas del frontend.

La compilación local no confirma una publicación remota. La confirmación del hosting es una ejecución de despliegue exitosa y la revisión de la URL pública.

## Referencias

- [Configuración de GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
- [Despliegue de Vite en GitHub Pages](https://vite.dev/guide/static-deploy.html#github-pages).
- [Recursos estáticos de Vite](https://vite.dev/guide/assets.html).

## Validación realizada el 3 de octubre de 2026

- 22 pruebas correctas y compilación TypeScript/Vite correcta.
- Vista previa de producción en /Macromicetos/: fotografías de Pleurotus y Trametes cargadas; navegación al catálogo mediante hash correcta.
- Favicon, JavaScript, CSS y fotografía del encabezado incluyen el prefijo /Macromicetos/ en la compilación.
- No se activó Pages ni se publicó un nuevo commit remoto en esta intervención.
