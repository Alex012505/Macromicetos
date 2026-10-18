import { createHttpClient, unwrapList, safeImageUrl, ApiError } from './http.mjs';
import type { Taxon, Occurrence, User, Role, Status, PendingPhoto, EthnoSurvey } from '../types';
import { bundleForm, bundlePath, recordPayload, taxonPayload, normalizeMorphology, normalizeParticipants, fromFields, sourceFields, surveyFields, knowledgeFields, useFields } from './record-contract.mjs';

export const config = {
  demo: import.meta.env.VITE_DATA_MODE !== 'api',
  baseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  occurrencesPath: import.meta.env.VITE_OCCURRENCES_LIST_PATH || '',
  curatePath: import.meta.env.VITE_CURATE_PATH || '',
  usersPath: import.meta.env.VITE_USERS_PATH || '',
  userUpdatePath: import.meta.env.VITE_USER_UPDATE_PATH || '',
  refreshPath: import.meta.env.VITE_REFRESH_PATH || '',
  mePath: import.meta.env.VITE_ME_PATH || '',
  recordBundlePath: import.meta.env.VITE_RECORD_BUNDLE_PATH || '',
  taxonBundlePath: import.meta.env.VITE_TAXON_BUNDLE_PATH || '',
  mediaBundlePath: import.meta.env.VITE_MEDIA_BUNDLE_PATH || '',
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
  if (!raw || typeof raw !== 'object') throw new ApiError('El servidor no devolvió la ficha taxonómica guardada.');
  raw = raw.taxon ? { ...raw.taxon, ...raw, taxon: undefined } : raw;
  const key = id(raw.taxonID || raw.taxon_id || raw.id);
  if (!key) throw new ApiError('Un taxón llegó sin identificador. Revisa el contrato de la API.');
  return { id: key, scientificName: raw.scientificName || raw.scientific_name || 'Sin identificación',
    commonName: raw.commonName_es || raw.common_name_es || raw.common_name || '', kingdom: raw.kingdom || '',
    phylum: raw.phylum || '', className: raw.class || raw.class_ || '', order: raw.order || raw.order_ || '', family: raw.family || '',
    genus: raw.genus || '', remarks: raw.taxonRemarks || raw.taxon_remarks || raw.remarks || '',
    ownerId: raw.owner_id, rank: raw.taxon_rank || raw.taxonRank || 'species', specificEpithet: raw.specific_epithet || raw.species || '', externalTaxonId: raw.external_taxon_id || raw.externalTaxonID || '',
    morphology: normalizeMorphology(raw.morphology || raw.morphology_facts || []),
    participants: normalizeParticipants(raw.participants), sources: (raw.sources || []).map((s: any) => fromFields(s, sourceFields)),
    knowledge: (raw.knowledge || []).map((s: any) => ({ ...fromFields(s.source || s, surveyFields), ...fromFields(s.knowledge || s, knowledgeFields), knowledgeId: s.knowledge?.knowledge_id || s.knowledge_id || s.knowledgeId, interviewDate: (s.source?.interview_date || s.interview_date || s.interviewDate || '').slice(0, 10), uses: (s.uses || []).map((u: any) => fromFields(u, useFields)) })) as EthnoSurvey[],
    image: safeImageUrl(raw.image || raw.image_url), status: status(raw.status) };
}
export function normalizeOccurrence(raw: any): Occurrence {
  if (!raw || typeof raw !== 'object') throw new ApiError('El servidor no devolvió el hallazgo guardado.');
  raw = raw.occurrence ? { ...raw.occurrence, ...raw, occurrence: undefined } : raw;
  const location = raw.event?.location || raw.location || {};
  const key = id(raw.occurrence_id || raw.id);
  if (!key) throw new ApiError('La ocurrencia llegó sin identificador.');
  return { id: key, ownerId: id(raw.owner_id || raw.user_id) || undefined, createdById: id(raw.created_by_id) || undefined, taxonId: id(raw.taxon_id || raw.taxon?.taxonID || raw.taxon?.taxon_id),
    eventId: id(raw.event_id || raw.event?.event_id), author: raw.identified_by || '',
    date: raw.date_identified || '',
    department: location.state_province || '', locality: location.locality || location.municipality || '',
    lat: coordinate(location.decimal_latitude, 90), lng: coordinate(location.decimal_longitude, 180),
    substrate: raw.substrate || '', habitat: location.habitat || '', remarks: raw.occurrence_remarks || '',
    status: status(raw.status), reviewNote: raw.review_note,
    country: location.country || '', municipality: location.municipality || '', locationId: location.location_id,
    uncertaintyM: location.coordinate_uncertainty_m == null ? null : Number(location.coordinate_uncertainty_m), elevationM: location.elevation_m == null ? null : Number(location.elevation_m), locationRemarks: location.location_remarks || '',
    eventType: raw.event?.event_type || '', fieldNumber: raw.event?.field_number || '', eventDate: raw.event?.event_date || raw.event_date?.slice(0, 10) || '',
    recordedBy: raw.recorded_by || raw.event?.recorded_by || '', samplingProtocol: raw.event?.sampling_protocol || '', samplingEffort: raw.event?.sampling_effort || '', eventRemarks: raw.event?.event_remarks || '',
    basisOfRecord: raw.basis_of_record || '', externalOccurrenceId: raw.external_occurrence_id || '', occurrenceDate: raw.event_date || '',
    morphology: normalizeMorphology(raw.morphology || raw.morphology_facts || []), participants: normalizeParticipants(raw.participants),
    photos: (raw.multimedia || []).map((m: any) => ({ id: m.media_id, url: safeImageUrl(m.source_url || m.access_uri || m.url || m.image_url), photoType: m.photo_type, fileName: m.file_name, photographer: m.photographer, rightsHolder: m.rights_holder, license: m.license, mimeFormat: m.mime_format, sourceUrl: m.source_url, blurScore: m.blur_score, qcPassed: m.qc_passed, credits: normalizeParticipants((m.credits || []).map((credit: any) => ({ ...credit, party_role: credit.credit_role || credit.party_role }))) })).filter((p: any) => p.url),
    images: (raw.multimedia || []).map((m: any) => safeImageUrl(m.source_url || m.access_uri || m.url || m.image_url)).filter(Boolean),
    measurements: (raw.measurements || []).map((m: any) => ({ name: m.measurement_type, value: m.measurement_value, unit: m.measurement_unit, scope: m.occurrence_id ? 'occurrence' : 'event' })),
  };
}
export function normalizeUser(raw: any): User {
  const roles: Role[] = ['readonly_user', 'researcher', 'curator', 'admin'];
  const value = raw.role || raw.user_role;
  const incoming = ({ viewer: 'readonly_user', analyst: 'readonly_user', field_collector: 'researcher' } as Record<string, string>)[value] || value;
  return { id: id(raw.user_web_id || raw.user_id || raw.id || raw.sub), email: raw.email || '',
    name: raw.party?.display_name || raw.name || [raw.first_name, raw.last_name].filter(Boolean).join(' ') || raw.email || 'Mi cuenta',
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
    return http.request(config.userUpdatePath.replace('{id}', encodeURIComponent(userId)), { method: 'PATCH', body: { role: ({ readonly_user: 'viewer', researcher: 'field_collector', curator: 'curator', admin: 'admin' } as Record<Role, string>)[role] } });
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
  async createTaxon(taxon: Taxon) {
    return normalizeTaxon(await http.request(bundlePath(config.taxonBundlePath, taxon.id, 'fichas taxonómicas'), { method: 'PUT', body: taxonPayload(taxon) }));
  },
  async saveOccurrence(o: Occurrence, photos: PendingPhoto[] = []) {
    return normalizeOccurrence(await http.request(bundlePath(config.recordBundlePath, o.id, 'hallazgos'), { method: 'PUT', body: bundleForm(recordPayload(o), photos) }));
  },
  async addPhotos(occurrenceId: string, photos: PendingPhoto[]) {
    return normalizeOccurrence(await http.request(bundlePath(config.mediaBundlePath, occurrenceId, 'fotografías'), { method: 'PUT', body: bundleForm({ occurrence_id: occurrenceId }, photos) }));
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
