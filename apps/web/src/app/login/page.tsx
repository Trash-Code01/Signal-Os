'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Terminal } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      
      if (res.ok) {
        window.location.href = '/dashboard';
      } else {
        const data = await res.json();
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('An error occurred during login');
    }
    
    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-[#09090b] flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <div className="bg-[#121214] p-3 rounded-xl border border-zinc-800 shadow-xl shadow-purple-900/10">
            <Terminal className="w-8 h-8 text-[#a78bfa]" />
          </div>
        </div>
        
        <div className="bg-[#121214] border border-zinc-800/60 rounded-2xl p-8 shadow-2xl">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Welcome back</h1>
            <p className="text-sm text-zinc-400">Sign in to Devacia Lead OS</p>
          </div>

          {error && (
            <div className="mb-6 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">Email</label>
              <input
                type="email"
                required
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors placeholder:text-zinc-600"
                placeholder="admin@devacia.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>
            
            <div>
              <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">Password</label>
              <input
                type="password"
                required
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors placeholder:text-zinc-600"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#8b5cf6] hover:bg-[#7c3aed] text-white py-3 rounded-lg text-sm font-medium transition shadow-lg shadow-purple-900/20 mt-4 flex items-center justify-center disabled:opacity-50"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
