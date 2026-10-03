export type Role = 'readonly_user' | 'researcher' | 'curator' | 'admin';
export type Status = 'verified' | 'pending' | 'rejected' | 'unknown';
export interface User { id: string; name: string; email: string; role: Role }
export interface Taxon {
  id: string; scientificName: string; commonName: string; kingdom: string;
  phylum: string; className: string; order: string; family: string; genus: string;
  remarks: string; image?: string; status: Status;
}
export interface Occurrence {
  ownerId?: string;
  id: string; taxonId: string; eventId: string; author: string; date: string;
  department: string; locality: string; lat: number | null; lng: number | null;
  substrate: string; habitat: string; remarks: string; status: Status;
  images: string[]; measurements: { name: string; value: string; unit?: string }[];
  reviewNote?: string;
}
export interface Dataset { taxa: Taxon[]; occurrences: Occurrence[]; users: User[] }
export const roleNames: Record<Role, string> = { readonly_user: 'Visitante', researcher: 'Investigador', curator: 'Curador', admin: 'Administrador' };
export const statusNames: Record<Status, string> = { verified: 'Verificado', pending: 'En revisión', rejected: 'Requiere ajustes', unknown: 'Sin estado' };
