import { NextRequest, NextResponse } from 'next/server';
import { hasValidRequestOrigin } from '@/lib/requestOrigin';
export async function POST(request: NextRequest) {
  if (!hasValidRequestOrigin(request)) return NextResponse.json({ detail: 'Invalid request origin' }, { status: 403 });
  const token = request.cookies.get('access_token')?.value;
  let sessionRevoked = !token;
  if (token) {
    try {
      const backend = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/auth/logout`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(10000) });
      sessionRevoked = backend.ok || backend.status === 401;
    } catch { sessionRevoked = false; }
  }
  const response = NextResponse.json({ success: true, session_revoked: sessionRevoked });
  response.cookies.set('access_token', '', { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'lax', path: '/', maxAge: 0 });
  return response;
}
