'use client';
import { usePathname } from 'next/navigation';
import { Sidebar } from "@/components/Sidebar";
import { MobileNav } from "@/components/MobileNav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || '';
  const isAuth = pathname === '/login';

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