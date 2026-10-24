/** Resolve responsibility from the simulated authenticated session before saving.
 * The server must enforce the same rule from its token in API mode.
 */
export function assignOccurrenceForSession(record, session, users = [], previous) {
  if (!session?.id || !session.name?.trim() || !['analyst', 'admin'].includes(session.role)) throw new Error('Inicia sesión como investigador o administrador para guardar un hallazgo.');
  if (previous && session.role !== 'admin' && previous.ownerId !== session.id) throw new Error('Solo puedes editar los registros de tu propia cuenta.');
  if (session.role === 'analyst') {
    return { ...record, ownerId: session.id, recordedBy: session.name, createdById: previous ? previous.createdById : session.id };
  }
  const ownerId = record.ownerId || session.id;
  const owner = ownerId === session.id ? session : users.find(user => user.id === ownerId);
  // Preserve historical ownership on edit, even if the account's role changed.
  const unchanged = previous && previous.ownerId === ownerId;
  if (!unchanged && (!owner || (owner.role !== 'analyst' && owner.id !== session.id))) throw new Error('Selecciona un investigador válido o tu propia cuenta para este hallazgo.');
  return { ...record, ownerId, recordedBy: owner?.name || previous?.recordedBy || previous?.author || '', createdById: previous ? previous.createdById : session.id };
}
