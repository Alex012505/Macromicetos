import test from 'node:test';
import assert from 'node:assert/strict';
import { assignOccurrenceForSession } from '../src/lib/record-ownership.mjs';
import { canEditOccurrence } from '../src/lib/permissions.mjs';
import { recordPayload } from '../src/lib/record-contract.mjs';

const analyst = { id: 'laura', name: 'Laura Martínez', role: 'analyst' };
const other = { id: 'diego', name: 'Diego Ramírez', role: 'analyst' };
const admin = { id: 'camila', name: 'Camila Torres', role: 'admin' };
const curator = { id: 'andres', name: 'Andrés Rojas', role: 'curator' };
const users = [analyst, other, admin, curator];

test('analyst creation takes responsibility from the session even if incoming identity is forged', () => {
  const saved = assignOccurrenceForSession({ id: 'o', ownerId: other.id, recordedBy: other.name, createdById: admin.id, author: 'Especialista que identificó la especie' }, analyst, users);
  assert.equal(saved.ownerId, analyst.id); assert.equal(saved.recordedBy, analyst.name); assert.equal(saved.createdById, analyst.id);
  assert.equal(saved.author, 'Especialista que identificó la especie');
});
test('an analyst can edit an assigned record without changing its original submitting account', () => {
  const previous = { id: 'o', ownerId: analyst.id, createdById: admin.id };
  const saved = assignOccurrenceForSession({ ...previous, ownerId: other.id, recordedBy: other.name, createdById: other.id }, analyst, users, previous);
  assert.equal(saved.ownerId, analyst.id); assert.equal(saved.recordedBy, analyst.name); assert.equal(saved.createdById, admin.id);
});
test('an analyst cannot edit another analyst record', () => {
  assert.throws(() => assignOccurrenceForSession({ ownerId: analyst.id }, analyst, users, { ownerId: other.id }), /propia cuenta/);
});
test('admin assignment gives ownership and edit permission to the chosen analyst', () => {
  const saved = assignOccurrenceForSession({ id: 'o', ownerId: other.id, recordedBy: 'Texto manipulado' }, admin, users);
  assert.equal(saved.ownerId, other.id); assert.equal(saved.recordedBy, other.name); assert.equal(saved.createdById, admin.id);
  assert.equal(canEditOccurrence(other.role, other.id, saved), true); assert.equal(canEditOccurrence(analyst.role, analyst.id, saved), false);
  assert.equal(recordPayload(saved).owner_id, other.id); assert.equal(recordPayload(saved).event.recorded_by, other.name);
});
test('admin may use own account, rejects invalid new assignees, and preserves historical owners on edit', () => {
  assert.equal(assignOccurrenceForSession({ id: 'o' }, admin, users).ownerId, admin.id);
  for (const id of [curator.id, 'missing']) assert.throws(() => assignOccurrenceForSession({ ownerId: id }, admin, users), /investigador válido/);
  const previous = { id: 'old', ownerId: 'retired', recordedBy: 'Investigador anterior', createdById: 'original' };
  const saved = assignOccurrenceForSession(previous, admin, users, previous);
  assert.equal(saved.recordedBy, previous.recordedBy); assert.equal(saved.createdById, previous.createdById);
});
test('missing sessions and non-writing profiles cannot assign records', () => {
  for (const session of [null, {}, { id: '', name: 'Ana', role: 'analyst' }, curator, { id: 'v', name: 'Visitante', role: 'viewer' }]) assert.throws(() => assignOccurrenceForSession({}, session, users), /Inicia sesión/);
});
