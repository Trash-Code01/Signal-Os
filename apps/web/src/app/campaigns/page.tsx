"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FiSearch, FiArchive, FiPlus } from 'react-icons/fi';
import { ChevronRight } from 'lucide-react';

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCampaigns() {
      try {
        const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
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
    <div className="p-4 md:p-10 max-w-[1400px] pb-24 md:pb-10 w-full mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-6 md:mb-10 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white mb-1 md:mb-2 tracking-tight">All Campaigns</h1>
          <p className="text-sm md:text-base text-zinc-400">Manage your active and past intelligence pipelines.</p>
        </div>
        <button 
          onClick={() => router.push('/campaigns/new')} 
          className="hidden md:flex items-center gap-2 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-4 py-2 rounded-md text-sm font-medium transition whitespace-nowrap"
        >
          <FiPlus /> New campaign
        </button>
      </div>

      <div className="bg-[#121214] md:border border-zinc-800/60 rounded-xl overflow-hidden">
        <div className="p-4 md:border-b border-zinc-800 flex justify-between items-center md:bg-zinc-900/50 bg-transparent px-0 md:px-4 pb-2 md:pb-4">
          <div className="relative w-full md:w-72">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
            <input 
              type="text" 
              placeholder="Filter campaigns by name..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#09090b] border border-zinc-800 text-sm text-white rounded-xl md:rounded-md pl-10 pr-4 py-3 md:py-2 outline-none focus:border-purple-500 transition"
            />
          </div>
        </div>
        
        {loading ? (
          <div className="p-10 text-center text-zinc-500">Loading campaigns...</div>
        ) : (
          <>
            {/* Desktop Table Layout */}
            <div className="hidden md:block overflow-x-auto">
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
                      <td className="px-6 py-4 text-right text-zinc-500 group-hover:text-white transition">â†’</td>
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

            {/* Mobile Cards Layout */}
            <div className="md:hidden flex flex-col gap-3">
              {filteredCampaigns.length > 0 ? filteredCampaigns.map((c: any) => (
                <div 
                  key={c.id} 
                  onClick={() => router.push(`/leads?campaignId=${c.id}`)}
                  className="bg-[#121214] border border-zinc-800/60 p-4 rounded-xl cursor-pointer active:scale-[0.98] transition-all hover:border-zinc-700"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <FiArchive className="text-purple-500 shrink-0" />
                      <h3 className="font-bold text-white text-base leading-tight">{c.name}</h3>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider shrink-0 ${
                      c.status === 'completed' ? 'text-green-400 bg-green-900/30' :
                      c.status === 'running' ? 'text-blue-400 bg-blue-900/30' :
                      'text-zinc-400 bg-zinc-800'
                    }`}>
                      {c.status.toUpperCase()}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-y-2 mb-4">
                    <div>
                      <p className="text-[10px] text-zinc-500 uppercase font-semibold">Location</p>
                      <p className="text-sm text-zinc-300 truncate pr-2">{c.city}, {c.country}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-zinc-500 uppercase font-semibold">Industry</p>
                      <p className="text-sm text-zinc-300 capitalize truncate">{c.industry}</p>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center pt-3 border-t border-zinc-800/60">
                    <span className="text-xs text-zinc-400"><span className="text-white font-medium">{c.target}</span> leads target</span>
                    <span className="text-xs text-purple-400 flex items-center gap-1 font-medium">View leads <ChevronRight className="w-3 h-3" /></span>
                  </div>
                </div>
              )) : (
                <div className="py-10 text-center text-zinc-500 bg-[#121214] rounded-xl border border-dashed border-zinc-800">
                  No campaigns found matching "{search}".
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
