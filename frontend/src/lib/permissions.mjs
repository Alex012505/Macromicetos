export function capabilitiesFor(role) {
  return { write: role === 'researcher' || role === 'admin', curate: role === 'curator' || role === 'admin', manageUsers: role === 'admin' };
}
export function canEditOccurrence(role, userId, occurrence) {
  return role === 'admin' || (role === 'researcher' && Boolean(userId) && occurrence.ownerId === userId);
}
export function canAccessPage(role, page) {
  const scope = capabilitiesFor(role);
  if (page === 'registros') return scope.write;
  if (page === 'curaduria') return scope.curate;
  if (page === 'usuarios') return scope.manageUsers;
  return ['dashboard', 'especies', 'mapa', 'galeria', 'guia'].includes(page);
}
