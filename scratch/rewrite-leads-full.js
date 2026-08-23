
const fs = require("fs");
const path = "c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\leads\\page.tsx";

const code = `"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, SlidersHorizontal, Loader2, X, ChevronDown } from "lucide-react";

type Filters = {
  q: string;
  stage: string;
  grade: string;
  campaignId: string;
  industry: string;
  country: string;
  contact: string;
  minScore: string;
};

const EMPTY_FILTERS: Filters = { q: "", stage: "all", grade: "all", campaignId: "", industry: "all", country: "all", contact: "", minScore: "" };

export default function LeadsPipeline() {
  const router = useRouter();
  const [leads, setLeads] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  
  // Dynamic facet data
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  const [countries, setCountries] = useState<string[]>([]);
  
  // Filter state
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [showFilters, setShowFilters] = useState(false);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace("localhost", "api") || "http://localhost:8000";
      const params = new URLSearchParams();
      if (filters.q.trim()) params.set("q", filters.q.trim());
      if (filters.stage !== "all") params.set("stage", filters.stage);
      if (filters.grade !== "all") params.set("grade", filters.grade);
      if (filters.campaignId) params.set("campaign_id", filters.campaignId);
      if (filters.industry && filters.industry !== "all") params.set("industry", filters.industry);
      if (filters.country && filters.country !== "all") params.set("country", filters.country);
      if (filters.contact) params.set("has_contact", filters.contact);
      if (filters.minScore) params.set("min_score", filters.minScore);
      params.set("page_size", "20");
      
      const res = await fetch(\`\${apiUrl}/api/crm/leads?\${params.toString()}\`);
      if (res.ok) {
        const data = await res.json();
        
        // Extract facets for dropdowns
        setCampaigns(data.facets?.campaigns || []);
        setIndustries(data.facets?.industries || []);
        setCountries(data.facets?.countries || []);
        
        if (data.leads?.length === 0 && !filters.q && filters.stage === "all") {
          // Mock data ONLY if completely empty DB on initial load
          setLeads([
            { id: 1, name: "Suds & Co.", industry: "Cleaning", location: "Dallas, US", commercial_score: 100, grade: "A+", stage: "qualified", contacts: [{ name: "John Smith", email: "john@sudsandco.com" }] },
            { id: 2, name: "Peak Roofing", industry: "Roofing", location: "Austin, US", commercial_score: 85, grade: "A", stage: "contacted", contacts: [{ name: "Sarah Connor" }] },
            { id: 3, name: "Bright Smiles", industry: "Clinic", location: "Houston, US", commercial_score: 92, grade: "A+", stage: "new", contacts: [] }
          ]);
          setTotal(3);
        } else {
          setLeads(data.leads || []);
          setTotal(data.total || 0);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    const timer = setTimeout(() => loadLeads(), 300);
    return () => clearTimeout(timer);
  }, [filters, loadLeads]);

  const updateFilters = (patch: Partial<Filters>) => {
    setFilters(prev => ({ ...prev, ...patch }));
  };

  const activeFilterCount = Object.entries(filters).filter(([k, v]) => k !== "q" && v && v !== "all").length;

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col font-sans pb-32">
      <main className="flex-1 p-4 md:p-8 max-w-4xl w-full mx-auto flex flex-col">
        
        {/* Header */}
        <div className="mt-4 mb-6">
          <div className="flex items-end gap-3 mb-2">
            <h1 className="text-3xl font-bold text-white tracking-tight">Leads CRM</h1>
            <span className="bg-[#a855f7]/20 text-[#a855f7] px-2 py-0.5 rounded-full text-xs font-bold mb-1">
              {total} leads
            </span>
          </div>
          <p className="text-sm text-zinc-400">View and manage enriched business prospects.</p>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
            <input 
              type="text" 
              placeholder="Search companies..." 
              value={filters.q}
              onChange={(e) => updateFilters({ q: e.target.value })}
              className="w-full bg-[#121214] border-none text-sm text-white rounded-xl pl-11 pr-4 py-3 outline-none placeholder:text-zinc-500 focus:ring-1 focus:ring-purple-500 transition-all shadow-sm"
            />
          </div>
          <button 
            onClick={() => setShowFilters(true)}
            className={\`relative p-3 rounded-xl transition-colors \${activeFilterCount > 0 ? "bg-purple-500 text-white shadow-md shadow-purple-500/20" : "bg-[#121214] text-zinc-400 hover:text-white"}\`}
          >
            <SlidersHorizontal className="w-5 h-5" />
            {activeFilterCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-white text-purple-600 w-4 h-4 rounded-full text-[10px] font-bold flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Lead Cards List */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-[#a855f7]" />
            <p>Loading leads...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {leads.length > 0 ? leads.map((lead) => {
              const contact = lead.contacts?.[0];
              const scoreClass = (lead.commercial_score || 0) >= 90 ? "bg-[#064e3b] text-[#34d399]" : (lead.commercial_score || 0) >= 75 ? "bg-[#1e3a8a] text-[#60a5fa]" : "bg-[#431407] text-[#fb923c]";
              
              return (
                <div 
                  key={lead.id} 
                  onClick={() => router.push(\`/leads/\${lead.id}\`)}
                  className="bg-[#121214] rounded-2xl p-5 cursor-pointer hover:bg-[#18181b] transition-all border border-transparent hover:border-white/5 active:scale-[0.98]"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h2 className="text-lg font-bold text-white">{lead.name}</h2>
                      <p className="text-sm text-zinc-400 mt-0.5 flex items-center gap-1.5">
                        {lead.industry || "Uncategorized"}
                        <span className="text-[10px] opacity-50">&#9679;</span>
                        {lead.location || "US"}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 mb-4">
                    <span className={\`\${scoreClass} px-2.5 py-0.5 rounded-full text-xs font-bold shadow-sm flex items-center gap-1\`}>
                      {lead.grade || "U"}
                      <span className="text-[8px] opacity-50">&#9679;</span>
                      {lead.commercial_score || 0}
                    </span>
                    <span className="bg-[#27272a] text-zinc-300 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase">
                      {lead.stage || "New"}
                    </span>
                  </div>

                  <div className="bg-[#09090b] rounded-xl p-3 flex items-center justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">
                        {contact?.name || "No primary contact"}
                      </p>
                      {contact?.email ? (
                        <p className="text-xs text-[#34d399] truncate">{contact.email}</p>
                      ) : (
                        <p className="text-xs text-zinc-500">Contact details pending</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            }) : (
              <div className="text-center text-zinc-500 py-20 bg-[#121214] rounded-2xl border border-dashed border-zinc-800">
                <p className="font-medium text-white mb-1">No leads match filters</p>
                <p className="text-sm">Try adjusting your filters or search query.</p>
                <button onClick={() => setFilters(EMPTY_FILTERS)} className="mt-4 text-purple-400 text-sm font-medium">Clear all filters</button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Full Screen Filter Modal */}
      {showFilters && (
        <div className="fixed inset-0 z-50 bg-[#09090b] flex flex-col animate-in slide-in-from-bottom-full duration-200">
          <header className="flex items-center justify-between p-4 border-b border-zinc-800">
            <h2 className="text-lg font-bold text-white">Filters</h2>
            <button onClick={() => setShowFilters(false)} className="p-2 -mr-2 text-zinc-400 hover:text-white rounded-full bg-zinc-800/50">
              <X className="w-5 h-5" />
            </button>
          </header>
          
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Stage</label>
                <div className="relative">
                  <select value={filters.stage} onChange={(e) => updateFilters({ stage: e.target.value })} className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl px-4 py-3 outline-none appearance-none focus:border-purple-500">
                    <option value="all">All stages</option>
                    <option value="new">New</option>
                    <option value="reviewing">Reviewing</option>
                    <option value="contacted">Contacted</option>
                    <option value="qualified">Qualified</option>
                    <option value="won">Won</option>
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Grade</label>
                <div className="relative">
                  <select value={filters.grade} onChange={(e) => updateFilters({ grade: e.target.value })} className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl px-4 py-3 outline-none appearance-none focus:border-purple-500">
                    <option value="all">All grades</option>
                    <option value="A+">A+ prospects</option>
                    <option value="A">A prospects</option>
                    <option value="B">B prospects</option>
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Score</label>
              <div className="relative">
                <select value={filters.minScore} onChange={(e) => updateFilters({ minScore: e.target.value })} className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl px-4 py-3 outline-none appearance-none focus:border-purple-500">
                  <option value="">Any score</option>
                  <option value="90">90+ score</option>
                  <option value="80">80+ score</option>
                  <option value="70">70+ score</option>
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Campaign</label>
              <div className="relative">
                <select value={filters.campaignId} onChange={(e) => updateFilters({ campaignId: e.target.value })} className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl px-4 py-3 outline-none appearance-none focus:border-purple-500">
                  <option value="">All campaigns</option>
                  {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Industry</label>
              <div className="relative">
                <select value={filters.industry} onChange={(e) => updateFilters({ industry: e.target.value })} className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl px-4 py-3 outline-none appearance-none focus:border-purple-500">
                  <option value="all">All industries</option>
                  {industries.map(i => <option key={i} value={i}>{i}</option>)}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Country</label>
              <div className="relative">
                <select value={filters.country} onChange={(e) => updateFilters({ country: e.target.value })} className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl px-4 py-3 outline-none appearance-none focus:border-purple-500">
                  <option value="all">All countries</option>
                  {countries.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Contact Status</label>
              <div className="relative">
                <select value={filters.contact} onChange={(e) => updateFilters({ contact: e.target.value })} className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl px-4 py-3 outline-none appearance-none focus:border-purple-500">
                  <option value="">Any contact</option>
                  <option value="true">Has decision maker</option>
                  <option value="false">No contact found</option>
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
              </div>
            </div>
          </div>
          
          <div className="p-5 border-t border-zinc-800 bg-[#09090b]">
            <div className="flex gap-3">
              <button 
                onClick={() => setFilters({ ...EMPTY_FILTERS, q: filters.q })} 
                className="flex-1 py-3.5 px-4 rounded-xl font-semibold text-zinc-300 bg-zinc-800/50 hover:bg-zinc-800 active:scale-95 transition-all"
              >
                Reset
              </button>
              <button 
                onClick={() => setShowFilters(false)} 
                className="flex-[2] py-3.5 px-4 rounded-xl font-bold text-white bg-purple-600 hover:bg-purple-500 active:scale-95 transition-all shadow-lg shadow-purple-900/30"
              >
                Show Results
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
`;

fs.writeFileSync(path, code);
console.log("Leads CRM list rewritten successfully with FULL SCREEN mobile filters!");

