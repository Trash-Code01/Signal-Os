'use client';
import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  CheckCircle2,
  Clock,
  Target,
  Search,
  Zap,
  AlertTriangle,
  XCircle,
  ArrowRight,
  ShieldCheck,
  Lock,
  RotateCcw,
} from 'lucide-react';

import { useSession } from '@/components/SessionProvider';
import { ContactOptions, LookupOptions } from '@/components/ContactOptions';

type StageStatus = 'pending' | 'running' | 'done' | 'partial' | 'failed';

interface Stage {
  key: string;
  label: string;
  status: StageStatus;
  count?: number;
  total?: number;
  description?: string;
}

const STAGE_METADATA: Record<string, { desc: string }> = {
  discovery: {
    desc: 'Discovers raw businesses & guarantees zero database duplicate repetition',
  },
  crawler: {
    desc: 'Audits live website, performance, mobile responsiveness & conversion CTAs',
  },
  enrichment: {
    desc: 'Extracts public crawl contacts & verified decision-maker info',
  },
  ai_sdr: {
    desc: 'Groq/Qwen AI diagnoses commercial problems & crafts hyper-tailored outreach angles',
  },
};

const PIPELINE_STAGES: Stage[] = [
  { key: 'discovery', label: 'Business Discovery & Deduplication', status: 'pending' },
  { key: 'crawler', label: 'Website Crawl & UX Audit', status: 'pending' },
  { key: 'enrichment', label: 'Contact Enrichment', status: 'pending' },
  { key: 'ai_sdr', label: 'AI SDR Analysis & Scoring', status: 'pending' },
];

function StatusIcon({ status }: { status: StageStatus }) {
  if (status === 'done') {
    return (
      <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
        <CheckCircle2 className="w-4 h-4" />
      </div>
    );
  }
  if (status === 'failed') {
    return (
      <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
        <XCircle className="w-4 h-4" />
      </div>
    );
  }
  if (status === 'partial') {
    return (
      <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
        <AlertTriangle className="w-4 h-4" />
      </div>
    );
  }
  if (status === 'running') {
    return (
      <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/30 flex items-center justify-center text-violet-400">
        <div className="w-4 h-4 border-2 border-violet-400/30 border-t-violet-400 rounded-full animate-spin"></div>
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-600">
      <div className="w-2 h-2 rounded-full bg-zinc-700"></div>
    </div>
  );
}

function ProgressBar({ count = 0, total = 100, isDone = false, isPartial = false }: { count?: number; total?: number; isDone?: boolean; isPartial?: boolean }) {
  const safeTotal = total > 0 ? total : 100;
  const pct = Math.min(100, Math.round((count / safeTotal) * 100));

  return (
    <div className="flex items-center gap-3 mt-2.5">
      <div className="flex-1 h-2 bg-zinc-900 border border-zinc-800/80 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-700 ${
            isPartial
              ? 'bg-gradient-to-r from-amber-500 to-orange-400 shadow-sm shadow-amber-500/20'
              : isDone
              ? 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-sm shadow-emerald-500/20'
              : 'bg-gradient-to-r from-violet-600 to-indigo-500 shadow-sm shadow-violet-500/20'
          }`}
          style={{ width: `${pct}%` }}
        ></div>
      </div>
      <div className="flex items-center gap-1 text-xs font-mono w-24 justify-end">
        <span className={isPartial ? 'text-amber-400 font-semibold' : isDone ? 'text-emerald-400 font-semibold' : 'text-white'}>{count}</span>
        <span className="text-zinc-600">/</span>
        <span className="text-zinc-400">{safeTotal}</span>
        <span className="text-[10px] text-zinc-500 ml-1">({pct}%)</span>
      </div>
    </div>
  );
}

function JobsContent() {
  const searchParams = useSearchParams();
  const campaignId = searchParams.get('campaign');
  const [stages, setStages] = useState<Stage[]>([]);
  const [websiteFilter, setWebsiteFilter] = useState('all');
  const [stats, setStats] = useState({
    discovered: 0,
    qualified: 0,
    enriched: 0,
    needs_review: 0,
    rejected: 0,
    target: 0,
    yield_pct: 0,
    shortfall: 0,
    target_reached: false,
    elapsed_seconds: 0,
    elapsed: '0m 0s',
  });
  const [campaignName, setCampaignName] = useState('');
  const [campaignStatus, setCampaignStatus] = useState('processing');
  const [dataMode, setDataMode] = useState<'live' | 'synthetic'>('live');
  const [summary, setSummary] = useState('');
  const [channelErrors, setChannelErrors] = useState<Record<string, string>>({});
  const { user } = useSession();
  const [options, setOptions] = useState<LookupOptions>({ personal_email_enabled: false, phone_enabled: false });
  const loadedOptions = useRef(false);
  const [saving, setSaving] = useState(false);
  const [optionMessage, setOptionMessage] = useState('');
  const [resuming, setResuming] = useState(false);
  const [resumeMessage, setResumeMessage] = useState('');
  const [runRevision, setRunRevision] = useState(0);

  async function resumeCampaign() {
    if (!campaignId) return;
    setResuming(true);
    setResumeMessage('');
    try {
      const response = await fetch(`/api/campaigns/${campaignId}/resume`, { method: 'POST', credentials: 'include' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to continue this campaign');
      setCampaignStatus(data.status === 'completed' ? 'completed' : 'processing');
      setResumeMessage(data.status === 'completed' ? 'Target is already complete.' : `Continuing discovery for ${data.remaining} remaining leads.`);
      setRunRevision((value) => value + 1);
    } catch (error) {
      setResumeMessage(error instanceof Error ? error.message : 'Unable to continue this campaign');
    } finally {
      setResuming(false);
    }
  }

  async function saveOptions() {
    if (!campaignId) return;
    setSaving(true);
    setOptionMessage('');
    try {
      const response = await fetch(`/api/campaigns/${campaignId}/contact-options`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(options),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to save options');
      setOptionMessage('Saved successfully. Applies to upcoming lead enrichment lookups.');
    } catch (error) {
      setOptionMessage(error instanceof Error ? error.message : 'Unable to save options');
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (!campaignId) return;
    loadedOptions.current = false;

    let localElapsedSeconds = 0;
    let isTerminalStatus = false;

    const ticker = setInterval(() => {
      if (!isTerminalStatus) {
        localElapsedSeconds += 1;
        setStats((s) => ({
          ...s,
          elapsed_seconds: localElapsedSeconds,
          elapsed: `${Math.floor(localElapsedSeconds / 60)}m ${localElapsedSeconds % 60}s`,
        }));
      }
    }, 1000);

    const fetchStatus = async () => {
      try {
        const res = await fetch(`/api/campaigns/${campaignId}/status`, { cache: 'no-store', credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setStages(data.stages || PIPELINE_STAGES);
          setWebsiteFilter(data.website_filter || 'all');
          setCampaignStatus(data.status || 'processing');
          setDataMode(data.data_mode === 'synthetic' ? 'synthetic' : 'live');
          setCampaignName(data.name || `Campaign #${campaignId}`);
          setSummary(data.summary || '');
          setChannelErrors(data.channel_errors || {});
          if (!loadedOptions.current && data.contact_options) {
            setOptions(data.contact_options);
            loadedOptions.current = true;
          }

          if (data.elapsed_seconds !== undefined) {
            localElapsedSeconds = data.elapsed_seconds;
          }

          setStats({
            discovered: data.stats.discovered,
            qualified: data.stats.qualified,
            enriched: data.stats.enriched,
            needs_review: data.stats.needs_review || 0,
            rejected: data.stats.rejected || 0,
            target: data.stats.target || 0,
            yield_pct: data.stats.yield_pct || (data.stats.target > 0 ? Math.round((data.stats.qualified / data.stats.target) * 100) : 100),
            shortfall: data.stats.shortfall || 0,
            target_reached: Boolean(data.stats.target_reached),
            elapsed_seconds: localElapsedSeconds,
            elapsed: data.elapsed || `${Math.floor(localElapsedSeconds / 60)}m ${localElapsedSeconds % 60}s`,
          });

          if (data.terminal) {
            setResumeMessage('');
            isTerminalStatus = true;
            clearInterval(poller);
            clearInterval(ticker);
          }
        }
      } catch (e) {
        console.error('Polling error', e);
      }
    };

    const poller = setInterval(fetchStatus, 3000);
    void fetchStatus();

    return () => {
      clearInterval(ticker);
      clearInterval(poller);
    };
  }, [campaignId, runRevision]);

  const terminalCount = stages.filter((s) => s.status === 'done' || s.status === 'partial' || s.status === 'failed').length;
  const stagesPct = stages.length ? Math.round((terminalCount / stages.length) * 100) : 0;
  const isTerminal = ['completed', 'completed_partial', 'needs_review', 'failed'].includes(campaignStatus);
  const isGoodComplete = campaignStatus === 'completed' && stats.target_reached;
  const statusLabel = campaignStatus.replace(/_/g, ' ');

  const targetLeads = stats.target || 100;
  const leadProgressPct = Math.min(100, Math.round((stats.qualified / targetLeads) * 100));
  const isShortfall = isTerminal && !stats.target_reached;
  const optionsLocked = isTerminal && !isShortfall;

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6">
      {dataMode === 'synthetic' && (
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-200">
          <strong>Synthetic staging data:</strong> this run tests workflow and counts only. Its companies, websites, scores, and analysis are fixtures; no contact details were scraped.
        </div>
      )}
      {/* Breadcrumbs & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-zinc-500 text-xs mb-2">
            <Link href="/campaigns" className="hover:text-zinc-300 transition">Campaigns</Link>
            <span>/</span>
            <span className="text-zinc-300 font-mono">Job #{campaignId}</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
              {campaignName || `Campaign #${campaignId}`}
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20 font-semibold uppercase">
              Pipeline Monitor
            </span>
          </div>
          <p className="text-zinc-400 text-xs mt-1">
            {websiteFilter === 'no_website'
              ? 'Business discovery, website-presence checks, public contacts, and no-website opportunity scoring.'
              : 'Real-time stage execution, website intelligence crawler, and AI SDR scoring.'}
          </p>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 text-xs font-mono">
            <Clock className="w-3.5 h-3.5 text-zinc-500" />
            <span>Elapsed: <strong className="text-white">{stats.elapsed}</strong></span>
          </div>

          <div
            className={`flex items-center gap-2 text-xs font-bold px-3 py-1.5 rounded-lg border capitalize ${
              isTerminal
                ? isGoodComplete
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : campaignStatus === 'failed'
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-violet-500/10 text-violet-300 border-violet-500/30'
            }`}
          >
            <span className={`w-2 h-2 rounded-full bg-current ${isTerminal ? '' : 'animate-pulse'}`} />
            {isTerminal ? statusLabel : 'Processing Stages'}
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-zinc-500 mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Target Leads</span>
            <Target className="w-3.5 h-3.5 text-zinc-400" />
          </div>
          <div className="text-xl font-bold text-white font-mono">{stats.target}</div>
          <div className="text-[10px] text-zinc-500 mt-1">Goal quantity</div>
        </div>

        <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-zinc-500 mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Discovered</span>
            <Search className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xl font-bold text-sky-400 font-mono">{stats.discovered}</div>
          <div className="text-[10px] text-zinc-500 mt-1">Raw candidates</div>
        </div>

        <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-zinc-500 mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Qualified</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-emerald-400 font-mono">{stats.qualified}</div>
          <div className="text-[10px] text-emerald-500/80 mt-1 font-mono">
            {leadProgressPct}% target reached
          </div>
        </div>

        <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-zinc-500 mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Enriched</span>
            <Zap className="w-3.5 h-3.5 text-violet-400" />
          </div>
          <div className="text-xl font-bold text-violet-300 font-mono">{stats.enriched}</div>
          <div className="text-[10px] text-zinc-500 mt-1">Enriched contact records</div>
        </div>

        <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-zinc-500 mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Needs Review</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-amber-400 font-mono">{stats.needs_review}</div>
          <div className="text-[10px] text-zinc-500 mt-1">Low confidence</div>
        </div>

        <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-zinc-500 mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider">Rejected</span>
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
          </div>
          <div className="text-xl font-bold text-rose-400 font-mono">{stats.rejected}</div>
          <div className="text-[10px] text-zinc-500 mt-1">Dead / duplicate</div>
        </div>
      </div>

      {/* Overall Progress Banner */}
      <div className="bg-[#121214] border border-zinc-800/80 rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <span>Pipeline Completion Progress</span>
              <span className="text-[11px] font-mono text-zinc-400">
                ({terminalCount} of {stages.length} stages finished)
              </span>
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              {summary || `${stats.qualified} qualified leads generated against target of ${targetLeads}.`}
            </p>
            {Object.entries(channelErrors).map(([channel, message]) => <p key={channel} className="mt-2 text-xs text-amber-300">{channel}: {message}</p>)}
          </div>

          <div className="flex items-center gap-2 text-xs font-mono self-start sm:self-auto">
            <span className="text-zinc-500">Yield:</span>
            <span className={`px-2 py-0.5 rounded font-bold ${
              leadProgressPct >= 100
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : isTerminal
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
            }`}>
              {stats.qualified} / {targetLeads} leads ({leadProgressPct}%)
            </span>
          </div>
        </div>

        <div className="h-2.5 bg-zinc-900 border border-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-700 ${
              isGoodComplete
                ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                : campaignStatus === 'failed'
                ? 'bg-rose-500'
                : isShortfall
                ? 'bg-gradient-to-r from-amber-500 to-orange-400'
                : 'bg-gradient-to-r from-violet-600 to-indigo-500'
            }`}
            style={{ width: `${stagesPct}%` }}
          />
        </div>
      </div>

      {/* Stage Breakdown List */}
      <div className="bg-[#121214] border border-zinc-800/80 rounded-2xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-zinc-800/80 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Pipeline Stage Execution</h2>
            <p className="text-xs text-zinc-400 mt-0.5">{websiteFilter === 'no_website' ? 'Website crawling is skipped for this campaign. Leads are checked using public listing and search evidence.' : 'Each stage executes sequentially and gates lead quality.'}</p>
          </div>
          <span className="text-xs font-mono text-zinc-500">{stages.length} Active Steps</span>
        </div>

        <div className="divide-y divide-zinc-800/60">
          {stages.map((stage, idx) => {
            const meta = STAGE_METADATA[stage.key] || {
              desc: 'Pipeline processing step',
            };
            const isDone = stage.status === 'done';
            const isPartial = stage.status === 'partial';
            const isRunning = stage.status === 'running';

            return (
              <div
                key={stage.key}
                className={`p-5 md:px-6 transition-colors ${
                  isRunning ? 'bg-violet-600/5' : isPartial ? 'bg-amber-500/5' : isDone ? 'bg-zinc-900/20' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  <StatusIcon status={stage.status} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-zinc-500">0{idx + 1}.</span>
                        <h4 className={`text-sm font-semibold ${
                          isPartial ? 'text-amber-200' : isDone ? 'text-zinc-200' : isRunning ? 'text-white' : 'text-zinc-500'
                        }`}>
                          {stage.label}
                        </h4>
                      </div>

                      <div>
                        {isRunning && (
                          <span className="inline-flex items-center gap-1.5 text-xs text-violet-400 font-medium px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20 animate-pulse">
                            Processing...
                          </span>
                        )}
                        {isDone && (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-400 font-medium px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                            Completed
                          </span>
                        )}
                        {isPartial && (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-400 font-medium px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
                            Partial
                          </span>
                        )}
                        {stage.status === 'pending' && (
                          <span className="text-xs text-zinc-600 font-mono">Queued</span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-zinc-400 mt-1">{stage.description || meta.desc}</p>

                    {(isRunning || isDone || isPartial) && stage.count !== undefined && (
                      <ProgressBar count={stage.count} total={stage.total} isDone={isDone} isPartial={isPartial} />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Completion Call to Action Banner */}
      {isTerminal && (
        <div
          className={`border rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl ${
            isGoodComplete
              ? 'bg-emerald-950/20 border-emerald-500/30'
              : campaignStatus === 'failed'
              ? 'bg-rose-950/20 border-rose-500/30'
              : 'bg-amber-950/20 border-amber-500/30'
          }`}
        >
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl border flex items-center justify-center shrink-0 ${
              isGoodComplete
                ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                : campaignStatus === 'failed'
                ? 'bg-rose-500/20 border-rose-500/30 text-rose-400'
                : 'bg-amber-500/20 border-amber-500/30 text-amber-400'
            }`}>
              {isGoodComplete ? <CheckCircle2 className="w-6 h-6" /> : campaignStatus === 'failed' ? <XCircle className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>{isGoodComplete ? 'Target reached' : campaignStatus === 'failed' ? 'Pipeline failed' : 'Run finished below target'}</span>
                <span className={`text-xs font-mono font-normal px-2 py-0.5 rounded border ${
                  isGoodComplete
                    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                    : 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                }`}>
                  {stats.qualified} / {targetLeads} qualified
                </span>
              </h3>
              <p className="text-xs text-zinc-300 mt-1">
                {campaignStatus === 'failed'
                  ? 'Resolve the error above, then retry this campaign. Existing qualified leads are retained.'
                  : isShortfall
                  ? `${stats.shortfall} more qualified leads are needed. Continue discovery to work toward the original target without repeating existing leads.`
                  : websiteFilter === 'no_website'
                  ? `${stats.qualified} no-website leads are in your CRM with public source evidence, available contacts, and opportunity scores.`
                  : `${stats.qualified} research-backed leads are organized with company dossiers, UX audits, scores, and outreach angles in your CRM.`}
              </p>
              {resumeMessage && <p className="text-xs text-amber-300 mt-2">{resumeMessage}</p>}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 shrink-0">
            {isShortfall && user?.role !== 'viewer' && (
              <button
                type="button"
                onClick={resumeCampaign}
                disabled={resuming}
                className="inline-flex items-center justify-center gap-2 bg-amber-400 hover:bg-amber-300 text-zinc-950 font-bold px-5 py-3 rounded-xl text-sm transition disabled:opacity-50"
              >
                <RotateCcw className={`w-4 h-4 ${resuming ? 'animate-spin' : ''}`} />
                <span>{resuming ? 'Starting…' : campaignStatus === 'failed' ? 'Retry campaign' : `Continue for ${stats.shortfall} leads`}</span>
              </button>
            )}
            <Link
              href={`/leads?campaignId=${campaignId}`}
              className="inline-flex items-center justify-center gap-2 bg-zinc-100 hover:bg-white text-zinc-950 font-bold px-5 py-3 rounded-xl text-sm transition shrink-0"
            >
              <span>Open CRM leads</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}

      {/* Contact Options Configuration (Moved to separate dedicated card) */}
      <div className="border border-zinc-800/80 rounded-2xl bg-[#121214] p-5">
        <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-violet-400" />
            <h3 className="text-sm font-semibold text-white">Campaign Contact Lookup Configuration</h3>
          </div>
          {optionsLocked ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
              <Lock className="w-3 h-3 text-zinc-500" />
              Locked (Completed Run)
            </span>
          ) : (
            <span className="text-[11px] font-mono text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded border border-violet-500/20">
              Active Session
            </span>
          )}
        </div>

        <ContactOptions
          value={options}
          onChange={setOptions}
          disabled={saving || optionsLocked || user?.role === 'viewer'}
        />

        {!optionsLocked && user?.role !== 'viewer' && (
          <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center justify-between gap-4">
            <p className="text-xs text-zinc-400">
              {optionMessage || 'Modifications apply to upcoming leads in this campaign.'}
            </p>
            <button
              type="button"
              disabled={saving || !loadedOptions.current}
              onClick={saveOptions}
              className="bg-violet-600 hover:bg-violet-500 text-white px-4 py-2 rounded-lg text-xs font-semibold transition disabled:opacity-50 shrink-0"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 max-w-6xl mx-auto space-y-6">
          <div className="h-8 w-64 bg-zinc-800 rounded animate-pulse" />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-20 bg-zinc-900 border border-zinc-800 rounded-xl animate-pulse" />
            ))}
          </div>
          <div className="h-64 bg-zinc-900 border border-zinc-800 rounded-2xl animate-pulse" />
        </div>
      }
    >
      <JobsContent />
    </Suspense>
  );
}
