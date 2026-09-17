'use client';
import { useEffect, useState } from 'react';
import { ExternalLink, KeyRound, Lock, Mail, ShieldCheck, TriangleAlert, Server, Terminal, Database } from 'lucide-react';

type ProviderStatus = {
  id: string;
  name: string;
  environment_keys: string[];
  configured: boolean;
  state: string;
  message: string;
  last_http_status?: number | null;
  action_required: boolean;
};

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function SettingsPage() {
  const [emailForm, setEmailForm] = useState({ currentPassword: '', newEmail: '' });
  const [passForm, setPassForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
  
  const [emailStatus, setEmailStatus] = useState({ loading: false, error: '', success: '' });
  const [passStatus, setPassStatus] = useState({ loading: false, error: '', success: '' });
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [renderEnvironmentUrl, setRenderEnvironmentUrl] = useState('https://dashboard.render.com/');
  const [providerError, setProviderError] = useState('');
  const [envInfo, setEnvInfo] = useState<{ environment?: string; discovery_mode?: string; database_host?: string } | null>(null);

  const appEnv = process.env.NEXT_PUBLIC_APP_ENV || (process.env.NEXT_PUBLIC_API_URL?.includes('localhost') || process.env.NEXT_PUBLIC_API_URL?.includes('127.0.0.1') ? 'staging' : 'production');
  const isStaging = appEnv === 'staging';
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || (isStaging ? 'http://localhost:8000' : 'https://devacia-backend.onrender.com');

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || '';
    fetch(`${base}/api/environment`)
      .then(async (res) => {
        if (res.ok) return res.json();
        return null;
      })
      .then((data) => {
        if (data) setEnvInfo(data);
      })
      .catch(() => {});

    fetch(`${base}/api/providers/status`)
      .then(async (response) => {
        if (!response.ok) throw new Error('Unable to load provider health.');
        return response.json();
      })
      .then((data) => {
        setProviders(data.providers || []);
        setRenderEnvironmentUrl(data.render_environment_url || 'https://dashboard.render.com/');
      })
      .catch((err) => setProviderError(err.message || 'Unable to load provider health.'));
  }, []);

  async function handleEmailChange(e: React.FormEvent) {
    e.preventDefault();
    setEmailStatus({ loading: true, error: '', success: '' });
    try {
      const res = await fetch("" + '/api/auth/update-email', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: emailForm.currentPassword, new_email: emailForm.newEmail })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update email');
      setEmailStatus({ loading: false, error: '', success: 'Email successfully updated.' });
      setEmailForm({ currentPassword: '', newEmail: '' });
    } catch (err: unknown) {
      setEmailStatus({ loading: false, error: errorMessage(err, 'Failed to update email'), success: '' });
    }
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setPassStatus({ loading: true, error: '', success: '' });
    if (passForm.newPassword !== passForm.confirmPassword) {
      return setPassStatus({ loading: false, error: 'New passwords do not match.', success: '' });
    }
    if (passForm.newPassword.length < 8) {
      return setPassStatus({ loading: false, error: 'Password must be at least 8 characters.', success: '' });
    }
    
    try {
      const res = await fetch("" + '/api/auth/update-password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: passForm.currentPassword, new_password: passForm.newPassword })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update password');
      setPassStatus({ loading: false, error: '', success: 'Password successfully updated.' });
      setPassForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (err: unknown) {
      setPassStatus({ loading: false, error: errorMessage(err, 'Failed to update password'), success: '' });
    }
  }

  return (
    <div className="p-4 md:p-10 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-[#8b5cf6]" /> Security & Settings
        </h1>
        <p className="text-sm md:text-base text-zinc-400 mt-2">Manage your account credentials and security preferences.</p>
      </div>

      <div className="space-y-8">
        {/* Environment & Runtime Mode Card */}
        <div className={`border rounded-xl p-6 transition-all ${
          isStaging 
            ? 'bg-amber-950/20 border-amber-500/30' 
            : 'bg-[#121214] border-zinc-800/60'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5">
                <Server className={`w-5 h-5 ${isStaging ? 'text-amber-400' : 'text-emerald-400'}`} />
                <h2 className="text-lg font-semibold text-white">System Environment</h2>
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                  isStaging 
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                }`}>
                  {isStaging ? 'Staging / Local Sandbox' : 'Production Mode'}
                </span>
              </div>
              <p className="mt-2 text-sm text-zinc-400 max-w-2xl">
                {isStaging 
                  ? 'You are running in Staging mode. Campaigns, enrichment, and leads will not touch live production data or consume production API credits.' 
                  : 'You are connected to the live Render production backend. Changes will affect live production data and credentials.'}
              </p>
            </div>
            <div className="shrink-0 flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium ${
                isStaging 
                  ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30' 
                  : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
              }`}>
                <span className={`w-2 h-2 rounded-full ${isStaging ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
                {isStaging ? 'Port 3001 (Staging)' : 'Port 3001 (Prod)'}
              </span>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-black/30 border border-white/5 rounded-lg p-3">
              <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Backend Target</div>
              <div className="text-sm font-mono text-white mt-1 truncate">{backendUrl}</div>
            </div>
            <div className="bg-black/30 border border-white/5 rounded-lg p-3">
              <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Discovery Engine</div>
              <div className="text-sm font-mono text-white mt-1 capitalize">
                {envInfo?.discovery_mode ? `${envInfo.discovery_mode} mode` : (isStaging ? 'mock (zero credit cost)' : 'live')}
              </div>
            </div>
            <div className="bg-black/30 border border-white/5 rounded-lg p-3">
              <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Database Target</div>
              <div className="text-sm font-mono text-white mt-1">
                {envInfo?.database_host === 'localhost' || isStaging ? 'Local PostgreSQL' : 'Render PostgreSQL'}
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-zinc-400">
            <div className="flex items-center gap-2">
              <Terminal className="w-3.5 h-3.5 text-zinc-500" />
              <span>Switch mode anytime:</span>
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px]">
              <code className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-amber-300">npm run dev:staging</code>
              <span>or</span>
              <code className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-emerald-300">npm run dev:prod</code>
            </div>
          </div>
        </div>

        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-violet-300" /> Enrichment API health
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">When a provider runs out of credits, is rate-limited, or has an invalid key, it appears here and on the lead page. Secrets stay in Render—they are never displayed or stored in the browser.</p>
            </div>
            <a href={renderEnvironmentUrl} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-violet-200 px-3.5 py-2.5 text-xs font-semibold text-violet-950 hover:bg-violet-100 transition-colors">
              Update keys in Render <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          {providerError ? (
            <p className="mt-5 rounded-lg border border-amber-400/20 bg-amber-400/10 p-3 text-sm text-amber-200">{providerError}</p>
          ) : (
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {providers.map((provider) => {
                const isHealthy = provider.state === 'active';
                const isPaused = provider.state === 'cooldown';
                const color = isHealthy ? 'emerald' : isPaused ? 'sky' : 'amber';
                return (
                  <div key={provider.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-medium text-zinc-100">{provider.name}</h3>
                        <p className="mt-1 text-xs text-zinc-500">{provider.environment_keys.join(' + ')}</p>
                      </div>
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${color === 'emerald' ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300' : color === 'sky' ? 'border-sky-400/20 bg-sky-400/10 text-sky-300' : 'border-amber-400/20 bg-amber-400/10 text-amber-300'}`}>
                        {provider.state.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-5 text-zinc-400">{provider.message}</p>
                    {provider.action_required && <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-300"><TriangleAlert className="w-3.5 h-3.5" /> Replace this key in Render, then rerun enrichment.</p>}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Email Settings */}
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <Mail className="w-5 h-5 text-zinc-400" /> Change Email Address
          </h2>
          
          {emailStatus.error && <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">{emailStatus.error}</div>}
          {emailStatus.success && <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 text-sm">{emailStatus.success}</div>}

          <form onSubmit={handleEmailChange} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">Current Password</label>
              <input
                type="password"
                required
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                value={emailForm.currentPassword}
                onChange={e => setEmailForm({ ...emailForm, currentPassword: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">New Email Address</label>
              <input
                type="email"
                required
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                value={emailForm.newEmail}
                onChange={e => setEmailForm({ ...emailForm, newEmail: e.target.value })}
              />
            </div>
            <button
              type="submit"
              disabled={emailStatus.loading}
              className="bg-zinc-800 hover:bg-zinc-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-50"
            >
              {emailStatus.loading ? 'Updating...' : 'Update Email'}
            </button>
          </form>
        </div>

        {/* Password Settings */}
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <Lock className="w-5 h-5 text-zinc-400" /> Change Password
          </h2>

          {passStatus.error && <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">{passStatus.error}</div>}
          {passStatus.success && <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 text-sm">{passStatus.success}</div>}

          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">Current Password</label>
              <input
                type="password"
                required
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                value={passForm.currentPassword}
                onChange={e => setPassForm({ ...passForm, currentPassword: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">New Password</label>
                <input
                  type="password"
                  required
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                  value={passForm.newPassword}
                  onChange={e => setPassForm({ ...passForm, newPassword: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">Confirm New Password</label>
                <input
                  type="password"
                  required
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                  value={passForm.confirmPassword}
                  onChange={e => setPassForm({ ...passForm, confirmPassword: e.target.value })}
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={passStatus.loading}
              className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-6 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-50"
            >
              {passStatus.loading ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
