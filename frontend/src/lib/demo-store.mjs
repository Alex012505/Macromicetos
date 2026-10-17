// IndexedDB keeps complete photo-bearing demo records beyond localStorage's
// small synchronous quota. Only report success after the transaction commits.
const databaseName = 'macromicetos-local';
async function openDatabase() {
  if (!globalThis.indexedDB) throw new Error('Este navegador no permite el almacenamiento local de fotografías.');
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(databaseName, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('datasets');
    request.onerror = () => reject(new Error('No se pudo abrir el almacenamiento local. Revisa los permisos del navegador.'));
    request.onblocked = () => reject(new Error('Otra pestaña está bloqueando el almacenamiento local. Ciérrala y vuelve a intentar.'));
    request.onsuccess = () => resolve(request.result);
  });
}
async function transaction(mode, operation) {
  const database = await openDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const tx = database.transaction('datasets', mode); let value;
      const request = operation(tx.objectStore('datasets'));
      request.onsuccess = () => { value = request.result; };
      tx.oncomplete = () => resolve(value);
      tx.onabort = () => reject(new Error('No se pudo guardar la información local: el almacenamiento está bloqueado o lleno. Conserva el formulario abierto y libera espacio.'));
      tx.onerror = () => { /* onabort handles the transaction failure. */ };
    });
  } finally { database.close(); }
}
export const readDemoDataset = () => transaction('readonly', store => store.get('current'));
export const writeDemoDataset = dataset => transaction('readwrite', store => store.put(dataset, 'current'));
export const clearDemoDataset = () => transaction('readwrite', store => store.delete('current'));
