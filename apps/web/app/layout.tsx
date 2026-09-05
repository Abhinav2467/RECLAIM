import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RECLAIM | Revenue Recovery Control Room",
  description: "Autonomous Revenue Recovery Decision & Verification Engine",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-[#FAF9F5] text-stone-900 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
