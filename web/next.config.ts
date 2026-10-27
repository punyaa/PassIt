import { existsSync } from "node:fs";
import { loadEnvFile } from "node:process";
import type { NextConfig } from "next";

// Native development shares the repository-root environment with Compose and FastAPI.
if (existsSync("../.env")) loadEnvFile("../.env");

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  turbopack: {
    root: process.cwd(),
  },
  async rewrites() {
    const apiOrigin = process.env.PASSIT_API_ORIGIN;
    return apiOrigin ? [{ source: "/v1/:path*", destination: `${apiOrigin}/v1/:path*` }] : [];
  },
};

export default nextConfig;
