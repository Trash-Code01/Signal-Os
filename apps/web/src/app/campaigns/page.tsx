"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FiSearch, FiArchive } from 'react-icons/fi';

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCampaigns() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace('localhost', 'api') || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/campaigns`);
        if (res.ok) {
          const data = await res.json();
          setCampaigns(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchCampaigns();
  }, []);

  const filteredCampaigns = campaigns.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-10 max-w-[1400px]">
      <div className="flex justify-between items-end mb-10">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">All Campaigns</h1>
          <p className="text-zinc-400">Manage your active and past intelligence pipelines.</p>
        </div>
        <a href="/campaigns/new" className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-4 py-2 rounded-md text-sm font-medium transition">
          + New campaign
        </a>
      </div>

      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50">
          <div className="relative w-72">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
            <input 
              type="text" 
              placeholder="Filter campaigns by name..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#09090b] border border-zinc-800 text-sm text-white rounded-md pl-9 pr-4 py-2 outline-none focus:border-purple-500 transition"
            />
          </div>
        </div>
        
        {loading ? (
          <div className="p-10 text-center text-zinc-500">Loading campaigns...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs text-zinc-500 uppercase tracking-wider border-b border-zinc-800/60 bg-zinc-900/20">
                  <th className="px-6 py-4 font-medium">Campaign Name</th>
                  <th className="px-6 py-4 font-medium">Location</th>
                  <th className="px-6 py-4 font-medium">Industry</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Target</th>
                  <th className="px-6 py-4 font-medium text-right">View Leads</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {filteredCampaigns.length > 0 ? filteredCampaigns.map((c: any) => (
                  <tr 
                    key={c.id} 
                    className="hover:bg-zinc-800/20 transition group cursor-pointer" 
                    onClick={() => router.push(`/leads?campaignId=${c.id}`)}
                  >
                    <td className="px-6 py-4 text-white font-medium flex items-center gap-3">
                      <FiArchive className="text-purple-500" />
                      {c.name}
                    </td>
                    <td className="px-6 py-4 text-zinc-400">{c.city}, {c.country}</td>
                    <td className="px-6 py-4"><span className="bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs px-3 py-1 rounded-full">{c.industry}</span></td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        c.status === 'completed' ? 'text-green-500 bg-green-500/10' :
                        c.status === 'running' ? 'text-blue-500 bg-blue-500/10' :
                        'text-zinc-400 bg-zinc-800'
                      }`}>
                        {c.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-zinc-300">{c.target} leads</td>
                    <td className="px-6 py-4 text-right text-zinc-500 group-hover:text-white transition">→</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-10 text-center text-zinc-500">
                      No campaigns found matching "{search}".
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}