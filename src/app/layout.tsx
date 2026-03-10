import type { Metadata } from "next";
import { Space_Grotesk, Inter } from "next/font/google";
import "./globals.css";
import SceneWrapper from "@/components/3d/SceneWrapper";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "InsightPilot",
  description: "3D Immersive Analytics Copilot",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${spaceGrotesk.variable} ${inter.variable} antialiased text-white bg-transparent min-h-screen`}
      >
        <SceneWrapper />
        <main className="relative z-10 min-h-screen pt-4">
          {children}
        </main>
      </body>
    </html>
  );
}
