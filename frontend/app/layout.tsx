import type { Metadata, Viewport } from "next";
import { Unbounded, Sora, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const unbounded = Unbounded({
  subsets: ["latin"],
  weight: ["500", "700", "800"],
  variable: "--font-display",
  display: "swap",
});

const sora = Sora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Summit",
  description: "A living on-chain marker always held by whoever's currently #1 on Hacker News's front page - verified live by GenLayer validators, no claim required.",
  manifest: "/site.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: "#0E1420",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${unbounded.variable} ${sora.variable} ${jetbrainsMono.variable}`} data-scroll-behavior="smooth">
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
