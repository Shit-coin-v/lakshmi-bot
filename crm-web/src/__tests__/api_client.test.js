import { describe, it, expect } from 'vitest';
import { ApiError, UnauthorizedError, ForbiddenError, NotFoundError } from '../api/client.js';

describe('API error classes', () => {
  it('exposes status', () => {
    const e = new ApiError(500, { detail: 'boom' });
    expect(e.status).toBe(500);
    expect(e.body.detail).toBe('boom');
  });

  it('UnauthorizedError is ApiError', () => {
    const e = new UnauthorizedError({});
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(401);
  });

  it('ForbiddenError, NotFoundError have right status', () => {
    expect(new ForbiddenError({}).status).toBe(403);
    expect(new NotFoundError({}).status).toBe(404);
  });
});
