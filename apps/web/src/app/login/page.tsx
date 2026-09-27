'use client';

import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';
import { Terminal, Mail, Lock, User as UserIcon, ArrowRight, Sparkles, Building2 } from 'lucide-react';

const FALLBACK_CLIENT_ID = '991104064928-r9v2tcb04lpgjo412np3tr1riep2gjeq.apps.googleusercontent.com';

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
      prompt: () => void;
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
  const [config, setConfig] = useState<{ client_id: string; nonce: string }>({
    client_id: FALLBACK_CLIENT_ID,
    nonce: '',
  });
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // Fetch nonce and client_id safely without crashing on non-JSON HTML
  useEffect(() => {
    fetch('/api/auth/google', { cache: 'no-store' })
      .then(async (response) => {
        const text = await response.text();
        try {
          const data = JSON.parse(text);
          if (data && data.nonce) {
            setConfig({
              client_id: data.client_id || FALLBACK_CLIENT_ID,
              nonce: data.nonce,
            });
          }
        } catch {
          // If non-JSON HTML returned during server wake-up, fallback to default
        }
      })
      .catch(() => {});
  }, []);

  // Initialize Google Identity Services
  useEffect(() => {
    if (!scriptReady || !config?.client_id || !window.google || !googleBtnRef.current) return;
    try {
      window.google.accounts.id.initialize({
        client_id: config.client_id,
        nonce: config.nonce || 'fallback-nonce-devacia',
        callback: async ({ credential }) => {
          setGoogleLoading(true);
          setError('');
          try {
            const response = await fetch('/api/auth/google', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ credential, nonce: config.nonce || 'fallback-nonce-devacia' }),
            });
            const text = await response.text();
            let data: any = {};
            try {
              data = JSON.parse(text);
            } catch {
              throw new Error('Authentication server is starting up. Please retry in 10 seconds.');
            }
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
        theme: 'filled_black',
        size: 'large',
        text: 'continue_with',
        width: 340,
      });
    } catch (err) {
      console.error('Google button init error:', err);
    }
  }, [scriptReady, config]);

  const handleGoogleClick = () => {
    if (window.google?.accounts?.id?.prompt) {
      window.google.accounts.id.prompt();
    } else {
      setError('Loading Google authentication service… please click again in a moment.');
    }
  };

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

      const text = await response.text();
      let data: any = {};
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error('Backend service is starting up. Please retry in a few moments.');
      }

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

      const text = await response.text();
      let data: any = {};
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error('Backend service is starting up.');
      }

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
        strategy="afterInteractive"
        onReady={() => setScriptReady(true)}
        onError={() => {}}
      />

      <section className="w-full max-w-md rounded-3xl border border-zinc-800 bg-[#121214] p-8 shadow-2xl shadow-black/60">
        {/* Brand Header */}
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-violet-500/20 bg-violet-500/10 text-violet-400 shadow-inner">
            <Terminal className="h-6 w-6" />
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-400">Devacia Lead OS</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">Lead Intelligence Platform</h1>
          <p className="mt-1 text-xs text-zinc-400">
            Sign in with Google or your account credentials
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div role="alert" className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-2.5 text-center text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Primary Method 1: Google Sign-In */}
        <div className="mt-6 space-y-3">
          <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-400 text-center">
            Sign In with Google
          </p>

          {/* Official Google Identity Button Mount */}
          <div
            ref={googleBtnRef}
            className={`flex justify-center min-h-[44px] ${googleLoading ? 'pointer-events-none opacity-50' : ''}`}
          />

          {/* Styled Google Fallback Button */}
          {(!scriptReady || !googleBtnRef.current?.hasChildNodes()) && (
            <button
              type="button"
              onClick={handleGoogleClick}
              disabled={googleLoading || loading}
              className="w-full flex items-center justify-center gap-3 rounded-xl border border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-white font-medium py-2.5 px-4 text-sm transition-all shadow-sm cursor-pointer disabled:opacity-50"
            >
              <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Continue with Google</span>
            </button>
          )}

          {googleLoading && (
            <p className="text-center text-xs text-zinc-400 animate-pulse">Verifying Google account…</p>
          )}
        </div>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-zinc-800" />
          </div>
          <div className="relative flex justify-center text-[11px] uppercase">
            <span className="bg-[#121214] px-2 text-zinc-500 font-medium">Or continue with email</span>
          </div>
        </div>

        {/* Tab Switcher: Sign In vs Create Account */}
        <div className="flex rounded-xl bg-zinc-900/90 p-1 border border-zinc-800/80">
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

        {/* Email & Password Form */}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
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
            <label className="text-[11px] font-medium uppercase tracking-wider text-zinc-400 block mb-1.5">
              Password
            </label>
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
            <p className="font-semibold text-zinc-300">Multi-Tenant Isolation</p>
            <p className="text-zinc-500">
              Each Google or email account gets a private database workspace. Campaigns, leads, and exports are 100% private to that account.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
