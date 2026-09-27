import { randomBytes } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { hasValidRequestOrigin } from '@/lib/requestOrigin';

const DEFAULT_GOOGLE_CLIENT_ID = '991104064928-r9v2tcb04lpgjo412np3tr1riep2gjeq.apps.googleusercontent.com';
const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const cookie = { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'lax' as const, path: '/' };

export async function GET() {
  const nonce = randomBytes(32).toString('hex');
  let clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || process.env.GOOGLE_CLIENT_ID || DEFAULT_GOOGLE_CLIENT_ID;

  try {
    const backend = await fetch(`${apiUrl}/api/auth/config`, { cache: 'no-store', signal: AbortSignal.timeout(4000) });
    if (backend.ok) {
      const text = await backend.text();
      try {
        const data = JSON.parse(text);
        if (data?.client_id) clientId = data.client_id;
      } catch {
        // Fallback to default client ID if backend returned non-JSON
      }
    }
  } catch {
    // Graceful fallback to env/default clientId if backend is starting or offline
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
      return NextResponse.json({ detail: 'Sign-in session expired. Please reload and try again.' }, { status: 403 });
    }

    const backend = await fetch(`${apiUrl}/api/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: body.credential, nonce }),
      cache: 'no-store',
      signal: AbortSignal.timeout(60000),
    });

    const text = await backend.text();
    let data: any = {};
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { detail: 'Authentication backend is waking up. Please wait 10 seconds and try again.' },
        { status: 503 }
      );
    }

    if (!backend.ok) {
      return NextResponse.json({ detail: data.detail || 'Google sign-in could not be completed.' }, { status: backend.status });
    }

    const response = NextResponse.json({ success: true, email: data.email, role: data.role });
    response.cookies.set('access_token', data.access_token, { ...cookie, maxAge: 60 * 60 * 24 * 7 });
    response.cookies.set('google_nonce', '', { ...cookie, maxAge: 0 });
    return response;
  } catch {
    return NextResponse.json({ detail: 'Sign-in service is momentarily unavailable. Please retry.' }, { status: 503 });
  }
}
