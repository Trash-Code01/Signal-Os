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
      signal: AbortSignal.timeout(60000),
    });

    const text = await backend.text();
    let data: any = {};
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { detail: 'Backend service is waking up on Render. Please wait 15 seconds and try again.' },
        { status: 503 }
      );
    }

    if (!backend.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Incorrect email or password' },
        { status: backend.status }
      );
    }

    const response = NextResponse.json({ success: true, email: data.email, role: data.role, name: data.name });
    response.cookies.set('access_token', data.access_token, {
      ...cookie,
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });
    return response;
  } catch {
    return NextResponse.json(
      { detail: 'Authentication backend is connecting. Please wait 15 seconds and retry.' },
      { status: 503 }
    );
  }
}
