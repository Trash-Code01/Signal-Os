'use client';
import { useEffect, useState } from 'react';
import { useSession, Account } from '@/components/SessionProvider';
import { ContactOptions, LookupOptions } from '@/components/ContactOptions';

export default function SettingsPage() {
  const { user, reload } = useSession();
  const [options, setOptions] = useState<LookupOptions>({ personal_email_enabled: false, phone_enabled: false });
  const [users, setUsers] = useState<Account[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<Account['role']>('viewer');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [providers, setProviders] = useState<{ name: string; state: string; message: string }[]>([]);
  useEffect(() => { if (user) setOptions({ personal_email_enabled: user.personal_email_enabled, phone_enabled: user.phone_enabled }); }, [user]);
  async function loadUsers() {
    const response = await fetch('/api/auth/users');
    if (!response.ok) throw new Error('Unable to load accounts.');
    setUsers(await response.json());
  }
  useEffect(() => {
    if (user?.role !== 'admin') return;
    loadUsers().catch(error => setError(error.message));
    fetch('/api/providers/status').then(async response => {
      if (response.ok) setProviders((await response.json()).providers || []);
    }).catch(() => {});
  }, [user?.role]);
  async function save(url: string, method: string, body: unknown, success: string) {
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not save changes.');
      if (url.includes('/users')) await loadUsers(); else await reload();
      setMessage(success);
      return true;
    } catch (error) { setError(error instanceof Error ? error.message : 'Could not save changes.'); return false; }
    finally { setBusy(false); }
  }
  if (!user) return null;
  return <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-10">
    <div><h1 className="text-3xl font-bold">Account settings</h1><p className="mt-2 text-sm text-zinc-400">{user.email} · <span className="capitalize">{user.role}</span></p></div>
    <div className="rounded-xl border border-zinc-800 bg-[#121214] p-5 text-sm text-zinc-400">Your campaigns, leads and exports belong to your account. Google manages your sign-in details.</div>
    {process.env.NEXT_PUBLIC_APP_ENV === 'staging' && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-300">Staging uses mock campaigns and a separate local database. Paid provider requests are disabled.</div>}
    {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
    {message && <p role="status" className="text-sm text-green-400">{message}</p>}
    <section className="space-y-4 rounded-xl border border-zinc-800 bg-[#121214] p-5">
      <h2 className="font-semibold">Default contact lookups</h2>
      <p className="text-sm text-zinc-400">Used for new campaigns and manual research. Existing campaigns keep their own choices.</p>
      <ContactOptions value={options} onChange={setOptions} disabled={busy} />
      <button disabled={busy} onClick={() => save('/api/auth/preferences', 'PUT', options, 'Defaults saved.')} className="rounded-lg bg-violet-600 px-4 py-2 text-sm disabled:opacity-50">Save defaults</button>
    </section>
    {user.role === 'admin' && <section className="space-y-5 rounded-xl border border-zinc-800 bg-[#121214] p-5">
      <h2 className="font-semibold">Accounts & roles</h2>
      <p className="text-sm text-zinc-400">Admin manages accounts. Member can run campaigns and edit their data. Viewer can read and export their data. Role changes require the affected account to sign in again.</p>
      <form className="flex flex-wrap gap-3" onSubmit={async event => {
        event.preventDefault();
        if (await save('/api/auth/users', 'POST', { email, role }, 'Access granted. The user can now sign in with this Google email.')) setEmail('');
      }}>
        <input aria-label="Google email to invite" required type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="Google email address" className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2" />
        <select aria-label="New account role" value={role} onChange={event => setRole(event.target.value as Account['role'])} className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2"><option value="viewer">Viewer</option><option value="member">Member</option><option value="admin">Admin</option></select>
        <button disabled={busy} className="rounded-lg bg-violet-600 px-4 py-2 text-sm disabled:opacity-50">Grant access</button>
      </form>
      <p className="text-xs text-zinc-500">Granting access creates an account invitation here; no email is sent.</p>
      <div className="space-y-3">{users.map(account => <div key={account.id} className="flex flex-wrap items-center gap-3 border-t border-zinc-800 pt-3">
        <div className="min-w-0 flex-1"><p className="break-all text-sm">{account.email}{account.id === user.id ? ' (you)' : ''}</p><p className="text-xs text-zinc-500">{account.is_active ? 'Enabled' : 'Disabled'}</p></div>
        <select aria-label={`Role for ${account.email}`} disabled={busy || account.id === user.id} value={account.role} onChange={event => save(`/api/auth/users/${account.id}`, 'PATCH', { role: event.target.value, is_active: account.is_active }, 'Role updated.')} className="rounded-lg border border-zinc-700 bg-zinc-900 p-2 text-sm disabled:opacity-50"><option value="viewer">Viewer</option><option value="member">Member</option><option value="admin">Admin</option></select>
        <button disabled={busy || account.id === user.id} onClick={() => save(`/api/auth/users/${account.id}`, 'PATCH', { role: account.role, is_active: !account.is_active }, 'Account access updated.')} className="rounded-lg border border-zinc-700 px-3 py-2 text-sm disabled:opacity-40">{account.is_active ? 'Disable' : 'Enable'}</button>
      </div>)}</div>
    </section>}
    {user.role === 'admin' && providers.length > 0 && <section className="rounded-xl border border-zinc-800 bg-[#121214] p-5"><h2 className="mb-4 font-semibold">Provider status</h2><div className="grid gap-3 md:grid-cols-2">{providers.map(provider => <div key={provider.name} className="rounded-lg border border-zinc-800 p-3"><p className="text-sm">{provider.name} · {provider.state}</p><p className="mt-1 text-xs text-zinc-500">{provider.message}</p></div>)}</div></section>}
  </div>;
}
