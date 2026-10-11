// The ONE place that talks to the backend: adds the token, unwraps the {data} envelope and
// turns {error:{code,message}} into ApiError. Components never call fetch() directly.
import { env } from '@/lib/env';
import { getSession } from '@/lib/session';
import { ApiError, ERROR_CODES } from './errors';

interface RequestOptions {
  body?: unknown;
  auth?: boolean;
}

export async function request<T>(
  method: string,
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
  const token = opts.auth === false ? null : getSession()?.accessToken;
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(new URL(path, env.apiUrl), {
      method,
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    });
  } catch {
    throw new ApiError(
      0,
      ERROR_CODES.network,
      'Cannot reach the EMS server. Check your connection and try again.',
    );
  }

  if (response.status === 204) return undefined as T;
  let json: { data?: T; error?: { code: string; message: string } } = {};
  try {
    json = await response.json();
  } catch {
    /* handled below */
  }
  if (!response.ok) {
    throw new ApiError(
      response.status,
      json.error?.code ?? ERROR_CODES.unknown,
      json.error?.message ?? `Request failed (${response.status}).`,
    );
  }
  return json.data as T;
}

export const api = {
  post: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'body'>) =>
    request<T>('POST', path, { ...opts, body }),
  get: <T>(path: string, opts?: RequestOptions) => request<T>('GET', path, opts),
};
