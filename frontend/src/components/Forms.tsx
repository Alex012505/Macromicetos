import { useState, type FormEvent } from 'react';
import { Check, Eye, EyeOff, ImagePlus, MapPin, Sprout } from 'lucide-react';
import { api, config } from '../lib/api';
import { demoUserForRole } from '../data/demo';
import { roleNames, type Occurrence, type Role, type Taxon, type User } from '../types';
import { Notice } from './UI';

export function AuthForm({ onSuccess }: { onSuccess: (user: User) => void }) {
  const [register, setRegister] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [message, setMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false); const [demoRole, setDemoRole] = useState<Role>('researcher');
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setBusy(true); setError(''); setMessage('');
    const fields = new FormData(e.currentTarget);
    try {
      if (register) {
        if (fields.get('password') !== fields.get('confirm_password')) throw new Error('Las contraseñas no coinciden.');
        await api.register({ email: String(fields.get('email')), password: String(fields.get('password')), first_name: String(fields.get('first_name')), last_name: String(fields.get('last_name')) });
        setMessage('Cuenta registrada. Inicia sesión para continuar.'); setRegister(false);
      } else onSuccess(await api.login(String(fields.get('email')), String(fields.get('password'))));
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  if (config.demo) return <div className="demo-auth"><span className="auth-mark"><Sprout size={32} /></span><h3>Registro académico de macromicetos</h3><p>Esta sesión es de demostración. Elige un perfil para revisar sus vistas y permisos, sin ingresar credenciales reales.</p><label className="field">Rol de demostración<select value={demoRole} onChange={e => setDemoRole(e.target.value as Role)}>{Object.entries(roleNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></label><button className="btn primary full-width" onClick={() => onSuccess(demoUserForRole(demoRole))}>Entrar a la demostración</button></div>;
  return <form onSubmit={submit}><p className="form-intro">{register ? 'Crea tu cuenta para explorar la biodiversidad del territorio.' : 'Inicia sesión para continuar tu trabajo de investigación.'}</p>{register && <div className="form-grid"><label className="field">Nombre<input name="first_name" required autoComplete="given-name" maxLength={80} /></label><label className="field">Apellido<input name="last_name" required autoComplete="family-name" maxLength={80} /></label></div>}<label className="field">Correo electrónico<input type="email" name="email" required autoComplete="email" placeholder="tu.correo@institucion.edu.co" maxLength={254} /></label><label className="field">Contraseña<div className="password-field"><input name="password" type={showPassword ? 'text' : 'password'} required minLength={register ? 8 : 1} autoComplete={register ? 'new-password' : 'current-password'} /><button type="button" className="icon-btn" aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>{register && <label className="field">Confirmar contraseña<input type="password" name="confirm_password" required minLength={8} autoComplete="new-password" /></label>}{error && <Notice error>{error}</Notice>}{message && <Notice>{message}</Notice>}<button className="btn primary full-width" disabled={busy}>{busy ? 'Procesando…' : register ? 'Crear cuenta' : 'Iniciar sesión'}</button><button type="button" className="text-button auth-switch" onClick={() => { setRegister(!register); setError(''); setMessage(''); }}>{register ? 'Ya tengo una cuenta' : 'Crear una cuenta nueva'}</button></form>;
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function RecordForm({ taxa, initial, author, ownerId, onSave, onCancel }: { taxa: Taxon[]; initial?: Occurrence; author: string; ownerId: string; onSave: (o: Occurrence) => Promise<void>; onCancel: () => void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [step, setStep] = useState(1);
  const [values, setValues] = useState({ taxonId: initial?.taxonId || '', author: initial?.author || author,
    date: initial?.date?.slice(0, 10) || new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' }).format(new Date()),
    department: initial?.department || 'Meta', locality: initial?.locality || '',
    lat: initial?.lat == null ? '' : String(initial.lat), lng: initial?.lng == null ? '' : String(initial.lng),
    substrate: initial?.substrate || 'Madera muerta', habitat: initial?.habitat || 'Bosque de galería',
    remarks: initial?.remarks || '', eventId: initial?.eventId || '', occurrenceId: initial?.id || '',
  });
  const set = (key: keyof typeof values, value: string) => setValues(v => ({ ...v, [key]: value }));
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError('');
    if (step === 1) { setStep(2); return; }
    if (!config.demo && (!uuid.test(values.eventId) || !uuid.test(values.taxonId))) { setError('Los identificadores de evento y taxón deben ser UUID válidos del backend.'); return; }
    if (!config.demo && !values.occurrenceId.trim()) { setError('Ingresa el ID de ocurrencia requerido por el contrato actual.'); return; }
    if (config.demo && Boolean(values.lat) !== Boolean(values.lng)) { setError('Ingresa tanto la latitud como la longitud, o deja ambas vacías.'); return; }
    setBusy(true);
    try {
      await onSave({ id: initial?.id || (config.demo ? `demo-${crypto.randomUUID()}` : values.occurrenceId), ownerId: initial?.ownerId || ownerId,
        eventId: config.demo ? initial?.eventId || `demo-event-${crypto.randomUUID()}` : values.eventId,
        taxonId: values.taxonId, author: values.author.trim(), date: values.date,
        department: config.demo ? values.department : initial?.department || '',
        locality: config.demo ? values.locality.trim() : initial?.locality || '',
        lat: config.demo ? values.lat ? Number(values.lat) : null : initial?.lat ?? null,
        lng: config.demo ? values.lng ? Number(values.lng) : null : initial?.lng ?? null,
        substrate: values.substrate, habitat: config.demo ? values.habitat : initial?.habitat || '',
        remarks: values.remarks.trim(), status: 'pending', images: initial?.images || [], measurements: initial?.measurements || [],
      });
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <form onSubmit={submit}><div className="form-stepper"><span className={step === 1 ? 'active' : 'done'}><i>{step > 1 ? <Check size={13} /> : '1'}</i>Identificación</span><span className={step === 2 ? 'active' : ''}><i>2</i>{config.demo ? 'Localidad y observación' : 'Evento y observación'}</span></div><p className="form-intro">{step === 1 ? 'Empecemos por la especie y la identificación del hallazgo.' : config.demo ? 'Ubica el hallazgo y describe su contexto ecológico.' : 'Relaciona la observación con un evento existente del backend.'}</p>
    {step === 1 ? <div className="form-grid"><label className="field span-2">Especie *<select required value={values.taxonId} onChange={e => set('taxonId', e.target.value)}><option value="">Selecciona una especie del catálogo</option>{taxa.map(t => <option value={t.id} key={t.id}>{t.scientificName} · {t.commonName || t.family}</option>)}</select></label><label className="field">Identificado por *<input required value={values.author} onChange={e => set('author', e.target.value)} maxLength={150} /></label><label className="field">Fecha de identificación *<input required type="date" value={values.date} onChange={e => set('date', e.target.value)} /></label><label className="field span-2">Sustrato *<select required value={values.substrate} onChange={e => set('substrate', e.target.value)}>{['Madera muerta', 'Suelo orgánico', 'Hojarasca', 'Estiércol'].map(s => <option key={s}>{s}</option>)}</select></label></div>
    : <><div className="form-grid">{config.demo ? <><label className="field">Departamento *<select value={values.department} onChange={e => set('department', e.target.value)}>{['Meta', 'Casanare', 'Arauca', 'Vichada'].map(s => <option key={s}>{s}</option>)}</select></label><label className="field">Hábitat<select value={values.habitat} onChange={e => set('habitat', e.target.value)}>{['Bosque de galería', 'Sabana abierta', 'Riberas de río', 'Bosque secundario'].map(s => <option key={s}>{s}</option>)}</select></label><label className="field span-2">Localidad *<input required value={values.locality} onChange={e => set('locality', e.target.value)} placeholder="Municipio, vereda o descripción del sitio" maxLength={300} /></label><label className="field">Latitud<input type="number" min={-90} max={90} step="any" value={values.lat} onChange={e => set('lat', e.target.value)} placeholder="Ej. 4.15" /></label><label className="field">Longitud<input type="number" min={-180} max={180} step="any" value={values.lng} onChange={e => set('lng', e.target.value)} placeholder="Ej. -73.64" /></label><p className="field-help span-2"><MapPin size={14} />Coordenadas WGS84 opcionales. Solo para esta demostración.</p></>
      : <><label className="field span-2">ID de evento existente (UUID) *<input required value={values.eventId} onChange={e => set('eventId', e.target.value)} placeholder="00000000-0000-0000-0000-000000000000" /></label>{!initial && <label className="field span-2">ID de la ocurrencia *<input required value={values.occurrenceId} onChange={e => set('occurrenceId', e.target.value)} /></label>}<div className="span-2"><Notice>La localidad y sus coordenadas pertenecen al evento. El contrato actual no permite crearlas desde este formulario. El servidor determinará el estado inicial del registro.</Notice></div></>}
      <label className="field span-2">Notas de la observación<textarea value={values.remarks} onChange={e => set('remarks', e.target.value)} placeholder="Describe el hallazgo y cualquier detalle relevante para su revisión…" rows={4} maxLength={2000} /></label></div><Notice>{config.demo ? 'Este registro se guardará en el navegador y se enviará a la cola de revisión de demostración.' : 'Se enviará la observación al backend. Los permisos y el estado de revisión deben validarse allí.'}</Notice></>}
    {error && <Notice error>{error}</Notice>}<div className="form-actions"><button type="button" className="btn" onClick={step === 1 ? onCancel : () => setStep(1)} disabled={busy}>{step === 1 ? 'Cancelar' : 'Anterior'}</button><button className="btn primary" disabled={busy || !taxa.length}>{busy ? 'Guardando…' : step === 1 ? 'Continuar' : initial ? 'Guardar cambios' : 'Guardar registro'}</button></div>
  </form>;
}
export function TaxonForm({ existing, onSave, onCancel }: { existing: Taxon[]; onSave: (taxon: Taxon) => Promise<void>; onCancel: () => void }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError(''); const f = new FormData(e.currentTarget); const name = String(f.get('scientificName')).trim();
    if (name.split(/\s+/).length < 2) { setError('Escribe al menos el género y el epíteto de la especie.'); return; }
    if (existing.some(t => t.scientificName.toLowerCase() === name.toLowerCase())) { setError('Esta especie ya está en el catálogo.'); return; }
    setBusy(true); try { await onSave({ id: `demo-taxon-${crypto.randomUUID()}`, scientificName: name,
      commonName: String(f.get('commonName')).trim(), kingdom: 'Fungi', phylum: String(f.get('phylum')),
      className: String(f.get('className')).trim(), order: String(f.get('order')).trim(), family: String(f.get('family')).trim(),
      genus: name.split(/\s+/)[0], remarks: String(f.get('remarks')).trim(), status: 'pending',
    }); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <form onSubmit={submit}><p className="form-intro">Una ficha taxonómica estandarizada es el punto de partida para tus observaciones.</p><div className="form-grid"><label className="field span-2">Nombre científico *<input name="scientificName" required placeholder="Género y especie" maxLength={200} /></label><label className="field span-2">Nombre común<input name="commonName" maxLength={150} /></label><label className="field">División *<select name="phylum" required><option>Basidiomycota</option><option>Ascomycota</option></select></label><label className="field">Clase *<input name="className" required maxLength={100} /></label><label className="field">Orden *<input name="order" required maxLength={100} /></label><label className="field">Familia *<input name="family" required maxLength={100} /></label><label className="field span-2">Notas taxonómicas<textarea name="remarks" rows={3} maxLength={2000} /></label></div>{error && <Notice error>{error}</Notice>}<div className="form-actions"><button className="btn" type="button" onClick={onCancel} disabled={busy}>Cancelar</button><button className="btn primary" disabled={busy}>{busy ? 'Guardando…' : 'Añadir especie'}</button></div></form>;
}
export function UploadForm({ records, taxa, onDone }: { records: Occurrence[]; taxa: Taxon[]; onDone: (recordId: string, url?: string) => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError(''); if (!file) { setError('Selecciona una fotografía.'); return; }
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) { setError('Usa una fotografía JPG, PNG o WebP.'); return; }
    const max = config.demo ? 2 : 10;
    if (file.size > max * 1024 * 1024) { setError(`El archivo debe pesar como máximo ${max} MB.`); return; }
    const f = new FormData(e.currentTarget); const recordId = String(f.get('recordId')); setBusy(true);
    try {
      if (config.demo) {
        const url = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = () => reject(new Error('No pudimos leer la imagen.')); reader.readAsDataURL(file); });
        await onDone(recordId, url);
      } else { await api.upload(file, recordId, String(f.get('photoType'))); await onDone(recordId); }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <form onSubmit={submit}><p className="form-intro">Vincula la fotografía a una observación para conservar su contexto.</p><label className="field">Observación *<select name="recordId" required><option value="">Selecciona un registro</option>{records.map(o => <option key={o.id} value={o.id}>{taxa.find(t => t.id === o.taxonId)?.scientificName || o.taxonId} · {o.department || o.id}</option>)}</select></label><label className="field">Tipo de fotografía<select name="photoType"><option value="habitus">Vista general (habitus)</option><option value="pileus">Sombrero (pileus)</option><option value="hymenophore">Himenóforo</option><option value="stipe">Estípite</option><option value="habitat">Hábitat</option></select></label><label className="upload-drop"><ImagePlus size={30} /><strong>{file ? file.name : 'Selecciona una fotografía'}</strong><span>JPG, PNG o WebP · hasta {config.demo ? '2' : '10'} MB</span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => setFile(e.target.files?.[0] || null)} aria-label="Seleccionar fotografía" /></label>{config.demo && <Notice>La imagen se guardará solo en este navegador. Para archivos grandes se necesita el backend.</Notice>}{error && <Notice error>{error}</Notice>}<button className="btn primary full-width" disabled={busy || !records.length}>{busy ? 'Guardando fotografía…' : 'Añadir fotografía'}</button></form>;
}
