import test from 'node:test';
import assert from 'node:assert/strict';
import { morphologyTypes, validateCoordinates, validateMorphology } from '../src/lib/morphology.mjs';
import { recordPayload, taxonPayload, ethnoSurveyPayload, normalizeEthnoSurvey, bundleForm, bundlePath, normalizeMorphology, normalizeParticipants } from '../src/lib/record-contract.mjs';
import { csvText, occurrenceRows, speciesRows } from '../src/lib/export-data.mjs';
import { migrateOccurrence, migrateDemoUser } from '../src/lib/demo-migration.mjs';
import { validateMeasurements } from '../src/lib/measurements.mjs';
import { isPdfImageUrl } from '../src/lib/pdf-images.mjs';

const morphology = [{ type: 'diametro_sombrero', value: '5–8', unit: 'cm', determinedDate: '2026-10-17', remarks: 'Medida en campo' }];
const taxon = { id: 'taxon', scientificName: 'Pleurotus ostreatus', commonName: 'Orellana', kingdom: 'Fungi', phylum: 'Basidiomycota', className: 'Agaricomycetes', order: 'Agaricales', family: 'Pleurotaceae', genus: 'Pleurotus', specificEpithet: 'ostreatus', rank: 'species', remarks: 'Descripción, con "comillas"\ny salto', morphology, image: 'SECRET-IMAGE', knowledge: [{ private: 'SECRET-INTERVIEW' }] };
const record = { id: 'record', taxonId: 'taxon', eventId: 'event', locationId: 'location', author: 'Identificador', recordedBy: 'Recolector', date: '2026-10-17', eventDate: '2026-10-15', lat: 0, lng: -73.5, country: 'CO', municipality: 'Villavicencio', department: 'Meta', locality: 'Sitio', uncertaintyM: 0, elevationM: 500, basisOfRecord: 'HumanObservation', substrate: 'Madera', habitat: 'Bosque', remarks: '', status: 'pending', images: ['SECRET-IMAGE'], morphology, measurements: [{ type: 'temperature', value: '24', unit: '°C', method: 'Estación portátil' }], participants: [{ id: 'p1', givenName: 'Ana', displayName: 'Ana', contactEmail: 'SECRET-EMAIL', role: 'collector', scope: 'event' }] };

test('WGS84 preserves zero and rejects incomplete, nonfinite and out-of-range coordinates', () => {
  assert.deepEqual(validateCoordinates('0', '0'), { lat: 0, lng: 0 });
  assert.deepEqual(validateCoordinates('', ''), { lat: null, lng: null });
  for (const pair of [['0', ''], ['91', '0'], ['0', '-181'], ['NaN', '0'], ['Infinity', '0']]) assert.throws(() => validateCoordinates(...pair));
});
test('18 controlled morphology traits, uniqueness, required values and diameter units', () => {
  assert.equal(morphologyTypes.length, 18); validateMorphology(morphology);
  assert.throws(() => validateMorphology([...morphology, ...morphology]), /repetido/);
  assert.throws(() => validateMorphology([{ type: 'invented', value: 'a' }]), /válido/);
  assert.throws(() => validateMorphology([{ type: 'tipo_himenio', value: '   ' }]), /Falta/);
  assert.throws(() => validateMorphology([{ type: 'diametro_sombrero', value: '5' }]), /cm o mm/);
});
test('environmental measurements follow the SQL enum, numeric value and required unit', () => {
  validateMeasurements([{ type: 'temperature', value: '24.5', unit: '°C' }, { type: 'relativeHumidity', value: '71', unit: '%' }]);
  assert.throws(() => validateMeasurements([{ type: 'pH', value: '6', unit: 'pH' }]), /válida/);
  assert.throws(() => validateMeasurements([{ type: 'temperature', value: 'cálido', unit: '°C' }]), /numérico/);
  assert.throws(() => validateMeasurements([{ type: 'temperature', value: '24', unit: ' ' }]), /unidad/);
  assert.throws(() => validateMeasurements([{ type: 'temperature', value: '24', unit: '°C' }, { type: 'temperature', value: '25', unit: '°C' }]), /repetida/);
});
test('record contract preserves each entity, dates, zero accuracy, and exactly one morphology owner', () => {
  const p = recordPayload(record);
  assert.equal(p.location.decimal_latitude, 0); assert.equal(p.location.coordinate_uncertainty_m, 0);
  assert.equal(p.event.event_date, '2026-10-15'); assert.equal(p.occurrence.date_identified, '2026-10-17');
  assert.equal(p.occurrence.recorded_by, 'Recolector'); assert.equal(p.occurrence.identified_by, 'Identificador');
  assert.equal(p.morphology[0].taxon_id, null); assert.equal(p.morphology[0].occurrence_id, 'record');
  assert.equal(p.measurements[0].event_id, 'event'); assert.equal(p.measurements[0].measurement_type, 'temperature');
  assert.equal(p.measurements[0].measurement_value, 24); assert.equal(p.measurements[0].measurement_unit, '°C');
  assert.deepEqual(normalizeMorphology(p.morphology), morphology);
  assert.equal(normalizeParticipants(p.participants)[0].displayName, 'Ana');
  assert.equal(recordPayload({ ...record, taxonId: '' }).occurrence.taxon_id, null);
});
test('taxon contract keeps bibliography and morphology separate and leaves interviews to their own section', () => {
  const p = taxonPayload({ ...taxon, knowledge: [{ id: 'interview', interviewDate: '2026-10-17', consentGiven: true, knowsFungi: false, uses: [{ id: 'use', useCategory: 'cultural' }] }], sources: [{ id: 'source', sourceType: 'book', year: '2026', title: 'Manual' }] });
  assert.equal(p.taxon.specific_epithet, 'ostreatus'); assert.equal(p.sources[0].year, 2026);
  assert.equal(p.morphology[0].occurrence_id, null); assert.equal(p.morphology[0].taxon_id, 'taxon');
  // Omitting the key keeps the interviews stored in the exclusive section.
  assert.equal('knowledge' in p, false);
});

test('exclusive interview contract links one source to one species with its uses', () => {
  const survey = { id: 'source', knowledgeId: 'knowledge', interviewDate: '2026-10-17', interviewer: 'Ana', consentGiven: true, anonymityLevel: 'pseudonym', knowsFungi: false, localName: 'oreja de palo', uses: [{ id: 'use', useCategory: 'medicinal', usesFungi: true }] };
  const payload = ethnoSurveyPayload('taxon', survey);
  assert.equal(payload.source.ethno_source_id, 'source');
  assert.equal(payload.source.interview_date, '2026-10-17T12:00:00-05:00');
  assert.equal(payload.source.consent_given, true);
  assert.equal(payload.knowledge.knowledge_id, 'knowledge');
  assert.equal(payload.knowledge.ethno_source_id, 'source');
  assert.equal(payload.knowledge.taxon_id, 'taxon');
  assert.equal(payload.knowledge.knows_fungi, false);
  assert.equal(payload.knowledge.local_name, 'oreja de palo');
  assert.equal(payload.uses[0].use_category, 'medicinal');
  assert.equal(payload.uses[0].uses_fungi, true);
  const normalized = normalizeEthnoSurvey({ source: { ethno_source_id: 'source', interview_date: '2026-10-17T12:00:00-05:00', consent_given: true }, knowledge: { knowledge_id: 'knowledge', taxon_id: 'taxon', knows_fungi: false }, uses: [{ use_id: 'use', use_category: 'medicinal', uses_fungi: true }] });
  assert.equal(normalized.knowledgeId, 'knowledge');
  assert.equal(normalized.taxonId, 'taxon');
  assert.equal(normalized.uses[0].usesFungi, true);
});
test('bundle writes require explicit configured paths and stable file IDs for safe retries', () => {
  assert.throws(() => bundlePath('', 'id', 'hallazgos'), /aún no/);
  assert.throws(() => bundlePath('/bundle', 'id', 'hallazgos'), /aún no/);
  assert.equal(bundlePath('/bundle/{id}', 'a/b', 'hallazgos'), '/bundle/a%2Fb');
  const file = new File(['test'], 'test.png', { type: 'image/png' });
  const body = bundleForm({ occurrence_id: 'id' }, [{ id: 'photo-uuid', file, metadata: { photoType: 'pileus', photographer: 'Ana', license: '' } }]);
  const p = JSON.parse(body.get('payload')); assert.equal(p.multimedia[0].media_id, 'photo-uuid');
  assert.equal(p.multimedia[0].license, null); assert.equal(body.get('file_photo-uuid').name, 'test.png');
});
test('CSV escapes quotes, commas, newlines and formula injection, keeping numeric coordinates', () => {
  const csv = csvText([['a,"b"\nc', '=SUM(1)', '\t +1', ' \r@cmd', -73.5, 0, null]]);
  assert.ok(csv.startsWith('\uFEFF')); assert.ok(csv.includes('"a,""b""\nc"')); assert.ok(csv.includes('"\'=SUM(1)"')); assert.ok(csv.includes('"\'\t +1"')); assert.ok(csv.includes('"\' \r@cmd"')); assert.ok(csv.includes('"-73.5","0",""'));
});
test('table exports contain primary species/field data, but no images, interviews or private contacts', () => {
  const rows = occurrenceRows([record], [taxon]); assert.equal(rows[0].length, rows[1].length);
  assert.ok(rows[1].includes(-73.5)); assert.ok(rows[1].includes('5–8 cm'));
  assert.ok(!JSON.stringify(rows).includes('SECRET'));
  const catalog = speciesRows([taxon], []); assert.equal(catalog.length, 2); assert.equal(catalog[1][14], 0);
  assert.ok(!JSON.stringify(catalog).includes('SECRET'));
});
test('old demo records migrate without losing photographs or duplicating morphology', () => {
  const old = { id: 'old', date: '2026-10-17', images: ['data:image/png;base64,abc'], measurements: [{ name: 'Diámetro del sombrero', value: '4–7', unit: 'cm' }, { name: 'Humedad', value: '80', unit: '%' }] };
  const migrated = migrateOccurrence(old, '/Macromicetos/');
  assert.equal(migrated.eventDate, old.date); assert.equal(migrated.morphology[0].type, 'diametro_sombrero');
  assert.equal(migrated.measurements.length, 1); assert.deepEqual(migrated.images, old.images);
  assert.deepEqual(migrateOccurrence(migrated, '/Macromicetos/'), migrated);
});
test('stored demo roles migrate without losing account identity or permissions', () => {
  for (const [oldRole, role] of [['readonly_user', 'viewer'], ['researcher', 'analyst'], ['field_collector', 'analyst'], ['viewer', 'viewer'], ['analyst', 'analyst'], ['curator', 'curator'], ['admin', 'admin'], ['unknown', 'viewer']]) {
    const user = { id: 'u', name: 'Ana', email: 'ana@example.org', role: oldRole };
    const migrated = migrateDemoUser(user);
    assert.deepEqual(migrated, { ...user, role });
    assert.deepEqual(migrateDemoUser(migrated), migrated);
  }
});

test('PDF loader accepts local raster uploads and rejects active data URLs', () => {
  assert.equal(isPdfImageUrl('data:image/jpeg;base64,YWJj'), true);
  assert.equal(isPdfImageUrl('data:image/png;base64,YWJj'), true);
  assert.equal(isPdfImageUrl('data:image/webp;base64,YWJj'), true);
  assert.equal(isPdfImageUrl('/Macromicetos/images/pleurotus.jpg'), true);
  assert.equal(isPdfImageUrl('data:image/svg+xml;base64,YWJj'), false);
  assert.equal(isPdfImageUrl('javascript:alert(1)'), false);
});
