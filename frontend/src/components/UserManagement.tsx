import { useState, type FormEvent } from 'react';
import { Pencil, Users } from 'lucide-react';
import { config } from '../lib/api';
import { roleNames, type Role, type User } from '../types';
import { Empty, Modal, Notice } from './UI';

export default function UserManagement({ users, onSave }: { users: User[]; onSave: (user: User) => Promise<void> }) {
  const [editing, setEditing] = useState<User | null>(null);
  const [role, setRole] = useState<Role>('readonly_user');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function save(e: FormEvent) {
    e.preventDefault(); if (!editing) return; setError('');
    if (editing.role === 'admin' && role !== 'admin' && users.filter(u => u.role === 'admin').length < 2) {
      setError('Debe permanecer al menos una cuenta administradora.'); return;
    }
    setBusy(true);
    try { await onSave({ ...editing, role }); setEditing(null); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <><div className="page-heading"><div><span className="eyebrow">ADMINISTRACIÓN ACADÉMICA</span><h1>Usuarios y permisos<span className="heading-dot">.</span></h1><p>Consulta las cuentas y asigna el alcance de cada perfil.</p></div><Users size={27} /></div>
    {!config.demo && !config.usersPath && <Notice>El backend debe habilitar la lista de usuarios. El contrato actual no define esta ruta.</Notice>}
    <section className="panel"><div className="table-scroll"><table><thead><tr><th>Usuario</th><th>Correo</th><th>Perfil</th><th>Acción</th></tr></thead><tbody>{users.map(u => <tr key={u.id}><td><div className="person-cell"><span className="avatar">{u.name.split(' ').map(n => n[0]).slice(0, 2).join('')}</span><strong>{u.name}</strong></div></td><td>{u.email}</td><td><span className="badge unknown">{roleNames[u.role]}</span></td><td><button className="btn small" disabled={!config.demo && !config.userUpdatePath} onClick={() => { setEditing(u); setRole(u.role); setError(''); }} aria-label={`Editar rol de ${u.name}`}><Pencil size={14} />Editar rol</button></td></tr>)}</tbody></table></div>{!users.length && <Empty title="Sin usuarios disponibles" />}</section>
    <Notice>{config.demo ? 'La asignación de perfiles se guarda únicamente en esta demostración. El selector del encabezado permite simular los cuatro perfiles para revisar sus vistas.' : 'El servidor debe comprobar la autorización de administrador y la continuidad de al menos una cuenta administradora.'}</Notice>
    {!config.demo && !config.userUpdatePath && <Notice>La actualización de roles se habilitará cuando el equipo configure su endpoint.</Notice>}
    <section className="panel prose"><h2>Alcance de los perfiles</h2><dl className="detail-fields"><div><dt>Visitante</dt><dd>Consulta dashboard, especies, fichas, mapa y galería.</dd></div><div><dt>Investigador</dt><dd>Crea registros y especies, edita sus propias observaciones y añade fotografías a ellas.</dd></div><div><dt>Curador</dt><dd>Revisa observaciones, verifica su información o solicita ajustes con comentario.</dd></div><div><dt>Administrador</dt><dd>Accede a todos los módulos, edita todos los registros y gestiona usuarios y roles.</dd></div></dl></section>
    {editing && <Modal title={`Perfil de ${editing.name}`} onClose={() => setEditing(null)}><form onSubmit={save}><label className="field">Perfil académico<select value={role} onChange={e => setRole(e.target.value as Role)}>{Object.entries(roleNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></label><Notice>El cambio determina las vistas y acciones disponibles para esta cuenta.</Notice>{error && <Notice error>{error}</Notice>}<div className="form-actions"><button type="button" className="btn" disabled={busy} onClick={() => setEditing(null)}>Cancelar</button><button className="btn primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar perfil'}</button></div></form></Modal>}
  </>;
}
