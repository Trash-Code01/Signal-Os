import { NextResponse } from 'next/server';

export async function GET() {
  const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  let backendStatus = null;
  let errorMsg = null;

  try {
    const res = await fetch(`${apiUrl}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(6000),
    });
    backendStatus = res.status;
  } catch (err: any) {
    errorMsg = err?.message || 'timeout/connection error';
  }

  return NextResponse.json({
    ok: backendStatus === 200,
    apiUrl,
    backendStatus,
    error: errorMsg,
    nodeEnv: process.env.NODE_ENV,
  });
}
