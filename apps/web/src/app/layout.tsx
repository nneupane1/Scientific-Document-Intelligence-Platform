import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import "katex/dist/katex.min.css";
import "./globals.css";
import brandArtwork from "../../../../image.png";

export const metadata: Metadata = {
  title: "NeetiTech · Scientific Document Intelligence",
  description: "Local-first scientific PDFs transformed into structured, reviewable data",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <header className="topbar">
          <Link className="brand" href="/">
            <span className="brand-mark">
              <Image src={brandArtwork} alt="" fill sizes="40px" priority />
            </span>
            <span className="brand-copy">
              <strong>NeetiTech</strong>
              <small>Document Intelligence</small>
            </span>
          </Link>
          <nav aria-label="Primary navigation">
            <Link href="/#platform">Capabilities</Link>
            <Link href="/#intelligence">AI stack</Link>
            <Link href="/#trust">Governance</Link>
            <Link href="/documents">Documents</Link>
            <Link className="nav-cta" href="/#workspace">Process a PDF</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
