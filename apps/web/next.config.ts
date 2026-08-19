import type { NextConfig } from "next";

const allowedDevOrigin = process.env.SCIDOC_ALLOWED_DEV_ORIGIN;
const internalApiUrl = process.env.SCIDOC_INTERNAL_API_URL ?? "http://127.0.0.1:8000";
const allowedDevOrigins = Array.from(
  new Set(["localhost", "127.0.0.1", ...(allowedDevOrigin ? [allowedDevOrigin] : [])]),
);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  devIndicators: false,
  allowedDevOrigins,
  experimental: { optimizePackageImports: ["pdfjs-dist"] },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${internalApiUrl}/api/:path*` }];
  },
};

export default nextConfig;
