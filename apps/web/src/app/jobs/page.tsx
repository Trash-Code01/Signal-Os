'use client';
import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

type StageStatus = 'pending' | 'running' | 'done' | 'failed';

interface Stage {
  key: string;
  label: string;
  status: StageStatus;
  count?: number;
  total?: number;
}

const PIPELINE_STAGES: Stage[] = [
  { key: 'discovery', label: 'Business Discovery', status: 'pending' },
  { key: 'deduplication', label: 'Deduplication', status: 'pending' },
  { key: 'website_check', label: 'Website Discovery', status: 'pending' },
  { key: 'crawler', label: 'Playwright Crawler', status: 'pending' },
  { key: 'ux_audit', label: 'UX / Conversion Audit', status: 'pending' },
  { key: 'scoring', label: 'Lead Qualification & Scoring', status: 'pending' },
  { key: 'apollo', label: 'Apollo Decision-Maker Enrichment', status: 'pending' },
  { key: 'hunter', label: 'Hunter Email Verification', status: 'pending' },
  { key: 'ai_sdr', label: 'AI SDR Analysis (Gemini)', status: 'pending' },
  { key: 'crm', label: 'CRM & Dossier Generation', status: 'pending' },
];

function StatusIcon({ status }: { status: StageStatus }) {
  if (status === 'done') return <span className="text-green-500 text-lg">âœ“</span>;
  if (status === 'failed') return <span className="text-red-500 text-lg">âœ—</span>;
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
  const [stats, setStats] = useState({ discovered: 0, qualified: 0, enriched: 0, elapsed: 0 });

  useEffect(() => {
    if (!campaignId) return;

    let ticker: ReturnType<typeof setInterval>;
    let poller: ReturnType<typeof setInterval>;
    
    // Tick elapsed time
    ticker = setInterval(() => setStats(s => ({ ...s, elapsed: s.elapsed + 1 })), 1000);

    // Poll API
    const fetchStatus = async () => {
      try {
        const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
        const res = await fetch(`${apiUrl}/api/campaigns/${campaignId}/status`);
        if (res.ok) {
          const data = await res.json();
          setStages(data.stages);
          setStats(s => ({ 
            ...s, 
            discovered: data.stats.discovered, 
            qualified: data.stats.qualified, 
            enriched: data.stats.enriched 
          }));
          if (data.status === 'completed') {
            clearInterval(poller);
            clearInterval(ticker);
          }
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    };

    fetchStatus(); // initial call
    poller = setInterval(fetchStatus, 3000); // poll every 3s

    return () => {
      clearInterval(ticker);
      clearInterval(poller);
    };
  }, [campaignId]);

  const doneCount = stages.filter(s => s.status === 'done').length;
  const overallPct = Math.round((doneCount / stages.length) * 100);
  const elapsed = `${Math.floor(stats.elapsed / 60)}m ${stats.elapsed % 60}s`;

  return (
    <div className="p-10 max-w-5xl">
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
              {campaignId ? `Campaign #${campaignId}` : 'No campaign selected'} â€” watching all stages
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500">Elapsed: {elapsed}</span>
            <div className={`flex items-center gap-2 text-xs font-bold px-3 py-1.5 rounded-full border ${
              doneCount === stages.length
                ? 'bg-green-500/10 text-green-500 border-green-500/30'
                : 'bg-[#8b5cf6]/10 text-[#a78bfa] border-[#8b5cf6]/30'
            }`}>
              <span className="w-2 h-2 rounded-full bg-current animate-pulse"></span>
              {doneCount === stages.length ? 'Complete' : 'Running'}
            </div>
          </div>
        </div>
      </div>

      {/* Overall progress */}
      <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-5 mb-6">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm text-white font-medium">Overall progress</span>
          <span className="text-sm text-zinc-400">{doneCount} / {stages.length} stages</span>
        </div>
        <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 transition-all duration-700" style={{ width: `${overallPct}%` }}></div>
        </div>
        <div className="flex justify-between mt-3 text-xs text-zinc-500">
          <span>Discovered: <span className="text-white">{stats.discovered}</span></span>
          <span>Qualified: <span className="text-green-400">{stats.qualified}</span></span>
          <span>Enriched: <span className="text-[#a78bfa]">{stats.enriched}</span></span>
          <span>{overallPct}% complete</span>
        </div>
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
      {doneCount === stages.length && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-5 flex items-center justify-between">
          <div>
            <p className="text-green-400 font-semibold">Pipeline Complete</p>
            <p className="text-zinc-400 text-sm mt-0.5">{stats.qualified} qualified leads are ready in your CRM</p>
          </div>
          <a href="/leads" className="bg-green-500 hover:bg-green-600 text-white px-5 py-2.5 rounded-md text-sm font-medium transition">
            View Leads â†’
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
