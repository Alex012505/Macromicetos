/** Run the actual TypeScript API client against an isolated, real FastAPI server. */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { mkdir, mkdtemp, readFile, rm } from 'node:fs/promises';
import { createServer } from 'node:net';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(frontend, '..');
const testRoot = join(root, 'Backend', '.test-data');
await mkdir(testRoot, { recursive: true });
const directory = await mkdtemp(join(testRoot, 'client-'));
const listener = createServer();
await new Promise((resolve, reject) => { listener.once('error', reject); listener.listen(0, '127.0.0.1', resolve); });
const port = listener.address().port;
await new Promise(resolve => listener.close(resolve));
const baseUrl = `http://127.0.0.1:${port}`;
const password = randomBytes(20).toString('hex');
const python = join(root, 'Backend', '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const postgresUrl = process.env.MACROMICETOS_TEST_POSTGRES_URL;
if (postgresUrl) {
  const target = new URL(postgresUrl.replace('postgresql+psycopg2:', 'postgresql:'));
  assert.equal(target.protocol, 'postgresql:');
  assert.match(target.pathname, /^\/macromicetos_test_[0-9a-f]{32}$/);
}
const server = spawn(python, [join(root, 'Backend/tests/serve_fixture.py')], { cwd: root, windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'],
  env: { ...process.env, APP_ENV: 'test', DATABASE_URL: postgresUrl || `sqlite:///${join(directory, 'test.db').replaceAll('\\', '/')}`, MULTIMEDIA_ROOT: join(directory, 'images'),
    SECRET_KEY: randomBytes(48).toString('hex'), INTEGRATION_ISOLATED_DB: '1', INTEGRATION_TEST_PORT: String(port), INTEGRATION_TEST_PASSWORD: password } });
let logs = ''; let failure;
server.stderr.on('data', chunk => { logs = (logs + chunk).slice(-12000); });
server.on('error', error => { failure = error; });

try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (failure || server.exitCode !== null) throw failure || new Error(logs || 'El backend de prueba terminó.');
    try { ready = (await fetch(`${baseUrl}/health`)).ok; } catch { /* server is starting */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  assert.ok(ready, 'La API no inició a tiempo.');
  const compiled = await build({ absWorkingDir: frontend, entryPoints: ['src/lib/api.ts'], bundle: true, platform: 'node', format: 'esm', write: false,
    define: { 'import.meta.env': JSON.stringify({ VITE_DATA_MODE: 'api', VITE_API_BASE_URL: baseUrl }) } });
  const { api, http } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString('base64')}`);
  // Only the UI's session-expiry notification is browser-specific.
  globalThis.window = { dispatchEvent() {} };
  const analyst = await api.login('analyst@example.org', password);
  assert.equal(analyst.role, 'analyst'); assert.equal(analyst.name, 'Analyst');
  const taxon = await api.createTaxon({ id: randomUUID(), scientificName: 'Pleurotus ostreatus', commonName: 'Orellana', kingdom: 'Fungi',
    phylum: 'Basidiomycota', className: 'Agaricomycetes', order: 'Agaricales', family: 'Pleurotaceae', genus: 'Pleurotus', rank: 'species', remarks: '', status: 'pending',
    morphology: [{ type: 'color_sombrero', value: 'Gris' }], sources: [{ id: randomUUID(), sourceType: 'book', title: 'Manual de campo', year: '2026' }],
    knowledge: [{ id: randomUUID(), interviewDate: '2026-10-23', interviewer: 'Analyst', consentGiven: true, anonymityLevel: 'anonymous', knowsFungi: false, uses: [] }],
    participants: [{ id: randomUUID(), givenName: 'Ana', displayName: 'Ana', contactEmail: 'private@example.org', role: 'author' }] });
  assert.equal(taxon.scientificName, 'Pleurotus ostreatus'); assert.equal(taxon.sources[0].title, 'Manual de campo');
  assert.equal(taxon.knowledge[0].knowsFungi, false);
  const record = { id: randomUUID(), eventId: randomUUID(), locationId: randomUUID(), taxonId: taxon.id, ownerId: analyst.id,
    author: 'Especialista', date: '2026-10-23', department: 'Meta', locality: 'Bosque de integración', country: 'CO', municipality: 'Villavicencio',
    lat: 0, lng: 0, uncertaintyM: 0, basisOfRecord: 'HumanObservation', substrate: 'Madera muerta', habitat: 'Bosque de galería', remarks: 'Prueba completa', recordedBy: analyst.name,
    eventType: 'Observation', eventDate: '2026-10-21', occurrenceDate: '2026-10-21T12:00:00-05:00', samplingProtocol: 'OpportunisticSearch',
    status: 'pending', images: [], morphology: [{ type: 'diametro_sombrero', value: '5–8', unit: 'cm' }],
    measurements: [{ name: 'Temperatura', value: '0', unit: '°C', scope: 'event' }], participants: [] };
  const image = new File([await readFile(join(frontend, 'public/images/pleurotus.jpg'))], 'photo.jpg', { type: 'image/jpeg' });
  const photo = { id: randomUUID(), file: image, metadata: { url: '', photoType: 'habitus', photographer: 'Analyst', license: 'CC BY 4.0' } };
  const saved = await api.saveOccurrence(record, [photo]);
  assert.equal(saved.ownerId, analyst.id); assert.equal(saved.eventDate, record.eventDate); assert.equal(saved.date, record.date);
  assert.equal(saved.lat, 0); assert.equal(saved.uncertaintyM, 0); assert.equal(saved.measurements[0].value, '0');
  assert.equal(saved.morphology[0].value, '5–8'); assert.equal(saved.photos.length, 1);
  assert.equal((await fetch(saved.images[0])).status, 200);
  const retry = await api.saveOccurrence(record, [photo]); assert.equal(retry.photos.length, 1);
  const extraPhoto = { id: randomUUID(), file: new File([await readFile(join(frontend, 'public/images/trametes.jpg'))], 'additional.jpg', { type: 'image/jpeg' }),
    metadata: { url: '', photoType: 'pileus', photographer: 'Ana', license: 'CC0', credits: [{ id: randomUUID(), givenName: 'Ana', displayName: 'Ana', role: 'photographer' }] } };
  const allPhotos = await api.addPhotos(saved.id, [extraPhoto]);
  assert.equal(allPhotos.length, 2); assert.equal(allPhotos.find(p => p.id === extraPhoto.id).credits[0].displayName, 'Ana');
  assert.equal((await api.taxon(taxon.id)).image, saved.images[0]);
  assert.equal((await api.occurrences()).length, 1);
  await api.login('curator@example.org', password);
  await api.curate(saved, 'verified', 'Verificación completa');
  assert.equal((await api.occurrence(saved.id)).status, 'verified');
  await api.login('viewer@example.org', password);
  const visible = await api.taxon(taxon.id);
  assert.equal(visible.knowledge.length, 0); assert.ok(!JSON.stringify(visible).includes('private@example.org'));
  await assert.rejects(api.createTaxon({ ...taxon, id: randomUUID() }), error => error.status === 403);
  await api.login('admin@example.org', password);
  const users = await api.users(); assert.equal(users.length, 4);
  await api.updateUserRole(analyst.id, 'curator');
  assert.equal((await api.login('analyst@example.org', password)).role, 'curator');
  http.setTokens();
  console.log('Integración real correcta: 4 perfiles, ficha completa, hallazgo, imagen, reintento, listado, curaduría, privacidad y gestión de roles.');
} catch (error) {
  console.error('Falló la integración:', error.message, error.status || '', error.details ? JSON.stringify(error.details) : '');
  if (logs) console.error(logs);
  process.exitCode = 1;
} finally {
  delete globalThis.window;
  if (server.exitCode === null) {
    const closed = new Promise(resolve => server.once('exit', resolve));
    server.kill(); await closed;
  }
  assert.equal(dirname(directory), testRoot);
  await rm(directory, { recursive: true, force: true });
}
