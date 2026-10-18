const searchable = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').trim();
export function searchTaxa(taxa, query) {
  const words = searchable(query).split(/\s+/).filter(Boolean);
  return taxa.filter(taxon => {
    const text = searchable([taxon.scientificName, taxon.commonName, taxon.genus, taxon.family].join(' '));
    return words.every(word => text.includes(word));
  });
}
