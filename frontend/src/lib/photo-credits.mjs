// Credits shipped with the local reference photographs (public/images/CREDITOS.md).
export function referencePhotoCredit(url) {
  if (typeof url !== 'string' || !url.startsWith('/')) return undefined;
  if (url.endsWith('/images/pleurotus.jpg')) return { photographer: 'Jean-Pol GRANDMONT', rightsHolder: 'Jean-Pol GRANDMONT', license: 'https://creativecommons.org/licenses/by/3.0/', sourceUrl: 'https://commons.wikimedia.org/wiki/File:Pleurotus_ostreatus_JPG7.jpg' };
  if (url.endsWith('/images/trametes.jpg')) return { photographer: 'National Park Service, NPS Photo', rightsHolder: 'National Park Service', license: 'Dominio público en EE. UU.', sourceUrl: 'https://commons.wikimedia.org/wiki/File:Turkey-tail_Trametes_versicolor.JPG_(87dbc148-05ec-4dbb-a830-1194b3d8d3aa).JPG' };
  return undefined;
}
