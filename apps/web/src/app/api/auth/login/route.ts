import { NextRequest, NextResponse } from 'next/server';

const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const cookie = { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'lax' as const, path: '/' };

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const backend = await fetch(`${apiUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    });

    const data = await backend.json().catch(() => ({}));
    if (!backend.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Incorrect email or password' },
        { status: backend.status }
      );
    }

    const response = NextResponse.json({ success: true, email: data.email, role: data.role });
    response.cookies.set('access_token', data.access_token, {
      ...cookie,
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });
    return response;
  } catch (error: any) {
    return NextResponse.json(
      { detail: 'Unable to connect to authentication backend. Please check server.' },
      { status: 503 }
    );
  }
}
