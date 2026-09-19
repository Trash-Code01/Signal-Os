import type { NextRequest } from 'next/server';

export function hasValidRequestOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  const host = request.headers.get('host');
  if (!origin || !host) return false;

  try {
    const parsedOrigin = new URL(origin);
    const forwardedProtocol = request.headers.get('x-forwarded-proto')?.split(',')[0]?.trim();
    const requestProtocol = forwardedProtocol || request.nextUrl.protocol.replace(':', '');
    return parsedOrigin.host === host && parsedOrigin.protocol === `${requestProtocol}:`;
  } catch {
    return false;
  }
}
