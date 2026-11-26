import { Sprout } from 'lucide-react';
import type { User } from '../types';
import { AuthForm } from './Forms';

export default function AuthScreen({ onSuccess, onGuest, message }: { onSuccess: (user: User) => void; onGuest: () => void; message?: string }) {
  return <main className="auth-page">
    <section className="auth-card" aria-labelledby="auth-title">
      <span className="auth-mark"><Sprout size={32} /></span>
      <p className="eyebrow">ORINOQUÍA COLOMBIANA</p>
      <h1 id="auth-title">Macromicetos</h1>
      <p className="auth-subtitle">Registro académico de biodiversidad</p>
      {message && <p role="status">{message}</p>}
      <AuthForm onSuccess={onSuccess} />
      <div className="auth-guest">
        <button className="btn" type="button" onClick={onGuest}>Entrar como visitante</button>
        <p className="muted">Consulta el catálogo, el mapa y las fotografías sin crear una cuenta. Para registrar hallazgos o entrevistas necesitas un perfil autorizado.</p>
      </div>
    </section>
  </main>;
}
