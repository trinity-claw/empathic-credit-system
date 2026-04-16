import type { NextConfig } from "next";

// Rewrite target: URL reachable from the Next.js *server* (Docker: http://api:8000).
// Browser code must NOT use this host — use same-origin `/api` (see src/lib/api.ts).
const backendRewriteTarget =
  process.env.BACKEND_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendRewriteTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
