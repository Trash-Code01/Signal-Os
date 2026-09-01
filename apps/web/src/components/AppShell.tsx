'use client';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { Sidebar } from "@/components/Sidebar";
import { MobileNav } from "@/components/MobileNav";

// Ping the backend every 13 minutes to prevent Render free tier from sleeping.
// Render sleeps after 15 minutes of inactivity — this keeps it awake.
const PING_INTERVAL_MS = 13 * 60 * 1000; // 13 minutes

function useBackendKeepalive() {
  useEffect(() => {
    const ping = () => {
      fetch('/api/ping').catch(() => {}); // silent — never shows errors to user
    };
    ping(); // ping immediately on mount
    const timer = setInterval(ping, PING_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || '';
  const isAuth = pathname === '/login';
  useBackendKeepalive(); // keeps Render backend warm — pings every 13 min

  if (isAuth) {
    return <main className="flex-1 min-w-0 min-h-screen relative">{children}</main>;
  }

  return (
    <>
      <Sidebar />
      <main className="flex-1 min-w-0 min-h-screen relative pb-24 md:pb-0">
        {children}
        <MobileNav />
      </main>
    </>
  );
}
