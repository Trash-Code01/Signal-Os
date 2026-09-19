import { randomBytes } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { hasValidRequestOrigin } from '@/lib/requestOrigin';

const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const cookie = { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'lax' as const, path: '/' };

export async function GET() {
  const nonce = randomBytes(32).toString('hex');
  let clientId = process.env.GOOGLE_CLIENT_ID || process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
  try {
    const backend = await fetch(`${apiUrl}/api/auth/config`, { cache: 'no-store', signal: AbortSignal.timeout(6000) });
    if (backend.ok) {
      const data = await backend.json();
      if (data.client_id) clientId = data.client_id;
    }
  } catch {
    // Graceful fallback to env clientId if backend is starting or offline
  }
  const response = NextResponse.json({ client_id: clientId, nonce }, { headers: { 'Cache-Control': 'no-store' } });
  response.cookies.set('google_nonce', nonce, { ...cookie, maxAge: 600 });
  return response;
}

export async function POST(request: NextRequest) {
  if (!hasValidRequestOrigin(request)) {
    return NextResponse.json({ detail: 'Invalid request origin' }, { status: 403 });
  }
  try {
    const body = await request.json();
    const nonce = request.cookies.get('google_nonce')?.value;
    if (!nonce || body.nonce !== nonce) {
      return NextResponse.json({ detail: 'Sign-in expired. Reload and try again.' }, { status: 403 });
    }
    const backend = await fetch(`${apiUrl}/api/auth/google`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: body.credential, nonce }),
      cache: 'no-store', signal: AbortSignal.timeout(20000),
    });
    const data = await backend.json();
    if (!backend.ok) return NextResponse.json({ detail: data.detail || 'Sign-in failed' }, { status: backend.status });
    const response = NextResponse.json({ success: true });
    response.cookies.set('access_token', data.access_token, { ...cookie, maxAge: 60 * 60 * 24 * 7 });
    response.cookies.set('google_nonce', '', { ...cookie, maxAge: 0 });
    return response;
  } catch {
    return NextResponse.json({ detail: 'Sign-in service is unavailable. Try again.' }, { status: 503 });
  }
}
