import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const compiled = await build({ entryPoints: ['src/components/ScientificFields.tsx'], bundle: true, platform: 'node', format: 'cjs', packages: 'external', write: false });
const module = { exports: {} };
new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
const { Fields } = module.exports;

test('populated textareas retain a stable accessible label independent of their saved content', () => {
  const html = renderToStaticMarkup(React.createElement(Fields, {
    fields: [{ key: 'remarks', label: 'Notas del hallazgo', type: 'textarea' }],
    value: { remarks: 'REGISTRO ARTIFICIAL guardado anteriormente' }, onChange() {},
  }));
  assert.match(html, /<textarea[^>]*aria-label="Notas del hallazgo"/);
  assert.match(html, /REGISTRO ARTIFICIAL guardado anteriormente/);
});

test('select accessible names do not include the selected option or the list of options', () => {
  const html = renderToStaticMarkup(React.createElement(Fields, {
    fields: [{ key: 'role', label: 'Perfil académico', options: [['viewer', 'Visitante'], ['curator', 'Curador']] }],
    value: { role: 'curator' }, onChange() {},
  }));
  assert.match(html, /<select[^>]*aria-label="Perfil académico"/);
  assert.match(html, /<option value="curator" selected="">Curador<\/option>/);
});
