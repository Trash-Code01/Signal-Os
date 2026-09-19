'use client';
import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

import { useSession } from '@/components/SessionProvider';
import { ContactOptions, LookupOptions } from '@/components/ContactOptions';

type StageStatus = 'pending' | 'running' | 'done' | 'failed';

interface Stage {
  key: string;
  label: string;
  status: StageStatus;
  count?: number;
  total?: number;
}

const PIPELINE_STAGES: Stage[] = [
  { key: 'discovery', label: 'Business Discovery & Deduplication', status: 'pending' },
  { key: 'crawler', label: 'Website Crawl & UX Audit', status: 'pending' },
  { key: 'enrichment', label: 'Contact Enrichment', status: 'pending' },
  { key: 'ai_sdr', label: 'AI SDR Analysis & Scoring', status: 'pending' },
];

function StatusIcon({ status }: { status: StageStatus }) {
  if (status === 'done') return <span className="text-green-500 text-lg">✓</span>;
  if (status === 'failed') return <span className="text-red-500 text-lg">!</span>;
  if (status === 'running') return <span className="w-4 h-4 border-2 border-[#8b5cf6]/30 border-t-[#8b5cf6] rounded-full animate-spin inline-block"></span>;
  return <span className="w-4 h-4 rounded-full border border-zinc-700 inline-block"></span>;
}

function ProgressBar({ count = 0, total = 100 }: { count?: number; total?: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3 mt-1.5">
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 transition-all duration-500" style={{ width: `${pct}%` }}></div>
      </div>
      <span className="text-xs text-zinc-500 w-16 text-right">{count} / {total}</span>
    </div>
  );
}

function JobsContent() {
  const searchParams = useSearchParams();
  const campaignId = searchParams.get('campaign');
  const [stages, setStages] = useState<Stage[]>(PIPELINE_STAGES);
  const [stats, setStats] = useState({ discovered: 0, qualified: 0, enriched: 0, needs_review: 0, rejected: 0, target: 0, elapsed: 0 });
  const [campaignStatus, setCampaignStatus] = useState('processing');
  const [summary, setSummary] = useState('');
  const { user } = useSession();
  const [options, setOptions] = useState<LookupOptions>({ personal_email_enabled: false, phone_enabled: false });
  const loadedOptions = useRef(false);
  const [saving, setSaving] = useState(false);
  const [optionMessage, setOptionMessage] = useState('');
  async function saveOptions() {
    if (!campaignId) return;
    setSaving(true); setOptionMessage('');
    try {
      const response = await fetch(`/api/campaigns/${campaignId}/contact-options`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(options) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to save options');
      setOptionMessage('Saved. Applies to upcoming lookups; requests already sent may still finish.');
    } catch (error) { setOptionMessage(error instanceof Error ? error.message : 'Unable to save options'); }
    finally { setSaving(false); }
  }

  useEffect(() => {
    if (!campaignId) return;
    loadedOptions.current = false;

    // Tick elapsed time
    const ticker = setInterval(() => setStats(s => ({ ...s, elapsed: s.elapsed + 1 })), 1000);

    // Poll API
    const fetchStatus = async () => {
      try {
        const apiUrl = "";
        const res = await fetch(`${apiUrl}/api/campaigns/${campaignId}/status`);
        if (res.ok) {
          const data = await res.json();
          setStages(data.stages);
          setCampaignStatus(data.status || 'processing');
          setSummary(data.summary || '');
          if (!loadedOptions.current && data.contact_options) { setOptions(data.contact_options); loadedOptions.current = true; }
          setStats(s => ({ 
            ...s, 
            discovered: data.stats.discovered, 
            qualified: data.stats.qualified, 
            enriched: data.stats.enriched,
            needs_review: data.stats.needs_review || 0,
            rejected: data.stats.rejected || 0,
            target: data.stats.target || 0,
          }));
          if (data.terminal) {
            clearInterval(poller);
            clearInterval(ticker);
          }
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    };

    const poller = setInterval(fetchStatus, 3000); // poll every 3s
    void fetchStatus(); // initial call

    return () => {
      clearInterval(ticker);
      clearInterval(poller);
    };
  }, [campaignId]);

  const terminalCount = stages.filter(s => s.status === 'done' || s.status === 'failed').length;
  const overallPct = Math.round((terminalCount / stages.length) * 100);
  const elapsed = `${Math.floor(stats.elapsed / 60)}m ${stats.elapsed % 60}s`;
  const isTerminal = ['completed', 'completed_partial', 'needs_review', 'failed'].includes(campaignStatus);
  const isGoodComplete = campaignStatus === 'completed';
  const statusLabel = campaignStatus.replace(/_/g, ' ');
  const progressClass = campaignStatus === 'failed'
    ? 'bg-red-500'
    : isTerminal && !isGoodComplete
      ? 'bg-orange-500'
      : 'bg-gradient-to-r from-purple-500 to-indigo-400';

  return (
    <div className="p-4 md:p-10 max-w-5xl">
      <div className="mb-8">
        <div className="flex items-center gap-2 text-zinc-500 text-sm mb-4">
          <a href="/campaigns" className="hover:text-white transition">Campaigns</a>
          <span>/</span>
          <span className="text-white">Job Monitor</span>
        </div>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Pipeline Monitor</h1>
            <p className="text-zinc-400 mt-1">
              {campaignId ? `Campaign #${campaignId}` : 'No campaign selected'} — watching all stages
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500">Elapsed: {elapsed}</span>
            <div className={`flex items-center gap-2 text-xs font-bold px-3 py-1.5 rounded-full border ${
              isTerminal
                ? isGoodComplete
                  ? 'bg-green-500/10 text-green-500 border-green-500/30'
                  : campaignStatus === 'failed'
                    ? 'bg-red-500/10 text-red-400 border-red-500/30'
                    : 'bg-orange-500/10 text-orange-400 border-orange-500/30'
                : 'bg-[#8b5cf6]/10 text-[#a78bfa] border-[#8b5cf6]/30'
            }`}>
              <span className={`w-2 h-2 rounded-full bg-current ${isTerminal ? '' : 'animate-pulse'}`}></span>
              {isTerminal ? statusLabel : 'Running'}
            </div>
          </div>
        </div>
      </div>

      {/* Overall progress */}
      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-5 mb-6">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm text-white font-medium">Overall progress</span>
          <span className="text-sm text-zinc-400">{terminalCount} / {stages.length} stages</span>
        </div>
        <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div className={`h-full transition-all duration-700 ${progressClass}`} style={{ width: `${overallPct}%` }}></div>
        </div>
        <div className="flex justify-between mt-3 text-xs text-zinc-500">
          <span>Discovered: <span className="text-white">{stats.discovered}</span></span>
          <span>Qualified: <span className="text-green-400">{stats.qualified}</span></span>
          <span>Review: <span className="text-orange-400">{stats.needs_review}</span></span>
          <span>Rejected: <span className="text-red-400">{stats.rejected}</span></span>
          <span>Enriched: <span className="text-[#a78bfa]">{stats.enriched}</span></span>
          <span>{overallPct}% complete</span>
        </div>
        {summary && <p className="mt-3 text-xs text-zinc-400">{summary}</p>}
        {campaignId && <div className="mt-5 space-y-3">
          <ContactOptions value={options} onChange={setOptions} disabled={saving || user?.role === 'viewer'} />
          {user?.role !== 'viewer' && <button disabled={saving || !loadedOptions.current} onClick={saveOptions} className="rounded-lg bg-violet-600 px-4 py-2 text-sm disabled:opacity-50">{saving ? 'Saving…' : 'Save campaign options'}</button>}
          <p role="status" className="text-xs text-zinc-400">{optionMessage || 'These choices control upcoming paid contact requests for this campaign.'}</p>
        </div>}
      </div>

      {/* Stage list */}
      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-zinc-800/60">
          <h2 className="text-white font-semibold">Pipeline Stages</h2>
        </div>
        <div className="divide-y divide-zinc-800/40">
          {stages.map((stage) => (
            <div key={stage.key} className={`px-6 py-4 transition-colors ${stage.status === 'running' ? 'bg-[#8b5cf6]/5' : ''}`}>
              <div className="flex items-center gap-4">
                <div className="w-8 flex justify-center"><StatusIcon status={stage.status} /></div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-medium ${
                      stage.status === 'done' ? 'text-zinc-400' :
                      stage.status === 'running' ? 'text-white' : 'text-zinc-600'
                    }`}>{stage.label}</span>
                    {stage.status === 'running' && <span className="text-xs text-[#a78bfa] font-medium animate-pulse">Processing...</span>}
                    {stage.status === 'done' && <span className="text-xs text-green-500">Done</span>}
                    {stage.status === 'pending' && <span className="text-xs text-zinc-700">Waiting</span>}
                  </div>
                  {(stage.status === 'running' || stage.status === 'done') && stage.count !== undefined && (
                    <ProgressBar count={stage.count} total={stage.total} />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Complete banner */}
      {isTerminal && (
          <div className={`mt-12 border rounded-xl p-6 flex items-center justify-between ${
            isGoodComplete
              ? 'bg-green-500/10 border-green-500/20'
              : campaignStatus === 'failed'
                ? 'bg-red-500/10 border-red-500/20'
                : 'bg-orange-500/10 border-orange-500/20'
          }`}>
            <div>
              <p className={`${isGoodComplete ? 'text-green-400' : campaignStatus === 'failed' ? 'text-red-400' : 'text-orange-400'} font-semibold`}>
                Pipeline {statusLabel}
              </p>
              <p className="text-zinc-400 text-sm mt-0.5">{summary || `${stats.qualified} qualified leads are ready in your CRM`}</p>
            </div>
            <a href={`/leads?campaignId=${campaignId}`} className="bg-green-500 hover:bg-green-600 text-white px-5 py-2.5 rounded-md text-sm font-medium transition">
              View Leads
            </a>
          </div>
      )}
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={
      <div className="p-10 max-w-5xl">
        <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse mb-4"></div>
        <div className="h-4 w-64 bg-zinc-800/50 rounded animate-pulse"></div>
      </div>
    }>
      <JobsContent />
    </Suspense>
  );
}
