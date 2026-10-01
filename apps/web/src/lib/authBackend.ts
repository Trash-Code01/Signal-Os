import { NextResponse } from 'next/server';
import { authRequest, AuthRequestError } from './authRequest';

export const authCookie = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
};

export function backendAuth(path: string, init?: RequestInit) {
  const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  return authRequest(`${apiUrl.replace(/\/$/, '')}/api/auth/${path}`, init, 60_000);
}

export function authErrorResponse(error: unknown) {
  return NextResponse.json(
    { detail: error instanceof AuthRequestError ? error.message : 'Sign-in could not be completed. Please retry.' },
    { status: error instanceof AuthRequestError ? error.status : 503, headers: { 'Cache-Control': 'no-store' } },
  );
}

export function sessionResponse(data: Record<string, unknown>) {
  if (typeof data.access_token !== 'string' || !data.access_token.trim()) {
    throw new AuthRequestError('Sign-in service returned an invalid session. Please retry.', 502);
  }
  const response = NextResponse.json(
    { success: true, email: data.email, role: data.role, name: data.name },
    { headers: { 'Cache-Control': 'no-store' } },
  );
  response.cookies.set('access_token', data.access_token, { ...authCookie, maxAge: 60 * 60 * 24 * 7 });
  return response;
}
