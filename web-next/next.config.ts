import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Turbopack (default in Next.js 16) reads tsconfig.json `paths` automatically.
  // The @pascal-app/* aliases are already declared there.
  turbopack: {},
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.expcloud.com" },
      { protocol: "https", hostname: "qbmxwkctscpkmxfbksmb.supabase.co" },
      { protocol: "https", hostname: "upwkbeyzmdfdkwoaayub.supabase.co" },
      { protocol: "https", hostname: "images.unsplash.com" },
    ],
    unoptimized: process.env.NODE_ENV === "development",
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
};

export default nextConfig;
