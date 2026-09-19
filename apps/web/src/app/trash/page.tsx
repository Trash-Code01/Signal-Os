"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from '@/components/SessionProvider';
import { useRouter } from "next/navigation";
import { Search, SlidersHorizontal, Loader2, X, ChevronDown, RotateCcw , PanelLeftClose, PanelLeftOpen } from "lucide-react";

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

const SELECT_CLS = "w-full bg-[#0d0d0f] border border-zinc-800 text-zinc-200 text-sm rounded-lg px-3 py-2.5 outline-none appearance-none focus:border-purple-500 transition-colors cursor-pointer";
const LABEL_CLS = "block text-[10px] font-bold text-zinc-500 mb-1.5 uppercase tracking-widest";

function FilterPanel({ filters, updateFilters, campaigns, industries, countries, onReset }: {
  filters: Filters; updateFilters: (p: Partial<Filters>) => void;
  campaigns: any[]; industries: string[]; countries: string[]; onReset: () => void;
}) {
  const activeCount = Object.entries(filters).filter(([k, v]) => k !== "q" && v && v !== "all").length;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Filters</span>
        {activeCount > 0 && (
          <button onClick={onReset} className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 transition-colors">
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
        )}
      </div>
      {[
        { label: "Stage", key: "stage", options: [["all","All stages"],["needs_review","Needs Review"],["new","New"],["reviewing","Reviewing"],["contacted","Contacted"],["qualified","Qualified"],["proposal","Proposal"],["won","Won"],["lost","Lost"]] as [string,string][] },
        { label: "Grade", key: "grade", options: [["all","All grades"],["A+","A+ prospects"],["A","A prospects"],["B","B prospects"]] as [string,string][] },
        { label: "Min Score", key: "minScore", options: [["","Any score"],["90","90+ score"],["80","80+ score"],["70","70+ score"]] as [string,string][] },
      ].map(({ label, key, options }) => (
        <div key={key}>
          <label className={LABEL_CLS}>{label}</label>
          <div className="relative">
            <select value={(filters as any)[key]} onChange={(e) => updateFilters({ [key]: e.target.value })} className={SELECT_CLS}>
              {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
          </div>
        </div>
      ))}
      <div>
        <label className={LABEL_CLS}>Campaign</label>
        <div className="relative">
          <select value={filters.campaignId} onChange={(e) => updateFilters({ campaignId: e.target.value })} className={SELECT_CLS}>
            <option value="">All campaigns</option>
            {campaigns.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
        </div>
      </div>
      <div>
        <label className={LABEL_CLS}>Industry</label>
        <div className="relative">
          <select value={filters.industry} onChange={(e) => updateFilters({ industry: e.target.value })} className={SELECT_CLS}>
            <option value="all">All industries</option>
            {industries.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
        </div>
      </div>
      <div>
        <label className={LABEL_CLS}>Country</label>
        <div className="relative">
          <select value={filters.country} onChange={(e) => updateFilters({ country: e.target.value })} className={SELECT_CLS}>
            <option value="all">All countries</option>
            {countries.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
        </div>
      </div>
      <div>
        <label className={LABEL_CLS}>Contact Status</label>
        <div className="relative">
          <select value={filters.contact} onChange={(e) => updateFilters({ contact: e.target.value })} className={SELECT_CLS}>
            <option value="">Any contact</option>
            <option value="true">Has decision maker</option>
            <option value="false">No contact found</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
        </div>
      </div>
    </div>
  );
}

export default function TrashBin() {
  const router = useRouter();
  const { user } = useSession();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [leads, setLeads] = useState<any[]>([]);
  const [total, setTotal] = useState(0);

  const handleBulkAction = async (action: 'delete' | 'recover' | 'permanent') => {
    if (!selectedIds.length) return;
    const apiUrl = "";
    let endpoint = '/api/crm/leads';
    let method = 'DELETE';
    if (action === 'recover') {
      endpoint = '/api/crm/leads/recover';
      method = 'POST';
    } else if (action === 'permanent') {
      if (!confirm("Delete permanently? This cannot be undone.")) return;
      endpoint = '/api/crm/leads/permanent';
      method = 'DELETE';
    }
    try {
      await fetch(`${apiUrl}${endpoint}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: selectedIds })
      });
      loadLeads();
    } catch (e) { console.error(e); }
  };

  const [loading, setLoading] = useState(true);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  const [countries, setCountries] = useState<string[]>([]);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [showFilters, setShowFilters] = useState(false);
  const statusTab = "trash";
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    setSelectedIds([]);
    try {
      const apiUrl = "";
      const params = new URLSearchParams();
      if (filters.q.trim()) params.set("q", filters.q.trim());
      if (filters.stage !== "all") params.set("stage", filters.stage);
      if (filters.grade !== "all") params.set("grade", filters.grade);
      if (filters.campaignId) params.set("campaign_id", filters.campaignId);
      if (filters.industry && filters.industry !== "all") params.set("industry", filters.industry);
      if (filters.country && filters.country !== "all") params.set("country", filters.country);
      if (filters.contact) params.set("has_contact", filters.contact);
      if (filters.minScore) params.set("min_score", filters.minScore);
      params.set("qualified_only", "false");
      params.set("page_size", "100");
      params.set("status", statusTab);
      const res = await fetch(`${apiUrl}/api/crm/leads?${params.toString()}`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data.facets?.campaigns || []);
        setIndustries(data.facets?.industries || []);
        setCountries(data.facets?.countries || []);
        setLeads(data.leads || []);
        setTotal(data.total || 0);
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filters, statusTab]);

  useEffect(() => { const t = setTimeout(() => loadLeads(), 300); return () => clearTimeout(t); }, [filters, loadLeads]);

  const updateFilters = (patch: Partial<Filters>) => setFilters((p) => ({ ...p, ...patch }));
  const resetFilters = () => setFilters({ ...EMPTY_FILTERS, q: filters.q });
  const activeFilterCount = Object.entries(filters).filter(([k, v]) => k !== "q" && v && v !== "all").length;

  const stageColor: Record<string, string> = {
    qualified: "bg-emerald-900/40 text-emerald-400 border border-emerald-800/40",
    new: "bg-zinc-800/60 text-zinc-300",
    contacted: "bg-blue-900/40 text-blue-400 border border-blue-800/40",
    reviewing: "bg-yellow-900/40 text-yellow-400 border border-yellow-800/40",
    proposal: "bg-purple-900/40 text-purple-400 border border-purple-800/40",
    won: "bg-green-900/40 text-green-400 border border-green-800/40",
    lost: "bg-red-900/40 text-red-400 border border-red-800/40",
  };

  const scoreClass = (score: number) =>
    score >= 90 ? "bg-emerald-900/40 text-emerald-300" : score >= 75 ? "bg-blue-900/40 text-blue-300" : "bg-orange-900/40 text-orange-300";

  return (
    <div className="min-h-screen bg-[#09090b] text-white font-sans">

      {/* =============== DESKTOP (md+) =============== */}
      <div className="hidden md:flex h-screen overflow-hidden">

        {/* Left filter sidebar */}
        <aside className={`shrink-0 bg-[#0a0a0c] border-zinc-800/60 flex flex-col overflow-y-auto gap-0 transition-all duration-300 ease-in-out ${isSidebarOpen ? "w-56 px-4 py-5 border-r opacity-100" : "w-0 px-0 py-5 border-r-0 opacity-0 overflow-hidden"}`}>
          <div className="mb-6">
            <h1 className="text-base font-bold text-white">Trash Bin</h1>
            <p className="text-xs text-zinc-500 mt-0.5">{total} leads</p>
          </div>

          <FilterPanel filters={filters} updateFilters={updateFilters} campaigns={campaigns} industries={industries} countries={countries} onReset={resetFilters} />
        </aside>

        {/* Right: search + table */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top search bar */}
          <div className="flex items-center gap-3 px-5 py-3.5 border-b border-zinc-800/60 bg-[#09090b] shrink-0">
            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 -ml-2 text-zinc-400 hover:text-white transition rounded-md hover:bg-zinc-800/50" title="Toggle Filters">
              {isSidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
            </button>
            <div className="relative flex-1 max-w-lg">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
              <input type="text" placeholder="Search companies..." value={filters.q} onChange={(e) => updateFilters({ q: e.target.value })}
                className="w-full bg-[#111113] border border-zinc-800 text-sm text-white rounded-lg pl-9 pr-4 py-2.5 outline-none placeholder:text-zinc-600 focus:border-purple-500 transition-colors" />
            </div>
            {activeFilterCount > 0 && (
              <span className="text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2.5 py-1 rounded-full font-medium">
                {activeFilterCount} active filter{activeFilterCount > 1 ? "s" : ""}
              </span>
            )}
            <span className="ml-auto text-xs text-zinc-500 whitespace-nowrap">{total} results</span>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-64"><Loader2 className="w-7 h-7 animate-spin text-purple-500" /></div>
            ) : leads.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
                <p className="font-medium text-white mb-1">No leads match your filters</p>
                <button onClick={resetFilters} className="mt-3 text-purple-400 text-sm hover:text-purple-300">Clear filters</button>
              </div>
            ) : (
              <table className="w-full text-sm border-collapse">
                <thead className="sticky top-0 z-10 bg-[#0a0a0c] border-b border-zinc-800/60">
                  <tr className="text-zinc-500 text-[11px] uppercase tracking-widest">
                    <th className="px-5 py-3 w-12 text-left">
  <input 
    type="checkbox" 
    className="accent-purple-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700 cursor-pointer" 
    checked={leads.length > 0 && selectedIds.length === leads.length}
    onChange={() => selectedIds.length === leads.length ? setSelectedIds([]) : setSelectedIds(leads.map(l => l.id))}
  />
</th>
<th className="text-left px-2 py-3 font-semibold">Company</th>
                    <th className="text-left px-4 py-3 font-semibold">Industry</th>
                    <th className="text-left px-4 py-3 font-semibold">Location</th>
                    <th className="text-left px-4 py-3 font-semibold">Score</th>
                    <th className="text-left px-4 py-3 font-semibold">Stage</th>
                    <th className="text-left px-4 py-3 font-semibold">Contact</th>
                    <th className="text-left px-4 py-3 font-semibold">Campaign</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/30">
                  {leads.map((lead) => {
                    const contact = lead.contacts?.[0];
                    return (
                      <tr key={lead.id} onClick={() => router.push(`/leads/${lead.id}`)}
                        className="hover:bg-white/[0.03] cursor-pointer transition-colors group">
                        <td className="px-5 py-3.5 w-12" onClick={(e) => { e.stopPropagation(); setSelectedIds(prev => prev.includes(lead.id) ? prev.filter(id => id !== lead.id) : [...prev, lead.id]) }}>
      <input 
        type="checkbox" 
        className="accent-purple-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700 cursor-pointer pointer-events-none" 
        checked={selectedIds.includes(lead.id)}
        readOnly
      />
  </td>
  <td className="px-2 py-3.5 cursor-pointer" onClick={() => router.push(`/leads/${lead.id}`)}>
                          <p className="font-semibold text-white group-hover:text-purple-300 transition-colors leading-tight">{lead.name}</p>
                          {lead.website_url && <p className="text-xs text-zinc-600 truncate max-w-[200px] mt-0.5">{lead.website_url.replace(/^https?:\/\//, "")}</p>}
                        </td>
                        <td className="px-4 py-3.5 text-zinc-400 text-xs capitalize">{lead.industry || ""}</td>
                        <td className="px-4 py-3.5 text-zinc-400 text-xs whitespace-nowrap">{lead.location || ""}</td>
                        <td className="px-4 py-3.5">
                          <span className={`${scoreClass(lead.commercial_score || 0)} px-2 py-0.5 rounded-md text-xs font-bold`}>
                            {lead.grade || "U"} · {lead.commercial_score || 0}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase ${stageColor[lead.stage?.toLowerCase()] || "bg-zinc-800 text-zinc-300"}`}>
                            {lead.stage || "new"}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          {contact ? (
                            <div>
                              <div className="flex items-center gap-1.5 mb-0.5">
                                <p className="text-white text-xs font-medium truncate max-w-[150px]">{contact.name}</p>
                                {contact.source && (
                                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 bg-zinc-800/50 px-1.5 py-0.5 rounded">
                                    {contact.source}
                                  </span>
                                )}
                              </div>
                              {contact.email && <p className="text-emerald-400 text-xs truncate max-w-[150px]">{contact.email}</p>}
                            </div>
                          ) : <span className="text-zinc-600 text-xs italic">No contact</span>}
                        </td>
                        <td className="px-4 py-3.5 text-zinc-400 text-xs whitespace-nowrap max-w-[140px] truncate">{lead.campaign_name || ""}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* =============== MOBILE (below md) =============== */}
      <div className="md:hidden pb-24">
        <main className="p-4">
          <div className="mt-4 mb-5">
            <div className="flex items-end gap-3 mb-1">
              <h1 className="text-2xl font-bold text-white tracking-tight">Trash Bin</h1>
              <span className="bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full text-xs font-bold mb-0.5">{total} leads</span>
            </div>
            <p className="text-sm text-zinc-500">Enriched business prospects.</p>
          </div>

          <div className="flex gap-3 mb-5">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
              <input type="text" placeholder="Search companies..." value={filters.q} onChange={(e) => updateFilters({ q: e.target.value })}
                className="w-full bg-[#121214] border-none text-sm text-white rounded-xl pl-11 pr-4 py-3 outline-none placeholder:text-zinc-500 focus:ring-1 focus:ring-purple-500 transition-all" />
            </div>
            <button onClick={() => setShowFilters(true)}
              className={`relative p-3 rounded-xl transition-colors ${activeFilterCount > 0 ? "bg-purple-500 text-white" : "bg-[#121214] text-zinc-400 hover:text-white"}`}>
              <SlidersHorizontal className="w-5 h-5" />
              {activeFilterCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 bg-white text-purple-600 w-4 h-4 rounded-full text-[10px] font-bold flex items-center justify-center">{activeFilterCount}</span>
              )}
            </button>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
              <Loader2 className="w-8 h-8 animate-spin mb-4 text-purple-500" /><p>Loading leads...</p>
            </div>
          ) : leads.length === 0 ? (
            <div className="text-center py-20 bg-[#121214] rounded-2xl border border-dashed border-zinc-800">
              <p className="font-medium text-white mb-1">No leads match filters</p>
              <button onClick={resetFilters} className="mt-3 text-purple-400 text-sm font-medium">Clear filters</button>
            </div>
          ) : (
            <div className="space-y-3">
              {leads.map((lead) => {
                const contact = lead.contacts?.[0];
                return (
                  <div key={lead.id} onClick={() => router.push(`/leads/${lead.id}`)}
                    className="bg-[#121214] rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-all border border-transparent hover:border-zinc-800">
                    <h2 className="text-base font-bold text-white leading-tight mb-0.5">{lead.name}</h2>
                    <p className="text-xs text-zinc-500 mb-3">{lead.industry || "Uncategorized"} · {lead.location || "US"}</p>
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`${scoreClass(lead.commercial_score || 0)} px-2 py-0.5 rounded-md text-xs font-bold`}>
                        {lead.grade || "U"} · {lead.commercial_score || 0}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase ${stageColor[lead.stage?.toLowerCase()] || "bg-zinc-800 text-zinc-300"}`}>
                        {lead.stage || "new"}
                      </span>
                    </div>
                    <div className="bg-[#09090b] rounded-xl p-3">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <p className="text-sm font-medium text-white truncate">{contact?.name || "No primary contact"}</p>
                        {contact?.source && (
                          <span className="text-[9px] uppercase tracking-wider text-zinc-500 bg-zinc-800/50 px-1.5 py-0.5 rounded">
                            {contact.source}
                          </span>
                        )}
                      </div>
                      {contact?.email ? <p className="text-xs text-emerald-400 truncate">{contact.email}</p> : <p className="text-xs text-zinc-600">Contact details pending</p>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>

      {/* Mobile Filter Modal */}
      {showFilters && (
        <div className="md:hidden fixed inset-0 z-50 bg-[#09090b] flex flex-col animate-in slide-in-from-bottom-full duration-200">
          <header className="flex items-center justify-between p-4 border-b border-zinc-800 shrink-0">
            <h2 className="text-lg font-bold text-white">Filters</h2>
            <button onClick={() => setShowFilters(false)} className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center">
              <X className="w-4 h-4 text-zinc-300" />
            </button>
          </header>
          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            <div>
              <label className={LABEL_CLS}>Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
                <input type="text" placeholder="Search companies..." value={filters.q} onChange={(e) => updateFilters({ q: e.target.value })}
                  className="w-full bg-[#121214] border border-zinc-800 text-zinc-200 text-sm rounded-xl pl-10 pr-4 py-3 outline-none focus:border-purple-500" />
              </div>
            </div>
            <FilterPanel filters={filters} updateFilters={updateFilters} campaigns={campaigns} industries={industries} countries={countries} onReset={resetFilters} />
          </div>
          <div className="p-4 border-t border-zinc-800 shrink-0">
            <div className="flex gap-3">
              <button onClick={resetFilters} className="flex-1 py-3 rounded-xl font-semibold text-zinc-300 bg-zinc-800/50 hover:bg-zinc-800 transition-all">Reset</button>
              <button onClick={() => setShowFilters(false)} className="flex-[2] py-3 rounded-xl font-bold text-white bg-purple-600 hover:bg-purple-500 transition-all shadow-lg shadow-purple-900/30">Show Results</button>
            </div>
          </div>
        </div>
      )}
    
      {/* Floating Action Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom-5">
          <div className="bg-[#18181b] border border-zinc-700 shadow-2xl rounded-full px-6 py-3 flex items-center gap-6 text-sm">
            <span className="text-white font-medium">
              <span className="text-purple-400">{selectedIds.length}</span> selected
            </span>
            <div className="w-px h-6 bg-zinc-700"></div>
            <div className="flex items-center gap-4">
              <button 
                disabled={user?.role === 'viewer'} onClick={() => handleBulkAction('recover')}
                className="flex items-center gap-2 text-emerald-400 hover:text-emerald-300 font-medium transition"
              >
                Recover
              </button>
              <button 
                disabled={user?.role !== 'admin'} onClick={() => handleBulkAction('permanent')}
                className="flex items-center gap-2 text-red-500 hover:text-red-400 font-medium transition"
              >
                Delete Permanently
              </button>
            </div>
            <button onClick={() => setSelectedIds([])} className="ml-4 text-zinc-500 hover:text-zinc-300 transition">Cancel</button>
          </div>
        </div>
      )}
</div>
  );
}
