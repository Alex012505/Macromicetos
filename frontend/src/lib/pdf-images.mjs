import { safeImageUrl } from './http.mjs';
export function isPdfImageUrl(url) {
  // Local uploads were decoded by PhotoPicker. Allow only raster data URLs;
  // keep active content and SVG data URLs out of the PDF image loader.
  return Boolean(safeImageUrl(url) || (typeof url === 'string' && /^data:image\/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=\r\n]+$/.test(url)));
}
