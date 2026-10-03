export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

/** HTTP transport. Tokens live in memory. A 401 is retried once, only if refresh is configured. */
export function createHttpClient({ baseUrl, fetchImpl = globalThis.fetch, timeoutMs = 15000, refreshPath = '', onSessionExpired = () => {} }) {
  let accessToken = '';
  let refreshToken = '';
  let refreshPromise = null;
  function setTokens(access = '', refresh = '') { accessToken = access; refreshToken = refresh; }
  function clearSession() { setTokens(); onSessionExpired(); }
  async function request(path, options = {}, retry = true) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const externalAbort = () => controller.abort();
    options.signal?.addEventListener('abort', externalAbort, { once: true });
    if (options.signal?.aborted) controller.abort();
    const headers = new Headers(options.headers);
    if (accessToken && options.auth !== false) headers.set('Authorization', `Bearer ${accessToken}`);
    const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData;
    if (options.body != null && !isForm) headers.set('Content-Type', 'application/json');
    headers.set('Accept', 'application/json');
    let response;
    let payload;
    try {
      response = await fetchImpl(`${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`, {
        method: options.method || 'GET', headers, signal: controller.signal,
        body: options.body == null ? undefined : isForm ? options.body : JSON.stringify(options.body),
      });
      const raw = await response.text();
      try { payload = raw ? JSON.parse(raw) : null; } catch { payload = null; }
    } catch (error) {
      if (options.signal?.aborted) throw new DOMException('Solicitud cancelada', 'AbortError');
      throw new ApiError(controller.signal.aborted ? 'El servidor tardó demasiado. Intenta nuevamente.' : 'No fue posible conectar con el servidor. Revisa que FastAPI esté disponible.', 0, error);
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener('abort', externalAbort);
    }
    if (response.status === 401 && options.auth !== false && accessToken) {
      if (retry && refreshPath && refreshToken) {
        if (!refreshPromise) refreshPromise = request(refreshPath, { method: 'POST', auth: false, body: { refreshToken } }, false)
          .then(data => {
            const token = data?.accessToken || data?.access_token;
            if (!token) throw new ApiError('El servidor no devolvió un token de acceso.', 401);
            setTokens(token, data.refreshToken || data.refresh_token || refreshToken);
          }).finally(() => { refreshPromise = null; });
        try { await refreshPromise; } catch (error) { clearSession(); throw error; }
        return request(path, options, false);
      }
      clearSession();
    }
    if (!response.ok) {
      const detail = payload?.detail || payload?.error || payload?.message;
      const message = Array.isArray(detail) ? detail.map(e => `${e.loc?.slice(1).join('.') || 'Campo'}: ${e.msg}`).join(' · ') : typeof detail === 'string' ? detail : `La solicitud falló (${response.status}).`;
      throw new ApiError(message, response.status, payload);
    }
    if (payload === null && response.status !== 204) throw new ApiError('El servidor no devolvió JSON válido. Revisa la URL de la API.', response.status);
    return payload;
  }
  return { request, setTokens, clearSession };
}

export function unwrapList(value) {
  const list = Array.isArray(value) ? value : value?.data || value?.items || value?.results;
  if (!Array.isArray(list)) throw new ApiError('La respuesta del servidor no contiene una lista válida.');
  return list;
}

export function safeImageUrl(value) {
  if (typeof value !== 'string') return undefined;
  try {
    const url = new URL(value, 'https://local.invalid');
    return ['https:', 'http:'].includes(url.protocol) ? value : undefined;
  } catch { return undefined; }
}
