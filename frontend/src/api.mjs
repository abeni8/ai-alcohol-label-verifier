export class ApiError extends Error {
  constructor(message, code = 'request_failed', status = 0, retryAfter = null) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export async function api(path, options = {}) {
  let response;
  try { response = await fetch(path, options); }
  catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('The review server could not be reached. Check your connection and try again.', 'network_error');
  }
  let body;
  try { body = await response.json(); }
  catch { throw new ApiError('The server returned an unreadable response. Retry or contact the operator.', 'invalid_response', response.status); }
  if (!response.ok) {
    throw new ApiError(body.error?.message || 'The request could not be completed.', body.error?.code, response.status, response.headers.get('Retry-After'));
  }
  return body;
}

export async function verify(application, files, token = '', signal) {
  const body = new FormData();
  body.append('application', JSON.stringify(application));
  files.forEach(file => body.append('images', file));
  const start = performance.now();
  const result = await api('/api/verify', { method: 'POST', body, signal, headers: token ? { 'X-Review-Token': token } : {} });
  return { ...result, browser_elapsed_ms: Math.round(performance.now() - start) };
}

export function checkFiles(files, maxCount = 3) {
  if (!files.length) return 'Select at least one JPEG or PNG image.';
  if (files.length > maxCount) return `Select no more than ${maxCount} images.`;
  const names = new Set();
  for (const file of files) {
    if (!/\.(jpe?g|png)$/i.test(file.name) || !['image/jpeg', 'image/png'].includes(file.type)) return 'Only JPEG and PNG images are supported.';
    if (file.size === 0) return 'An uploaded image is empty.';
    if (file.size > 5 * 1024 * 1024) return 'Each image must be 5 MB or smaller.';
    if (names.has(file.name)) return 'Selected images must have unique filenames.';
    names.add(file.name);
  }
  return '';
}

export async function sampleFiles(names) {
  return Promise.all(names.map(async name => {
    const response = await fetch('/api/sample-files/' + encodeURIComponent(name));
    if (!response.ok) throw new ApiError('A sample image could not be loaded.');
    return new File([await response.blob()], name, { type: name.endsWith('.png') ? 'image/png' : 'image/jpeg' });
  }));
}
