"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FiSearch, FiArchive, FiPlus, FiTrash2, FiRotateCcw, FiAlertTriangle } from 'react-icons/fi';
import { ChevronRight } from 'lucide-react';
import ExportDropdown, { ExportFormat, ExportScope } from '@/components/ExportDropdown';
import { exportCampaigns } from '@/lib/exportUtils';

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [statusTab, setStatusTab] = useState("active");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const apiUrl = "";
      const res = await fetch(`${apiUrl}/api/campaigns?status=${statusTab}`);
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setSelectedIds([]);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, [statusTab]);

  const filteredCampaigns = campaigns.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  const toggleSelection = (id: number) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const toggleAll = () => {
    if (selectedIds.length === filteredCampaigns.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredCampaigns.map(c => c.id));
    }
  };

  const handleBulkAction = async (action: 'delete' | 'recover' | 'permanent') => {
    if (!selectedIds.length) return;
    const apiUrl = "";
    
    let endpoint = '/api/campaigns';
    let method = 'DELETE';
    
    if (action === 'recover') {
      endpoint = '/api/campaigns/recover';
      method = 'POST';
    } else if (action === 'permanent') {
      if (!confirm("Are you sure you want to permanently delete these campaigns? This cannot be undone.")) return;
      endpoint = '/api/campaigns/permanent';
      method = 'DELETE';
    }

    try {
      await fetch(`${apiUrl}${endpoint}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: selectedIds })
      });
      fetchCampaigns();
    } catch (e) {
      console.error(e);
    }
  };

  const handleExportCampaigns = async (format: ExportFormat, scope: ExportScope) => {
    const targetCampaigns = scope === "selected" && selectedIds.length > 0
      ? filteredCampaigns.filter(c => selectedIds.includes(c.id))
      : filteredCampaigns;
    if (!targetCampaigns.length) return;
    const prefix = scope === "selected" ? `devacia-campaigns-selected-${targetCampaigns.length}` : `devacia-campaigns-all-${targetCampaigns.length}`;
    exportCampaigns(targetCampaigns, format, prefix);
  };

  return (
    <div className="p-4 md:p-10 max-w-[1400px] pb-32 md:pb-32 w-full mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-6 md:mb-10 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white mb-1 md:mb-2 tracking-tight">Campaigns</h1>
          <p className="text-sm md:text-base text-zinc-400">Manage your active and past intelligence pipelines.</p>
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          <ExportDropdown
            totalCount={filteredCampaigns.length}
            selectedCount={selectedIds.length}
            onExport={handleExportCampaigns}
            entityName="Campaigns"
            variant="header"
          />
          <button 
            onClick={() => router.push('/campaigns/new')} 
            className="flex items-center gap-2 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-4 py-2 rounded-md text-sm font-medium transition whitespace-nowrap"
          >
            <FiPlus /> New campaign
          </button>
        </div>
      </div>

      <div className="flex gap-4 border-b border-zinc-800 mb-6">
        <button 
          onClick={() => setStatusTab('active')} 
          className={`pb-2 px-2 text-sm font-medium transition ${statusTab === 'active' ? 'text-purple-400 border-b-2 border-purple-500' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          Active
        </button>
        <button 
          onClick={() => setStatusTab('trash')} 
          className={`pb-2 px-2 text-sm font-medium transition flex items-center gap-2 ${statusTab === 'trash' ? 'text-purple-400 border-b-2 border-purple-500' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          Trash Bin
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
                <thead className="text-xs text-zinc-500 bg-zinc-900/30 uppercase tracking-wider border-b border-zinc-800">
                  <tr>
                    <th className="px-6 py-4 w-12">
                      <input 
                        type="checkbox" 
                        checked={filteredCampaigns.length > 0 && selectedIds.length === filteredCampaigns.length}
                        onChange={toggleAll}
                        className="accent-purple-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700" 
                      />
                    </th>
                    <th className="px-6 py-4 font-medium">Campaign Name</th>
                    <th className="px-6 py-4 font-medium">Target Geo</th>
                    <th className="px-6 py-4 font-medium">Industry</th>
                    <th className="px-6 py-4 font-medium text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                  {filteredCampaigns.map(c => (
                    <tr key={c.id} className={`hover:bg-zinc-800/20 transition group ${selectedIds.includes(c.id) ? 'bg-purple-500/5' : ''}`}>
                      <td className="px-6 py-4">
                        <input 
                          type="checkbox" 
                          checked={selectedIds.includes(c.id)}
                          onChange={() => toggleSelection(c.id)}
                          className="accent-purple-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700" 
                        />
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push(`/leads?campaignId=${c.id}`)}>
                          <div className="w-8 h-8 rounded-full bg-[#8b5cf6]/20 flex items-center justify-center">
                            <FiArchive className="text-[#a78bfa] w-4 h-4" />
                          </div>
                          <div>
                            <div className="font-medium text-white group-hover:text-[#a78bfa] transition">{c.name}</div>
                            <div className="text-xs text-zinc-500">{new Date(c.created_at).toLocaleDateString()}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-zinc-400">
                        {c.city}, {c.country}
                      </td>
                      <td className="px-6 py-4 text-zinc-400 capitalize">
                        {c.industry || 'Any'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium uppercase tracking-wider ${
                          c.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                          c.status === 'running' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                          'bg-zinc-800 text-zinc-400 border border-zinc-700'
                        }`}>
                          {statusTab === 'trash' ? 'Deleted' : c.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {filteredCampaigns.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center text-zinc-500">
                        No campaigns found in this view.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Mobile List Layout */}
            <div className="md:hidden divide-y divide-zinc-800/60">
              {filteredCampaigns.map(c => (
                <div key={c.id} className={`p-4 ${selectedIds.includes(c.id) ? 'bg-purple-500/5' : ''}`}>
                  <div className="flex items-center gap-3 mb-2">
                    <input 
                      type="checkbox" 
                      checked={selectedIds.includes(c.id)}
                      onChange={() => toggleSelection(c.id)}
                      className="accent-purple-500 w-5 h-5 rounded bg-zinc-800 border-zinc-700" 
                    />
                    <div className="flex-1 cursor-pointer" onClick={() => router.push(`/leads?campaignId=${c.id}`)}>
                      <div className="font-medium text-white line-clamp-1">{c.name}</div>
                      <div className="text-xs text-zinc-500">{new Date(c.created_at).toLocaleDateString()}</div>
                    </div>
                  </div>
                  <div className="pl-8 text-xs text-zinc-400">
                    <span className="block mb-1">{c.city}, {c.country}</span>
                    <span className="block">{c.industry || 'Any'}</span>
                  </div>
                </div>
              ))}
              {filteredCampaigns.length === 0 && (
                <div className="p-8 text-center text-zinc-500 text-sm">
                  No campaigns found.
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Floating Action Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom-5">
          <div className="bg-[#18181b] border border-zinc-700 shadow-2xl rounded-full px-5 py-2.5 flex items-center gap-4 text-sm">
            <span className="text-white font-medium text-xs">
              <span className="text-purple-400 font-bold">{selectedIds.length}</span> selected
            </span>
            <div className="w-px h-5 bg-zinc-700"></div>
            <ExportDropdown
              totalCount={filteredCampaigns.length}
              selectedCount={selectedIds.length}
              onExport={handleExportCampaigns}
              entityName="Campaigns"
              variant="floating"
            />
            <div className="w-px h-5 bg-zinc-700"></div>
            {statusTab === 'active' ? (
              <button 
                onClick={() => handleBulkAction('delete')}
                className="flex items-center gap-1.5 text-red-400 hover:text-red-300 font-medium transition text-xs"
              >
                <FiTrash2 /> Move to Trash
              </button>
            ) : (
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => handleBulkAction('recover')}
                  className="flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 font-medium transition text-xs"
                >
                  <FiRotateCcw /> Recover
                </button>
                <button 
                  onClick={() => handleBulkAction('permanent')}
                  className="flex items-center gap-1.5 text-red-500 hover:text-red-400 font-medium transition text-xs"
                >
                  <FiAlertTriangle /> Delete Permanently
                </button>
              </div>
            )}
            <button 
              onClick={() => setSelectedIds([])}
              className="text-zinc-500 hover:text-zinc-300 transition text-xs"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
