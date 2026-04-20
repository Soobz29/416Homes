import { MetadataRoute } from "next";

const BASE = "https://416-homes.vercel.app";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      // ── Allow all well-behaved search engines ──────────────────────────
      {
        userAgent: ["Googlebot", "Bingbot", "Slurp", "DuckDuckBot", "Baiduspider", "YandexBot"],
        allow: "/",
        disallow: ["/api/", "/mockup/"],
      },
      // ── Generic catch-all: allow public pages, block private routes ─────
      {
        userAgent: "*",
        allow: ["/", "/dashboard", "/video", "/tours"],
        disallow: ["/api/", "/mockup/"],
      },
      // ── Block AI training crawlers ─────────────────────────────────────
      { userAgent: "GPTBot",          disallow: "/" },
      { userAgent: "ChatGPT-User",    disallow: "/" },
      { userAgent: "CCBot",           disallow: "/" },
      { userAgent: "anthropic-ai",    disallow: "/" },
      { userAgent: "Claude-Web",      disallow: "/" },
      { userAgent: "Google-Extended", disallow: "/" },
      { userAgent: "Amazonbot",       disallow: "/" },
      { userAgent: "Omgilibot",       disallow: "/" },
      { userAgent: "FacebookBot",     disallow: "/" },
      { userAgent: "PerplexityBot",   disallow: "/" },
      { userAgent: "YouBot",          disallow: "/" },
      { userAgent: "Diffbot",         disallow: "/" },
      { userAgent: "ImagesiftBot",    disallow: "/" },
      { userAgent: "cohere-ai",       disallow: "/" },
    ],
    sitemap: `${BASE}/sitemap.xml`,
    host: BASE,
  };
}
