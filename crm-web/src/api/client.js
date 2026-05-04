const BASE = import.meta.env.VITE_API_BASE || '/api/crm';

export class ApiError extends Error {
  constructor(status, body, message) {
    super(message || `API error ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export class UnauthorizedError extends ApiError {
  constructor(body) {
    super(401, body, 'Unauthorized');
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends ApiError {
  constructor(body) {
    super(403, body, 'Forbidden');
    this.name = 'ForbiddenError';
  }
}

export class NotFoundError extends ApiError {
  constructor(body) {
    super(404, body, 'Not Found');
    this.name = 'NotFoundError';
  }
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|;)\\s*${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function parseBody(response) {
  const ct = response.headers.get('content-type') || '';
  if (response.status === 204) return null;
  if (ct.includes('application/json')) return response.json();
  return response.text();
}

function paginationFromHeaders(headers) {
  const total = parseInt(headers.get('X-Total-Count') || '0', 10);
  const page = parseInt(headers.get('X-Page') || '1', 10);
  const pageSize = parseInt(headers.get('X-Page-Size') || '0', 10) || total || 1;
  return {
    total,
    page,
    pageSize,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
  };
}

async function request(path, { method = 'GET', body, query } = {}) {
  let url = `${BASE}${path}`;
  if (query) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    }
    const qsString = qs.toString();
    if (qsString) url += `?${qsString}`;
  }

  const headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
  if (method !== 'GET') {
    const csrf = getCookie('csrftoken');
    if (csrf) headers['X-CSRFToken'] = csrf;
  }

  const response = await fetch(url, {
    method,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errBody = await parseBody(response).catch(() => null);
    if (response.status === 401) throw new UnauthorizedError(errBody);
    if (response.status === 403) throw new ForbiddenError(errBody);
    if (response.status === 404) throw new NotFoundError(errBody);
    throw new ApiError(response.status, errBody);
  }

  const data = await parseBody(response);
  return { data, pagination: paginationFromHeaders(response.headers) };
}

export const apiGet = (path, query) => request(path, { query });
export const apiPost = (path, body) => request(path, { method: 'POST', body });
