import { NextResponse } from 'next/server';

// Lightweight ping endpoint — called every 13 minutes by the frontend keepalive.
// It pings the backend's /api/health route to prevent Render from sleeping it.
export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  try {
    const res = await fetch(`${apiUrl}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(10_000), // 10s timeout
    });
    return NextResponse.json({ ok: true, status: res.status }, { status: 200 });
  } catch {
    // Never propagate errors — this is a silent keepalive
    return NextResponse.json({ ok: false }, { status: 200 });
  }
}
