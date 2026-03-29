import type { Metadata } from "next";

import Navbar from "@/components/Navbar";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "FairGuard - AI Bias Auditor",
  description: "Interactive bias auditing frontend for AI decisions.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto min-h-screen max-w-6xl px-4 pb-10 pt-6 sm:px-6 lg:px-8">
          <Navbar />
          <main className="mt-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
