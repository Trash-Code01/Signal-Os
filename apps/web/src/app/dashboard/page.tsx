import React from 'react';

async function getDashboardStats() {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/dashboard', { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    return null;
  }
}



export default async function Dashboard() {
  const data = await getDashboardStats();
  
  if (!data) {
    return (
      <div className="p-8 max-w-7xl h-full flex items-center justify-center text-center">
        <div>
          <h1 className="text-2xl font-bold">API Offline</h1>
          <p className="text-zinc-500 mt-2">Make sure the FastAPI backend is running on port 8000.</p>
        </div>
      </div>
    );
  }

  const { stats, recent_campaigns } = data;

  return (
    <div 
      
      
      
      className="p-10 max-w-[1400px]"
    >
      
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Good evening, Laraib.</h1>
          <p className="text-zinc-400">Your lead engine is running. Here is what needs your attention.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-green-500/10 text-green-500 px-3 py-1.5 rounded-full text-xs font-bold tracking-wide uppercase border border-green-500/20">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Live System
          </div>
          <button className="bg-zinc-900 border border-zinc-800 text-zinc-400 p-2 rounded-md hover:text-white transition">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/></svg>
          </button>
          <a href="/campaigns" className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-4 py-2.5 rounded-md text-sm font-medium transition flex items-center gap-2">
            <span>+</span> New campaign
          </a>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div 
        initial="hidden"
        animate="visible"
        variants={{
          hidden: { opacity: 0 },
          visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
        }}
        className="grid grid-cols-4 gap-6 mb-8"
      >
        
        <div variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }} className="bg-[#121214] border border-zinc-800/60 p-5 rounded-xl shadow-sm hover:border-zinc-700/80 transition-colors">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Qualified leads</h3>
          <p className="text-4xl font-bold text-white mb-4">{stats.qualified_opportunities || 164}</p>
          <span className="bg-green-500/10 text-green-500 text-xs px-2 py-1 rounded-full font-medium">
            +28 today
          </span>
        </div>

        <div variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }} className="bg-[#121214] border border-zinc-800/60 p-5 rounded-xl shadow-sm hover:border-zinc-700/80 transition-colors">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">A / A+ prospects</h3>
          <p className="text-4xl font-bold text-white mb-4">114</p>
          <span className="bg-green-500/10 text-green-500 text-xs px-2 py-1 rounded-full font-medium">
            69% of qualified
          </span>
        </div>

        <div variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }} className="bg-[#121214] border border-zinc-800/60 p-5 rounded-xl shadow-sm hover:border-zinc-700/80 transition-colors">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Campaigns running</h3>
          <p className="text-4xl font-bold text-white mb-4">{stats.campaigns || 7}</p>
          <span className="bg-green-500/10 text-green-500 text-xs px-2 py-1 rounded-full font-medium">
            +2 this week
          </span>
        </div>

        <div variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }} className="bg-[#121214] border border-zinc-800/60 p-5 rounded-xl shadow-sm hover:border-zinc-700/80 transition-colors">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Avg. lead score</h3>
          <p className="text-4xl font-bold text-white mb-4">{stats.average_score || 86.4}</p>
          <span className="bg-green-500/10 text-green-500 text-xs px-2 py-1 rounded-full font-medium">
            +4.2%
          </span>
        </div>

      </div>

      {/* Main Content Area: Chart and Active Campaigns */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        
        {/* Fake Bar Chart */}
        <div className="col-span-2 bg-[#121214] border border-zinc-800/60 rounded-xl p-6 relative">
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
             {/* Y-axis labels */}
             <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-[10px] text-zinc-600 pb-6">
                <span>200</span>
                <span>160</span>
                <span>120</span>
             </div>
             
             {/* Bars */}
             <div className="w-12 h-24 bg-zinc-700/50 rounded-t-md ml-8"></div>
             <div className="w-12 h-32 bg-zinc-700/50 rounded-t-md"></div>
             <div className="w-12 h-28 bg-zinc-700/50 rounded-t-md"></div>
             <div className="w-12 h-40 bg-zinc-700/50 rounded-t-md"></div>
             <div className="w-12 h-36 bg-zinc-700/50 rounded-t-md"></div>
             <div className="w-12 h-48 bg-zinc-700/50 rounded-t-md"></div>
             <div className="w-12 h-60 bg-[#8b5cf6] rounded-t-md shadow-[0_0_15px_rgba(139,92,246,0.3)]"></div>
          </div>
          <div className="flex justify-between px-2 pt-3 ml-8 text-[10px] text-zinc-500 font-medium">
            <span className="w-12 text-center">M</span>
            <span className="w-12 text-center">T</span>
            <span className="w-12 text-center">W</span>
            <span className="w-12 text-center">T</span>
            <span className="w-12 text-center">F</span>
            <span className="w-12 text-center">S</span>
            <span className="w-12 text-center text-white">S</span>
          </div>
        </div>

        {/* Active Campaigns */}
        <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white">Active campaigns</h2>
          <p className="text-sm text-zinc-500 mt-1 mb-6">Currently processing</p>

          <div className="space-y-6">
            
            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-white">USA • Roofing</span>
                <span className="text-zinc-400">82 / 100</span>
              </div>
              <p className="text-xs text-zinc-500 mb-2">Texas</p>
              <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 w-[82%]"></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-white">UK • Restaurants</span>
                <span className="text-zinc-400">61 / 100</span>
              </div>
              <p className="text-xs text-zinc-500 mb-2">Manchester</p>
              <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 w-[61%]"></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-white">AUS • Cleaning</span>
                <span className="text-zinc-400">37 / 100</span>
              </div>
              <p className="text-xs text-zinc-500 mb-2">Melbourne</p>
              <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 w-[37%]"></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="font-medium text-white">USA • HVAC</span>
                <span className="text-zinc-400">24 / 100</span>
              </div>
              <p className="text-xs text-zinc-500 mb-2">Dallas</p>
              <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 w-[24%]"></div>
              </div>
            </div>

          </div>
        </div>

      </div>

      {/* Priority Opportunities Table */}
      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6 mb-10">
        <h2 className="text-lg font-bold text-white">Priority opportunities</h2>
        <p className="text-sm text-zinc-500 mt-1 mb-6">Highest-value leads requiring SDR action</p>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <tbody className="divide-y divide-zinc-800/60">
              
              <tr className="hover:bg-zinc-800/20 transition group cursor-pointer">
                <td className="py-4 text-white font-medium">ABC Roofing LLC</td>
                <td className="py-4 text-zinc-400">Dallas, TX</td>
                <td className="py-4">
                  <span className="bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs px-3 py-1 rounded-full">Roofing</span>
                </td>
                <td className="py-4">
                  <span className="text-green-500 bg-green-500/10 px-2 py-1 rounded text-xs font-bold">94</span>
                </td>
                <td className="py-4 text-zinc-300">Booking + Quote</td>
                <td className="py-4 text-right text-zinc-500 group-hover:text-white transition">
                  →
                </td>
              </tr>

              <tr className="hover:bg-zinc-800/20 transition group cursor-pointer">
                <td className="py-4 text-white font-medium">Northline HVAC</td>
                <td className="py-4 text-zinc-400">Houston, TX</td>
                <td className="py-4">
                  <span className="bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs px-3 py-1 rounded-full">HVAC</span>
                </td>
                <td className="py-4">
                  <span className="text-green-500 bg-green-500/10 px-2 py-1 rounded text-xs font-bold">91</span>
                </td>
                <td className="py-4 text-zinc-300">Service Booking</td>
                <td className="py-4 text-right text-zinc-500 group-hover:text-white transition">
                  →
                </td>
              </tr>

              <tr className="hover:bg-zinc-800/20 transition group cursor-pointer">
                <td className="py-4 text-white font-medium">Velvet Table</td>
                <td className="py-4 text-zinc-400">Manchester, UK</td>
                <td className="py-4">
                  <span className="bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs px-3 py-1 rounded-full">Restaurant</span>
                </td>
                <td className="py-4">
                  <span className="text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded text-xs font-bold">89</span>
                </td>
                <td className="py-4 text-zinc-300">Reservations</td>
                <td className="py-4 text-right text-zinc-500 group-hover:text-white transition">
                  →
                </td>
              </tr>
              
              <tr className="hover:bg-zinc-800/20 transition group cursor-pointer border-b-0">
                <td className="py-4 text-white font-medium">BrightHome Clean</td>
                <td className="py-4 text-zinc-400">Melbourne, AUS</td>
                <td className="py-4">
                  <span className="bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs px-3 py-1 rounded-full">Cleaning</span>
                </td>
                <td className="py-4">
                  <span className="text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded text-xs font-bold">87</span>
                </td>
                <td className="py-4 text-zinc-300">Quote Funnel</td>
                <td className="py-4 text-right text-zinc-500 group-hover:text-white transition">
                  →
                </td>
              </tr>

            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
