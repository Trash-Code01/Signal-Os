'use client';

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  FiAlertCircle,
  FiArrowUpRight,
  FiAward,
  FiBriefcase,
  FiCalendar,
  FiCheck,
  FiCheckCircle,
  FiChevronDown,
  FiClock,
  FiDownload,
  FiExternalLink,
  FiFileText,
  FiFilter,
  FiGlobe,
  FiLinkedin,
  FiLoader,
  FiMail,
  FiMapPin,
  FiMonitor,
  FiMoreHorizontal,
  FiPhone,
  FiPlus,
  FiRefreshCw,
  FiSearch,
  FiShield,
  FiSmartphone,
  FiTag,
  FiTrendingUp,
  FiUpload,
  FiUser,
  FiUsers,
  FiX,
  FiXCircle,
} from 'react-icons/fi';

type Stage = 'new' | 'reviewing' | 'contacted' | 'qualified' | 'proposal' | 'won' | 'lost' | 'archived';

type Contact = {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  title?: string | null;
  verification_status?: string | null;
  linkedin_url?: string | null;
  contact_type?: string | null;
  source?: string | null;
  confidence?: number | null;
};

type Lead = {
  id: number;
  name: string;
  website_url?: string | null;
  phone?: string | null;
  industry?: string | null;
  city?: string | null;
  state_province?: string | null;
  country?: string | null;
  location: string;
  stage: Stage;
  owner_name?: string | null;
  tags: string[];
  source: string;
  campaign_id?: number | null;
  campaign_name: string;
  commercial_score?: number | null;
  data_confidence?: number | null;
  grade?: string | null;
  primary_problem?: string | null;
  recommended_offer?: string | null;
  outreach_angle?: string | null;
  next_follow_up_at?: string | null;
  last_activity_at?: string | null;
  contacts: Contact[];
  contact_count: number;
};

type LeadDetail = Lead & {
  ai_reasoning?: string | null;
  ticket_range?: string | null;
  opportunity?: { ticket_low?: number | null; ticket_high?: number | null; problems?: string[]; confidence?: string | null };
  website?: {
    url?: string | null;
    is_live?: boolean | null;
    has_ssl?: boolean | null;
    cms?: string | null;
    framework?: string | null;
    technology_stack?: string[];
    pages_checked?: number;
    screenshot_count?: number;
  };
  audit?: {
    mobile_responsive?: boolean | null;
    horizontal_overflow?: boolean | null;
    performance_score?: number | null;
    seo_score?: number | null;
    desktop_ux_score?: number | null;
    mobile_ux_score?: number | null;
    accessibility_score?: number | null;
    phone_cta?: boolean | null;
    contact_form?: boolean | null;
    quote_form?: boolean | null;
    live_chat?: boolean | null;
    sticky_cta?: boolean | null;
    ecommerce_detected?: boolean | null;
    booking_detected?: boolean | null;
  };
  evidence?: { source: string; text: string; confidence?: number | null }[];
  dossier?: {
    priority?: 'high' | 'medium' | 'normal';
    metrics?: { mobile?: number | null; desktop?: number | null; ux?: number | null; conversion?: number | null };
    digital_gaps?: string[];
    audit_available?: boolean;
    why_contact?: string | null;
    evidence_labels?: string[];
    evidence_summary?: string | null;
    owner?: {
      name?: string | null;
      role?: string | null;
      email?: string | null;
      phone?: string | null;
      linkedin_url?: string | null;
      contact_type?: string | null;
      verification_status?: string | null;
      email_verified?: boolean;
      has_phone?: boolean;
      has_linkedin?: boolean;
    };
  };
  crm?: { stage: Stage; owner_name?: string | null; tags: string[]; next_follow_up_at?: string | null };
  activities: { id: number; type: string; body: string; created_at?: string | null; created_by?: string | null }[];
};

type Campaign = { id: number; name: string };

type Filters = {
  q: string;
  stage: string;
  grade: string;
  campaignId: string;
  contact: string;
  minScore: string;
};

const STAGES: { value: Stage; label: string; className: string }[] = [
  { value: 'new', label: 'New', className: 'bg-slate-400/10 text-slate-300 border-slate-400/20' },
  { value: 'reviewing', label: 'Reviewing', className: 'bg-violet-400/10 text-violet-300 border-violet-400/20' },
  { value: 'contacted', label: 'Contacted', className: 'bg-sky-400/10 text-sky-300 border-sky-400/20' },
  { value: 'qualified', label: 'Qualified', className: 'bg-emerald-400/10 text-emerald-300 border-emerald-400/20' },
  { value: 'proposal', label: 'Proposal', className: 'bg-amber-400/10 text-amber-300 border-amber-400/20' },
  { value: 'won', label: 'Won', className: 'bg-green-400/10 text-green-300 border-green-400/20' },
  { value: 'lost', label: 'Lost', className: 'bg-rose-400/10 text-rose-300 border-rose-400/20' },
  { value: 'archived', label: 'Archived', className: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20' },
];

const EMPTY_FILTERS: Filters = { q: '', stage: 'all', grade: 'all', campaignId: '', contact: '', minScore: '' };

function apiUrl() {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

function stageMeta(stage?: string) {
  return STAGES.find((item) => item.value === stage) ?? STAGES[0];
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function dateInputValue(value?: string | null) {
  return value ? value.slice(0, 10) : '';
}

function scoreClass(score?: number | null) {
  if (!score) return 'text-zinc-500 bg-zinc-800/70';
  if (score >= 90) return 'text-emerald-300 bg-emerald-400/10';
  if (score >= 75) return 'text-sky-300 bg-sky-400/10';
  return 'text-amber-300 bg-amber-400/10';
}

function auditMetric(value?: number | null) {
  return value === null || value === undefined ? '—' : String(value);
}

function priorityMeta(score?: number | null) {
  if ((score ?? 0) >= 80) return { label: 'High priority', className: 'bg-orange-400/10 text-orange-200 border-orange-400/25' };
  if ((score ?? 0) >= 70) return { label: 'Worth reviewing', className: 'bg-amber-400/10 text-amber-200 border-amber-400/25' };
  return { label: 'Research lead', className: 'bg-zinc-800 text-zinc-300 border-zinc-700' };
}

function StatusPill({ stage }: { stage: string }) {
  const meta = stageMeta(stage);
  return <span className={`inline-flex items-center border px-2 py-0.5 text-[11px] font-medium ${meta.className}`}>{meta.label}</span>;
}

function LeadAvatar({ name }: { name: string }) {
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
  return <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-violet-400/15 text-[10px] font-bold text-violet-200">{initials}</span>;
}

function ExactLeadDossier({ lead, detail, loading, onClose }: { lead: Lead; detail: LeadDetail | null; loading: boolean; onClose: () => void }) {
  const owner = detail?.dossier?.owner;
  const contact = detail?.contacts?.[0] ?? lead.contacts[0];
  const contactName = owner?.name || contact?.name || (lead.phone ? 'Business contact' : null);
  const contactRole = owner?.role || contact?.title || (owner?.contact_type === 'company' ? 'Website contact' : 'Decision maker');
  const contactEmail = owner?.email || contact?.email;
  const contactPhone = owner?.phone || contact?.phone || lead.phone;
  const contactLinkedin = owner?.linkedin_url || contact?.linkedin_url;
  const emailVerified = owner?.email_verified || contact?.verification_status === 'verified';
  const metrics = detail?.dossier?.metrics;
  const digitalGaps = detail?.dossier?.digital_gaps ?? [];
  const priority = detail?.dossier?.priority === 'high' ? 'HIGH PRIORITY' : detail?.dossier?.priority === 'medium' ? 'MEDIUM PRIORITY' : 'RESEARCH LEAD';
  const location = [lead.city, lead.state_province, lead.country].filter(Boolean).join(', ') || lead.location;
  const tech = detail?.website?.cms || detail?.website?.technology_stack?.[0] || 'Technology not identified';
  const liveLabel = detail?.website?.is_live === true ? 'Live' : detail?.website?.is_live === false ? 'Unavailable' : 'Not checked';

  return <aside className="fixed inset-y-0 right-0 z-40 flex w-full max-w-[540px] flex-col border-l border-zinc-800 bg-[#101012] shadow-2xl shadow-black/70">
    <header className="border-b border-zinc-800 px-6 py-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0"><h2 className="truncate text-2xl font-semibold tracking-tight text-white">{lead.name}</h2><p className="mt-1 truncate text-sm text-zinc-400">{[lead.industry, location].filter(Boolean).join(' • ')}</p></div>
        <div className="flex items-center gap-3"><span className="whitespace-nowrap text-lg font-semibold text-sky-200">{lead.grade ?? '—'} {lead.commercial_score ?? '—'}</span><button onClick={onClose} className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-white" aria-label="Close details"><FiX className="text-lg" /></button></div>
      </div>
      <div className="mt-5 flex items-center justify-between gap-3"><span className={`inline-flex items-center gap-1.5 border px-2.5 py-1.5 text-xs font-semibold tracking-wide ${detail?.dossier?.priority === 'high' ? 'border-orange-400/25 bg-orange-400/10 text-orange-200' : 'border-zinc-700 bg-zinc-900 text-zinc-300'}`}>🔥 {priority}</span><span className="text-sm font-semibold text-zinc-200">{detail?.ticket_range || 'Estimate pending'}</span></div>
    </header>

    {loading ? <div className="flex flex-1 items-center justify-center text-zinc-500"><FiLoader className="mr-2 animate-spin" /> Loading lead dossier…</div> : <div className="flex-1 overflow-y-auto">
      <section className="border-b border-zinc-800 px-6 py-5"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Owner</p>{contactName || contactEmail || contactPhone ? <div className="mt-3"><p className="text-base font-medium text-white">{contactName || 'Website contact'}</p><p className="mt-0.5 text-sm text-zinc-500">{contactRole}</p><div className="mt-3 space-y-1.5 text-sm">{contactEmail ? <a href={`mailto:${contactEmail}`} className="block break-all text-violet-200 hover:text-violet-100">{emailVerified ? '✓ Verified email: ' : '✓ Email: '}{contactEmail}</a> : <p className="text-zinc-600">— Email not found</p>}{contactPhone ? <a href={`tel:${contactPhone}`} className="block text-emerald-300 hover:text-emerald-200">✓ Phone: {contactPhone}</a> : <p className="text-zinc-600">— Phone not found</p>}{contactLinkedin ? <a href={contactLinkedin} target="_blank" rel="noreferrer" className="block text-sky-300 hover:text-sky-200">✓ LinkedIn</a> : <p className="text-zinc-600">— LinkedIn not found</p>}</div></div> : <p className="mt-3 text-sm text-zinc-600">No owner or decision maker captured yet.</p>}</section>

      <section className="border-b border-zinc-800 px-6 py-5"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Website</p><div className="mt-3 flex items-center gap-4 text-sm"><span className={detail?.website?.is_live === true ? 'text-emerald-300' : 'text-zinc-500'}>{detail?.website?.is_live === true ? '✓' : '—'} {liveLabel}</span><span className="text-zinc-300">{tech}</span></div><div className="mt-4 grid grid-cols-2 gap-y-2 text-sm text-zinc-300"><p>Mobile: <span className="font-medium text-white">{auditMetric(metrics?.mobile)}</span></p><p>Desktop: <span className="font-medium text-white">{auditMetric(metrics?.desktop)}</span></p><p>UX: <span className="font-medium text-white">{auditMetric(metrics?.ux)}</span></p><p>Conversion: <span className="font-medium text-white">{auditMetric(metrics?.conversion)}</span></p></div></section>

      <section className="border-b border-zinc-800 px-6 py-5"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Digital gaps</p>{detail?.dossier?.audit_available ? <div className="mt-3 space-y-1.5 text-sm">{digitalGaps.length ? digitalGaps.map((gap) => <p key={gap} className="text-rose-300">✕ {gap}</p>) : <p className="text-emerald-300">✓ No material digital gaps detected</p>}</div> : <p className="mt-3 text-sm text-zinc-600">Audit not available for this website yet.</p>}</section>

      <section className="border-b border-zinc-800 px-6 py-5"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Devacia opportunity</p><p className="mt-3 text-base font-medium text-violet-100">{detail?.recommended_offer || lead.recommended_offer || 'Offer still being matched'}</p><p className="mt-3 text-sm text-zinc-300">Estimated: <span className="font-medium text-white">{detail?.ticket_range || 'Pending'}</span></p></section>

      <section className="border-b border-zinc-800 px-6 py-5"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Why we should contact them</p><p className="mt-3 text-sm leading-6 text-zinc-300">{detail?.dossier?.why_contact || detail?.primary_problem || lead.primary_problem || 'Research is still being collected for this lead.'}</p></section>

      <section className="border-b border-zinc-800 px-6 py-5"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Outreach angle</p><p className="mt-3 text-sm leading-6 text-zinc-300">{detail?.outreach_angle || lead.outreach_angle || 'Personalized opener has not been generated yet.'}</p></section>

      <section className="px-6 py-5"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Evidence</p><p className="mt-3 text-sm leading-6 text-zinc-300">{detail?.dossier?.evidence_summary || 'Crawl data and audit findings will appear here after research completes.'}</p></section>
    </div>}
  </aside>;
}

export default function LeadsPipeline() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [activeLead, setActiveLead] = useState<Lead | null>(null);
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [note, setNote] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [detailSaving, setDetailSaving] = useState(false);
  const [bulkStage, setBulkStage] = useState<Stage>('contacted');
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [notice, setNotice] = useState('');
  const importInputRef = useRef<HTMLInputElement>(null);

  const requestUrl = useCallback(() => {
    const params = new URLSearchParams();
    if (filters.q.trim()) params.set('q', filters.q.trim());
    if (filters.stage !== 'all') params.set('stage', filters.stage);
    if (filters.grade !== 'all') params.set('grade', filters.grade);
    if (filters.campaignId) params.set('campaign_id', filters.campaignId);
    if (filters.contact) params.set('has_contact', filters.contact);
    if (filters.minScore) params.set('min_score', filters.minScore);
    params.set('qualified_only', 'true');
    params.set('page_size', '100');
    return `${apiUrl()}/api/crm/leads?${params.toString()}`;
  }, [filters]);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(requestUrl(), { cache: 'no-store' });
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not load the CRM');
      const data = await response.json();
      setLeads(data.leads ?? []);
      setTotal(data.total ?? 0);
      setCampaigns(data.facets?.campaigns ?? []);
      setSelectedIds((current) => current.filter((id) => data.leads?.some((lead: Lead) => lead.id === id)));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load the CRM');
    } finally {
      setLoading(false);
    }
  }, [requestUrl]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadLeads(), filters.q ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [filters, loadLeads]);

  const loadDetail = useCallback(async (lead: Lead) => {
    setActiveLead(lead);
    setDetail(null);
    setDetailLoading(true);
    try {
      const response = await fetch(`${apiUrl()}/api/crm/leads/${lead.id}`, { cache: 'no-store' });
      if (!response.ok) throw new Error('Could not load lead details');
      setDetail(await response.json());
    } catch (requestError) {
      setNotice(requestError instanceof Error ? requestError.message : 'Could not load lead details');
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const activeData = detail ?? activeLead;
  const currentStage = detail?.crm?.stage ?? activeData?.stage ?? 'new';
  const currentTags = detail?.crm?.tags ?? activeData?.tags ?? [];
  const currentOwner = detail?.crm?.owner_name ?? activeData?.owner_name ?? '';
  const currentFollowUp = detail?.crm?.next_follow_up_at ?? activeData?.next_follow_up_at ?? null;
  const primaryContact = (detail?.contacts ?? activeData?.contacts ?? [])[0];
  const audit = detail?.audit;
  const website = detail?.website;
  const priority = priorityMeta(activeData?.commercial_score);
  const technologyStack = website?.technology_stack ?? [];
  const auditSignals = detail && website?.is_live !== false ? [
    { value: audit?.booking_detected, missing: 'No booking flow detected', covered: 'Booking flow detected' },
    { value: audit?.quote_form, missing: 'No dedicated quote or estimate flow detected', covered: 'Quote or estimate flow detected' },
    { value: audit?.phone_cta, missing: 'No clear phone CTA detected', covered: 'Phone CTA detected' },
    { value: audit?.mobile_responsive, missing: 'Mobile layout issue flagged', covered: 'Mobile layout passes crawl' },
  ] : [];

  function updateFilters(patch: Partial<Filters>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  function toggleLead(id: number) {
    setSelectedIds((current) => current.includes(id) ? current.filter((selected) => selected !== id) : [...current, id]);
  }

  function toggleAll() {
    setSelectedIds(selectedIds.length === leads.length ? [] : leads.map((lead) => lead.id));
  }

  async function updateLead(leadId: number, payload: Record<string, unknown>) {
    setDetailSaving(true);
    try {
      const response = await fetch(`${apiUrl()}/api/crm/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not save lead');
      await loadLeads();
      if (activeLead?.id === leadId) await loadDetail({ ...activeLead, ...payload } as Lead);
    } catch (requestError) {
      setNotice(requestError instanceof Error ? requestError.message : 'Could not save lead');
    } finally {
      setDetailSaving(false);
    }
  }

  async function moveSelected() {
    if (!selectedIds.length) return;
    try {
      const response = await fetch(`${apiUrl()}/api/crm/actions/bulk`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: selectedIds, stage: bulkStage }),
      });
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not update selected leads');
      setNotice(`${selectedIds.length} lead${selectedIds.length === 1 ? '' : 's'} moved to ${stageMeta(bulkStage).label}`);
      setSelectedIds([]);
      await loadLeads();
    } catch (requestError) {
      setNotice(requestError instanceof Error ? requestError.message : 'Could not update selected leads');
    }
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!activeData || !note.trim()) return;
    try {
      const response = await fetch(`${apiUrl()}/api/crm/leads/${activeData.id}/activities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: note.trim() }),
      });
      if (!response.ok) throw new Error('Could not save note');
      setNote('');
      await loadDetail(activeData);
      await loadLeads();
    } catch (requestError) {
      setNotice(requestError instanceof Error ? requestError.message : 'Could not save note');
    }
  }

  async function addTag() {
    if (!activeData || !tagInput.trim()) return;
    await updateLead(activeData.id, { tags: [...currentTags, tagInput.trim()] });
    setTagInput('');
  }

  async function removeTag(tag: string) {
    if (activeData) await updateLead(activeData.id, { tags: currentTags.filter((item) => item !== tag) });
  }

  function exportLeads(format: 'csv' | 'tsv' | 'json') {
    const params = new URLSearchParams({ format });
    selectedIds.forEach((id) => params.append('ids', String(id)));
    window.location.assign(`${apiUrl()}/api/crm/leads/export?${params.toString()}`);
    setShowExportMenu(false);
  }

  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(`${apiUrl()}/api/crm/leads/import`, { method: 'POST', body: formData });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || 'Could not import this file');
      setNotice(`${data.added} lead${data.added === 1 ? '' : 's'} imported${data.skipped ? ` · ${data.skipped} skipped` : ''}`);
      await loadLeads();
    } catch (requestError) {
      setNotice(requestError instanceof Error ? requestError.message : 'Could not import this file');
    } finally {
      event.target.value = '';
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0b0d] text-zinc-100">
      <div className="mx-auto max-w-[1700px] px-8 py-8">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-5">
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs text-zinc-500"><FiBriefcase /> Workspace <span className="text-zinc-700">/</span> CRM</div>
            <div className="flex items-end gap-3">
              <h1 className="text-3xl font-semibold tracking-tight text-white">Leads CRM</h1>
              <span className="mb-1 rounded-full bg-violet-400/10 px-2.5 py-1 text-xs font-medium text-violet-200">{total.toLocaleString()} leads</span>
            </div>
            <p className="mt-2 max-w-2xl text-sm text-zinc-400">Showing only campaign leads with live website research, a usable email and phone, and an evidence-backed AI opportunity.</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => void loadLeads()} className="inline-flex h-9 items-center gap-2 border border-zinc-800 px-3 text-sm text-zinc-300 hover:border-zinc-600 hover:text-white" title="Refresh CRM"><FiRefreshCw className={loading ? 'animate-spin' : ''} /> Refresh</button>
            <button onClick={() => setShowImport(true)} className="inline-flex h-9 items-center gap-2 border border-zinc-800 px-3 text-sm text-zinc-300 hover:border-zinc-600 hover:text-white"><FiUpload /> Import</button>
            <div className="relative">
              <button onClick={() => setShowExportMenu((open) => !open)} className="inline-flex h-9 items-center gap-2 border border-zinc-800 px-3 text-sm text-zinc-300 hover:border-zinc-600 hover:text-white"><FiDownload /> Export <FiChevronDown className="text-zinc-500" /></button>
              {showExportMenu && <div className="absolute right-0 z-30 mt-2 w-56 border border-zinc-800 bg-[#18181b] p-1 shadow-2xl">
                <button onClick={() => exportLeads('csv')} className="block w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white">CSV <span className="float-right text-xs text-zinc-600">Excel / Sheets</span></button>
                <button onClick={() => exportLeads('tsv')} className="block w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white">TSV <span className="float-right text-xs text-zinc-600">spreadsheet-safe</span></button>
                <button onClick={() => exportLeads('json')} className="block w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white">JSON <span className="float-right text-xs text-zinc-600">full data</span></button>
              </div>}
            </div>
            <button onClick={() => setShowCreate(true)} className="inline-flex h-9 items-center gap-2 bg-violet-500 px-3.5 text-sm font-medium text-white hover:bg-violet-400"><FiPlus /> New lead</button>
          </div>
        </header>

        {notice && <div className="mb-4 flex items-center justify-between border border-violet-400/20 bg-violet-400/10 px-4 py-3 text-sm text-violet-100"><span>{notice}</span><button onClick={() => setNotice('')} className="text-violet-200 hover:text-white"><FiX /></button></div>}
        {error && <div className="mb-4 flex items-center gap-2 border border-rose-400/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100"><FiAlertCircle /> {error}<button onClick={() => void loadLeads()} className="ml-auto text-rose-200 underline">Try again</button></div>}

        <section className="border border-zinc-800 bg-[#121214]">
          <div className="border-b border-zinc-800 px-4 pt-4">
            <div className="flex flex-wrap items-center gap-2 pb-4">
              <label className="flex h-9 min-w-[270px] flex-1 items-center gap-2 border border-zinc-800 bg-[#0e0e10] px-3 text-zinc-400 focus-within:border-violet-400/60">
                <FiSearch className="shrink-0" />
                <input value={filters.q} onChange={(event) => updateFilters({ q: event.target.value })} placeholder="Search company, website, or city…" className="w-full bg-transparent text-sm text-white outline-none placeholder:text-zinc-600" />
              </label>
              <div className="flex h-9 items-center gap-2 border border-zinc-800 px-3 text-xs text-zinc-500"><FiFilter /> Filters</div>
              <select value={filters.stage} onChange={(event) => updateFilters({ stage: event.target.value })} className="h-9 border border-zinc-800 bg-[#0e0e10] px-3 text-sm text-zinc-300 outline-none hover:border-zinc-600"><option value="all">All stages</option>{STAGES.map((stage) => <option key={stage.value} value={stage.value}>{stage.label}</option>)}</select>
              <select value={filters.grade} onChange={(event) => updateFilters({ grade: event.target.value })} className="h-9 border border-zinc-800 bg-[#0e0e10] px-3 text-sm text-zinc-300 outline-none hover:border-zinc-600"><option value="all">All scores</option><option value="A+">A+ prospects</option><option value="A">A prospects</option><option value="B">B prospects</option><option value="C">C prospects</option></select>
              <select value={filters.campaignId} onChange={(event) => updateFilters({ campaignId: event.target.value })} className="h-9 max-w-[200px] border border-zinc-800 bg-[#0e0e10] px-3 text-sm text-zinc-300 outline-none hover:border-zinc-600"><option value="">All campaigns</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select>
              <select value={filters.contact} onChange={(event) => updateFilters({ contact: event.target.value })} className="h-9 border border-zinc-800 bg-[#0e0e10] px-3 text-sm text-zinc-300 outline-none hover:border-zinc-600"><option value="">Any contact</option><option value="true">Has contact</option><option value="false">No contact</option></select>
              <select value={filters.minScore} onChange={(event) => updateFilters({ minScore: event.target.value })} className="h-9 border border-zinc-800 bg-[#0e0e10] px-3 text-sm text-zinc-300 outline-none hover:border-zinc-600"><option value="">Any score</option><option value="90">90+ score</option><option value="80">80+ score</option><option value="70">70+ score</option></select>
              {(filters.q || filters.stage !== 'all' || filters.grade !== 'all' || filters.campaignId || filters.contact || filters.minScore) && <button onClick={() => setFilters(EMPTY_FILTERS)} className="h-9 px-2 text-sm text-zinc-500 hover:text-white">Clear</button>}
            </div>
            <div className="flex items-center gap-5 text-sm">
              <button onClick={() => updateFilters({ stage: 'all' })} className={`border-b-2 px-1 pb-3 ${filters.stage === 'all' ? 'border-violet-400 text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}>All <span className="ml-1 text-xs text-zinc-600">{total}</span></button>
              {(['new', 'qualified', 'contacted', 'won'] as Stage[]).map((stage) => <button key={stage} onClick={() => updateFilters({ stage })} className={`border-b-2 px-1 pb-3 ${filters.stage === stage ? 'border-violet-400 text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}>{stageMeta(stage).label}</button>)}
            </div>
          </div>

          {selectedIds.length > 0 && <div className="flex flex-wrap items-center gap-3 border-b border-violet-400/20 bg-violet-400/10 px-4 py-3 text-sm">
            <span className="font-medium text-violet-100">{selectedIds.length} selected</span>
            <select value={bulkStage} onChange={(event) => setBulkStage(event.target.value as Stage)} className="h-8 border border-violet-400/20 bg-[#17141f] px-2 text-sm text-violet-100 outline-none">{STAGES.map((stage) => <option key={stage.value} value={stage.value}>{stage.label}</option>)}</select>
            <button onClick={() => void moveSelected()} className="inline-flex h-8 items-center gap-1.5 bg-violet-500 px-3 text-sm font-medium text-white hover:bg-violet-400"><FiArrowUpRight /> Move leads</button>
            <button onClick={() => exportLeads('csv')} className="inline-flex h-8 items-center gap-1.5 border border-violet-400/20 px-3 text-violet-100 hover:bg-violet-400/10"><FiDownload /> Export selected</button>
            <button onClick={() => setSelectedIds([])} className="ml-auto text-zinc-400 hover:text-white">Clear selection</button>
          </div>}

          <div className="overflow-x-auto">
            <table className="min-w-[1220px] w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-[#101012] text-[11px] uppercase tracking-wider text-zinc-500">
                <tr>
                  <th className="w-10 px-4 py-3"><input type="checkbox" checked={leads.length > 0 && selectedIds.length === leads.length} onChange={toggleAll} className="accent-violet-500" aria-label="Select all visible leads" /></th>
                  <th className="min-w-[250px] px-2 py-3 font-medium">Company</th>
                  <th className="min-w-[135px] px-3 py-3 font-medium">Stage</th>
                  <th className="min-w-[85px] px-3 py-3 font-medium">Score</th>
                  <th className="min-w-[185px] px-3 py-3 font-medium">Contact</th>
                  <th className="min-w-[170px] px-3 py-3 font-medium">Location</th>
                  <th className="min-w-[165px] px-3 py-3 font-medium">Campaign</th>
                  <th className="min-w-[125px] px-3 py-3 font-medium">Follow-up</th>
                  <th className="w-10 px-3 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/80">
                {loading ? <tr><td colSpan={9} className="px-5 py-20 text-center text-zinc-500"><FiLoader className="mx-auto mb-3 animate-spin text-xl text-violet-300" />Loading your CRM…</td></tr> : leads.length === 0 ? <tr><td colSpan={9} className="px-5 py-20 text-center"><FiUsers className="mx-auto mb-3 text-3xl text-zinc-700" /><p className="font-medium text-white">No qualified campaign leads yet</p><p className="mt-1 text-sm text-zinc-500">Mock, unreachable, and contactless records are intentionally hidden. Run a live campaign or import your own contacts.</p></td></tr> : leads.map((lead) => {
                  const primaryContact = lead.contacts[0];
                  return <tr key={lead.id} onClick={() => void loadDetail(lead)} className={`group cursor-pointer ${activeLead?.id === lead.id ? 'bg-violet-400/[0.06]' : 'hover:bg-zinc-800/40'}`}>
                    <td className="px-4 py-3" onClick={(event) => event.stopPropagation()}><input type="checkbox" checked={selectedIds.includes(lead.id)} onChange={() => toggleLead(lead.id)} className="accent-violet-500" aria-label={`Select ${lead.name}`} /></td>
                    <td className="px-2 py-3"><div className="flex items-center gap-3"><LeadAvatar name={lead.name} /><div className="min-w-0"><p className="truncate font-medium text-zinc-100">{lead.name}</p><p className="mt-0.5 truncate text-xs text-zinc-500">{lead.website_url?.replace(/^https?:\/\//, '') || lead.industry || 'No website added'}</p></div></div></td>
                    <td className="px-3 py-3" onClick={(event) => event.stopPropagation()}><select value={lead.stage} onChange={(event) => void updateLead(lead.id, { stage: event.target.value })} className={`max-w-[126px] border px-2 py-1 text-xs font-medium outline-none ${stageMeta(lead.stage).className}`}><option value={lead.stage}>{stageMeta(lead.stage).label}</option>{STAGES.filter((stage) => stage.value !== lead.stage).map((stage) => <option key={stage.value} value={stage.value} className="bg-[#18181b] text-zinc-100">{stage.label}</option>)}</select></td>
                    <td className="px-3 py-3"><span className={`inline-flex min-w-11 items-center justify-center px-2 py-1 text-xs font-semibold ${scoreClass(lead.commercial_score)}`}>{lead.commercial_score ?? '—'}{lead.grade ? <span className="ml-1 opacity-70">{lead.grade}</span> : null}</span></td>
                    <td className="px-3 py-3"><div className="min-w-0">{primaryContact ? <><p className="truncate text-zinc-300">{primaryContact.contact_type === 'company' ? 'Website contact' : primaryContact.name}</p><p className="truncate text-xs text-violet-300">{primaryContact.email || primaryContact.phone || lead.phone || 'Contact details unavailable'}</p></> : lead.phone ? <><p className="text-zinc-300">Business phone</p><p className="truncate text-xs text-emerald-300">{lead.phone}</p></> : <span className="text-xs text-zinc-600">No contact found</span>}</div></td>
                    <td className="px-3 py-3"><span className="flex max-w-[170px] items-center gap-1.5 truncate text-zinc-400"><FiMapPin className="shrink-0 text-zinc-600" />{lead.location}</span></td>
                    <td className="px-3 py-3"><span className="block max-w-[165px] truncate text-xs text-zinc-500">{lead.campaign_name}</span></td>
                    <td className="px-3 py-3"><span className={lead.next_follow_up_at ? 'flex items-center gap-1.5 text-xs text-amber-300' : 'text-xs text-zinc-600'}>{lead.next_follow_up_at && <FiCalendar />}{formatDate(lead.next_follow_up_at)}</span></td>
                    <td className="px-3 py-3 text-zinc-600 group-hover:text-zinc-200"><FiMoreHorizontal /></td>
                  </tr>;
                })}
              </tbody>
            </table>
          </div>
          <footer className="flex items-center justify-between border-t border-zinc-800 px-4 py-3 text-xs text-zinc-500"><span>Showing {leads.length.toLocaleString()} of {total.toLocaleString()} leads</span><span>Campaign leads sync here automatically</span></footer>
        </section>
      </div>

      {activeData && <ExactLeadDossier lead={activeData} detail={detail} loading={detailLoading} onClose={() => { setActiveLead(null); setDetail(null); }} />}
      {/* Previous expanded drawer retained below only as an implementation reference.
        <header className="border-b border-zinc-800 bg-gradient-to-br from-violet-500/[0.10] via-[#141218] to-[#101012] px-6 py-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-start gap-3">
              <LeadAvatar name={activeData.name} />
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2"><StatusPill stage={currentStage} />{currentTags.slice(0, 2).map((tag) => <span key={tag} className="border border-zinc-700 bg-zinc-900/70 px-2 py-0.5 text-[11px] text-zinc-400">{tag}</span>)}</div>
                <h2 className="truncate text-2xl font-semibold tracking-tight text-white">{activeData.name}</h2>
                <p className="mt-1 truncate text-sm text-zinc-400">{[activeData.industry, activeData.location].filter(Boolean).join(' • ')}</p>
              </div>
            </div>
            <button onClick={() => { setActiveLead(null); setDetail(null); }} className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-white" aria-label="Close details"><FiX className="text-lg" /></button>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 border px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wide ${priority.className}`}><FiTrendingUp /> {priority.label}</span>
            <span className="inline-flex items-center gap-1.5 border border-sky-400/20 bg-sky-400/[0.08] px-2.5 py-1.5 text-sm font-semibold text-sky-200"><FiAward /> {activeData.commercial_score ?? '—'} {activeData.grade ?? ''}</span>
            {detail?.ticket_range && <span className="ml-auto text-sm font-semibold text-zinc-200">Estimated {detail.ticket_range}</span>}
          </div>
        </header>

        {detailLoading ? <div className="flex flex-1 items-center justify-center text-zinc-500"><FiLoader className="mr-2 animate-spin" /> Loading research…</div> : <div className="flex-1 overflow-y-auto">
          <section className="border-b border-zinc-800 px-6 py-5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Owner & contact</p>
            {currentOwner && <div className="mb-4 flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-violet-400/15 text-violet-200"><FiUser /></span><div><p className="text-sm font-medium text-white">{currentOwner}</p><p className="text-xs text-zinc-500">CRM owner</p></div></div>}
            {primaryContact ? <div className="rounded border border-zinc-800 bg-[#141416] p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-medium text-zinc-100">{primaryContact.name}</p><p className="mt-0.5 text-xs text-zinc-500">{primaryContact.title || 'Decision maker'}</p></div>{primaryContact.verification_status === 'verified' && <span className="inline-flex items-center gap-1 text-xs text-emerald-300"><FiShield /> Verified</span>}</div><div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs">{primaryContact.email ? <a href={`mailto:${primaryContact.email}`} className="inline-flex items-center gap-1.5 text-violet-300 hover:text-violet-200"><FiCheckCircle className="text-emerald-400" /> {primaryContact.verification_status === 'verified' ? 'Verified email' : primaryContact.email}</a> : <span className="inline-flex items-center gap-1.5 text-zinc-600"><FiXCircle /> No email</span>}{primaryContact.phone ? <a href={`tel:${primaryContact.phone}`} className="inline-flex items-center gap-1.5 text-zinc-300 hover:text-white"><FiCheckCircle className="text-emerald-400" /> Phone</a> : <span className="inline-flex items-center gap-1.5 text-zinc-600"><FiXCircle /> No phone</span>}{primaryContact.linkedin_url ? <a href={primaryContact.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-sky-300 hover:text-sky-200"><FiLinkedin /> LinkedIn</a> : <span className="inline-flex items-center gap-1.5 text-zinc-600"><FiLinkedin /> No LinkedIn</span>}</div></div> : <div className="rounded border border-dashed border-zinc-800 px-4 py-3 text-sm text-zinc-500">No decision maker has been captured yet.</div>}
          </section>

          <section className="border-b border-zinc-800 px-6 py-5">
            <div className="mb-3 flex items-center justify-between gap-3"><p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Website</p>{website?.url && <a href={website.url.startsWith('http') ? website.url : `https://${website.url}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs text-violet-300 hover:text-violet-200">Open site <FiExternalLink /></a>}</div>
            <div className="flex flex-wrap items-center gap-2 text-sm"><span className={`inline-flex items-center gap-1.5 ${website?.is_live === true ? 'text-emerald-300' : 'text-zinc-500'}`}><FiGlobe /> {website?.is_live === true ? 'Live' : website?.is_live === false ? 'Unavailable' : 'Not checked'}</span>{technologyStack.length ? technologyStack.map((technology) => <span key={technology} className="border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-xs text-zinc-300">{technology}</span>) : <span className="text-xs text-zinc-600">Technology not detected</span>}</div>
            <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden border border-zinc-800 bg-zinc-800 sm:grid-cols-4"><div className="bg-[#141416] p-3"><p className="text-[10px] uppercase tracking-wide text-zinc-600">Mobile UX</p><p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-zinc-200"><FiSmartphone className="text-zinc-500" />{auditMetric(audit?.mobile_ux_score)}</p></div><div className="bg-[#141416] p-3"><p className="text-[10px] uppercase tracking-wide text-zinc-600">Desktop UX</p><p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-zinc-200"><FiMonitor className="text-zinc-500" />{auditMetric(audit?.desktop_ux_score)}</p></div><div className="bg-[#141416] p-3"><p className="text-[10px] uppercase tracking-wide text-zinc-600">Performance</p><p className="mt-1 text-sm font-semibold text-zinc-200">{auditMetric(audit?.performance_score)}</p></div><div className="bg-[#141416] p-3"><p className="text-[10px] uppercase tracking-wide text-zinc-600">SEO</p><p className="mt-1 text-sm font-semibold text-zinc-200">{auditMetric(audit?.seo_score)}</p></div></div>
          </section>

          <section className="border-b border-zinc-800 px-6 py-5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Digital gaps</p>
            {auditSignals.length ? <div className="space-y-2">{auditSignals.map((signal) => signal.value === null || signal.value === undefined ? <div key={signal.missing} className="flex items-center gap-2 text-sm text-zinc-600"><FiFileText /> {signal.missing.replace('detected', 'not assessed')}</div> : <div key={signal.missing} className={`flex items-center gap-2 text-sm ${signal.value ? 'text-emerald-300' : 'text-rose-300'}`}>{signal.value ? <FiCheckCircle /> : <FiXCircle />}{signal.value ? signal.covered : signal.missing}</div>)}</div> : <p className="text-sm text-zinc-600">{website?.is_live === false ? 'Website was unavailable during the crawl, so gaps could not be verified.' : 'Website audit has not run for this lead yet.'}</p>}
          </section>

          <section className="border-b border-zinc-800 px-6 py-5"><p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Devacia opportunity</p><div className="rounded border border-violet-400/20 bg-violet-400/[0.06] p-4"><p className="font-medium text-violet-100">{detail?.recommended_offer || activeData.recommended_offer || 'Offer still being matched'}</p>{detail?.ticket_range && <p className="mt-2 text-sm text-violet-200">Estimated: {detail.ticket_range}</p>}</div></section>

          <section className="border-b border-zinc-800 px-6 py-5"><p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Why we should contact them</p><p className="text-sm leading-6 text-zinc-300">{detail?.ai_reasoning || detail?.primary_problem || activeData.primary_problem || 'Research is still being collected for this lead.'}</p></section>

          <section className="border-b border-zinc-800 px-6 py-5"><p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Outreach angle</p><p className="text-sm leading-6 text-zinc-300">{detail?.outreach_angle || activeData.outreach_angle || 'No personalized opener has been generated yet.'}</p></section>

          <section className="border-b border-zinc-800 px-6 py-5"><p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Evidence</p><div className="mb-3 flex flex-wrap gap-2 text-xs text-zinc-400"><span className="border border-zinc-800 px-2 py-1">{website?.pages_checked ?? 0} pages crawled</span><span className="border border-zinc-800 px-2 py-1">{website?.screenshot_count ?? 0} screenshots</span><span className="border border-zinc-800 px-2 py-1">{detail?.evidence?.length ?? 0} findings</span></div>{detail?.evidence?.length ? <div className="space-y-2">{detail.evidence.slice(0, 4).map((item, index) => <div key={`${item.source}-${index}`} className="border-l-2 border-violet-400/50 pl-3"><p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-600">{item.source.replaceAll('_', ' ')}</p><p className="mt-0.5 text-xs leading-5 text-zinc-400">{item.text}</p></div>)}</div> : <p className="text-sm text-zinc-600">No crawl findings recorded yet.</p>}</section>

          <section className="border-b border-zinc-800 px-6 py-5"><p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">CRM controls</p><div className="grid grid-cols-2 gap-3"><label className="text-xs text-zinc-500">Pipeline stage<select value={currentStage} onChange={(event) => void updateLead(activeData.id, { stage: event.target.value })} className="mt-1.5 w-full border border-zinc-800 bg-[#0d0d0f] px-2.5 py-2 text-sm text-zinc-200 outline-none">{STAGES.map((stage) => <option key={stage.value} value={stage.value}>{stage.label}</option>)}</select></label><label className="text-xs text-zinc-500">Next follow-up<input type="date" value={dateInputValue(currentFollowUp)} onChange={(event) => void updateLead(activeData.id, { next_follow_up_at: event.target.value ? `${event.target.value}T09:00:00Z` : null })} className="mt-1.5 w-full border border-zinc-800 bg-[#0d0d0f] px-2.5 py-2 text-sm text-zinc-200 outline-none" /></label></div><label className="mt-3 block text-xs text-zinc-500">Owner<input key={`${activeData.id}-${currentOwner}`} defaultValue={currentOwner ?? ''} onBlur={(event) => void updateLead(activeData.id, { owner_name: event.target.value })} placeholder="Assign owner" className="mt-1.5 w-full border border-zinc-800 bg-[#0d0d0f] px-2.5 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600" /></label><div className="mt-3 flex flex-wrap items-center gap-2">{currentTags.map((tag) => <span key={tag} className="inline-flex items-center gap-1 border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300">{tag}<button onClick={() => void removeTag(tag)} className="text-zinc-500 hover:text-white"><FiX /></button></span>)}<input value={tagInput} onChange={(event) => setTagInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); void addTag(); } }} placeholder="Add a tag" className="w-24 border-b border-zinc-700 bg-transparent py-1 text-xs text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-violet-400" /><button onClick={() => void addTag()} className="inline-flex items-center gap-1 text-xs text-violet-300 hover:text-white"><FiTag /> Add</button></div></section>

          <section className="px-6 py-5"><p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Activity</p><form onSubmit={addNote} className="mb-4 flex gap-2"><input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Write a note…" className="min-w-0 flex-1 border border-zinc-800 bg-[#0d0d0f] px-3 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-violet-400/60" /><button disabled={!note.trim()} className="bg-violet-500 px-3 text-white disabled:cursor-not-allowed disabled:opacity-40"><FiCheck /></button></form><div className="space-y-3">{detail?.activities?.length ? detail.activities.map((activity) => <div key={activity.id} className="border-l border-zinc-700 pl-3"><p className="text-sm text-zinc-300">{activity.body}</p><p className="mt-1 flex items-center gap-1 text-xs text-zinc-600"><FiClock /> {formatDate(activity.created_at)} · {activity.created_by || 'Workspace'}</p></div>) : <p className="text-sm text-zinc-600">No activity recorded yet.</p>}</div></section>
        </div>}
        {detailSaving && <div className="border-t border-zinc-800 px-6 py-2 text-xs text-violet-300">Saving changes…</div>}
      */}

      {/* Previous compact drawer retained below only as an implementation reference.
        <div className="flex items-start justify-between border-b border-zinc-800 px-6 py-5"><div className="flex min-w-0 items-center gap-3"><LeadAvatar name={activeData.name} /><div className="min-w-0"><h2 className="truncate text-lg font-semibold text-white">{activeData.name}</h2><p className="mt-0.5 text-xs text-zinc-500">{activeData.campaign_name}</p></div></div><button onClick={() => { setActiveLead(null); setDetail(null); }} className="p-1 text-zinc-500 hover:text-white" aria-label="Close details"><FiX className="text-lg" /></button></div>
        {detailLoading ? <div className="flex flex-1 items-center justify-center text-zinc-500"><FiLoader className="mr-2 animate-spin" /> Loading detail…</div> : <div className="flex-1 overflow-y-auto p-6">
          <div className="mb-6 flex flex-wrap gap-2"><StatusPill stage={currentStage} />{currentTags.map((tag) => <span key={tag} className="inline-flex items-center gap-1 bg-zinc-800 px-2 py-1 text-xs text-zinc-300">{tag}<button onClick={() => void removeTag(tag)} className="text-zinc-500 hover:text-white"><FiX /></button></span>)}</div>
          <div className="grid grid-cols-2 gap-3 border-y border-zinc-800 py-5 text-sm"><div><p className="mb-1 text-xs text-zinc-600">Pipeline stage</p><select value={currentStage} onChange={(event) => void updateLead(activeData.id, { stage: event.target.value })} className="w-full border border-zinc-800 bg-[#0d0d0f] px-2.5 py-2 text-zinc-200 outline-none">{STAGES.map((stage) => <option key={stage.value} value={stage.value}>{stage.label}</option>)}</select></div><div><p className="mb-1 text-xs text-zinc-600">Lead score</p><div className={`inline-flex px-2.5 py-2 text-sm font-semibold ${scoreClass(activeData.commercial_score)}`}>{activeData.commercial_score ?? 'No score'} {activeData.grade ?? ''}</div></div><div><p className="mb-1 text-xs text-zinc-600">Owner</p><input defaultValue={currentOwner ?? ''} onBlur={(event) => void updateLead(activeData.id, { owner_name: event.target.value })} placeholder="Assign owner" className="w-full border border-zinc-800 bg-[#0d0d0f] px-2.5 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600" /></div><div><p className="mb-1 text-xs text-zinc-600">Next follow-up</p><input type="date" value={dateInputValue(currentFollowUp)} onChange={(event) => void updateLead(activeData.id, { next_follow_up_at: event.target.value ? `${event.target.value}T09:00:00Z` : null })} className="w-full border border-zinc-800 bg-[#0d0d0f] px-2.5 py-2 text-sm text-zinc-200 outline-none" /></div></div>
          <section className="border-b border-zinc-800 py-5"><h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Lead overview</h3><div className="space-y-3 text-sm"><div className="flex gap-3"><FiBriefcase className="mt-0.5 shrink-0 text-zinc-600" /><div><p className="text-xs text-zinc-600">Recommended offer</p><p className="mt-0.5 text-zinc-200">{detail?.recommended_offer || activeData.recommended_offer || 'Not generated yet'}</p></div></div><div className="flex gap-3"><FiFileText className="mt-0.5 shrink-0 text-zinc-600" /><div><p className="text-xs text-zinc-600">Opportunity signal</p><p className="mt-0.5 leading-relaxed text-zinc-300">{detail?.primary_problem || activeData.primary_problem || 'Research is still being collected for this lead.'}</p></div></div>{activeData.website_url && <a href={activeData.website_url.startsWith('http') ? activeData.website_url : `https://${activeData.website_url}`} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-violet-300 hover:text-violet-200"><FiExternalLink /> Open website</a>}</div></section>
          <section className="border-b border-zinc-800 py-5"><h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Contacts</h3>{(detail?.contacts || activeData.contacts).length ? <div className="space-y-3">{(detail?.contacts || activeData.contacts).map((contact: Contact, index: number) => <div key={`${contact.name}-${index}`} className="flex items-start gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 text-xs text-zinc-400">{contact.name.slice(0, 1)}</span><div className="min-w-0"><p className="text-sm text-zinc-200">{contact.name} {contact.title && <span className="text-zinc-500">· {contact.title}</span>}</p>{contact.email && <a href={`mailto:${contact.email}`} className="mt-1 flex items-center gap-1.5 text-xs text-violet-300"><FiMail /> {contact.email}</a>}{contact.phone && <a href={`tel:${contact.phone}`} className="mt-1 flex items-center gap-1.5 text-xs text-zinc-400"><FiPhone /> {contact.phone}</a>}</div></div>)}</div> : <p className="text-sm text-zinc-600">No decision maker has been added yet.</p>}</section>
          <section className="border-b border-zinc-800 py-5"><h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Tags</h3><div className="flex flex-wrap gap-2"><input value={tagInput} onChange={(event) => setTagInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); void addTag(); } }} placeholder="Add a tag" className="w-28 border-b border-zinc-700 bg-transparent py-1 text-xs text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-violet-400" /><button onClick={() => void addTag()} className="inline-flex items-center gap-1 text-xs text-violet-300 hover:text-white"><FiTag /> Add</button></div></section>
          <section className="py-5"><h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Activity</h3><form onSubmit={addNote} className="mb-5 flex gap-2"><input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Write a note…" className="min-w-0 flex-1 border border-zinc-800 bg-[#0d0d0f] px-3 py-2 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-violet-400/60" /><button disabled={!note.trim()} className="bg-violet-500 px-3 text-white disabled:cursor-not-allowed disabled:opacity-40"><FiCheck /></button></form><div className="space-y-4">{detail?.activities?.length ? detail.activities.map((activity) => <div key={activity.id} className="border-l border-zinc-700 pl-3"><p className="text-sm text-zinc-300">{activity.body}</p><p className="mt-1 flex items-center gap-1 text-xs text-zinc-600"><FiClock /> {formatDate(activity.created_at)} · {activity.created_by || 'Workspace'}</p></div>) : <p className="text-sm text-zinc-600">No activity recorded yet.</p>}</div></section>
        </div>}
        {detailSaving && <div className="border-t border-zinc-800 px-6 py-2 text-xs text-violet-300">Saving changes…</div>}
      */}

      {showImport && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><div className="w-full max-w-md border border-zinc-800 bg-[#18181b] p-6 shadow-2xl"><div className="flex items-start justify-between"><div><h2 className="text-lg font-semibold text-white">Import leads</h2><p className="mt-1 text-sm text-zinc-400">Add rows from Excel or Google Sheets.</p></div><button onClick={() => setShowImport(false)} className="text-zinc-500 hover:text-white"><FiX /></button></div><div className="mt-5 border border-dashed border-zinc-700 bg-zinc-900/40 p-5 text-center"><FiUpload className="mx-auto mb-3 text-xl text-violet-300" /><p className="text-sm text-zinc-200">Upload CSV, TSV, or JSON</p><p className="mt-1 text-xs leading-relaxed text-zinc-500">Export a worksheet as CSV, then map common columns such as Company, Website, Stage, Score, Contact, and Email automatically.</p><button onClick={() => importInputRef.current?.click()} className="mt-4 bg-violet-500 px-4 py-2 text-sm font-medium text-white hover:bg-violet-400">Choose file</button><input ref={importInputRef} type="file" accept=".csv,.tsv,.txt,.json,text/csv,text/tab-separated-values,application/json" onChange={(event) => { void importFile(event); setShowImport(false); }} className="hidden" /></div><button onClick={() => setShowImport(false)} className="mt-4 text-sm text-zinc-500 hover:text-white">Cancel</button></div></div>}
      {showCreate && <CreateLeadModal onClose={() => setShowCreate(false)} onCreated={async (message) => { setShowCreate(false); setNotice(message); await loadLeads(); }} />}
    </div>
  );
}

function CreateLeadModal({ onClose, onCreated }: { onClose: () => void; onCreated: (message: string) => Promise<void> }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      name: String(form.get('name') || ''),
      website_url: String(form.get('website_url') || '') || null,
      primary_phone: String(form.get('phone') || '') || null,
      city: String(form.get('city') || '') || null,
      state_province: String(form.get('state') || '') || null,
      country: String(form.get('country') || '') || null,
      industry: String(form.get('industry') || '') || null,
      stage: String(form.get('stage') || 'new'),
      contact_name: String(form.get('contact_name') || '') || null,
      contact_email: String(form.get('contact_email') || '') || null,
      contact_title: String(form.get('contact_title') || '') || null,
      tags: String(form.get('tags') || '').split(',').map((tag) => tag.trim()).filter(Boolean),
    };
    setSaving(true);
    setError('');
    try {
      const response = await fetch(`${apiUrl()}/api/crm/leads`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || 'Could not add lead');
      await onCreated(`${payload.name} was added to your CRM`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not add lead');
    } finally {
      setSaving(false);
    }
  }

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><form onSubmit={submit} className="w-full max-w-xl border border-zinc-800 bg-[#18181b] shadow-2xl"><div className="flex items-start justify-between border-b border-zinc-800 p-5"><div><h2 className="text-lg font-semibold text-white">Add lead</h2><p className="mt-1 text-sm text-zinc-400">Create a prospect directly in your CRM.</p></div><button type="button" onClick={onClose} className="text-zinc-500 hover:text-white"><FiX /></button></div><div className="grid grid-cols-2 gap-4 p-5"><Field name="name" label="Company name" required /><Field name="website_url" label="Website" placeholder="https://example.com" /><Field name="industry" label="Industry" /><Field name="stage" label="Stage" type="select" /><Field name="city" label="City" /><Field name="state" label="State / province" /><Field name="country" label="Country" /><Field name="phone" label="Company phone" /><Field name="contact_name" label="Primary contact" /><Field name="contact_title" label="Contact title" /><Field name="contact_email" label="Contact email" /><Field name="tags" label="Tags" placeholder="warm, referral" />{error && <p className="col-span-2 text-sm text-rose-300">{error}</p>}</div><div className="flex justify-end gap-3 border-t border-zinc-800 p-5"><button type="button" onClick={onClose} className="px-3 py-2 text-sm text-zinc-400 hover:text-white">Cancel</button><button disabled={saving} className="inline-flex items-center gap-2 bg-violet-500 px-4 py-2 text-sm font-medium text-white hover:bg-violet-400 disabled:opacity-50">{saving && <FiLoader className="animate-spin" />} Add lead</button></div></form></div>;
}

function Field({ name, label, required = false, placeholder, type = 'text' }: { name: string; label: string; required?: boolean; placeholder?: string; type?: 'text' | 'select' }) {
  return <label className="block text-xs text-zinc-500">{label}{type === 'select' ? <select name={name} defaultValue="new" className="mt-1.5 w-full border border-zinc-800 bg-[#101012] px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-400/60">{STAGES.filter((stage) => stage.value !== 'archived').map((stage) => <option key={stage.value} value={stage.value}>{stage.label}</option>)}</select> : <input name={name} required={required} placeholder={placeholder} className="mt-1.5 w-full border border-zinc-800 bg-[#101012] px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-700 focus:border-violet-400/60" />}</label>;
}
