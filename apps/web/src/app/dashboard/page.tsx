import React from 'react';
import { SidebarTrigger } from "@/components/ui/sidebar";

async function getDashboardStats() {
  try {
    let res = await fetch("http://api:8000/api/dashboard", { cache: 'no-store' }).catch(() => null);
    if (!res) {
      res = await fetch("http://localhost:8000/api/dashboard", { cache: 'no-store' });
    }
    if (!res?.ok) return null;
    return res.json();
  } catch (e) {
    return null;
  }
}

export default async function DashboardPage() {
  const data = await getDashboardStats();
  if (!data) return <div>Failed to load dashboard</div>;

  const { stats, recent_campaigns = [], chart_data = [], priority_opportunities = [] } = data;
  
  // Calculate max value for chart scaling (at least 200 for good visuals)
  const maxChartVal = Math.max(200, ...chart_data.map((d: any) => d.value));

  return (
    <div className="p-4 md:p-6 lg:p-10 max-w-[1400px] w-full mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-10">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <SidebarTrigger className="lg:hidden text-zinc-400 hover:text-white" />
            <h1 className="text-3xl font-bold text-white tracking-tight">Good evening, Laraib.</h1>
          </div>
          <p className="text-zinc-400">Your lead engine is running. Here is what needs your attention.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            LIVE SYSTEM
          </div>
          <a href="/campaigns/new" className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-4 py-2 rounded-md text-sm font-medium transition">
            + New campaign
          </a>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6 relative overflow-hidden">
          <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Qualified Leads</p>
          <p className="text-4xl font-bold text-white">{stats.qualified_opportunities}</p>
          <div className="mt-4 flex items-center text-xs font-medium text-green-500">
            <span>+{Math.floor(stats.qualified_opportunities * 0.1)} today</span>
          </div>
        </div>
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
          <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">A / A+ Prospects</p>
          <p className="text-4xl font-bold text-white">{stats.a_plus_leads}</p>
          <div className="mt-4 flex items-center text-xs font-medium text-green-500 bg-green-500/10 w-max px-2 py-0.5 rounded">
            <span>{stats.qualified_opportunities > 0 ? Math.round((stats.a_plus_leads / stats.qualified_opportunities) * 100) : 0}% of qualified</span>
          </div>
        </div>
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
          <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Campaigns Running</p>
          <p className="text-4xl font-bold text-white">{stats.campaigns}</p>
          <div className="mt-4 flex items-center text-xs font-medium text-green-500">
            <span>+2 this week</span>
          </div>
        </div>
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
          <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Avg. Lead Score</p>
          <p className="text-4xl font-bold text-white">{stats.average_score}</p>
          <div className="mt-4 flex items-center text-xs font-medium text-green-500">
            <span>+4.2%</span>
          </div>
        </div>
      </div>

      {/* Main Content Area: Chart and Active Campaigns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mb-8">

        {/* Bar Chart */}
        <div className="lg:col-span-2 bg-[#121214] border border-zinc-800/60 rounded-xl p-4 md:p-6 relative">
          <div className="flex justify-between items-center mb-10">
            <div>
              <h2 className="text-lg font-bold text-white">Pipeline performance</h2>
              <p className="text-sm text-zinc-500 mt-1">Qualified opportunities by day</p>
            </div>
            <select className="bg-zinc-900 border border-zinc-800 text-xs text-zinc-400 rounded-md px-3 py-1.5 outline-none">
              <option>Last 7 days</option>
            </select>
          </div>
          <div className="h-64 flex items-end justify-between gap-4 px-2 pb-6 border-b border-zinc-800 relative">
            <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-[10px] text-zinc-600 pb-6">
              <span>{maxChartVal}</span><span>{Math.round(maxChartVal * 0.75)}</span><span>{Math.round(maxChartVal * 0.5)}</span>
            </div>
            <div className="ml-8 flex items-end justify-between w-full h-full pb-0">
              {chart_data.map((d: any, i: number) => {
                const heightPercentage = Math.max(5, (d.value / maxChartVal) * 100);
                const isLast = i === chart_data.length - 1;
                return (
                  <div key={i} style={{ height: `${heightPercentage}%` }} className={`w-12 rounded-t-md ${isLast ? 'bg-[#8b5cf6] shadow-[0_0_15px_rgba(139,92,246,0.3)]' : 'bg-zinc-700/50'}`}></div>
                );
              })}
            </div>
          </div>
          <div className="flex justify-between px-2 pt-3 ml-8 text-[10px] text-zinc-500 font-medium">
            {chart_data.map((d: any, i: number) => (
              <span key={i} className={`w-12 text-center ${i === chart_data.length - 1 ? 'text-white' : ''}`}>{d.day}</span>
            ))}
          </div>
        </div>

        {/* Active Campaigns */}
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-bold text-white">Active campaigns</h2>
          <p className="text-sm text-zinc-500 mt-1 mb-6">Currently processing</p>
          <div className="space-y-6">
            {recent_campaigns.length > 0 ? recent_campaigns.map((c: any) => (
              <div key={c.id}>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="font-medium text-white">{c.country} • {c.industry}</span>
                  <span className="text-zinc-400">{c.progress} / {c.target}</span>
                </div>
                <p className="text-xs text-zinc-500 mb-2">{c.city}</p>
                <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-500" style={{ width: `${(c.progress / c.target) * 100}%` }}></div>
                </div>
              </div>
            )) : (
              <div className="text-sm text-zinc-500">No active campaigns.</div>
            )}
          </div>
        </div>
      </div>

      {/* Priority Opportunities Table */}
      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-4 md:p-6 mb-10">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-lg font-bold text-white">Priority opportunities</h2>
            <p className="text-sm text-zinc-500 mt-1">Highest-value leads requiring SDR action</p>
          </div>
          <a href="/leads" className="text-xs text-zinc-400 hover:text-white border border-zinc-800 px-3 py-1.5 rounded-md transition">View all →</a>
        </div>
        <div className="space-y-4">
          {priority_opportunities.length > 0 ? priority_opportunities.map((opp: any) => (
            <a 
              key={opp.id}
              href={`/leads/${opp.id}`}
              className="block bg-[#18181b] rounded-2xl p-5 hover:bg-zinc-800 transition-colors border border-transparent hover:border-white/5"
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-bold text-white text-lg">{opp.name}</h3>
                  <p className="text-sm text-zinc-400">{opp.industry} • {opp.city}</p>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${opp.score >= 90 ? "text-[#34d399] bg-[#064e3b]" : "text-[#fb923c] bg-[#431407]"}`}>
                  {opp.score >= 90 ? "A+" : "A"} • {opp.score}
                </span>
              </div>
              <div className="bg-[#121214] rounded-xl p-3">
                <p className="text-xs text-zinc-500 mb-1 uppercase tracking-wider font-semibold">Recommended Offer</p>
                <p className="text-sm text-[#34d399] font-medium truncate">{opp.recommended_offer}</p>
              </div>
            </a>
          )) : (
            <div className="text-center py-10 bg-[#18181b] rounded-2xl border border-dashed border-zinc-800">
              <p className="text-zinc-500 text-sm">No priority opportunities yet. Keep running campaigns!</p>
            </div>
          )}
        </div></div>
      </div>
  );
}
