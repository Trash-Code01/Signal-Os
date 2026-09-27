'use client';

import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';
import { 
  Terminal, 
  Mail, 
  Lock, 
  User as UserIcon, 
  ArrowRight, 
  Sparkles, 
  ShieldCheck, 
  Eye, 
  EyeOff, 
  CheckCircle2, 
  Database, 
  Search, 
  Zap, 
  Globe,
  Layers
} from 'lucide-react';

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
  const initializedRef = useRef(false);
  const [scriptReady, setScriptReady] = useState(false);
  const [config, setConfig] = useState<{ client_id: string; nonce: string }>({
    client_id: FALLBACK_CLIENT_ID,
    nonce: '',
  });
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleRendered, setGoogleRendered] = useState(false);

  // Safely fetch Google auth nonce without crashing if backend returns HTML during cold starts
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
          // Graceful fallback to default client ID
        }
      })
      .catch(() => {});
  }, []);

  // Initialize Google Identity Services strictly once
  useEffect(() => {
    if (!scriptReady || !config?.nonce || !window.google || !googleBtnRef.current || initializedRef.current) return;
    try {
      initializedRef.current = true;
      const effectiveClientId = config.client_id || FALLBACK_CLIENT_ID;
      window.google.accounts.id.initialize({
        client_id: effectiveClientId,
        nonce: config.nonce,
        auto_select: false,
        itp_support: true,
        use_fedcm_for_prompt: true,
        callback: async ({ credential }) => {
          setGoogleLoading(true);
          setError('');
          try {
            const response = await fetch('/api/auth/google', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ credential, nonce: config.nonce }),
            });
            const text = await response.text();
            let data: any = {};
            try {
              data = JSON.parse(text);
            } catch {
              throw new Error('Authentication backend is starting. Please wait a moment and retry.');
            }
            if (!response.ok) throw new Error(data.detail || 'Google sign-in could not be completed.');
            window.location.replace('/dashboard');
          } catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Google sign-in could not be completed.');
            setGoogleLoading(false);
          }
        },
      });

      googleBtnRef.current.replaceChildren();
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'filled_black',
        size: 'large',
        text: 'continue_with',
        width: 360,
      });
      setGoogleRendered(true);
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
        throw new Error('Backend service is waking up.');
      }

      if (!response.ok) {
        throw new Error(data.detail || 'Quick sign-in failed.');
      }

      window.location.replace('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Quick sign-in failed.');
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#070709] text-white flex flex-col lg:grid lg:grid-cols-12 selection:bg-violet-500/30">
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onReady={() => setScriptReady(true)}
        onError={() => {}}
      />

      {/* LEFT COLUMN: Enterprise Showcase & Branding (Hidden on mobile/tablet, glorious on desktop) */}
      <div className="hidden lg:flex lg:col-span-6 xl:col-span-7 flex-col justify-between p-12 lg:p-16 border-r border-zinc-800/60 bg-gradient-to-br from-[#0c0c10] via-[#09090d] to-[#050507] relative overflow-hidden">
        {/* Ambient background glow & grid */}
        <div className="absolute top-0 -left-20 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute inset-0 bg-[radial-gradient(#1f1f2e_1px,transparent_1px)] [background-size:24px_24px] opacity-20 pointer-events-none" />

        {/* Top Header */}
        <div className="relative z-10">
          <div className="flex items-center gap-3.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-violet-600/30">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-white block">DEVACIA LEAD OS</span>
              <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-widest block -mt-0.5">Enterprise Pipeline Intelligence</span>
            </div>
          </div>
        </div>

        {/* Center Hero Value Proposition */}
        <div className="relative z-10 my-auto py-12 max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-300 text-xs font-medium mb-6">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span>Autonomous B2B Lead Intelligence 2.0</span>
          </div>

          <h1 className="text-4xl xl:text-5xl font-extrabold tracking-tight text-white leading-[1.15]">
            Turn web signals into verified pipeline <span className="bg-gradient-to-r from-violet-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">in seconds.</span>
          </h1>

          <p className="mt-4 text-base text-zinc-400 leading-relaxed">
            Autonomous multi-source discovery, deep website signal auditing, and verified contact enrichment — built with enterprise data isolation for high-converting sales teams.
          </p>

          {/* Three Feature Highlight Cards */}
          <div className="mt-8 space-y-3.5">
            <div className="flex items-start gap-3.5 p-3.5 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 backdrop-blur-sm">
              <div className="h-9 w-9 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 shrink-0 mt-0.5">
                <Search className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-zinc-200">Multi-Directory Discovery Engine</h4>
                <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">
                  Real-time Google SERP & Google Maps scraping with advanced Boolean qualification.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3.5 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 backdrop-blur-sm">
              <div className="h-9 w-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                <Zap className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-zinc-200">Verified Contact Intelligence</h4>
                <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">
                  Identifies company leadership, verified work emails, and direct mobile lines.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 p-3.5 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 backdrop-blur-sm">
              <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                <Database className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-zinc-200">Multi-Tenant Database Isolation</h4>
                <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">
                  Every account receives an isolated workspace. Your leads and campaigns are 100% private.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Trust & Security Metrics */}
        <div className="relative z-10 pt-6 border-t border-zinc-800/60 flex items-center justify-between text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Platform Status: Operational</span>
          </div>
          <div className="flex items-center gap-6">
            <span>256-bit Encryption</span>
            <span>SOC-2 Architecture</span>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: The Luxury Authentication Interface */}
      <div className="col-span-12 lg:col-span-6 xl:col-span-5 flex items-center justify-center p-6 sm:p-10 relative">
        <div className="w-full max-w-md">
          {/* Mobile brand header (shown on small screens only) */}
          <div className="lg:hidden text-center mb-8">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-500 text-white shadow-lg shadow-violet-600/30">
              <Terminal className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white">Devacia Lead OS</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Enterprise Pipeline Intelligence</p>
          </div>

          <div className="rounded-3xl border border-zinc-800/90 bg-[#111114]/90 p-8 sm:p-9 shadow-2xl shadow-black/80 backdrop-blur-xl">
            {/* Form Title & Subtitle */}
            <div className="mb-6">
              <h2 className="text-2xl font-bold tracking-tight text-white">
                {mode === 'signin' ? 'Welcome back' : 'Create workspace'}
              </h2>
              <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                {mode === 'signin'
                  ? 'Sign in to access your private campaigns, leads, and analytics'
                  : 'Start your isolated lead workspace in seconds'}
              </p>
            </div>

            {/* Error Banner */}
            {error && (
              <div role="alert" className="mb-5 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-center text-xs text-rose-300 leading-relaxed">
                {error}
              </div>
            )}

            {/* Method 1: Google Single Sign-On (Prominent) */}
            <div className="space-y-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block text-center">
                One-Click Single Sign-On
              </p>

              {/* Official Google Identity Button mount */}
              <div
                ref={googleBtnRef}
                className={`flex justify-center min-h-[44px] ${googleLoading ? 'pointer-events-none opacity-50' : ''}`}
              />

              {/* Styled Fallback Google Button */}
              {!googleRendered && (
                <button
                  type="button"
                  onClick={handleGoogleClick}
                  disabled={googleLoading || loading}
                  className="w-full flex items-center justify-center gap-3 rounded-xl border border-zinc-700/80 bg-zinc-900/90 hover:bg-zinc-800 text-white font-medium py-2.5 px-4 text-sm transition-all shadow-sm cursor-pointer disabled:opacity-50"
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
                <p className="text-center text-xs text-zinc-400 animate-pulse">Authenticating with Google…</p>
              )}
            </div>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-zinc-800" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-[#111114] px-3 text-zinc-500 font-semibold tracking-wider">
                  or work email credentials
                </span>
              </div>
            </div>

            {/* Tab Switcher: Sign In vs Create Account */}
            <div className="flex rounded-xl bg-zinc-950/70 p-1 border border-zinc-800/80 mb-5">
              <button
                type="button"
                onClick={() => { setMode('signin'); setError(''); }}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
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
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  mode === 'signup'
                    ? 'bg-violet-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Create Account
              </button>
            </div>

            {/* Email & Password Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'signup' && (
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block mb-1.5">
                    Your Name
                  </label>
                  <div className="relative">
                    <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Alex Rivers"
                      className="w-full rounded-xl border border-zinc-800 bg-zinc-950/80 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 transition-all [color-scheme:dark]"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block mb-1.5">
                  Work Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950/80 pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 transition-all [color-scheme:dark]"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950/80 pl-10 pr-10 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 transition-all [color-scheme:dark]"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || googleLoading}
                className="w-full mt-2 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold py-2.5 px-4 text-sm transition-all duration-150 shadow-lg shadow-violet-600/30 disabled:opacity-50 cursor-pointer"
              >
                {loading ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <span>{mode === 'signin' ? 'Sign In to Workspace' : 'Create Isolated Workspace'}</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Sandbox Access Badge */}
            <div className="mt-6 pt-4 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-400">
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

            {/* Multi-Tenant Security Note */}
            <div className="mt-4 rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3 text-[11px] text-zinc-400 flex items-start gap-2.5">
              <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <p className="leading-relaxed text-zinc-400">
                <strong className="text-zinc-300">Multi-Tenant Isolation:</strong> Each account's campaigns, search queries, leads, and exports are strictly isolated.
              </p>
            </div>
          </div>

          <p className="mt-6 text-center text-xs text-zinc-500">
            Protected by enterprise encryption · Devacia Lead OS v2.0
          </p>
        </div>
      </div>
    </main>
  );
}
