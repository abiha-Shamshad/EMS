import type { NextConfig } from "next";

// The browser only ever talks to this origin. /api/v1/* is proxied to the FastAPI service, so the session and CSRF
// cookies are first-party and the Chrome extension can share the same session (spec Section 7.3).
const apiOrigin = (process.env.EMS_API_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${apiOrigin}/api/v1/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};

export default nextConfig;
