import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';

const compiled = await build({ entryPoints: ['src/lib/api.ts'], bundle: true, platform: 'node', format: 'esm', write: false, define: { 'import.meta.env': JSON.stringify({ VITE_DATA_MODE: 'api' }) } });
const { normalizeTaxon, normalizeOccurrence, normalizeUser, api } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString('base64')}`);

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
test('backend ORM profiles map to the correct UI role and party identity', () => {
  assert.deepEqual(normalizeUser({ user_web_id: 'u', role: 'field_collector', email: 'a@example.org', party: { display_name: 'Ana' } }), { id: 'u', name: 'Ana', email: 'a@example.org', role: 'researcher' });
  assert.equal(normalizeUser({ role: 'analyst' }).role, 'readonly_user');
  assert.equal(normalizeUser({ role: 'viewer' }).role, 'readonly_user');
  assert.equal(normalizeUser({ role: 'unknown-admin' }).role, 'readonly_user');
});
test('missing full-record server contract fails before issuing a basic request that would drop fields', async () => {
  await assert.rejects(api.saveOccurrence({ id: 'o' }), /guardado completo/);
  await assert.rejects(api.createTaxon({ id: 't' }), /guardado completo/);
  await assert.rejects(api.addPhotos('o', []), /guardado completo/);
});
test('empty save responses produce meaningful errors', () => {
  assert.throws(() => normalizeOccurrence(null), /no devolvió/);
  assert.throws(() => normalizeTaxon(undefined), /no devolvió/);
});
