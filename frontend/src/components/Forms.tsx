import { useState, type FormEvent } from 'react';
import { Eye, EyeOff, Sprout } from 'lucide-react';
import { api, config } from '../lib/api';
import { demoUserForRole } from '../data/demo';
import { roleNames, type Role, type User } from '../types';
import { Notice } from './UI';

export function AuthForm({ onSuccess, demoAccounts = [] }: { onSuccess: (user: User) => void; demoAccounts?: User[] }) {
  const [register, setRegister] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [message, setMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false); const [demoRole, setDemoRole] = useState<Role>('researcher');
  const [demoAccountId, setDemoAccountId] = useState('');
  const accounts = demoAccounts.filter(account => account.role === demoRole);
  const demoAccount = accounts.find(account => account.id === demoAccountId) || accounts[0] || demoUserForRole(demoRole);
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
  if (config.demo) return <div className="demo-auth"><span className="auth-mark"><Sprout size={32} /></span><h3>Registro académico de macromicetos</h3><p>Esta sesión es de demostración. Elige un perfil para revisar sus vistas y permisos, sin ingresar credenciales reales.</p><label className="field">Rol de demostración<select value={demoRole} onChange={e => setDemoRole(e.target.value as Role)}>{Object.entries(roleNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></label>{demoRole === 'researcher' && accounts.length > 0 && <label className="field">Cuenta de investigador<select value={demoAccount.id} onChange={e => setDemoAccountId(e.target.value)}>{accounts.map(account => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>}<button className="btn primary full-width" onClick={() => onSuccess(demoAccount)}>Entrar a la demostración</button></div>;
  return <form onSubmit={submit}><p className="form-intro">{register ? 'Crea tu cuenta para explorar la biodiversidad del territorio.' : 'Inicia sesión para continuar tu trabajo de investigación.'}</p>{register && <div className="form-grid"><label className="field">Nombre<input name="first_name" required autoComplete="given-name" maxLength={80} /></label><label className="field">Apellido<input name="last_name" required autoComplete="family-name" maxLength={80} /></label></div>}<label className="field">Correo electrónico<input type="email" name="email" required autoComplete="email" placeholder="tu.correo@institucion.edu.co" maxLength={254} /></label><label className="field">Contraseña<div className="password-field"><input name="password" type={showPassword ? 'text' : 'password'} required minLength={register ? 8 : 1} autoComplete={register ? 'new-password' : 'current-password'} /><button type="button" className="icon-btn" aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>{register && <label className="field">Confirmar contraseña<input type="password" name="confirm_password" required minLength={8} autoComplete="new-password" /></label>}{error && <Notice error>{error}</Notice>}{message && <Notice>{message}</Notice>}<button className="btn primary full-width" disabled={busy}>{busy ? 'Procesando…' : register ? 'Crear cuenta' : 'Iniciar sesión'}</button><button type="button" className="text-button auth-switch" onClick={() => { setRegister(!register); setError(''); setMessage(''); }}>{register ? 'Ya tengo una cuenta' : 'Crear una cuenta nueva'}</button></form>;
}
