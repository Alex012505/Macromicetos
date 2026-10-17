// Explicit adapters for the proposed full-record contract. No field is silently
// dropped through the older, basic OccurrenceInput endpoint.
const nullable = value => value === '' || value === undefined ? null : value;
const mapFields = (value, mapping) => Object.fromEntries(Object.entries(mapping).map(([front, back]) => [back, nullable(value[front])]));
export const sourceFields = { id: 'source_id', sourceType: 'source_type', title: 'title', authors: 'authors', year: 'year', doi: 'doi' };
export const surveyFields = { id: 'ethno_source_id', interviewDate: 'interview_date', interviewer: 'interviewer', consentGiven: 'consent_given', consentType: 'consent_type', anonymityLevel: 'anonymity_level', ageRange: 'age_range', gender: 'gender', occupation: 'occupation', stateProvince: 'state_province', municipality: 'municipality', village: 'village', remarks: 'remarks' };
export const knowledgeFields = { knowsFungi: 'knows_fungi', localName: 'local_name', learningSource: 'learning_source', recognitionCues: 'recognition_cues', foundInPlaces: 'found_in_places', seasonality: 'seasonality', months: 'months', safetyPractices: 'safety_practices', mythsStories: 'myths_stories', culturalIdentity: 'cultural_identity' };
export const useFields = { id: 'use_id', useCategory: 'use_category', importance: 'importance', preparationMethod: 'preparation_method', ailment: 'ailment', dosage: 'dosage', contraindications: 'contraindications', recommendations: 'recommendations' };
export const fromFields = (value, mapping) => Object.fromEntries(Object.entries(mapping).map(([front, back]) => [front, value[back] ?? value[front] ?? '']));
export function morphologyPayload(facts, link) {
  return (facts || []).map(m => ({ ...link, measurement_type: m.type, measurement_value: m.value.trim(), measurement_unit: nullable(m.unit), measurement_determined_date: nullable(m.determinedDate), measurement_remarks: nullable(m.remarks) }));
}
export function normalizeMorphology(facts = []) {
  return facts.map(m => ({ type: m.measurement_type ?? m.type, value: m.measurement_value ?? m.value, unit: m.measurement_unit ?? m.unit ?? '', determinedDate: m.measurement_determined_date ?? m.determinedDate ?? '', remarks: m.measurement_remarks ?? m.remarks ?? '' }));
}
export function participantsPayload(participants = []) {
  return participants.map(p => ({ party: { party_id: p.partyId || p.id, ...mapFields(p, { givenName: 'given_name', familyName: 'family_name', displayName: 'display_name', orcid: 'orcid', affiliation: 'affiliation', contactEmail: 'contact_email' }) }, party_role: p.role, scope: p.scope, is_primary: !!p.isPrimary }));
}
export function normalizeParticipants(participants = []) {
  return participants.map(p => ({ ...fromFields(p.party || p, { familyName: 'family_name', orcid: 'orcid', affiliation: 'affiliation', contactEmail: 'contact_email' }), givenName: p.party?.given_name || p.given_name || p.givenName || '', displayName: p.party?.display_name || p.display_name || p.displayName || '', id: p.party?.party_id || p.party_id || p.id, partyId: p.party?.party_id || p.party_id, role: p.party_role || p.role || 'observer', scope: p.scope || 'occurrence', isPrimary: p.is_primary ?? p.isPrimary ?? false }));
}
export function recordPayload(o) {
  return {
    location: { location_id: o.locationId, ...mapFields(o, { country: 'country', department: 'state_province', municipality: 'municipality', locality: 'locality', lat: 'decimal_latitude', lng: 'decimal_longitude', uncertaintyM: 'coordinate_uncertainty_m', elevationM: 'elevation_m', habitat: 'habitat', locationRemarks: 'location_remarks' }) },
    event: { event_id: o.eventId, location_id: o.locationId, ...mapFields(o, { eventType: 'event_type', fieldNumber: 'field_number', eventDate: 'event_date', recordedBy: 'recorded_by', samplingProtocol: 'sampling_protocol', samplingEffort: 'sampling_effort', eventRemarks: 'event_remarks' }) },
    occurrence: { occurrence_id: o.id, event_id: o.eventId, taxon_id: o.taxonId || null, ...mapFields(o, { externalOccurrenceId: 'external_occurrence_id', basisOfRecord: 'basis_of_record', recordedBy: 'recorded_by', occurrenceDate: 'event_date', substrate: 'substrate', author: 'identified_by', date: 'date_identified', remarks: 'occurrence_remarks' }) },
    morphology: morphologyPayload(o.morphology, { occurrence_id: o.id, taxon_id: null }),
    measurements: (o.measurements || []).map(m => ({ event_id: m.scope === 'event' ? o.eventId : null, occurrence_id: m.scope === 'event' ? null : o.id, measurement_type: m.name, measurement_value: m.value, measurement_unit: nullable(m.unit) })),
    participants: participantsPayload(o.participants),
  };
}
export function taxonPayload(t) {
  return {
    taxon: { taxon_id: t.id, ...mapFields(t, { scientificName: 'scientific_name', commonName: 'common_name_es', rank: 'taxon_rank', kingdom: 'kingdom', phylum: 'phylum', className: 'class', order: 'order', family: 'family', genus: 'genus', specificEpithet: 'specific_epithet', externalTaxonId: 'external_taxon_id', remarks: 'taxon_remarks' }) },
    morphology: morphologyPayload(t.morphology, { taxon_id: t.id, occurrence_id: null }),
    sources: (t.sources || []).map(s => ({ ...mapFields(s, sourceFields), year: s.year ? Number(s.year) : null })),
    knowledge: (t.knowledge || []).map(k => ({ source: { ...mapFields(k, surveyFields), interview_date: k.interviewDate ? `${k.interviewDate.slice(0, 10)}T12:00:00-05:00` : null }, knowledge: { ...mapFields(k, knowledgeFields), knowledge_id: k.knowledgeId || k.id, ethno_source_id: k.id, taxon_id: t.id }, uses: k.uses.map(u => ({ ...mapFields(u, useFields), knowledge_id: k.knowledgeId || k.id })) })),
    participants: participantsPayload(t.participants),
  };
}
export function photoPayload(p) {
  return { media_id: p.id, photo_type: p.metadata.photoType, file_name: p.file.name, mime_format: p.file.type, media_type: 'StillImage', photographer: nullable(p.metadata.photographer), license: nullable(p.metadata.license), rights_holder: nullable(p.metadata.rightsHolder), credits: participantsPayload(p.metadata.credits).map(({ party, party_role, is_primary }) => ({ party, credit_role: party_role, is_primary })) };
}
export function bundleForm(payload, photos = []) {
  const body = new FormData();
  body.append('payload', JSON.stringify({ ...payload, multimedia: photos.map(photoPayload) }));
  for (const p of photos) body.append(`file_${p.id}`, p.file, p.file.name);
  return body;
}
export function bundlePath(path, id, label) {
  if (!path || !path.includes('{id}')) throw new Error(`El servidor aún no tiene habilitado el guardado completo de ${label}. Conserva el formulario abierto y solicita habilitar esta función.`);
  return path.replace('{id}', encodeURIComponent(id));
}
