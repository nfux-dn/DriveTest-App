// Small fetch wrapper. Always sends credentials so the session cookie flows,
// and normalizes the backend error envelope (spec section 39).

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface ApiErrorShape {
  code: string;
  message: string;
  details: unknown;
  request_id: string;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(status: number, body: ApiErrorShape | null, fallback: string) {
    super(body?.message ?? fallback);
    this.code = body?.code ?? "UNKNOWN";
    this.status = status;
    this.details = body?.details ?? null;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const envelope = (data && data.error) as ApiErrorShape | undefined;
    throw new ApiError(res.status, envelope ?? null, res.statusText);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};
