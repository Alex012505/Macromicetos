export type Role = 'viewer' | 'analyst' | 'curator' | 'admin';
export type Status = 'verified' | 'pending' | 'rejected' | 'unknown';
export interface User { id: string; name: string; email: string; role: Role; expiresAt?: number }
export interface Taxon {
  ownerId?: string;
  id: string; scientificName: string; commonName: string; kingdom: string;
  phylum: string; className: string; order: string; family: string; genus: string;
  remarks: string; image?: string; status: Status;
  rank?: string; specificEpithet?: string; externalTaxonId?: string;
  morphology?: MorphologyFact[]; sources?: ScientificSource[];
  knowledge?: EthnoSurvey[]; participants?: Participant[];
}
export interface MorphologyFact {
  type: string; value: string; unit?: string; determinedDate?: string; remarks?: string;
}
export interface Measurement { name: string; value: string; unit?: string; scope?: 'event' | 'occurrence' }
export interface PhotoMetadata {
  id?: string; url: string; fileName?: string; photoType: string; photographer?: string;
  license?: string; rightsHolder?: string; mimeFormat?: string; sourceUrl?: string;
  blurScore?: number | null; qcPassed?: boolean | null;
  credits?: Participant[];
}
export interface PendingPhoto { id: string; file: File; preview: string; metadata: PhotoMetadata }
export interface Participant {
  id: string; partyId?: string; givenName: string; familyName?: string; displayName: string;
  orcid?: string; affiliation?: string; contactEmail?: string; role: string;
  scope?: 'event' | 'occurrence'; isPrimary?: boolean;
}
export interface ScientificSource { id: string; sourceType: string; title?: string; authors?: string; year?: string; doi?: string }
export interface EthnoUse {
  id: string; useCategory: string; importance?: string; preparationMethod?: string;
  ailment?: string; dosage?: string; contraindications?: string; recommendations?: string;
}
export interface EthnoSurvey {
  knowledgeId?: string;
  id: string; interviewDate: string; interviewer: string; consentGiven: boolean;
  consentType?: string; anonymityLevel: string; ageRange?: string; gender?: string;
  occupation?: string; stateProvince?: string; municipality?: string; village?: string; remarks?: string;
  knowsFungi: boolean; localName?: string; learningSource?: string; recognitionCues?: string;
  foundInPlaces?: string; seasonality?: string; months?: string; safetyPractices?: string;
  mythsStories?: string; culturalIdentity?: string; uses: EthnoUse[];
}
export interface Occurrence {
  ownerId?: string;
  createdById?: string;
  id: string; taxonId: string; eventId: string; author: string; date: string;
  department: string; locality: string; lat: number | null; lng: number | null;
  substrate: string; habitat: string; remarks: string; status: Status;
  images: string[]; measurements: Measurement[];
  reviewNote?: string;
  country?: string; municipality?: string; uncertaintyM?: number | null; elevationM?: number | null;
  locationRemarks?: string; locationSource?: 'device' | 'map' | 'manual'; locationId?: string;
  eventType?: string; fieldNumber?: string; eventDate?: string; recordedBy?: string;
  samplingProtocol?: string; samplingEffort?: string; eventRemarks?: string;
  basisOfRecord?: string; externalOccurrenceId?: string; occurrenceDate?: string;
  morphology?: MorphologyFact[]; photos?: PhotoMetadata[]; participants?: Participant[];
}
export interface Dataset { taxa: Taxon[]; occurrences: Occurrence[]; users: User[] }
export const roleNames: Record<Role, string> = { viewer: 'Visitante', analyst: 'Investigador', curator: 'Curador', admin: 'Administrador' };
export const statusNames: Record<Status, string> = { verified: 'Verificado', pending: 'En revisión', rejected: 'Requiere ajustes', unknown: 'Sin estado' };
