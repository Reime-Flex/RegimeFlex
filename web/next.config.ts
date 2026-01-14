import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Fix turbopack workspace root detection
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Enable standalone output for Docker
  output: 'standalone',
};

export default nextConfig;
