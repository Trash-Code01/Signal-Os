import type { NextConfig } from 'next';

const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR || '.next',
  output: 'standalone',
  eslint: {
    ignoreDuringBuilds: true,
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin-allow-popups',
          },
        ],
      },
    ];
  },
  async rewrites() {
    // Next.js route handlers in src/app/api/auth/* handle google, login, and logout requests.
    // All other /api/* requests (including /api/auth/users) are proxied to the FastAPI backend.
    return [
      {
        source: '/api/:path((?!auth/google|auth/login|auth/logout).*)',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  }
};

export default nextConfig;
