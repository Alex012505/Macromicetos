import { ApiError } from './http.mjs';

export const authRoles = ['viewer', 'analyst', 'curator', 'admin'];

/** Read display/session claims only from the token returned by a successful login.
 * This does not verify its signature: every protected endpoint must do that on the server.
 */
export function readAccessToken(token, now = Date.now()) {
  try {
    if (typeof token !== 'string') throw new Error();
    const parts = token.split('.');
    if (parts.length !== 3 || parts.some(part => !part)) throw new Error();
    const encoded = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const bytes = Uint8Array.from(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, '=')), char => char.charCodeAt(0));
    const claims = JSON.parse(new TextDecoder().decode(bytes));
    if (typeof claims.sub !== 'string' || !claims.sub.trim() || !authRoles.includes(claims.role)
      || typeof claims.exp !== 'number' || !Number.isFinite(claims.exp) || claims.exp * 1000 <= now) throw new Error();
    return { ...claims, expiresAt: claims.exp * 1000 };
  } catch {
    throw new ApiError('El servidor devolvió una sesión inválida o vencida. Inicia sesión nuevamente.', 401);
  }
}

export function profileFromLogin(claims, profile, email) {
  if (!profile) return { id: claims.sub, role: claims.role, email, name: claims.name || email };
  const id = String(profile.user_web_id || profile.user_id || profile.id || profile.sub || '');
  const role = profile.role || profile.user_role;
  if (id !== claims.sub || !authRoles.includes(role)) {
    throw new ApiError('El perfil devuelto por el servidor no corresponde a la sesión autenticada.', 401);
  }
  return profile;
}
