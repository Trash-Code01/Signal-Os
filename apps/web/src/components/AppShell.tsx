'use client';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { Sidebar } from "@/components/Sidebar";
import { MobileNav } from "@/components/MobileNav";

import { useSession } from '@/components/SessionProvider';

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
  const { user } = useSession();
  const isAuth = pathname === '/login';
  const appEnv = process.env.NEXT_PUBLIC_APP_ENV || (process.env.NEXT_PUBLIC_API_URL?.includes('localhost') || process.env.NEXT_PUBLIC_API_URL?.includes('127.0.0.1') ? 'staging' : 'production');
  const isStaging = appEnv === 'staging';

  useBackendKeepalive(); // keeps Render backend warm — pings every 13 min

  if (isAuth) {
    return <main className="flex-1 min-w-0 min-h-screen relative">{children}</main>;
  }

  return (
    <>
      <Sidebar />
      <main className="flex-1 min-w-0 min-h-screen relative pb-24 md:pb-0 flex flex-col">
        {isStaging && (
          <div className="md:hidden bg-amber-500/10 border-b border-amber-500/20 px-3 py-1 text-center text-[10px] font-bold text-amber-300 tracking-wider uppercase flex items-center justify-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
            Staging Mode (Local)
          </div>
        )}
        <div className="border-b border-zinc-800 px-4 py-2 text-xs text-zinc-400 flex flex-wrap justify-between gap-2"><span>{user?.email} · {user?.role} · Private account</span><a href="/settings" className="text-violet-300">Account settings</a></div>
        {user?.role === 'viewer' && <div className="px-4 py-2 text-xs text-amber-300">Viewer access: read and export only.</div>}
        <div className="flex-1 min-w-0">
          {children}
        </div>
        <MobileNav />
      </main>
    </>
  );
}
