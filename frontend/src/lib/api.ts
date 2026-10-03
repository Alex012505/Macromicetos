import { createHttpClient, unwrapList, safeImageUrl, ApiError } from './http.mjs';
import type { Taxon, Occurrence, User, Role, Status } from '../types';

export const config = {
  demo: import.meta.env.VITE_DATA_MODE !== 'api',
  baseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  occurrencesPath: import.meta.env.VITE_OCCURRENCES_LIST_PATH || '',
  curatePath: import.meta.env.VITE_CURATE_PATH || '',
  usersPath: import.meta.env.VITE_USERS_PATH || '',
  userUpdatePath: import.meta.env.VITE_USER_UPDATE_PATH || '',
  refreshPath: import.meta.env.VITE_REFRESH_PATH || '',
  mePath: import.meta.env.VITE_ME_PATH || '',
};
export const http = createHttpClient({ baseUrl: config.baseUrl, refreshPath: config.refreshPath,
  onSessionExpired: () => window.dispatchEvent(new Event('macromicetos-session-expired')) });
const id = (value: unknown) => String(value ?? '');
const status = (value: unknown): Status => ({ verified: 'verified', approved: 'verified', verificado: 'verified', pending: 'pending', rejected: 'rejected' } as Record<string, Status>)[String(value).toLowerCase()] || 'unknown';
const coordinate = (value: unknown, limit: number) => {
  if (value == null || value === '') return null;
  const n = Number(value); return Number.isFinite(n) && Math.abs(n) <= limit ? n : null;
};
export function normalizeTaxon(raw: any): Taxon {
  const key = id(raw.taxonID || raw.taxon_id || raw.id);
  if (!key) throw new ApiError('Un taxón llegó sin identificador. Revisa el contrato de la API.');
  return { id: key, scientificName: raw.scientificName || raw.scientific_name || 'Sin identificación',
    commonName: raw.commonName_es || raw.common_name_es || raw.common_name || '', kingdom: raw.kingdom || '',
    phylum: raw.phylum || '', className: raw.class || '', order: raw.order || '', family: raw.family || '',
    genus: raw.genus || '', remarks: raw.taxonRemarks || raw.remarks || '',
    image: safeImageUrl(raw.image || raw.image_url), status: status(raw.status) };
}
export function normalizeOccurrence(raw: any): Occurrence {
  const location = raw.event?.location || raw.location || {};
  const key = id(raw.occurrence_id || raw.id);
  if (!key) throw new ApiError('La ocurrencia llegó sin identificador.');
  return { id: key, ownerId: id(raw.owner_id || raw.created_by_id || raw.user_id) || undefined, taxonId: id(raw.taxon_id || raw.taxon?.taxonID || raw.taxon?.taxon_id),
    eventId: id(raw.event_id || raw.event?.event_id), author: raw.identified_by || raw.event?.recorded_by || '',
    date: raw.date_identified || raw.event?.event_date || '',
    department: location.state_province || '', locality: location.locality || location.municipality || '',
    lat: coordinate(location.decimal_latitude, 90), lng: coordinate(location.decimal_longitude, 180),
    substrate: raw.substrate || '', habitat: location.habitat || '', remarks: raw.occurrence_remarks || '',
    status: status(raw.status), reviewNote: raw.review_note,
    images: (raw.multimedia || []).map((m: any) => safeImageUrl(m.source_url || m.access_uri || m.url || m.image_url)).filter(Boolean),
    measurements: (raw.measurements || []).map((m: any) => ({ name: m.measurement_type, value: m.measurement_value, unit: m.measurement_unit })),
  };
}
export function normalizeUser(raw: any): User {
  const roles: Role[] = ['readonly_user', 'researcher', 'curator', 'admin'];
  const incoming = raw.role || raw.user_role;
  return { id: id(raw.user_id || raw.id || raw.sub), email: raw.email || '',
    name: raw.name || [raw.first_name, raw.last_name].filter(Boolean).join(' ') || raw.email || 'Mi cuenta',
    role: roles.includes(incoming) ? incoming : 'readonly_user' };
}
export const api = {
  async taxa(search = '') { return unwrapList(await http.request(`/taxa${search ? `?search=${encodeURIComponent(search)}` : ''}`)).map(normalizeTaxon); },
  async taxon(taxonId: string) { return normalizeTaxon(await http.request(`/taxa/${encodeURIComponent(taxonId)}`)); },
  async occurrences() { return config.occurrencesPath ? unwrapList(await http.request(config.occurrencesPath)).map(normalizeOccurrence) : []; },
  async occurrence(occurrenceId: string) { return normalizeOccurrence(await http.request(`/occurrences/${encodeURIComponent(occurrenceId)}`)); },
  async users() { return config.usersPath ? unwrapList(await http.request(config.usersPath)).map(normalizeUser) : []; },
  async updateUserRole(userId: string, role: Role) {
    if (!config.userUpdatePath) throw new ApiError('El backend debe definir la actualización de roles.');
    return http.request(config.userUpdatePath.replace('{id}', encodeURIComponent(userId)), { method: 'PATCH', body: { role } });
  },
  async login(email: string, password: string): Promise<User> {
    const data = await http.request('/auth/login', { method: 'POST', body: { email, password }, auth: false });
    const token = data?.access_token || data?.accessToken || data?.token;
    if (!token) throw new ApiError('El contrato de login no devuelve un token. El equipo backend debe retornar access_token y el perfil del usuario.');
    http.setTokens(token, data.refresh_token || data.refreshToken || '');
    let profile = data.userProfile || data.user || data.profile;
    if (!profile && config.mePath) {
      try { profile = await http.request(config.mePath); } catch (error) { http.setTokens(); throw error; }
    }
    // Sin perfil, la interfaz conserva el mínimo privilegio. No confía en un rol editable por el cliente.
    return normalizeUser(profile || { email });
  },
  register(body: { email: string; password: string; first_name: string; last_name: string }) {
    return http.request('/auth/register', { method: 'POST', body, auth: false });
  },
  createTaxon(taxon: Taxon) {
    return http.request('/taxa', { method: 'POST', body: {
      scientificName: taxon.scientificName, commonName_es: taxon.commonName, taxonRank: 'species',
      kingdom: taxon.kingdom, phylum: taxon.phylum, class: taxon.className, order: taxon.order,
      family: taxon.family, genus: taxon.genus, species: taxon.scientificName.split(' ').slice(1).join(' '), taxonRemarks: taxon.remarks,
    } });
  },
  saveOccurrence(o: Occurrence) {
    return http.request(`/occurrences/${encodeURIComponent(o.id)}`, { method: 'POST', body: {
      event_id: o.eventId, taxon_id: o.taxonId, basis_of_record: 'HumanObservation', substrate: o.substrate,
      identified_by: o.author, date_identified: o.date, occurrence_remarks: o.remarks,
    } });
  },
  curate(o: Occurrence, next: Status, note: string) {
    if (!config.curatePath) throw new ApiError('El endpoint de curaduría está pendiente de definición con el equipo backend.');
    return http.request(config.curatePath.replace('{id}', encodeURIComponent(o.id)), { method: 'PATCH', body: { status: next, review_note: note } });
  },
  upload(file: File, occurrenceId: string, photoType: string) {
    const body = new FormData(); body.append('file', file); body.append('occurrence_id', occurrenceId); body.append('photo_type', photoType);
    return http.request('/multimedia/upload', { method: 'POST', body });
  },
};
