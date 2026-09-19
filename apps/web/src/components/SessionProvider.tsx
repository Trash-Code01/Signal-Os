'use client';
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { usePathname } from 'next/navigation';

export type Account = { id: number; email: string; name: string | null; role: 'admin' | 'member' | 'viewer'; is_active: boolean; personal_email_enabled: boolean; phone_enabled: boolean };
const Session = createContext<{ user: Account | null; reload: () => Promise<void> }>({ user: null, reload: async () => {} });
export const useSession = () => useContext(Session);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [user, setUser] = useState<Account | null>(null);
  const [error, setError] = useState('');
  const reload = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/me', { cache: 'no-store' });
      if (response.status === 401) {
        window.location.replace('/login');
        return;
      }
      if (!response.ok) throw new Error();
      setUser(await response.json());
      setError('');
    } catch { setError('Unable to load your account. Please retry.'); }
  }, []);
  useEffect(() => {
    if (pathname !== '/login') void reload();
    else setUser(null);
  }, [pathname, reload]);
  if (pathname !== '/login' && !user) return <div className="p-10 text-zinc-400">{error || 'Loading your account…'}{error && <button className="ml-3 underline" onClick={reload}>Retry</button>}</div>;
  return <Session.Provider value={{ user, reload }}>{children}</Session.Provider>;
}
