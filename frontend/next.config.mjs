/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: (process.env.ALLOWED_DEV_ORIGINS || "")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean),
  async rewrites() {
    return [
      {
        source: "/agent-api/:path*",
        destination: "http://127.0.0.1:2024/:path*",
      },
    ];
  },
  experimental: {
    proxyTimeout: 300000,
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
};

export default nextConfig;
