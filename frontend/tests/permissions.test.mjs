import test from 'node:test';
import assert from 'node:assert/strict';
import { canAccessPage, canEditOccurrence, capabilitiesFor } from '../src/lib/permissions.mjs';

test('public and unknown roles have no write, review or administration permission', () => {
  for (const role of ['readonly_user', '', undefined, 'unknown']) {
    assert.deepEqual(capabilitiesFor(role), { write: false, curate: false, manageUsers: false });
    for (const page of ['registros', 'curaduria', 'usuarios', 'conexion']) assert.equal(canAccessPage(role, page), false);
    for (const page of ['dashboard', 'especies', 'mapa', 'galeria', 'guia']) assert.equal(canAccessPage(role, page), true);
  }
});
test('researchers write and edit their own records only, with explicit ownership', () => {
  assert.deepEqual(capabilitiesFor('researcher'), { write: true, curate: false, manageUsers: false });
  assert.equal(canEditOccurrence('researcher', 'user-1', { ownerId: 'user-1' }), true);
  assert.equal(canEditOccurrence('researcher', 'user-1', { ownerId: 'user-2' }), false);
  assert.equal(canEditOccurrence('researcher', 'user-1', {}), false);
  assert.equal(canEditOccurrence('researcher', '', { ownerId: '' }), false);
  assert.equal(canAccessPage('researcher', 'registros'), true);
  assert.equal(canAccessPage('researcher', 'curaduria'), false);
});
test('curators review records without acquiring researcher or admin actions', () => {
  assert.deepEqual(capabilitiesFor('curator'), { write: false, curate: true, manageUsers: false });
  assert.equal(canAccessPage('curator', 'curaduria'), true);
  assert.equal(canAccessPage('curator', 'usuarios'), false);
  assert.equal(canEditOccurrence('curator', 'user-1', { ownerId: 'user-1' }), false);
});
test('only administrators manage users and may edit every record; removed pages are inaccessible', () => {
  assert.deepEqual(capabilitiesFor('admin'), { write: true, curate: true, manageUsers: true });
  assert.equal(canAccessPage('admin', 'usuarios'), true);
  for (const role of ['readonly_user', 'researcher', 'curator', 'admin']) {
    assert.equal(canAccessPage(role, 'conexion'), false);
    assert.equal(canAccessPage(role, 'unknown-page'), false);
  }
  assert.equal(canEditOccurrence('admin', 'user-1', { ownerId: 'user-2' }), true);
});
