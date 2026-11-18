import type { Metadata } from "next";
import { Anton, Inter, JetBrains_Mono, Montserrat } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "500", "600", "700"],
});

const montserrat = Montserrat({
  subsets: ["latin"],
  variable: "--font-montserrat",
  weight: ["700", "800", "900"],
  style: ["normal", "italic"],
});

const anton = Anton({
  subsets: ["latin"],
  variable: "--font-anton",
  weight: ["400"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "GTA6 Viral Shorts Studio | AI 8K Beat-Synced Shorts Engine",
  description:
    "Automated AI video editing studio turning GTA 6 YouTube livestreams & VODs into 15–30s viral Gen-Z 9:16 Shorts with Remotion After Effects VFX, librosa beat sync & 8K HDR grading.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${inter.variable} ${montserrat.variable} ${anton.variable} ${jetbrainsMono.variable}`}
    >
      <body className="min-h-screen bg-[#07070d] text-slate-100 font-sans antialiased selection:bg-vice-pink/40 selection:text-white">
        {children}
      </body>
    </html>
  );
}
