'use client';

import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';
import { ShieldCheck, Terminal, Mail, Lock, User as UserIcon, ArrowRight, Sparkles, Building2, CheckCircle2 } from 'lucide-react';

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
  const googleBtnRef = useRef<HTMLDivElement>(null);
  const [scriptReady, setScriptReady] = useState(false);
  const [config, setConfig] = useState<{ client_id: string; nonce: string } | null>(null);
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    fetch('/api/auth/google', { cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json();
        if (response.ok && data.nonce) {
          setConfig(data);
        }
      })
      .catch(() => {
        // Silently continue with password authentication
      });
  }, []);

  useEffect(() => {
    if (!scriptReady || !config?.client_id || !window.google || !googleBtnRef.current) return;
    try {
      window.google.accounts.id.initialize({
        client_id: config.client_id,
        nonce: config.nonce,
        callback: async ({ credential }) => {
          setGoogleLoading(true);
          setError('');
          try {
            const response = await fetch('/api/auth/google', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ credential, nonce: config.nonce }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Google sign-in failed.');
            window.location.replace('/dashboard');
          } catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Google sign-in failed.');
            setGoogleLoading(false);
          }
        },
      });
      googleBtnRef.current.replaceChildren();
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        width: 320,
      });
    } catch (err) {
      console.error('Google button render error:', err);
    }
  }, [scriptReady, config]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in both email and password.');
      return;
    }
    if (password.length < 4) {
      setError('Password must be at least 4 characters.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password,
          name: mode === 'signup' ? name.trim() : undefined,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Sign-in failed. Please verify credentials.');
      }

      window.location.replace('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Please retry.');
      setLoading(false);
    }
  };

  const handleDevSignIn = async (userEmail: string = 'admin@devacia.com', userPassword: string = 'admin123') => {
    setEmail(userEmail);
    setPassword(userPassword);
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: userEmail,
          password: userPassword,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Sign-in failed.');
      }

      window.location.replace('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Quick sign-in failed.');
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#09090b] text-white flex items-center justify-center p-4 selection:bg-violet-500/30">
      <Script
        src="https://accounts.google.com/gsi/client"
        onReady={() => setScriptReady(true)}
        onError={() => {}}
      />

      <section className="w-full max-w-md rounded-3xl border border-zinc-800 bg-[#121214] p-8 shadow-2xl shadow-black/50">
        {/* Brand Header */}
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-violet-500/20 bg-violet-500/10 text-violet-400 shadow-inner">
            <Terminal className="h-6 w-6" />
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-400">Devacia Lead OS</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">Lead Intelligence Platform</h1>
          <p className="mt-1 text-xs text-zinc-400">
            {mode === 'signin' ? 'Sign in to access your private pipeline' : 'Create your isolated workspace'}
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="mt-6 flex rounded-xl bg-zinc-900/90 p-1 border border-zinc-800/80">
          <button
            type="button"
            onClick={() => { setMode('signin'); setError(''); }}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              mode === 'signin'
                ? 'bg-violet-600 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode('signup'); setError(''); }}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              mode === 'signup'
                ? 'bg-violet-600 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div role="alert" className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-2.5 text-center text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-5 space-y-3.5">
          {mode === 'signup' && (
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wider text-zinc-400 block mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Alex Rivers"
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-950/70 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500/70 transition-colors"
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-[11px] font-medium uppercase tracking-wider text-zinc-400 block mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-xl border border-zinc-800 bg-zinc-950/70 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500/70 transition-colors"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-medium uppercase tracking-wider text-zinc-400 block">
                Password
              </label>
            </div>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-zinc-800 bg-zinc-950/70 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500/70 transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || googleLoading}
            className="w-full mt-2 flex items-center justify-center gap-2 rounded-xl bg-violet-600 hover:bg-violet-500 active:bg-violet-700 text-white font-medium py-2.5 px-4 text-sm transition-all duration-150 shadow-lg shadow-violet-600/25 disabled:opacity-50 cursor-pointer"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <span>{mode === 'signin' ? 'Sign In' : 'Create Account & Workspace'}</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        {/* Google SSO Section (if available) */}
        {config?.client_id && (
          <div className="mt-5 space-y-3">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-zinc-800/80" />
              </div>
              <div className="relative flex justify-center text-[11px] uppercase">
                <span className="bg-[#121214] px-2 text-zinc-500 font-medium">Or continue with</span>
              </div>
            </div>

            <div className={`flex justify-center min-h-[44px] ${googleLoading ? 'pointer-events-none opacity-50' : ''}`} ref={googleBtnRef} />
            {googleLoading && <p className="text-center text-xs text-zinc-400">Verifying Google account…</p>}
          </div>
        )}

        {/* 1-Click Sandbox Fast Access */}
        <div className="mt-5 pt-4 border-t border-zinc-800/80">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="flex items-center gap-1.5 text-zinc-400">
              <Sparkles className="h-3.5 w-3.5 text-amber-400" />
              Quick Sandbox Access:
            </span>
            <button
              type="button"
              onClick={() => handleDevSignIn('admin@devacia.com', 'admin123')}
              disabled={loading || googleLoading}
              className="font-mono text-[11px] text-violet-400 hover:text-violet-300 underline font-semibold transition-colors cursor-pointer"
            >
              admin@devacia.com
            </button>
          </div>
        </div>

        {/* Multi-Tenant SaaS Info Banner */}
        <div className="mt-4 rounded-xl border border-zinc-800/80 bg-zinc-950/50 p-3.5 text-xs text-zinc-400 flex items-start gap-2.5">
          <Building2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5 leading-relaxed text-[11px]">
            <p className="font-semibold text-zinc-300">Multi-Tenant Data Isolation</p>
            <p className="text-zinc-500">
              Every account has a completely isolated database workspace. Campaigns, scraped leads, enrichment data, and exports are 100% private to each user.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
