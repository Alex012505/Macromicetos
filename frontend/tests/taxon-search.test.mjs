import test from 'node:test';
import assert from 'node:assert/strict';
import { searchTaxa } from '../src/lib/taxon-search.mjs';

const taxa = [
  { id: 'p', scientificName: 'Pleurotus ostreatus', commonName: 'Orellana', genus: 'Pleurotus', family: 'Pleurotaceae' },
  { id: 't', scientificName: 'Trametes versicolor', commonName: 'Cola de pavo', genus: 'Trametes', family: 'Polyporaceae' },
  { id: 'a', scientificName: 'Auricularia auricula-judae', commonName: 'Oreja de árbol', genus: 'Auricularia', family: 'Auriculariaceae' },
];
test('record search finds registered taxa by scientific, common, genus or family names', () => {
  for (const query of ['pleurotus', 'OSTREATUS', 'orellana', 'Pleurotaceae']) assert.equal(searchTaxa(taxa, query)[0].id, 'p');
  assert.deepEqual(searchTaxa(taxa, 'Trametes versicolor').map(t => t.id), ['t']);
});
test('record search handles accents, whitespace and multiple words', () => {
  assert.deepEqual(searchTaxa(taxa, '  oreja arbol ').map(t => t.id), ['a']);
  assert.deepEqual(searchTaxa(taxa, '  ').map(t => t.id), ['p', 't', 'a']);
});
test('no matches leaves the catalog unchanged and allows the creation alternative', () => {
  assert.deepEqual(searchTaxa(taxa, 'Especie nueva'), []); assert.equal(taxa.length, 3);
  assert.deepEqual(searchTaxa([], 'Especie nueva'), []);
});
