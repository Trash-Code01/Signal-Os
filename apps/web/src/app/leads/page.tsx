import React from 'react';

async function getLeads() {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/leads', { cache: 'no-store' });
    if (!res.ok) return { leads: [] };
    return res.json();
  } catch (e) {
    return { leads: [] };
  }
}

export default async function LeadsPipeline() {
  const data = await getLeads();
  const leads = data.leads || [];

  return (
    <div className="p-10 max-w-[1400px]">
      
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider mb-2">Leads / All qualified prospects</p>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Qualified leads</h1>
          <p className="text-zinc-400">Review, filter and hand off the best opportunities to SDR.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-green-500/10 text-green-500 px-3 py-1.5 rounded-full text-xs font-bold tracking-wide uppercase border border-green-500/20">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Live System
          </div>
          <button className="bg-zinc-900 border border-zinc-800 text-zinc-400 p-2 rounded-md hover:text-white transition">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/></svg>
          </button>
          <button className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-4 py-2.5 rounded-md text-sm font-medium transition">
            Export selected
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-4 mb-8 flex gap-4 items-center">
        <div className="flex bg-zinc-900 rounded-md p-1 border border-zinc-800">
          <button className="bg-zinc-800 text-green-500 text-xs font-bold px-3 py-1.5 rounded shadow-sm">A+ · 41</button>
          <button className="text-zinc-400 hover:text-white text-xs font-bold px-3 py-1.5 rounded transition">A · 73</button>
        </div>
        <select className="bg-zinc-900 border border-zinc-800 text-sm text-zinc-300 rounded-md px-4 py-2 outline-none appearance-none">
          <option>Industry: All</option>
        </select>
        <select className="bg-zinc-900 border border-zinc-800 text-sm text-zinc-300 rounded-md px-4 py-2 outline-none appearance-none">
          <option>Location: All</option>
        </select>
        <select className="bg-zinc-900 border border-zinc-800 text-sm text-zinc-300 rounded-md px-4 py-2 outline-none appearance-none">
          <option>Offer: All</option>
        </select>
        <input 
          type="text" 
          placeholder="Search companies..." 
          className="ml-auto bg-zinc-900 border border-zinc-800 text-sm text-white rounded-md px-4 py-2 outline-none focus:border-zinc-600 w-64"
        />
      </div>

      {/* Table */}
      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl">
        <div className="overflow-x-auto p-2">
          <table className="w-full text-left text-sm">
            <thead className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">
              <tr>
                <th className="px-6 py-4">Company</th>
                <th className="px-6 py-4">Location</th>
                <th className="px-6 py-4">Industry</th>
                <th className="px-6 py-4">Score</th>
                <th className="px-6 py-4">Opportunity</th>
                <th className="px-6 py-4">Contact</th>
                <th className="px-6 py-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              
              {leads.length > 0 ? leads.map((lead: any) => (
                <tr key={lead.id} className="hover:bg-zinc-800/20 transition group cursor-pointer" onClick={() => window.location.href = `/leads/${lead.id}`}>
                  <td className="px-6 py-5 text-white font-medium">{lead.name}</td>
                  <td className="px-6 py-5 text-zinc-400">{lead.location}</td>
                  <td className="px-6 py-5">
                    <span className="bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs px-3 py-1 rounded-full">Detected</span>
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-green-500 bg-green-500/10 px-2 py-1 rounded text-xs font-bold">{lead.score}</span>
                  </td>
                  <td className="px-6 py-5 text-zinc-300">Qualified</td>
                  <td className="px-6 py-5 text-zinc-400">
                    {lead.contact || 'No Decision Maker'}
                  </td>
                  <td className="px-6 py-5 text-right">
                    <a href={`/leads/${lead.id}`} className="text-zinc-500 group-hover:text-white transition inline-block">
                      →
                    </a>
                  </td>
                </tr>
              )) : (
                <tr className="border-b border-zinc-800/60">
                  <td colSpan={7} className="px-6 py-12 text-center text-zinc-500">
                    <div className="flex flex-col items-center justify-center">
                      <svg className="w-12 h-12 text-zinc-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                      </svg>
                      <p className="text-lg text-white font-medium mb-1">No leads found</p>
                      <p className="text-sm">Start a new campaign or check your DataForSEO API credits.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {/* Footer */}
        <div className="border-t border-zinc-800/60 p-4 flex justify-between items-center text-xs text-zinc-500">
          <p>Showing 1-{Math.max(8, leads.length)} of {Math.max(164, leads.length)} qualified leads</p>
          <div className="flex gap-1">
            <button className="w-8 h-8 rounded flex items-center justify-center bg-zinc-900 text-zinc-500 hover:text-white transition">‹</button>
            <button className="w-8 h-8 rounded flex items-center justify-center bg-[#8b5cf6] text-white font-medium">1</button>
            <button className="w-8 h-8 rounded flex items-center justify-center bg-zinc-900 text-zinc-400 hover:text-white transition">2</button>
            <button className="w-8 h-8 rounded flex items-center justify-center bg-zinc-900 text-zinc-400 hover:text-white transition">›</button>
          </div>
        </div>
      </div>
      
      <p className="text-xs text-zinc-600 mt-6">Tip: prioritize A+ leads with a verified decision maker and a clear offer fit.</p>
    </div>
  );
}
