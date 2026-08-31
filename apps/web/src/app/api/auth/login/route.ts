import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    
    // Call the FastAPI login endpoint
    const response = await fetch(`${apiUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      return NextResponse.json(
        { detail: `Backend returned invalid JSON. Status: ${response.status}. Body: ${text.substring(0, 100)}` },
        { status: 502 }
      );
    }

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Login failed' },
        { status: response.status }
      );
    }

    // Create response and set HttpOnly cookie
    const res = NextResponse.json({ success: true });
    res.cookies.set('access_token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7 // 1 week
    });

    return res;
  } catch (error: any) {
    const msg = error ? (error.message || String(error)) : "Unknown error";
    return NextResponse.json(
      { detail: `Frontend API error: ${msg}` },
      { status: 500 }
    );
  }
}
