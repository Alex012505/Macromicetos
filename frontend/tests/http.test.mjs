import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, createHttpClient, safeImageUrl, unwrapList } from '../src/lib/http.mjs';

const json = (payload, status = 200) => new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } });
test('sends JSON, Bearer token and correctly joins the API prefix', async () => {
  let call;
  const client = createHttpClient({ baseUrl: 'https://example.org/api/v1/', fetchImpl: async (...args) => { call = args; return json({ saved: true }); } });
  client.setTokens('session-token');
  assert.deepEqual(await client.request('/taxa', { method: 'POST', body: { scientificName: 'Test species' } }), { saved: true });
  assert.equal(call[0], 'https://example.org/api/v1/taxa');
  assert.equal(call[1].headers.get('Authorization'), 'Bearer session-token');
  assert.equal(call[1].headers.get('Content-Type'), 'application/json');
  assert.deepEqual(JSON.parse(call[1].body), { scientificName: 'Test species' });
});
test('public login never receives a stale Bearer token', async () => {
  const client = createHttpClient({ baseUrl: '/api', fetchImpl: async (url, opts) => { assert.equal(opts.headers.has('Authorization'), false); return json({ ok: true }); } });
  client.setTokens('old-token'); await client.request('/auth/login', { method: 'POST', auth: false, body: { email: 'demo@example.org' } });
});
test('FastAPI validation errors retain useful field messages', async () => {
  const client = createHttpClient({ baseUrl: '/api', fetchImpl: async () => json({ detail: [{ loc: ['body', 'event_id'], msg: 'Field required' }] }, 422) });
  await assert.rejects(client.request('/occurrences/one'), error => error instanceof ApiError && error.status === 422 && error.message.includes('event_id: Field required'));
});
test('uploads preserve FormData and let the browser set its multipart boundary', async () => {
  const body = new FormData(); body.append('file', new Blob(['image']), 'photo.jpg');
  const client = createHttpClient({ baseUrl: '/api', fetchImpl: async (url, opts) => { assert.equal(opts.body, body); assert.equal(opts.headers.has('Content-Type'), false); return json({ uploaded: true }); } });
  await client.request('/multimedia/upload', { method: 'POST', body });
});
test('network failures surface as errors, never as successful demo data', async () => {
  const client = createHttpClient({ baseUrl: '/api', fetchImpl: async () => { throw new TypeError('offline'); } });
  await assert.rejects(client.request('/taxa'), error => error instanceof ApiError && error.status === 0 && /conectar/.test(error.message));
});
test('a server returning HTML is rejected instead of masquerading as an empty API', async () => {
  const client = createHttpClient({ baseUrl: '/api', fetchImpl: async () => new Response('<html>wrong url</html>') });
  await assert.rejects(client.request('/taxa'), /JSON válido/);
});
test('supports successful no-content mutations', async () => {
  const client = createHttpClient({ baseUrl: '/api', fetchImpl: async () => new Response(null, { status: 204 }) });
  assert.equal(await client.request('/taxa/one', { method: 'DELETE' }), null);
});
test('a protected 401 clears the session when refresh is not configured', async () => {
  let expired = 0;
  const client = createHttpClient({ baseUrl: '/api', onSessionExpired: () => expired++, fetchImpl: async () => json({ detail: 'expired' }, 401) });
  client.setTokens('expired'); await assert.rejects(client.request('/taxa'), error => error.status === 401); assert.equal(expired, 1);
});
test('concurrent 401s share one refresh, and each protected request retries once', async () => {
  let refreshed = 0; let expired = 0;
  const client = createHttpClient({ baseUrl: '/api', refreshPath: '/auth/refresh', onSessionExpired: () => expired++, fetchImpl: async (url, opts) => {
    if (url.endsWith('/auth/refresh')) { refreshed++; await new Promise(resolve => setTimeout(resolve, 10)); return json({ accessToken: 'new' }); }
    return opts.headers.get('Authorization') === 'Bearer new' ? json({ ok: true }) : json({ detail: 'expired' }, 401);
  } });
  client.setTokens('old', 'refresh'); const results = await Promise.all([client.request('/taxa'), client.request('/users')]);
  assert.equal(refreshed, 1); assert.equal(expired, 0); assert.deepEqual(results, [{ ok: true }, { ok: true }]);
});
test('unsuccessful refresh ends the session and does not loop', async () => {
  let calls = 0; let expired = 0;
  const client = createHttpClient({ baseUrl: '/api', refreshPath: '/auth/refresh', onSessionExpired: () => expired++, fetchImpl: async () => { calls++; return json({ detail: 'expired' }, 401); } });
  client.setTokens('old', 'refresh'); await assert.rejects(client.request('/taxa')); assert.equal(calls, 2); assert.equal(expired, 1);
});
test('timeout aborts the outstanding network request', async () => {
  const client = createHttpClient({ baseUrl: '/api', timeoutMs: 10, fetchImpl: (url, opts) => new Promise((resolve, reject) => opts.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))) });
  await assert.rejects(client.request('/taxa'), /tardó demasiado/);
});
test('caller cancellation is distinct from a network failure', async () => {
  const controller = new AbortController();
  const client = createHttpClient({ baseUrl: '/api', fetchImpl: (url, opts) => new Promise((resolve, reject) => opts.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))) });
  const pending = client.request('/taxa', { signal: controller.signal }); controller.abort();
  await assert.rejects(pending, error => error.name === 'AbortError');
});
test('normalizes supported list envelopes and rejects unknown contracts', () => {
  assert.deepEqual(unwrapList({ data: [1, 2] }), [1, 2]); assert.deepEqual(unwrapList({ items: [] }), []); assert.deepEqual(unwrapList([1]), [1]);
  assert.throws(() => unwrapList({ message: 'success' }), ApiError);
});
test('rejects active or malformed external image URLs', () => {
  assert.equal(safeImageUrl('javascript:alert(1)'), undefined); assert.equal(safeImageUrl('data:text/html;base64,abc'), undefined);
  assert.equal(safeImageUrl('https://example.org/photo.jpg'), 'https://example.org/photo.jpg'); assert.equal(safeImageUrl('/photo.jpg'), '/photo.jpg');
});
