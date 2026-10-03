/** Build URLs for public files under either localhost or a project Pages path. */
export function publicAssetUrl(path, baseUrl = '/') {
  return `${baseUrl.replace(/\/?$/, '/')}${path.replace(/^\/+/, '')}`;
}

/** Repair only bundled demo photographs; keep uploaded and remote media intact. */
export function normalizeDemoImage(value, baseUrl = '/') {
  if (typeof value !== 'string') return value;
  const photo = value.match(/^\/(?:Macromicetos\/)?images\/(pleurotus|trametes)\.jpg$/);
  return photo ? publicAssetUrl(`images/${photo[1]}.jpg`, baseUrl) : value;
}
