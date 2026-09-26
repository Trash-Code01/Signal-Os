'use client';

import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';
import { ShieldCheck, Terminal } from 'lucide-react';

type GoogleIdentity = {
  accounts: {
    id: {
      initialize: (options: {
        client_id: string;
        nonce: string;
        callback: (response: { credential: string }) => void;
      }) => void;
      renderButton: (
        element: HTMLElement,
        options: { theme: string; size: string; text: string; width: number },
      ) => void;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentity;
  }
}

export default function LoginPage() {
  const button = useRef<HTMLDivElement>(null);
  const [scriptReady, setScriptReady] = useState(false);
  const [config, setConfig] = useState<{ client_id: string; nonce: string } | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/api/auth/google', { cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Sign-in service is unavailable.');
        if (!data.client_id) throw new Error('Google sign-in is not configured yet. Contact your admin.');
        setConfig(data);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Sign-in service is unavailable.'));
  }, []);

  useEffect(() => {
    if (!scriptReady || !config?.client_id || !window.google || !button.current) return;
    window.google.accounts.id.initialize({
      client_id: config.client_id,
      nonce: config.nonce,
      callback: async ({ credential }) => {
        setLoading(true);
        setError('');
        try {
          const response = await fetch('/api/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential, nonce: config.nonce }),
          });
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'Sign-in failed.');
          window.location.replace('/dashboard');
        } catch (reason) {
          setError(reason instanceof Error ? reason.message : 'Sign-in failed.');
          setLoading(false);
        }
      },
    });
    button.current.replaceChildren();
    window.google.accounts.id.renderButton(button.current, {
      theme: 'outline',
      size: 'large',
      text: 'continue_with',
      width: 320,
    });
  }, [scriptReady, config]);

  const handleDevSignIn = async (email: string = 'devacia.com@gmail.com') => {
    if (!config?.nonce) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: `dev-mock:${email}`, nonce: config.nonce }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Dev sign-in failed.');
      window.location.replace('/dashboard');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Dev sign-in failed.');
      setLoading(false);
    }
  };

  const isStaging = process.env.NEXT_PUBLIC_APP_ENV === 'staging' || process.env.NODE_ENV !== 'production';

  return (
    <main className="min-h-screen bg-[#09090b] text-white flex items-center justify-center p-5">
      <Script
        src="https://accounts.google.com/gsi/client"
        onReady={() => setScriptReady(true)}
        onError={() => setError('Google sign-in could not be loaded. Check your connection and try again.')}
      />
      <section className="w-full max-w-md rounded-3xl border border-zinc-800 bg-[#121214] p-8 shadow-2xl shadow-black/40">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-violet-500/20 bg-violet-500/10 text-violet-400">
          <Terminal className="h-6 w-6" />
        </div>
        <div className="text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-300">Devacia Lead OS</p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight">Your private lead workspace</h1>
          <p className="mt-2 text-sm leading-6 text-zinc-400">
            Continue with an invited Google account. Campaigns, leads, and exports stay isolated to that account.
          </p>
        </div>

        {error && (
          <div role="alert" className="mt-6 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-center text-sm text-rose-300">
            {error}
          </div>
        )}

        <div className={`mt-6 flex min-h-11 justify-center ${loading ? 'pointer-events-none opacity-50' : ''}`} ref={button} />
        {loading && <p className="mt-3 text-center text-xs text-zinc-400">Verifying credentials…</p>}

        {isStaging && (
          <div className="mt-6 space-y-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-zinc-800" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-[#121214] px-2 text-zinc-500 font-medium tracking-wider">
                  Or Sandbox Quick-Access
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleDevSignIn('devacia.com@gmail.com')}
              disabled={loading || !config?.nonce}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-violet-600 hover:bg-violet-500 active:bg-violet-700 text-white font-medium py-2.5 px-4 transition-all duration-150 shadow-lg shadow-violet-600/20 disabled:opacity-50 disabled:cursor-not-allowed text-sm cursor-pointer"
            >
              <Terminal className="h-4 w-4" />
              <span>1-Click Dev Sign-In (Admin)</span>
            </button>

            <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/40 p-3 text-xs text-zinc-400 space-y-1">
              <p className="font-semibold text-zinc-300">Google OAuth Error 400 (origin_mismatch)?</p>
              <p className="text-[11px] leading-relaxed text-zinc-500">
                Google requires exact authorized origins. To test Google Auth locally, add <code className="text-violet-300 bg-zinc-900 px-1 py-0.5 rounded">http://localhost:3001</code> and <code className="text-violet-300 bg-zinc-900 px-1 py-0.5 rounded">http://127.0.0.1:3001</code> to Authorized JavaScript Origins in Google Cloud Console, or use the 1-Click Dev Sign-In above.
              </p>
            </div>
          </div>
        )}

        <div className="mt-6 flex items-start gap-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          <p className="text-xs leading-5 text-zinc-400">
            Access is invite-only. Admin, Member, and Viewer permissions are enforced by the API.
          </p>
        </div>

        {process.env.NEXT_PUBLIC_APP_ENV === 'staging' && (
          <p className="mt-5 text-center text-[11px] font-medium text-amber-300">
            Staging · mock campaigns · no paid discovery calls
          </p>
        )}
      </section>
    </main>
  );
}
