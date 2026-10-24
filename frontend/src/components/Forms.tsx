import { useState, type FormEvent } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { api } from '../lib/api';
import type { User } from '../types';
import { Notice } from './UI';

export function AuthForm({ onSuccess }: { onSuccess: (user: User) => void }) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setError(''); setMessage('');
    const form = e.currentTarget;
    const fields = new FormData(form);
    const email = String(fields.get('email') || '').trim();
    const password = String(fields.get('password') || '');
    try {
      if (register) {
        if (password !== fields.get('confirm_password')) throw new Error('Las contraseñas no coinciden.');
        await api.register({ email, password, first_name: String(fields.get('first_name') || '').trim(), last_name: String(fields.get('last_name') || '').trim() });
        form.reset(); setShowPassword(false);
        setMessage('Cuenta creada como visitante. Inicia sesión con tu correo y contraseña. Los permisos de investigador, curador o administrador los asigna la administración.');
        setRegister(false);
      } else {
        const user = await api.login(email, password);
        form.reset(); onSuccess(user);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally { setBusy(false); }
  }

  return <form onSubmit={submit} aria-busy={busy}>
    <p className="form-intro">{register ? 'Crea una cuenta de visitante para consultar la plataforma.' : 'Ingresa con tu cuenta. Tus permisos se asignan según el perfil registrado en el servidor.'}</p>
    <fieldset disabled={busy} className="auth-fields">
      {register && <div className="form-grid">
        <label className="field">Nombre<input name="first_name" required autoComplete="given-name" maxLength={80} /></label>
        <label className="field">Apellido<input name="last_name" required autoComplete="family-name" maxLength={80} /></label>
      </div>}
      <label className="field">Correo electrónico<input type="email" name="email" required autoComplete="username" placeholder="tu.correo@institucion.edu.co" maxLength={254} /></label>
      <label className="field">Contraseña<div className="password-field">
        <input name="password" type={showPassword ? 'text' : 'password'} required minLength={register ? 8 : 1} autoComplete={register ? 'new-password' : 'current-password'} />
        <button type="button" className="icon-btn" aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button>
      </div></label>
      {register && <label className="field">Confirmar contraseña<input type="password" name="confirm_password" required minLength={8} autoComplete="new-password" /></label>}
    </fieldset>
    {error && <Notice error>{error}</Notice>}
    {message && <Notice>{message}</Notice>}
    <button className="btn primary full-width" disabled={busy}>{busy ? 'Validando…' : register ? 'Crear cuenta' : 'Iniciar sesión'}</button>
    <button type="button" className="text-button auth-switch" disabled={busy} onClick={() => { setRegister(!register); setError(''); setMessage(''); setShowPassword(false); }}>{register ? 'Ya tengo una cuenta' : 'Crear una cuenta de visitante'}</button>
  </form>;
}
