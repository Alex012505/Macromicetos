import test from 'node:test';
import assert from 'node:assert/strict';
import { assignOccurrenceForSession } from '../src/lib/record-ownership.mjs';
import { canEditOccurrence } from '../src/lib/permissions.mjs';
import { recordPayload } from '../src/lib/record-contract.mjs';

const researcher = { id: 'laura', name: 'Laura Martínez', role: 'researcher' };
const other = { id: 'diego', name: 'Diego Ramírez', role: 'researcher' };
const admin = { id: 'camila', name: 'Camila Torres', role: 'admin' };
const curator = { id: 'andres', name: 'Andrés Rojas', role: 'curator' };
const users = [researcher, other, admin, curator];

test('researcher creation takes responsibility from the session even if incoming identity is forged', () => {
  const saved = assignOccurrenceForSession({ id: 'o', ownerId: other.id, recordedBy: other.name, createdById: admin.id, author: 'Especialista que identificó la especie' }, researcher, users);
  assert.equal(saved.ownerId, researcher.id); assert.equal(saved.recordedBy, researcher.name); assert.equal(saved.createdById, researcher.id);
  assert.equal(saved.author, 'Especialista que identificó la especie');
});
test('a researcher can edit an assigned record without changing its original submitting account', () => {
  const previous = { id: 'o', ownerId: researcher.id, createdById: admin.id };
  const saved = assignOccurrenceForSession({ ...previous, ownerId: other.id, recordedBy: other.name, createdById: other.id }, researcher, users, previous);
  assert.equal(saved.ownerId, researcher.id); assert.equal(saved.recordedBy, researcher.name); assert.equal(saved.createdById, admin.id);
});
test('a researcher cannot edit another researcher record', () => {
  assert.throws(() => assignOccurrenceForSession({ ownerId: researcher.id }, researcher, users, { ownerId: other.id }), /propia cuenta/);
});
test('admin assignment gives ownership and edit permission to the chosen researcher', () => {
  const saved = assignOccurrenceForSession({ id: 'o', ownerId: other.id, recordedBy: 'Texto manipulado' }, admin, users);
  assert.equal(saved.ownerId, other.id); assert.equal(saved.recordedBy, other.name); assert.equal(saved.createdById, admin.id);
  assert.equal(canEditOccurrence(other.role, other.id, saved), true); assert.equal(canEditOccurrence(researcher.role, researcher.id, saved), false);
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
  for (const session of [null, {}, { id: '', name: 'Ana', role: 'researcher' }, curator, { id: 'v', name: 'Visitante', role: 'readonly_user' }]) assert.throws(() => assignOccurrenceForSession({}, session, users), /Inicia sesión/);
});
