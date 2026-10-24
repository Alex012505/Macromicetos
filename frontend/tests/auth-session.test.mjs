import test from 'node:test';
import assert from 'node:assert/strict';
import { readAccessToken, profileFromLogin } from '../src/lib/auth-session.mjs';

const now = Date.now();
const jwt = claims => `${Buffer.from('{"alg":"HS256"}').toString('base64url')}.${Buffer.from(JSON.stringify(claims)).toString('base64url')}.signature`;
const claims = { sub: 'u', role: 'analyst', exp: Math.floor(now / 1000) + 3600 };

test('all four roles require a nonexpired server token with an account ID', () => {
  for (const role of ['viewer', 'analyst', 'curator', 'admin']) {
    const session = readAccessToken(jwt({ ...claims, role, name: 'María Muñoz' }), now);
    assert.equal(session.role, role); assert.equal(session.sub, 'u');
    assert.equal(session.expiresAt, claims.exp * 1000); assert.equal(session.name, 'María Muñoz');
  }
});

test('malformed, missing, expired and unsupported session claims are rejected', () => {
  for (const token of [null, '', 'token', 'a.b.c', jwt({ ...claims, sub: '' }), jwt({ ...claims, sub: null }),
    jwt({ ...claims, exp: undefined }), jwt({ ...claims, exp: '9999999999' }), jwt({ ...claims, exp: Math.floor(now / 1000) }),
    jwt({ ...claims, role: 'researcher' }), jwt({ ...claims, role: undefined })]) {
    assert.throws(() => readAccessToken(token, now), error => error.status === 401);
  }
});

test('a profile must match the signed-in account; only server profile roles may override the JWT display role', () => {
  assert.deepEqual(profileFromLogin(claims, null, 'a@example.org'), { id: 'u', role: 'analyst', email: 'a@example.org', name: 'a@example.org' });
  const profile = { user_web_id: 'u', role: 'curator', first_name: 'Ana' };
  assert.equal(profileFromLogin(claims, profile, ''), profile);
  assert.throws(() => profileFromLogin(claims, { user_id: 'other', role: 'admin' }, ''), /no corresponde/);
  assert.throws(() => profileFromLogin(claims, { user_id: 'u', role: 'invented' }, ''), /no corresponde/);
});
