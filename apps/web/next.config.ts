import type { NextConfig } from "next";

// Force rebuild to capture updated NEXT_PUBLIC_API_URL from Render dashboard
const nextConfig: NextConfig = {
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  }
};

export default nextConfig;
