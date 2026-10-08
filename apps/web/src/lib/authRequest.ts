export class AuthRequestError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = 'AuthRequestError';
  }
}

// The deadline covers both the connection and reading the response body.
export async function authRequest(
  url: string,
  init: RequestInit = {},
  timeoutMs = 65_000,
): Promise<Record<string, unknown>> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (init.signal?.aborted) controller.abort();
  init.signal?.addEventListener('abort', cancel, { once: true });
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...init, cache: 'no-store', credentials: 'include', signal: controller.signal });
    const text = await response.text();
    let data: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(text);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error();
      data = parsed as Record<string, unknown>;
    } catch {
      throw new AuthRequestError('Sign-in service is unavailable. Please wait a moment and retry.', 503);
    }
    if (!response.ok) {
      throw new AuthRequestError(
        typeof data.detail === 'string' ? data.detail : 'Sign-in could not be completed. Please retry.',
        response.status,
      );
    }
    return data;
  } catch (error) {
    if (error instanceof AuthRequestError) throw error;
    throw new AuthRequestError(
      controller.signal.aborted
        ? 'Sign-in service took too long to respond. Please retry in a moment.'
        : 'Unable to connect to the sign-in service. Please retry.',
      503,
    );
  } finally {
    clearTimeout(timer);
    init.signal?.removeEventListener('abort', cancel);
  }
}
