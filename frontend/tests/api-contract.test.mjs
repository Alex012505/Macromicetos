import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';

const compiled = await build({ entryPoints: ['src/lib/api.ts'], bundle: true, platform: 'node', format: 'esm', write: false, define: { 'import.meta.env': JSON.stringify({ VITE_DATA_MODE: 'api' }) } });
const { normalizeTaxon, normalizeOccurrence, normalizeUser, api, http, config } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString('base64')}`);

test('ORM names, bibliography, knowledge, false boolean values, and IDs survive normalization', () => {
  const taxon = normalizeTaxon({ taxon: { taxon_id: 't', scientific_name: 'Pleurotus ostreatus', class: 'Agaricomycetes', taxon_remarks: 'Nota', specific_epithet: 'ostreatus' }, sources: [{ source_id: 's', source_type: 'book', title: 'Manual', year: 2026 }], knowledge: [{ source: { ethno_source_id: 'source', interview_date: '2026-10-17T12:00:00-05:00', consent_given: false, anonymity_level: 'anonymous' }, knowledge: { knowledge_id: 'knowledge', knows_fungi: false }, uses: [{ use_id: 'u', use_category: 'cultural' }] }] });
  assert.equal(taxon.id, 't'); assert.equal(taxon.remarks, 'Nota'); assert.equal(taxon.sources[0].sourceType, 'book');
  assert.equal(taxon.knowledge[0].id, 'source'); assert.equal(taxon.knowledge[0].knowledgeId, 'knowledge');
  assert.equal(taxon.knowledge[0].consentGiven, false); assert.equal(taxon.knowledge[0].knowsFungi, false);
});
test('full occurrence preserves geography, morphology, photo credits and separate observation/identification dates', () => {
  const o = normalizeOccurrence({ occurrence: { occurrence_id: 'o', taxon_id: null, recorded_by: 'Recorder', date_identified: null }, event: { event_id: 'e', recorded_by: 'Recorder', event_date: '2026-10-17', location: { location_id: 'l', decimal_latitude: '0', decimal_longitude: '-73', coordinate_uncertainty_m: '0', municipality: 'Sitio', elevation_m: '500' } }, morphology: [{ measurement_type: 'color_pie', measurement_value: 'Blanco' }], multimedia: [{ media_id: 'm', source_url: 'https://example.org/photo.jpg', photo_type: 'stipe', qc_passed: false, credits: [{ party: { party_id: 'p', given_name: 'Ana', display_name: 'Ana' }, credit_role: 'photographer', is_primary: true }] }] });
  assert.equal(o.lat, 0); assert.equal(o.uncertaintyM, 0); assert.equal(o.elevationM, 500);
  assert.equal(o.author, ''); assert.equal(o.date, ''); assert.equal(o.eventDate, '2026-10-17');
  assert.equal(o.morphology[0].type, 'color_pie'); assert.equal(o.photos[0].qcPassed, false);
  assert.equal(o.photos[0].credits[0].displayName, 'Ana'); assert.equal(o.photos[0].credits[0].role, 'photographer');
});
test('canonical roles survive normalization and unknown profiles default to viewer', () => {
  assert.deepEqual(normalizeUser({ user_web_id: 'u', role: 'analyst', email: 'a@example.org', party: { display_name: 'Ana' } }), { id: 'u', name: 'Ana', email: 'a@example.org', role: 'analyst' });
  for (const role of ['viewer', 'analyst', 'curator', 'admin']) {
    assert.equal(normalizeUser({ role }).role, role);
    assert.equal(normalizeUser({ user_role: role }).role, role);
  }
  for (const role of [undefined, 'unknown-admin', 'field_collector', 'researcher', 'readonly_user']) assert.equal(normalizeUser({ role }).role, 'viewer');
});
test('missing full-record server contract fails before issuing a basic request that would drop fields', async () => {
  await assert.rejects(api.saveOccurrence({ id: 'o' }), /guardado completo/);
  for (const field of ['morphology', 'sources', 'knowledge', 'participants']) {
    await assert.rejects(api.createTaxon({ id: 't', [field]: [{}] }), /guardado completo/);
  }
});
test('basic taxon creation sends flat snake_case JSON to POST /taxa and uses the server ID', async t => {
  t.mock.method(http, 'request', async (path, options) => {
    assert.equal(path, '/taxa'); assert.equal(options.method, 'POST');
    assert.deepEqual(options.body, {
      scientific_name: 'Pleurotus ostreatus', common_name_es: 'Orellana', taxon_rank: 'species',
      kingdom: 'Fungi', phylum: 'Basidiomycota', class: 'Agaricomycetes', order: 'Agaricales',
      family: 'Pleurotaceae', genus: 'Pleurotus', specific_epithet: 'ostreatus',
      external_taxon_id: null, taxon_remarks: 'Nota',
    });
    return { taxon_id: 'server-id', ...options.body };
  });
  const saved = await api.createTaxon({ id: 'client-id', scientificName: 'Pleurotus ostreatus', commonName: 'Orellana',
    kingdom: 'Fungi', phylum: 'Basidiomycota', className: 'Agaricomycetes', order: 'Agaricales', family: 'Pleurotaceae',
    genus: 'Pleurotus', specificEpithet: 'ostreatus', remarks: 'Nota' });
  assert.equal(saved.id, 'server-id'); assert.equal(saved.scientificName, 'Pleurotus ostreatus');
  assert.equal(saved.rank, 'species');
});

test('photos use POST with repeated files fields and normalize a media list rather than an occurrence', async t => {
  const files = [new File(['a'], 'a.png', { type: 'image/png' }), new File(['b'], 'b.jpg', { type: 'image/jpeg' })];
  t.mock.method(http, 'request', async (path, options) => {
    assert.equal(path, '/occurrences/a%2Fb/photos'); assert.equal(options.method, 'POST');
    assert.ok(options.body instanceof FormData);
    assert.deepEqual([...options.body.keys()], ['files', 'files']);
    assert.deepEqual(options.body.getAll('files').map(f => f.name), ['a.png', 'b.jpg']);
    assert.equal(await options.body.getAll('files')[1].text(), 'b');
    return [{ media_id: 'm', occurrence_id: 'a/b', photo_type: 'voucher', file_name: 'a.png',
      source_url: 'https://example.org/a.png', photographer: 'Ana', qc_passed: false }];
  });
  const photos = await api.addPhotos('a/b', files.map((file, i) => ({ id: String(i), file, metadata: {} })));
  assert.equal(photos.length, 1); assert.equal(photos[0].id, 'm');
  assert.equal(photos[0].url, 'https://example.org/a.png'); assert.equal(photos[0].qcPassed, false);
});

test('single-file upload uses the same occurrence photos route', async t => {
  t.mock.method(http, 'request', async (path, options) => {
    assert.equal(path, '/occurrences/o/photos'); assert.equal(options.method, 'POST');
    assert.equal(options.body.get('files').name, 'a.png');
    return [{ media_id: 'm' }];
  });
  assert.deepEqual(await api.upload(new File(['a'], 'a.png'), 'o', 'voucher'), [{ media_id: 'm' }]);
});

test('role updates send canonical roles unchanged', async t => {
  config.userUpdatePath = '/users/{id}';
  t.mock.method(http, 'request', async (path, options) => {
    assert.equal(path, '/users/a%2Fb'); assert.equal(options.method, 'PATCH');
    return options.body;
  });
  try {
    for (const role of ['viewer', 'analyst', 'curator', 'admin']) assert.deepEqual(await api.updateUserRole('a/b', role), { role });
  } finally { config.userUpdatePath = ''; }
});

test('configured complete taxon and media contracts remain available', async t => {
  config.taxonBundlePath = '/taxa/{id}/bundle'; config.mediaBundlePath = '/occurrences/{id}/media-bundle';
  t.mock.method(http, 'request', async (path, options) => {
    assert.equal(options.method, 'PUT');
    if (path === '/taxa/t/bundle') {
      assert.equal(options.body.taxon.scientific_name, 'Test species');
      assert.equal(options.body.taxon.taxon_rank, 'species');
      return options.body;
    }
    assert.equal(path, '/occurrences/o/media-bundle');
    assert.ok(options.body instanceof FormData);
    return { occurrence_id: 'o', multimedia: [{ media_id: 'm', source_url: 'https://example.org/m.png' }] };
  });
  try {
    assert.equal((await api.createTaxon({ id: 't', scientificName: 'Test species', rank: 'species' })).id, 't');
    assert.equal((await api.addPhotos('o', []))[0].id, 'm');
  } finally { config.taxonBundlePath = ''; config.mediaBundlePath = ''; }
});

const loginToken = (role = 'viewer', extra = {}) => `${Buffer.from('{"alg":"HS256"}').toString('base64url')}.${Buffer.from(JSON.stringify({ sub: 'u', role, exp: Math.floor(Date.now() / 1000) + 3600, ...extra })).toString('base64url')}.signature`;

test('each profile signs in through the backend JSON endpoint and receives its server role', async t => {
  let role;
  t.mock.method(http, 'request', async (path, options) => {
    assert.equal(path, '/auth/login-json'); assert.equal(options.method, 'POST');
    assert.equal(options.auth, false);
    assert.deepEqual(options.body, { email: 'a@example.org', password: ' keep spaces ' });
    return { access_token: loginToken(role), token_type: 'Bearer' };
  });
  for (role of ['viewer', 'analyst', 'curator', 'admin']) {
    const user = await api.login(' a@example.org ', ' keep spaces ');
    assert.equal(user.id, 'u'); assert.equal(user.role, role);
    assert.equal(user.email, 'a@example.org'); assert.ok(user.expiresAt > Date.now());
  }
});

test('failed login never keeps an old token or starts a synthetic session', async t => {
  const setTokens = t.mock.method(http, 'setTokens');
  t.mock.method(http, 'request', async () => { throw new Error('Correo o contraseña incorrectos'); });
  await assert.rejects(api.login('a@example.org', 'incorrect'), /incorrectos/);
  assert.deepEqual(setTokens.mock.calls.at(-1).arguments, []);
});

test('missing or expired tokens fail login even when a privileged profile is returned', async t => {
  const setTokens = t.mock.method(http, 'setTokens');
  let token;
  t.mock.method(http, 'request', async () => ({ access_token: token, user: { id: 'u', role: 'admin' } }));
  for (token of [undefined, 'invalid', loginToken('admin', { exp: 1 })]) {
    await assert.rejects(api.login('a@example.org', 'password'), /inválida o vencida/);
    assert.deepEqual(setTokens.mock.calls.at(-1).arguments, []);
  }
});

test('configured authenticated profile is loaded with a token and a profile error clears it', async t => {
  const token = loginToken('analyst');
  const setTokens = t.mock.method(http, 'setTokens');
  config.mePath = '/auth/me';
  let fail = false;
  t.mock.method(http, 'request', async (path) => {
    if (path === config.loginPath) return { access_token: token };
    assert.equal(path, '/auth/me');
    assert.equal(setTokens.mock.calls.at(-1).arguments[0], token);
    if (fail) throw new Error('Perfil no disponible');
    return { user_web_id: 'u', first_name: 'Ana', role: 'curator' };
  });
  try {
    const user = await api.login('a@example.org', 'password');
    assert.equal(user.name, 'Ana'); assert.equal(user.role, 'curator');
    fail = true;
    await assert.rejects(api.login('a@example.org', 'password'), /Perfil no disponible/);
    assert.deepEqual(setTokens.mock.calls.at(-1).arguments, []);
  } finally { config.mePath = ''; }
});

test('empty save responses produce meaningful errors', () => {
  assert.throws(() => normalizeOccurrence(null), /no devolvió/);
  assert.throws(() => normalizeTaxon(undefined), /no devolvió/);
});
test('record owner is distinct from the account that submitted it', () => {
  const assigned = normalizeOccurrence({ occurrence_id: 'o', owner_id: 'researcher', created_by_id: 'admin', recorded_by: 'Investigador' });
  assert.equal(assigned.ownerId, 'researcher'); assert.equal(assigned.createdById, 'admin');
  assert.equal(normalizeOccurrence({ occurrence_id: 'old', created_by_id: 'admin' }).ownerId, undefined);
});
