import type { Metadata } from "next";
import { Syne, Cormorant_Garamond, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { GlobalBackground } from "@/components/ui/global-background";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

const syne = Syne({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-syne",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-mono",
  display: "swap",
});

const SITE_URL = "https://416-homes.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "416Homes — Toronto Real Estate Intelligence",
  description:
    "GTA listing scanner that runs every 30 minutes. Real sold-comp valuations, Telegram alerts, and automated agent outreach. Free to start.",
  openGraph: {
    title: "416Homes — Toronto Real Estate Intelligence",
    description:
      "GTA listing scanner that runs every 30 minutes. Real sold-comp valuations, Telegram alerts, and automated agent outreach. Free to start.",
    url: SITE_URL,
    siteName: "416Homes",
    type: "website",
    locale: "en_CA",
  },
  twitter: {
    card: "summary_large_image",
    title: "416Homes — Toronto Real Estate Intelligence",
    description:
      "GTA listing scanner that runs every 30 minutes. Real sold-comp valuations, Telegram alerts. Free to start.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${cormorant.variable} ${syne.variable} ${jetbrains.variable}`}
      >
        <GlobalBackground />
        {children}
      </body>
    </html>
  );
}
