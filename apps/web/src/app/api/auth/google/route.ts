import { randomBytes } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { hasValidRequestOrigin } from '@/lib/requestOrigin';
import { authCookie, authErrorResponse, backendAuth, sessionResponse } from '@/lib/authBackend';
import { AuthRequestError } from '@/lib/authRequest';

export async function GET() {
  try {
    // Use the client ID the reachable API will verify, never a guessed fallback.
    const data = await backendAuth('config');
    if (typeof data.client_id !== 'string' || !data.client_id.trim()) {
      throw new AuthRequestError('Google sign-in is not configured. Please contact your admin.', 503);
    }
    const nonce = randomBytes(32).toString('hex');
    const response = NextResponse.json(
      { client_id: data.client_id.trim(), nonce },
      { headers: { 'Cache-Control': 'no-store' } },
    );
    response.cookies.set('google_nonce', nonce, { ...authCookie, maxAge: 600 });
    return response;
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function POST(request: NextRequest) {
  if (!hasValidRequestOrigin(request)) {
    return NextResponse.json({ detail: 'Invalid request origin' }, { status: 403 });
  }
  try {
    const body = await request.json();
    const nonce = request.cookies.get('google_nonce')?.value;
    if (!nonce || body?.nonce !== nonce) {
      return NextResponse.json({ detail: 'Sign-in session expired. Please reload and try again.' }, { status: 403 });
    }
    const data = await backendAuth('google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: body.credential, nonce }),
    });
    const response = sessionResponse(data);
    response.cookies.set('google_nonce', '', { ...authCookie, maxAge: 0 });
    return response;
  } catch (error) {
    return authErrorResponse(error);
  }
}
