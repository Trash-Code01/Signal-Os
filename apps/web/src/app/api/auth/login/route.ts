import { NextRequest, NextResponse } from 'next/server';
import { hasValidRequestOrigin } from '@/lib/requestOrigin';
import { authErrorResponse, backendAuth, sessionResponse } from '@/lib/authBackend';

export async function POST(request: NextRequest) {
  if (!hasValidRequestOrigin(request)) {
    return NextResponse.json({ detail: 'Invalid request origin' }, { status: 403 });
  }
  try {
    const data = await backendAuth('login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(await request.json()),
    });
    return sessionResponse(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
