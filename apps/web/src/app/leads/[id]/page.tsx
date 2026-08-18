"use client";

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { FiArrowLeft, FiExternalLink, FiMail, FiTarget, FiAlertTriangle, FiBriefcase, FiZap } from 'react-icons/fi';

export default function LeadDossier() {
  const { id } = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  useEffect(() => {
    async function fetchLead() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/leads/${id}`);
        if (res.ok) {
          setLead(await res.json());
        }
      } catch (e) {
        console.error("Failed to fetch lead details", e);
      }
      setLoading(false);
    }
    fetchLead();
  }, [id]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/leads/${id}/export`, { method: 'POST' });
      if (res.ok) setExportSuccess(true);
    } catch (e) {
      console.error(e);
    }
    setExporting(false);
  };

  if (loading) {
    return (
      <div className="p-10 max-w-[1000px] mx-auto min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#8b5cf6] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="p-10 text-center">
        <h1 className="text-2xl font-bold">Lead Not Found</h1>
        <button onClick={() => router.push('/leads')} className="mt-4 text-[#8b5cf6] hover:underline">Back to CRM</button>
      </div>
    );
  }

  return (
    <div className="p-10 max-w-[1000px] mx-auto min-h-screen pb-32">
      
      {/* Top Navigation */}
      <button 
        onClick={() => router.push('/leads')}
        className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition mb-8"
      >
        <FiArrowLeft /> Back to pipeline
      </button>

      {/* Notion-Style Header */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-zinc-800 text-zinc-300 text-xs px-2 py-1 rounded">Qualified Lead</div>
          <div className="flex items-center gap-1 text-green-400 bg-green-400/10 px-2 py-1 rounded text-xs font-bold">
            <FiZap className="w-3 h-3" />
            Score: {lead.score}
          </div>
        </div>
        <h1 className="text-5xl font-black tracking-tight mb-4 text-white">
          {lead.name}
        </h1>
        <div className="flex items-center gap-6 text-zinc-400 text-sm">
          {lead.domain && (
            <a href={`https://${lead.domain}`} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 hover:text-[#8b5cf6] transition">
              <FiExternalLink /> {lead.domain}
            </a>
          )}
          {lead.location && <span>{lead.location}</span>}
          {lead.phone && <span>{lead.phone}</span>}
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex items-center gap-3 mb-12 border-b border-zinc-800 pb-8">
        <button 
          onClick={handleExport}
          disabled={exporting || exportSuccess}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
            exportSuccess 
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-[#8b5cf6] hover:bg-[#7c3aed] text-white shadow-lg shadow-purple-500/20'
          }`}
        >
          {exporting ? 'Exporting...' : exportSuccess ? 'Sent to n8n CRM \u2713' : 'Export to CRM / Webhook'}
        </button>
      </div>

      {/* Notion-Style Sections */}
      <div className="space-y-12">
        
        {/* Core Intelligence */}
        <section>
          <div className="flex items-center gap-2 text-lg font-bold text-white mb-4 border-b border-zinc-800 pb-2">
            <FiTarget className="text-[#8b5cf6]" />
            AI Outreach Angle
          </div>
          <div className="bg-[#121214] border border-zinc-800 rounded-xl p-6 text-zinc-300 leading-relaxed text-sm whitespace-pre-wrap">
            {lead.outreach_angle}
          </div>
        </section>

        {/* Primary Problem */}
        <section>
          <div className="flex items-center gap-2 text-lg font-bold text-white mb-4 border-b border-zinc-800 pb-2">
            <FiAlertTriangle className="text-orange-500" />
            Detected Business Problem
          </div>
          <div className="bg-orange-500/5 border border-orange-500/10 rounded-xl p-6 text-orange-200 leading-relaxed text-sm">
            {lead.primary_problem}
          </div>
        </section>

        {/* Contacts */}
        <section>
          <div className="flex items-center gap-2 text-lg font-bold text-white mb-4 border-b border-zinc-800 pb-2">
            <FiBriefcase className="text-blue-500" />
            Decision Makers
          </div>
          {lead.contacts && lead.contacts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {lead.contacts.map((c: any, i: number) => (
                <div key={i} className="bg-[#121214] border border-zinc-800 rounded-xl p-4 flex flex-col gap-1">
                  <span className="text-white font-bold">{c.name}</span>
                  <span className="text-zinc-500 text-xs uppercase tracking-wider">{c.title || 'Unknown Title'}</span>
                  {c.email && (
                    <a href={`mailto:${c.email}`} className="text-[#8b5cf6] text-sm flex items-center gap-1.5 mt-2 hover:underline">
                      <FiMail className="w-3 h-3" /> {c.email}
                    </a>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-zinc-500 text-sm italic">No decision makers identified yet.</div>
          )}
        </section>

        {/* Evidence */}
        <section>
          <div className="flex items-center gap-2 text-lg font-bold text-white mb-4 border-b border-zinc-800 pb-2">
            <FiTarget className="text-zinc-500" />
            Raw Crawler Evidence
          </div>
          <div className="space-y-3">
            {lead.evidence && lead.evidence.length > 0 ? lead.evidence.map((e: any, i: number) => (
              <div key={i} className="bg-[#121214] border border-zinc-800 rounded-xl p-4">
                <div className="text-xs font-bold text-zinc-500 mb-2 uppercase">{e.source}</div>
                <div className="text-zinc-400 text-xs leading-relaxed">{e.text}</div>
              </div>
            )) : (
              <div className="text-zinc-500 text-sm italic">No raw evidence recorded.</div>
            )}
          </div>
        </section>

      </div>
    </div>
  );
}
