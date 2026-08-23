"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Magnet, Megaphone, PlusCircle } from "lucide-react";

export function MobileNav() {
  const pathname = usePathname() || '';

  const links = [
    { href: "/dashboard", icon: Home, label: "Home" },
    { href: "/leads", icon: Magnet, label: "Leads" },
    { href: "/campaigns", icon: Megaphone, label: "Campaigns" },
    { href: "/campaigns/new", icon: PlusCircle, label: "Run" },
  ];

  return (
    <div className="md:hidden fixed bottom-0 left-0 w-full bg-[#121214]/90 backdrop-blur-md border-t border-zinc-800 pb-safe pt-2 z-50">
      <div className="flex justify-around items-center px-4 pb-2">
        {links.map((link) => {
          const isActive = pathname.startsWith(link.href);
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${
                isActive ? "text-white" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <div className={isActive ? "bg-[#3b275c] p-1.5 rounded-lg text-violet-400" : "p-1.5"}>
                <Icon className="w-5 h-5" strokeWidth={isActive ? 2.5 : 2} />
              </div>
              <span className={`text-[10px] font-medium ${isActive ? "text-white" : ""}`}>{link.label}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
