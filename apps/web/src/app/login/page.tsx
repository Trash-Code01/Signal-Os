'use client';
import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';
import { Terminal, Lock, Mail, ArrowRight, ShieldCheck } from 'lucide-react';

type GoogleIdentity = { 
  accounts: { 
    id: { 
      initialize: (options: { client_id: string; nonce: string; callback: (response: { credential: string }) => void }) => void; 
      renderButton: (element: HTMLElement, options: { theme: string; size: string; text: string; width?: number }) => void 
    } 
  } 
};
declare global { interface Window { google?: GoogleIdentity } }

export default function LoginPage() {
  const googleBtnRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [config, setConfig] = useState<{ client_id: string; nonce: string } | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Email/Password states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pwLoading, setPwLoading] = useState(false);

  useEffect(() => {
    fetch('/api/auth/google', { cache: 'no-store' })
      .then(async response => {
        const data = await response.json();
        if (response.ok && data) {
          setConfig(data);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!ready || !config?.client_id || !window.google || !googleBtnRef.current) return;
    try {
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
              body: JSON.stringify({ credential, nonce: config.nonce })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Sign-in failed');
            window.location.replace('/dashboard');
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Sign-in failed');
            setLoading(false);
          }
        }
      });
      googleBtnRef.current.replaceChildren();
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        width: 340
      });
    } catch {
      // Ignored
    }
  }, [ready, config]);

  async function handleDevGoogleLogin(targetEmail = 'devacia.com@gmail.com') {
    setLoading(true);
    setError('');
    try {
      let currentNonce = config?.nonce;
      if (!currentNonce) {
        const res = await fetch('/api/auth/google', { cache: 'no-store' });
        const data = await res.json();
        if (data?.nonce) {
          currentNonce = data.nonce;
          setConfig(data);
        }
      }
      if (!currentNonce) throw new Error('Could not establish session nonce. Please refresh.');

      const response = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: `dev-mock:${targetEmail}`, nonce: currentNonce })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Sign-in failed');
      window.location.replace('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed');
      setLoading(false);
    }
  }

  async function handlePasswordLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }
    setPwLoading(true);
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Incorrect email or password');
      }
      window.location.replace('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
      setPwLoading(false);
    }
  }

  function fillDemoAdmin() {
    setEmail('admin@devacia.com');
    setPassword('admin123');
    setError('');
  }

  return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center p-4">
      <Script
        src="https://accounts.google.com/gsi/client"
        onReady={() => setReady(true)}
        onError={() => {}}
      />
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#121214] p-8 shadow-2xl">
        <div className="text-center mb-6">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600/10 border border-violet-500/20 text-violet-400">
            <Terminal className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Devacia Lead OS</h1>
          <p className="mt-1.5 text-sm text-zinc-400">Sign in to your lead intelligence workspace</p>
        </div>

        {error && (
          <div role="alert" className="mb-5 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400 text-center">
            {error}
          </div>
        )}

        {/* Google Sign In Option */}
        <div className="space-y-3">
          <div ref={googleBtnRef} className={`flex justify-center min-h-[44px] ${loading ? 'pointer-events-none opacity-50' : ''}`} />

          {/* 1-Click Dev Google Sign In */}
          <button
            type="button"
            onClick={() => handleDevGoogleLogin('devacia.com@gmail.com')}
            disabled={loading || pwLoading}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border border-violet-500/30 bg-violet-600/10 hover:bg-violet-600/20 text-violet-300 text-xs font-semibold transition hover:border-violet-500/50 shadow-sm"
          >
            <ShieldCheck className="w-4 h-4 text-violet-400 shrink-0" />
            <span>1-Click Sign-In: <b>devacia.com@gmail.com</b></span>
          </button>

          <div className="text-center px-2 py-1.5 rounded bg-zinc-900/80 border border-zinc-800/60 text-[11px] text-zinc-400 leading-tight">
            Encountering Google <span className="text-amber-400 font-mono">origin_mismatch</span> on localhost? Use the 1-Click button above or add localhost to Google Cloud Console.
          </div>

          {!config?.client_id && (
            <div className="text-center p-2.5 rounded-lg border border-white/5 bg-white/[0.02] text-xs text-zinc-500">
              Google OAuth client pending configuration in Google Cloud
            </div>
          )}
          {loading && <p className="text-center text-xs text-zinc-400 animate-pulse">Verifying Google account…</p>}
        </div>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-zinc-800/80"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-[#121214] px-3 text-zinc-500 font-medium tracking-wider">or email & password</span>
          </div>
        </div>

        {/* Email & Password Form */}
        <form onSubmit={handlePasswordLogin} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-1.5 block">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin@devacia.com"
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500/60 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-1.5 block">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500/60 transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={pwLoading || loading}
            className="w-full bg-violet-600 hover:bg-violet-500 text-white py-2.5 rounded-lg text-sm font-semibold transition flex items-center justify-center gap-2 shadow-lg shadow-violet-900/20 disabled:opacity-50 mt-2"
          >
            {pwLoading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            ) : (
              <>
                Sign In
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Fill Helper */}
        <div className="mt-5 pt-4 border-t border-zinc-800/60 flex items-center justify-between text-xs text-zinc-500">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-zinc-400" />
            Quick Fill:
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => { setEmail('devacia.com@gmail.com'); setPassword('admin123'); setError(''); }}
              className="text-violet-400 hover:text-violet-300 transition-colors underline font-mono text-[11px]"
            >
              devacia.com@gmail.com
            </button>
            <span className="text-zinc-700">|</span>
            <button
              type="button"
              onClick={fillDemoAdmin}
              className="text-violet-400 hover:text-violet-300 transition-colors underline font-mono text-[11px]"
            >
              admin@devacia.com
            </button>
          </div>
        </div>

        {process.env.NEXT_PUBLIC_APP_ENV === 'staging' && (
          <div className="mt-4 text-center">
            <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              Staging Mode Active
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
