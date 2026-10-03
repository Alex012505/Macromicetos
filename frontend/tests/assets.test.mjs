import test from 'node:test';
import assert from 'node:assert/strict';
import { publicAssetUrl, normalizeDemoImage } from '../src/lib/assets.mjs';

test('public files resolve within the GitHub Pages project path', () => {
  assert.equal(publicAssetUrl('/images/pleurotus.jpg', '/Macromicetos/'), '/Macromicetos/images/pleurotus.jpg');
  assert.equal(publicAssetUrl('favicon.svg', '/Macromicetos'), '/Macromicetos/favicon.svg');
});
test('public files also resolve at the domain root for local development', () => {
  assert.equal(publicAssetUrl('images/trametes.jpg', '/'), '/images/trametes.jpg');
});
test('stored demo photos migrate without doubling or retaining the old base', () => {
  assert.equal(normalizeDemoImage('/images/pleurotus.jpg', '/Macromicetos/'), '/Macromicetos/images/pleurotus.jpg');
  assert.equal(normalizeDemoImage('/Macromicetos/images/trametes.jpg', '/Macromicetos/'), '/Macromicetos/images/trametes.jpg');
  assert.equal(normalizeDemoImage('/Macromicetos/images/trametes.jpg', '/'), '/images/trametes.jpg');
});
test('uploaded images, external URLs and absent photos remain unchanged', () => {
  for (const image of [undefined, '', 'data:image/png;base64,AAAA', 'https://example.org/images/pleurotus.jpg', '/uploads/example.jpg']) {
    assert.equal(normalizeDemoImage(image, '/Macromicetos/'), image);
  }
});
