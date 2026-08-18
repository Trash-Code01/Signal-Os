"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function CampaignBuilder() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [industry, setIndustry] = useState("Roofing");
  const [country, setCountry] = useState("United States");
  const [targetQuantity, setTargetQuantity] = useState(5);
  const [minScore, setMinScore] = useState(80);

  const handleStartCampaign = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/campaigns`, { 
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          industry: industry,
          country: country,
          target_quantity: targetQuantity,
          min_quality_score: minScore
        })
      });
      if (res.ok) {
        setTimeout(() => {
          router.push('/dashboard');
        }, 1000);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="p-10 max-w-[1400px]">
      
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider mb-2">Campaigns / New campaign</p>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Build a qualified lead campaign</h1>
          <p className="text-zinc-400">Define the market. Devacia handles the research.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-green-500/10 text-green-500 px-3 py-1.5 rounded-full text-xs font-bold tracking-wide uppercase border border-green-500/20">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Live System
          </div>
          <button className="bg-zinc-900 border border-zinc-800 text-zinc-400 p-2 rounded-md hover:text-white transition">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/></svg>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-10">
        
        {/* Left Column: Form */}
        <div className="col-span-2 space-y-10">
          
          {/* Section 1 */}
          <div>
            <h2 className="text-lg font-bold text-white mb-6">1. Market</h2>
            
            <div className="grid grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Country</label>
                <select 
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="w-full bg-[#121214] border border-zinc-800 text-white rounded-md p-3 outline-none focus:border-zinc-600 appearance-none">
                  <option value="United States">United States</option>
                  <option value="United Kingdom">United Kingdom</option>
                  <option value="Australia">Australia</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Industry</label>
                <input 
                  type="text" 
                  placeholder="e.g. Roofing, HVAC, Real Estate..."
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full bg-[#121214] border border-zinc-800 text-white rounded-md p-3 outline-none focus:border-zinc-600"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">State / Region</label>
                <select className="w-full bg-[#121214] border border-zinc-800 text-white rounded-md p-3 outline-none focus:border-zinc-600 appearance-none">
                  <option>Texas</option>
                  <option>California</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Cities</label>
                <input 
                  type="text" 
                  defaultValue="Dallas, Houston, Austin"
                  className="w-full bg-[#121214] border border-zinc-800 text-white rounded-md p-3 outline-none focus:border-zinc-600"
                />
              </div>
            </div>
          </div>

          <hr className="border-zinc-800/60" />

          {/* Section 2 */}
          <div>
            <h2 className="text-lg font-bold text-white mb-6">2. Qualification</h2>
            
            <div className="grid grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Target Qualified Leads</label>
                <input 
                  type="number" 
                  value={targetQuantity}
                  onChange={(e) => setTargetQuantity(parseInt(e.target.value))}
                  className="w-full bg-[#121214] border border-zinc-800 text-white rounded-md p-3 outline-none focus:border-zinc-600"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Minimum Score</label>
                <input 
                  type="number" 
                  value={minScore}
                  onChange={(e) => setMinScore(parseInt(e.target.value))}
                  className="w-full bg-[#121214] border border-zinc-800 text-white rounded-md p-3 outline-none focus:border-zinc-600"
                />
              </div>
            </div>
            
            <div className="mb-6">
              <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Lead Objective</label>
              <div className="w-full bg-[#121214] border border-zinc-800 rounded-md p-4 cursor-pointer hover:border-zinc-600 transition">
                <p className="text-white font-medium mb-1">Businesses with high-value digital gaps</p>
                <p className="text-xs text-zinc-500">Website, booking, conversion or automation opportunity</p>
              </div>
            </div>

            <div className="mb-10">
              <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3">Required Contact</label>
              <div className="flex gap-3">
                <button className="bg-zinc-800 text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-zinc-700 transition">Decision maker</button>
                <button className="bg-[#121214] border border-zinc-800 text-zinc-400 px-4 py-2 rounded-full text-sm font-medium hover:text-white transition">Email</button>
                <button className="bg-[#121214] border border-zinc-800 text-zinc-400 px-4 py-2 rounded-full text-sm font-medium hover:text-white transition">Phone</button>
              </div>
            </div>

            <button 
              onClick={handleStartCampaign}
              disabled={loading}
              className="w-full bg-[#8b5cf6] hover:bg-[#7c3aed] text-white font-bold py-4 rounded-lg text-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Starting..." : "Start campaign"}
            </button>
          </div>

        </div>

        {/* Right Column: Preview */}
        <div>
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-8 sticky top-10">
            <h2 className="text-lg font-bold text-white mb-6">Campaign preview</h2>
            
            <div className="mb-8">
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">System Will Search</p>
              <p className="text-2xl font-bold text-white">~1,000+ businesses</p>
              <p className="text-xs text-zinc-500 mt-1">until 100 qualified leads remain</p>
            </div>

            <div className="border-t border-zinc-800/60 pt-6 pb-6 relative">
              {/* Timeline line */}
              <div className="absolute left-[11px] top-6 bottom-6 w-[2px] bg-zinc-800/60 z-0"></div>
              
              <div className="space-y-6 relative z-10">
                <div className="flex gap-4">
                  <div className="w-6 h-6 rounded-full bg-[#8b5cf6] text-white flex items-center justify-center text-xs font-bold shrink-0 ring-4 ring-[#121214]">1</div>
                  <div>
                    <p className="text-sm font-bold text-white">Discovery</p>
                    <p className="text-xs text-zinc-500">Google Business + web</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-6 h-6 rounded-full bg-[#8b5cf6] text-white flex items-center justify-center text-xs font-bold shrink-0 ring-4 ring-[#121214]">2</div>
                  <div>
                    <p className="text-sm font-bold text-white">Website audit</p>
                    <p className="text-xs text-zinc-500">Mobile + conversion</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-6 h-6 rounded-full bg-[#8b5cf6] text-white flex items-center justify-center text-xs font-bold shrink-0 ring-4 ring-[#121214]">3</div>
                  <div>
                    <p className="text-sm font-bold text-white">Qualification</p>
                    <p className="text-xs text-zinc-500">Roofing-specific rules</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-6 h-6 rounded-full bg-[#8b5cf6] text-white flex items-center justify-center text-xs font-bold shrink-0 ring-4 ring-[#121214]">4</div>
                  <div>
                    <p className="text-sm font-bold text-white">Enrichment</p>
                    <p className="text-xs text-zinc-500">Decision maker + email</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-6 h-6 rounded-full bg-[#8b5cf6] text-white flex items-center justify-center text-xs font-bold shrink-0 ring-4 ring-[#121214]">5</div>
                  <div>
                    <p className="text-sm font-bold text-white">AI analysis</p>
                    <p className="text-xs text-zinc-500">Offer + outreach angle</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-zinc-800/60 pt-6">
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Expected Output</p>
              <p className="text-lg font-bold text-green-500 mb-2">A / A+ SDR-ready leads</p>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Every lead includes evidence, score, offer recommendation and contact data.
              </p>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
