import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Image Crawler Console",
  description: "Queue and monitor image crawling jobs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <div className="site-shell">
          <header className="site-header">
            <Link href="/" className="brand-mark">
              <span className="brand-kicker">Image</span>
              <strong className="brand-title">Crawler Console</strong>
            </Link>
            <nav className="site-nav" aria-label="Primary">
              <Link href="/">Upload</Link>
              <Link href="/status">Status</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
