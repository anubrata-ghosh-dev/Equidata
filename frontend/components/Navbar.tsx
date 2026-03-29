"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/simulate", label: "Simulator" },
  { href: "/audit", label: "Audit" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="panel flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.24em] text-textMuted">FairGuard</p>
        <h1 className="text-xl font-semibold text-textMain">AI Bias Auditor</h1>
      </div>

      <nav className="flex items-center gap-2 rounded-xl bg-black/25 p-1">
        {links.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                isActive ? "bg-accent text-white shadow-glow" : "text-textMuted hover:bg-white/5 hover:text-textMain"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
