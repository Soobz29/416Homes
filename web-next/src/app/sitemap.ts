import { MetadataRoute } from "next";

const BASE = "https://416-homes.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: BASE,              lastModified: new Date(), changeFrequency: "daily",   priority: 1 },
    { url: `${BASE}/dashboard`, lastModified: new Date(), changeFrequency: "hourly",  priority: 0.9 },
    { url: `${BASE}/video`,   lastModified: new Date(), changeFrequency: "weekly",  priority: 0.7 },
    { url: `${BASE}/tours`,   lastModified: new Date(), changeFrequency: "weekly",  priority: 0.7 },
  ];
}
