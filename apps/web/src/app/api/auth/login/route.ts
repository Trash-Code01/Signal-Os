import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json(
    { detail: 'Password login is disabled. Continue with Google.' },
    { status: 410 },
  );
}
