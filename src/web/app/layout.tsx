import type { Metadata } from "next";
import { Merriweather } from "next/font/google";
import "./globals.css";

const merriweather = Merriweather({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: ["300", "400", "700", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Dhi // The Intellect",
  description: "Local, Privacy-First, Scripture Research Engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        {/* Tiro Fonts for Indic Scripts */}
        <link href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Sanskrit&family=Tiro+Telugu&family=Tiro+Kannada&family=Tiro+Malayalam&display=swap" rel="stylesheet" />
      </head>
      <body
        className={`${merriweather.variable} antialiased font-serif`}
      >
        {children}
      </body>
    </html>
  );
}
