import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const url = request.url;
  const pathname = request.nextUrl.pathname;

  // SSRF Protection Logic ported from legacy server.js
  if (
    url.includes('169.254.169.254') ||
    url.includes('localhost') ||
    url.includes('.env') ||
    pathname.startsWith('/api/proxy') ||
    pathname.startsWith('/api/fetch')
  ) {
    return NextResponse.json(
      { error: 'Forbidden request' },
      { status: 403 }
    );
  }

  return NextResponse.next();
}

// See "Matching Paths" below to learn more
export const config = {
  matcher: '/api/:path*',
};
