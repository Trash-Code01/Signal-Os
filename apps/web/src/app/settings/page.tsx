'use client';
import { useState } from 'react';
import { Lock, Mail, ShieldCheck } from 'lucide-react';

export default function SettingsPage() {
  const [emailForm, setEmailForm] = useState({ currentPassword: '', newEmail: '' });
  const [passForm, setPassForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
  
  const [emailStatus, setEmailStatus] = useState({ loading: false, error: '', success: '' });
  const [passStatus, setPassStatus] = useState({ loading: false, error: '', success: '' });

  async function handleEmailChange(e: React.FormEvent) {
    e.preventDefault();
    setEmailStatus({ loading: true, error: '', success: '' });
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/api/auth/update-email', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: emailForm.currentPassword, new_email: emailForm.newEmail })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update email');
      setEmailStatus({ loading: false, error: '', success: 'Email successfully updated.' });
      setEmailForm({ currentPassword: '', newEmail: '' });
    } catch (err: any) {
      setEmailStatus({ loading: false, error: err.message, success: '' });
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
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/api/auth/update-password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: passForm.currentPassword, new_password: passForm.newPassword })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update password');
      setPassStatus({ loading: false, error: '', success: 'Password successfully updated.' });
      setPassForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (err: any) {
      setPassStatus({ loading: false, error: err.message, success: '' });
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