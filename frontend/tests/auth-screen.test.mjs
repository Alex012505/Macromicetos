import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

for (const mode of ['api', 'demo']) {
  test(`the ${mode} build shows a credential form before any profile or protected page`, async () => {
    const compiled = await build({ entryPoints: ['src/App.tsx'], bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false,
      define: { 'import.meta.env': JSON.stringify({ VITE_DATA_MODE: mode, BASE_URL: '/Macromicetos/' }) },
      plugins: [{ name: 'leaflet-without-dom', setup(build) {
        build.onResolve({ filter: /^leaflet(?:\/.*)?$/ }, () => ({ path: 'leaflet', namespace: 'test' }));
        build.onLoad({ filter: /.*/, namespace: 'test' }, () => ({ contents: 'export default {};' }));
      } }] });
    const module = { exports: {} };
    new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
    const previousWindow = globalThis.window;
    globalThis.window = { location: { hash: '#/usuarios' } };
    try {
      const html = renderToStaticMarkup(React.createElement(module.exports.default));
      assert.match(html, /name="email"/); assert.match(html, /name="password"/);
      assert.match(html, /Iniciar sesión/);
      assert.doesNotMatch(html, /<select|Rol de demostración|Entrar a la demostración|Camila Torres|Usuarios y permisos|Cerrar sesión/);
    } finally { if (previousWindow === undefined) delete globalThis.window; else globalThis.window = previousWindow; }
  });
}
