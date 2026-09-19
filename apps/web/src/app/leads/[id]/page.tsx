
"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { SidebarTrigger } from "@/components/ui/sidebar";

import { useSession } from '@/components/SessionProvider';
import { ContactOptions, LookupOptions } from '@/components/ContactOptions';

export default function LeadDossier() {
  const { id } = useParams();
  const router = useRouter();
  const { user } = useSession();
  const [options, setOptions] = useState<LookupOptions>({ personal_email_enabled: false, phone_enabled: false });
  const [researchMessage, setResearchMessage] = useState('');
  useEffect(() => { if (user) setOptions({ personal_email_enabled: user.personal_email_enabled, phone_enabled: user.phone_enabled }); }, [user]);
  const [lead, setLead] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isGeneratingEmail, setIsGeneratingEmail] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [contactViewMode, setContactViewMode] = useState<'crawl' | 'personal' | 'all'>('crawl');

  const handleCopy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleRefreshResearch = async () => {
    setIsRefreshing(true);
    setResearchMessage('');
    try {
      const apiUrl = "";
      const res = await fetch(`${apiUrl}/api/crm/leads/${id}/enrich`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(options) });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || "Contact research failed");
      setResearchMessage("Research queued with your selected options. Reload this lead after the job completes.");
      if (res.ok) {
        const refreshRes = await fetch(`${apiUrl}/api/crm/leads/${id}`);
        if (refreshRes.ok) {
          setLead(await refreshRes.json());
        }
      }
    } catch (e) {
      setResearchMessage(e instanceof Error ? e.message : "Contact research failed");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    async function fetchLead() {
      try {
        const apiUrl = "";
        const res = await fetch(`${apiUrl}/api/crm/leads/${id}`);
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

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#141313]">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-[#141313] text-on-surface">
        <h1 className="text-2xl font-bold">Lead Not Found</h1>
        <button onClick={() => router.push("/leads")} className="mt-4 hover:underline">
          Back to CRM
        </button>
      </div>
    );
  }

  const handleGenerateEmail = async () => {
    setIsGeneratingEmail(true);
    setEmailError(null);
    try {
      const apiUrl = "";
      const res = await fetch(`${apiUrl}/api/leads/${id}/generate-email`, {
        method: "POST",
      });
      if (res.ok) {
        const refreshRes = await fetch(`${apiUrl}/api/crm/leads/${id}`);
        if (refreshRes.ok) {
          setLead(await refreshRes.json());
        }
      } else {
        setEmailError("Failed to generate email");
      }
    } catch (e) {
      setEmailError("Error connecting to server");
    } finally {
      setIsGeneratingEmail(false);
    }
  };

  const generatedEmailActivity = (lead.activities || []).find((a: any) => a.type === "generated_email");
  const generatedEmail = generatedEmailActivity ? generatedEmailActivity.body : null;

  const parsedEmail = (() => {
    if (!generatedEmail) return { subject: "", body: "" };
    const match = generatedEmail.match(/^Subject:\s*(.*?)(?:\r?\n\r?\n|\r?\n)([\s\S]*)$/i);
    if (match) {
      return { subject: match[1].trim(), body: match[2].trim() };
    }
    const lines = generatedEmail.split(/\r?\n/);
    if (lines.length > 1 && lines[0].toLowerCase().startsWith("subject:")) {
      return {
        subject: lines[0].replace(/^subject:\s*/i, "").trim(),
        body: lines.slice(1).join("\n").trim()
      };
    }
    return { subject: "", body: generatedEmail.trim() };
  })();

  const websiteHref = lead.website_url
    ? lead.website_url.startsWith("http")
      ? lead.website_url
      : `https://${lead.website_url}`
    : null;

  const detail = lead.dossier || {};
  const metrics = detail.metrics || { mobile: 0, desktop: 0, ux: 0, conversion: 0 };
  const digitalGaps = detail.digital_gaps || [];
  const recommendedOffer = lead.recommended_offer || "Offer still being matched";
  const whyContact = detail.why_contact || lead.primary_problem || "Research is still being collected for this lead.";
  const outreachAngle = lead.outreach_angle || "Personalized opener has not been generated yet.";
  const evidenceSummary = detail.evidence_summary || "Crawl data and audit findings will appear here after research completes.";
  const socialProfiles = lead.social_profiles || [];

  const contactsList = lead.contacts || [];

  // 1. Crawl Emails & Phones (Website & General Contacts)
  const crawlEmails: Array<{ email: string; sourceUrl?: string }> = (() => {
    const seen = new Set<string>();
    const list: Array<{ email: string; sourceUrl?: string }> = [];
    contactsList.forEach((c: any) => {
      if (c.email && !c.source?.includes("snovio") && !c.source?.includes("proxycurl") && !c.source?.includes("apollo")) {
        const clean = c.email.trim().toLowerCase();
        if (!seen.has(clean)) {
          seen.add(clean);
          list.push({ email: c.email.trim(), sourceUrl: c.source_url });
        }
      }
    });
    return list;
  })();

  const crawlPhones: string[] = (() => {
    const seen = new Set<string>();
    const list: string[] = [];
    if (lead.phone && lead.phone.trim()) {
      seen.add(lead.phone.trim());
      list.push(lead.phone.trim());
    }
    contactsList.forEach((c: any) => {
      const p = (c.phone || c.mobile || "").trim();
      if (p && !seen.has(p)) {
        seen.add(p);
        list.push(p);
      }
    });
    return list;
  })();

  // 2. Snov.io Personal Emails
  const snovioList: any[] = (() => {
    const seen = new Set<string>();
    const list: any[] = [];
    contactsList.forEach((c: any) => {
      if (c.source?.includes("snovio")) {
        const email = (c.email || "").trim().toLowerCase();
        if (email && !seen.has(email)) {
          seen.add(email);
          list.push(c);
        } else if (!email && c.name && !seen.has(c.name.toLowerCase())) {
          seen.add(c.name.toLowerCase());
          list.push(c);
        }
      }
    });
    return list;
  })();

  // 3. Owners & Decision Makers (Proxycurl + named leaders)
  const decisionMakers: any[] = (() => {
    const seen = new Set<string>();
    const list: any[] = [];
    contactsList.forEach((c: any) => {
      const name = (c.name || "").trim();
      const hasValidName = name && name !== "Unknown" && name !== "Unknown contact" && c.contact_type !== "company";
      const isExecutive = c.source?.includes("proxycurl") || c.source?.includes("apollo") || 
        c.title?.toLowerCase().includes("owner") || c.title?.toLowerCase().includes("founder") || 
        c.title?.toLowerCase().includes("chef") || c.title?.toLowerCase().includes("ceo") || 
        c.title?.toLowerCase().includes("president") || c.title?.toLowerCase().includes("manager") ||
        c.title?.toLowerCase().includes("director");
        
      if (hasValidName || isExecutive) {
        const key = (name || c.email || c.linkedin_url || "").trim().toLowerCase();
        if (key && !seen.has(key)) {
          seen.add(key);
          list.push(c);
        }
      }
    });
    return list;
  })();

  return (
    <div className="lead-dossier-page min-h-screen bg-[#141313] text-on-surface text-sm flex flex-col animate-in fade-in duration-500">
      <style>{`
        .lead-dossier-page {
          --background: #141313;
          --foreground: #e5e2e1;
          --primary: #ffffff;
          --secondary: #c6c6cf;
        }
      `}</style>
      
      {/* TopAppBar */}
      <header className="hidden md:flex bg-[#141313]/80 backdrop-blur-md text-on-surface text-xs font-semibold uppercase tracking-wider justify-between items-center w-full px-4 sm:px-6 md:px-8 py-4 sticky top-0 z-40 border-b border-outline-variant/30 shadow-sm">
        <div className="flex items-center gap-2 text-on-surface-variant text-sm lowercase tracking-normal">
          <SidebarTrigger className="lg:hidden text-outline hover:text-primary transition-colors mr-2 p-1 -ml-2" />
          <span className="material-symbols-outlined text-sm">home</span>
          <span className="text-outline">Workspace</span>
          <span className="text-outline mx-1">/</span>
          <span className="text-outline">CRM</span>
          <span className="text-outline mx-1">/</span>
          <Link href="/leads" className="hover:text-primary transition-colors text-outline">
            Leads
          </Link>
          <span className="text-outline mx-1">/</span>
          <span className="text-primary font-medium">{lead.name}</span>
        </div>
        <div className="flex items-center gap-4">
          <button className="text-outline hover:text-primary transition-colors font-medium tracking-wide">Edit</button>
          <button className="text-outline hover:text-primary transition-colors font-medium tracking-wide">Share</button>
          <button className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-container-high transition-colors text-outline hover:text-primary">
            <span className="material-symbols-outlined text-[20px]">more_horiz</span>
          </button>
          <button onClick={() => router.push("/leads")} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-container-high transition-colors text-outline hover:text-primary">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
      </header>

      {/* Page Content */}
      <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-6xl w-full flex flex-col lg:flex-row gap-6 lg:gap-10 mt-4 mx-auto pb-32">
        {/* Main Content Area */}
        <div className="flex-1">
          {/* Header Section */}
          <div className="mb-12 border-b border-outline-variant/30 pb-8">
            <div className="flex items-start justify-between mb-4">
              <h1 className=" text-[30px] leading-[36px] font-bold text-primary tracking-tight font-serif">
                {lead.name}
              </h1>
              <div className="flex items-center gap-3">
                <span className="bg-surface-container-high border border-outline-variant/50 text-primary px-3 py-1 rounded text-sm font-medium flex items-center gap-1.5 shadow-sm">
                  <span className="font-semibold">{lead.grade || "U"}</span> {lead.commercial_score || 0}
                </span>
                <button className="text-outline hover:text-primary transition-colors">
                  <span className="material-symbols-outlined text-[20px]">star</span>
                </button>
              </div>
            </div>
            
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-on-surface-variant mb-6">
              <span className="flex items-center gap-1 whitespace-nowrap">
                <span className="material-symbols-outlined text-[16px]">domain</span>
                <span className="capitalize">{lead.industry || "Uncategorized"}</span>
              </span>
              <span className="text-outline/40">•</span>
              <span className="flex items-center gap-1 whitespace-nowrap">
                <span className="material-symbols-outlined text-[16px]">location_on</span>
                <span>{lead.location || "Location not set"}</span>
              </span>
              {websiteHref && (
                <>
                  <span className="text-outline/40">•</span>
                  <a
                    href={websiteHref}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-primary underline decoration-outline-variant underline-offset-2 transition-colors flex items-center gap-1 min-w-0 max-w-[180px]"
                  >
                    <span className="material-symbols-outlined text-[16px] shrink-0">link</span>
                    <span className="truncate">{lead.website_url?.replace(/^https?:\/\//, "")}</span>
                  </a>
                </>
              )}
            </div>
            
            <div className="flex items-center gap-4">
              <span className="bg-[#2a1a1a] text-[#ff8a65] border border-[#ff8a65]/30 px-3 py-1 rounded-sm text-xs font-bold tracking-wider uppercase flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: `"FILL" 1` }}>local_fire_department</span> {lead.stage || "New"}
              </span>
              {lead.ticket_range && (
                <span className="text-sm font-medium text-primary bg-surface-container px-3 py-1 rounded-sm border border-outline-variant/30">
                  {lead.ticket_range}
                </span>
              )}
            </div>
          </div>

          {/* Editable Content Blocks */}
          <div className="space-y-12">
            {/* Section: Contacts Workspace */}
            <section className="group space-y-6">
              <div className="mb-5"><ContactOptions value={options} onChange={setOptions} disabled={isRefreshing || user?.role === 'viewer'} />{researchMessage && <p role="status" className="mt-2 text-xs text-zinc-400">{researchMessage}</p>}</div>
              {/* Contact Mode Toggle: Crawl (Default) vs Personal vs All */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-[#1a1919] border border-outline-variant/30 rounded-xl p-2 gap-2 mb-6">
                <div className="flex items-center gap-1 bg-[#121214] p-1 rounded-lg border border-outline-variant/20">
                  <button
                    type="button"
                    onClick={() => setContactViewMode('crawl')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                      contactViewMode === 'crawl'
                        ? 'bg-purple-600 text-white shadow-sm'
                        : 'text-outline hover:text-primary hover:bg-white/5'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[15px]">language</span>
                    <span>Crawl Contacts</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-700/60 text-purple-200 uppercase font-bold tracking-wider">Default</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setContactViewMode('personal')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                      contactViewMode === 'personal'
                        ? 'bg-purple-600 text-white shadow-sm'
                        : 'text-outline hover:text-primary hover:bg-white/5'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[15px]">person</span>
                    <span>Personal Contacts</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setContactViewMode('all')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                      contactViewMode === 'all'
                        ? 'bg-surface-container-high text-primary border border-outline-variant/40'
                        : 'text-outline hover:text-primary hover:bg-white/5'
                    }`}
                  >
                    <span>All Contacts</span>
                  </button>
                </div>
                <div className="text-[11px] text-outline font-mono pr-2">
                  {contactViewMode === 'crawl' && `${crawlEmails.length} crawl emails • ${crawlPhones.length} phones`}
                  {contactViewMode === 'personal' && `${snovioList.length} personal emails • ${decisionMakers.length} leaders`}
                  {contactViewMode === 'all' && `${contactsList.length} total contact records`}
                </div>
              </div>

              {/* 1. Website & General Contacts Container */}
              {(contactViewMode === 'crawl' || contactViewMode === 'all') && (
                <div>
                  <div className="flex items-center justify-between mb-3 border-b border-outline-variant/20 pb-2">
                    <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                      <span className="material-symbols-outlined text-[16px]">manage_accounts</span> Website & General Contacts
                      <span className="text-[10px] bg-surface-container px-2 py-0.5 rounded text-outline border border-outline-variant/30 font-sans tracking-normal font-normal">
                        {crawlEmails.length} {crawlEmails.length === 1 ? "email" : "emails"} • {crawlPhones.length} {crawlPhones.length === 1 ? "phone" : "phones"}
                      </span>
                    </h2>
                    <button onClick={handleRefreshResearch} disabled={isRefreshing || user?.role === 'viewer'} className="text-xs text-outline hover:text-primary border border-outline-variant/40 px-2.5 py-1 rounded transition-colors flex items-center gap-1.5 disabled:opacity-50">
                      <span className={`material-symbols-outlined text-[14px] ${isRefreshing ? "animate-spin" : ""}`}>refresh</span>
                      {isRefreshing ? "Refreshing..." : "Refresh contacts"}
                    </button>
                  </div>

                  <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm p-5 space-y-4">
                    {/* Emails */}
                    <div>
                      <div className="text-[10px] font-semibold text-outline uppercase tracking-wider mb-2 flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <span className="material-symbols-outlined text-[14px]">mail</span> Crawled Website Emails
                        </span>
                        <span className="text-[10px] text-outline/60 lowercase">click to copy</span>
                      </div>
                      {crawlEmails.length > 0 ? (
                        <div className="flex flex-wrap gap-2.5">
                          {crawlEmails.map((item, idx) => (
                            <div
                              key={idx}
                              onClick={() => handleCopy(item.email, `crawl-email-${idx}`)}
                              className="group flex items-center gap-2 bg-[#1a1919] hover:bg-[#222121] border border-outline-variant/30 hover:border-[#4ade80]/50 px-3 py-2 rounded-lg cursor-pointer transition-all active:scale-[0.98]"
                              title="Click to copy email"
                            >
                              <span className="material-symbols-outlined text-[#4ade80] text-[16px] shrink-0">mail</span>
                              <span className="text-sm font-serif text-[#4ade80] break-all">{item.email}</span>
                              <span className="material-symbols-outlined text-outline group-hover:text-primary text-[14px] ml-1 shrink-0">
                                {copiedId === `crawl-email-${idx}` ? "check" : "content_copy"}
                              </span>
                              {copiedId === `crawl-email-${idx}` && (
                                <span className="text-[10px] text-[#4ade80] font-semibold animate-in fade-in">Copied!</span>
                              )}
                              {item.sourceUrl && (
                                <a
                                  href={item.sourceUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-[10px] text-outline hover:text-primary border-l border-outline-variant/30 pl-2 ml-1"
                                  title="View Evidence Source"
                                >
                                  Evidence
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-outline italic py-1">No public emails discovered on website.</div>
                      )}
                    </div>

                    {/* Phone Numbers */}
                    <div className="pt-3 border-t border-outline-variant/20">
                      <div className="text-[10px] font-semibold text-outline uppercase tracking-wider mb-2 flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <span className="material-symbols-outlined text-[14px]">call</span> Phone Numbers
                        </span>
                        <span className="text-[10px] text-outline/60 lowercase">click to copy</span>
                      </div>
                      {crawlPhones.length > 0 ? (
                        <div className="flex flex-wrap gap-2.5">
                          {crawlPhones.map((phone, idx) => (
                            <div
                              key={idx}
                              onClick={() => handleCopy(phone, `crawl-phone-${idx}`)}
                              className="group flex items-center gap-2 bg-[#1a1919] hover:bg-[#222121] border border-outline-variant/30 hover:border-[#4ade80]/50 px-3 py-2 rounded-lg cursor-pointer transition-all active:scale-[0.98]"
                              title="Click to copy phone"
                            >
                              <span className="material-symbols-outlined text-[#4ade80] text-[16px] shrink-0">phone</span>
                              <span className="text-sm font-serif text-[#4ade80]">{phone}</span>
                              <span className="material-symbols-outlined text-outline group-hover:text-primary text-[14px] ml-1 shrink-0">
                                {copiedId === `crawl-phone-${idx}` ? "check" : "content_copy"}
                              </span>
                              {copiedId === `crawl-phone-${idx}` && (
                                <span className="text-[10px] text-[#4ade80] font-semibold animate-in fade-in">Copied!</span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-outline italic py-1">No phone numbers captured.</div>
                      )}
                    </div>
                  </div>

                  {contactViewMode === 'crawl' && (snovioList.length > 0 || decisionMakers.length > 0) && (
                    <div className="mt-4 bg-[#18181b] border border-outline-variant/30 rounded-xl p-3.5 flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="material-symbols-outlined text-purple-400 text-[18px]">person</span>
                        <p className="text-xs text-primary font-medium">{snovioList.length + decisionMakers.length} Personal / Decision Maker contacts discovered for this lead.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setContactViewMode('personal')}
                        className="text-xs text-purple-400 hover:text-purple-300 underline font-medium whitespace-nowrap ml-2"
                      >
                        View Personal Contacts →
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* 2. SNOV.IO Personal Emails Container */}
              {(contactViewMode === 'personal' || contactViewMode === 'all') && (
                <div>
                  <div className="flex items-center justify-between mb-3 border-b border-outline-variant/20 pb-2">
                    <h3 className="text-xs font-semibold text-outline uppercase tracking-wider flex items-center gap-2">
                      <span className="material-symbols-outlined text-[14px]">radar</span> SNOV.IO PERSONAL EMAILS
                      <span className="text-[10px] bg-surface-container px-2 py-0.5 rounded text-outline border border-outline-variant/30 font-sans tracking-normal font-normal">
                        {snovioList.length} {snovioList.length === 1 ? "email" : "emails"}
                      </span>
                    </h3>
                  </div>
                  <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm p-5">
                    {snovioList.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {snovioList.map((c: any, idx: number) => (
                          <div
                            key={idx}
                            onClick={() => c.email && handleCopy(c.email, `snovio-${idx}`)}
                            className={`flex items-start justify-between gap-3 bg-[#1a1919] hover:bg-[#222121] border border-outline-variant/30 hover:border-[#4ade80]/50 p-3 rounded-lg transition-all ${c.email ? "cursor-pointer active:scale-[0.98]" : ""}`}
                            title={c.email ? "Click to copy email" : ""}
                          >
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 mb-1 flex-wrap">
                                <span className="material-symbols-outlined text-[#4ade80] text-[16px] shrink-0">alternate_email</span>
                                <span className="text-sm font-serif text-[#4ade80] truncate font-medium break-all">
                                  {c.email || "No email"}
                                </span>
                                {c.verification_status === "verified" && (
                                  <span className="text-[9px] bg-[#4ade80]/15 text-[#4ade80] border border-[#4ade80]/30 px-1.5 py-0.2 rounded font-semibold uppercase shrink-0">
                                    Verified
                                  </span>
                                )}
                              </div>
                              {(c.name || c.title) && (
                                <p className="text-xs text-on-surface-variant truncate pl-6">
                                  {c.name && <span className="text-primary font-medium">{c.name}</span>}
                                  {c.name && c.title && <span className="text-outline mx-1">•</span>}
                                  {c.title && <span className="text-outline">{c.title}</span>}
                                </p>
                              )}
                            </div>
                            {c.email && (
                              <button className="text-outline hover:text-primary shrink-0 pt-0.5" title="Copy">
                                <span className="material-symbols-outlined text-[16px]">
                                  {copiedId === `snovio-${idx}` ? "check" : "content_copy"}
                                </span>
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="bg-surface-container/30 border border-outline-variant/20 rounded-lg p-6 flex flex-col items-center justify-center text-center">
                        <span className="material-symbols-outlined text-outline/50 text-[32px] mb-2">mark_email_unread</span>
                        <span className="text-sm text-on-surface-variant font-medium">Snov.io search yielded no personal emails.</span>
                        <span className="text-xs text-outline mt-1 max-w-sm">Domain query found no personal inboxes or was rate-limited.</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 3. Owner & Decision Makers Container */}
              {(contactViewMode === 'personal' || contactViewMode === 'all') && (
                <div>
                  <div className="flex items-center justify-between mb-3 border-b border-outline-variant/20 pb-2">
                    <h3 className="text-xs font-semibold text-outline uppercase tracking-wider flex items-center gap-2">
                      <span className="material-symbols-outlined text-[14px]">manage_search</span> OWNERS & DECISION MAKERS
                      <span className="text-[10px] bg-surface-container px-2 py-0.5 rounded text-outline border border-outline-variant/30 font-sans tracking-normal font-normal">
                        {decisionMakers.length} {decisionMakers.length === 1 ? "person" : "people"}
                      </span>
                    </h3>
                  </div>
                  <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm p-5">
                    {decisionMakers.length > 0 ? (
                      <div className="divide-y divide-outline-variant/20">
                        {decisionMakers.map((dm: any, idx: number) => (
                          <div key={idx} className="py-3.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="w-10 h-10 rounded-full bg-surface-container-high border border-outline-variant/50 flex items-center justify-center text-xs text-primary font-semibold shrink-0 font-serif">
                                {dm.name ? dm.name.split(" ").map((n: string) => n[0]).join("").substring(0, 2).toUpperCase() : "DM"}
                              </div>
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <h4 className="text-sm font-semibold text-primary truncate font-serif">{dm.name || "Unnamed Executive"}</h4>
                                  {dm.source && (
                                    <span className="text-[9px] bg-surface-container px-1.5 py-0.5 rounded text-outline border border-outline-variant/30 uppercase tracking-wider shrink-0">
                                      {dm.source.includes("proxycurl") ? "Proxycurl" : dm.source.includes("serper") ? "Google Maps" : dm.source}
                                    </span>
                                  )}
                                </div>
                                <p className="text-xs text-on-surface-variant truncate mt-0.5">
                                  {dm.title || "Decision Maker / Executive"}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center flex-wrap gap-2 pl-12 sm:pl-0 font-serif">
                              {dm.email && (
                                <div
                                  onClick={() => handleCopy(dm.email, `dm-email-${idx}`)}
                                  className="flex items-center gap-1 text-xs text-[#4ade80] bg-[#4ade80]/10 border border-[#4ade80]/20 px-2.5 py-1.5 rounded cursor-pointer hover:bg-[#4ade80]/20 transition-colors"
                                  title="Click to copy email"
                                >
                                  <span className="material-symbols-outlined text-[#4ade80] text-[14px]">mail</span>
                                  <span>{dm.email}</span>
                                  <span className="material-symbols-outlined text-outline text-[12px]">
                                    {copiedId === `dm-email-${idx}` ? "check" : "content_copy"}
                                  </span>
                                </div>
                              )}
                              {dm.phone && (
                                <div
                                  onClick={() => handleCopy(dm.phone, `dm-phone-${idx}`)}
                                  className="flex items-center gap-1 text-xs text-[#4ade80] bg-[#4ade80]/10 border border-[#4ade80]/20 px-2.5 py-1.5 rounded cursor-pointer hover:bg-[#4ade80]/20 transition-colors"
                                  title="Click to copy phone"
                                >
                                  <span className="material-symbols-outlined text-[#4ade80] text-[14px]">phone</span>
                                  <span className="text-[#4ade80]">{dm.phone}</span>
                                  <span className="material-symbols-outlined text-outline text-[12px]">
                                    {copiedId === `dm-phone-${idx}` ? "check" : "content_copy"}
                                  </span>
                                </div>
                              )}
                              {dm.linkedin_url && (
                                <a
                                  href={dm.linkedin_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="flex items-center gap-1 text-xs text-[#0a66c2] hover:text-[#388ee7] bg-[#0a66c2]/10 border border-[#0a66c2]/20 px-2.5 py-1.5 rounded transition-colors"
                                  title="View LinkedIn Profile"
                                >
                                  <span className="material-symbols-outlined text-[14px]">work</span>
                                  <span>LinkedIn</span>
                                  <span className="material-symbols-outlined text-[10px]">open_in_new</span>
                                </a>
                              )}
                              {!dm.email && !dm.phone && !dm.linkedin_url && (
                                <span className="text-xs text-outline italic">Profile found, awaiting direct inbox</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="bg-surface-container/30 border border-outline-variant/20 rounded-lg p-6 flex flex-col items-center justify-center text-center">
                        <span className="material-symbols-outlined text-outline/50 text-[32px] mb-2">person_off</span>
                        <span className="text-sm text-on-surface-variant font-medium">Proxycurl search yielded no results.</span>
                        <span className="text-xs text-outline mt-1 max-w-sm">No matches found or rate limit was reached.</span>
                      </div>
                    )}
                  </div>

                  {contactViewMode === 'personal' && (crawlEmails.length > 0 || crawlPhones.length > 0) && (
                    <div className="mt-4 bg-[#18181b] border border-outline-variant/30 rounded-xl p-3.5 flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="material-symbols-outlined text-[#4ade80] text-[18px]">language</span>
                        <p className="text-xs text-primary font-medium">{crawlEmails.length} Crawled Website emails and {crawlPhones.length} phone numbers available.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setContactViewMode('crawl')}
                        className="text-xs text-[#4ade80] hover:text-[#86efac] underline font-medium whitespace-nowrap ml-2"
                      >
                        View Crawl Contacts (Default) →
                      </button>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* Section: Outreach Intelligence */}
                          <section className="group">
                <div className="flex items-center justify-between mb-4 border-b border-outline-variant/20 pb-2">
                  <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">psychology</span> AI Outreach Angle
                  </h2>
                </div>
                <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-5">
                  <p className="text-sm leading-relaxed text-on-surface whitespace-pre-wrap font-serif">{outreachAngle}</p>
                  
                  <div className="mt-6 pt-6 border-t border-outline-variant/20">
                    <button 
                      onClick={handleGenerateEmail} 
                      disabled={isGeneratingEmail || user?.role === 'viewer'}
                      className="bg-primary text-[#141313] hover:bg-primary/90 px-4 py-2 rounded-lg text-xs font-semibold tracking-wider flex items-center gap-2 transition-colors disabled:opacity-50 uppercase shadow-sm active:scale-95"
                    >
                      <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: '"FILL" 1' }}>
                        {isGeneratingEmail ? "hourglass_empty" : "auto_awesome"}
                      </span>
                      {isGeneratingEmail ? "Generating top-tier email..." : "Generate Personalised Outreach Email"}
                    </button>

                    {emailError && (
                      <p className="text-red-400 text-xs mt-2 flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">error</span> {emailError}
                      </p>
                    )}

                    {generatedEmail && (
                      <div className="mt-6 space-y-3">
                        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                          <h3 className="text-[11px] font-semibold text-[#4ade80] uppercase tracking-widest flex items-center gap-2">
                            <span className="material-symbols-outlined text-[16px]">auto_awesome</span> AI-GENERATED OUTREACH EMAIL
                          </h3>
                          <div className="flex items-center flex-wrap gap-2">
                            {parsedEmail.subject && (
                              <button 
                                onClick={() => handleCopy(parsedEmail.subject, "copy_subject")}
                                className="text-xs text-outline hover:text-[#4ade80] border border-outline-variant/40 px-2.5 py-1.5 rounded transition-all flex items-center gap-1.5 active:scale-95 bg-surface-container-low hover:bg-surface-container"
                                title="Copy Subject Line only"
                              >
                                <span className="material-symbols-outlined text-[14px]">
                                  {copiedId === "copy_subject" ? "check" : "title"}
                                </span> 
                                {copiedId === "copy_subject" ? "Subject Copied!" : "Copy Subject"}
                              </button>
                            )}
                            <button 
                              onClick={() => handleCopy(parsedEmail.body || generatedEmail, "copy_body")}
                              className="text-xs text-outline hover:text-[#4ade80] border border-outline-variant/40 px-2.5 py-1.5 rounded transition-all flex items-center gap-1.5 active:scale-95 bg-surface-container-low hover:bg-surface-container"
                              title="Copy Email Body only"
                            >
                              <span className="material-symbols-outlined text-[14px]">
                                {copiedId === "copy_body" ? "check" : "article"}
                              </span> 
                              {copiedId === "copy_body" ? "Body Copied!" : "Copy Body"}
                            </button>
                            <button 
                              onClick={() => handleCopy(generatedEmail, "generated_email")}
                              className="text-xs text-outline hover:text-[#4ade80] border border-outline-variant/40 px-2.5 py-1.5 rounded transition-all flex items-center gap-1.5 active:scale-95 bg-surface-container-low hover:bg-surface-container font-medium"
                              title="Copy Full Email with Subject"
                            >
                              <span className="material-symbols-outlined text-[14px]">
                                {copiedId === "generated_email" ? "check" : "content_copy"}
                              </span> 
                              {copiedId === "generated_email" ? "All Copied!" : "Copy All"}
                            </button>
                          </div>
                        </div>

                        {/* Subject preview box */}
                        {parsedEmail.subject && (
                          <div className="bg-[#1a1919] border border-outline-variant/20 rounded-lg p-3.5 flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <span className="text-[10px] uppercase tracking-wider text-outline font-semibold block mb-0.5">Subject</span>
                              <span className="text-sm font-medium text-primary font-serif">{parsedEmail.subject}</span>
                            </div>
                            <button
                              onClick={() => handleCopy(parsedEmail.subject, "copy_subject_inline")}
                              className="text-outline hover:text-[#4ade80] p-1.5 rounded hover:bg-surface-container shrink-0 transition-colors"
                              title="Copy Subject"
                            >
                              <span className="material-symbols-outlined text-[16px]">
                                {copiedId === "copy_subject_inline" ? "check" : "content_copy"}
                              </span>
                            </button>
                          </div>
                        )}

                        {/* Email Body preview box */}
                        <div className="bg-[#1a1919] border border-outline-variant/20 rounded-lg p-5">
                          <p className="text-sm leading-relaxed text-on-surface whitespace-pre-wrap font-serif">
                            {parsedEmail.body || generatedEmail}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </section>

            {/* Section: Devacia Opportunity */}
            <section className="group">
              <div className="flex items-center justify-between mb-4 border-b border-outline-variant/20 pb-2">
                <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">lightbulb</span> Devacia Opportunity
                </h2>
              </div>
              <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-5">
                <p className="text-base font-medium text-primary mb-3 font-serif">{recommendedOffer}</p>
                <p className="text-sm text-on-surface-variant">Estimated value: <span className="font-medium text-primary">{lead.ticket_range || "Pending"}</span></p>
              </div>
            </section>

            {/* Section: Why we should contact them */}
            <section className="group">
              <div className="flex items-center justify-between mb-4 border-b border-outline-variant/20 pb-2">
                <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">report_problem</span> Why we should contact them
                </h2>
              </div>
              <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-5">
                <p className="text-sm leading-relaxed text-[#fbbf24] whitespace-pre-wrap font-serif">{whyContact}</p>
              </div>
            </section>

            {/* Section: Evidence */}
            <section className="group">
              <div className="flex items-center justify-between mb-4 border-b border-outline-variant/20 pb-2">
                <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">inventory_2</span> Evidence
                </h2>
              </div>
              <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-5">
                <p className="text-sm leading-relaxed text-on-surface whitespace-pre-wrap font-serif">{evidenceSummary}</p>
              </div>
            </section>

            {/* Section: Social Media */}
            <section className="group">
              <div className="flex items-center justify-between mb-4 border-b border-outline-variant/20 pb-2">
                <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">public</span> Social Media
                </h2>
              </div>
              <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-5">
                {socialProfiles.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {socialProfiles.map((p: any, idx: number) => (
                      <a key={idx} href={p.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 border border-outline-variant/30 bg-surface-container px-3 py-1.5 text-xs capitalize text-primary hover:bg-surface-container-highest transition-colors rounded">
                        <span className="material-symbols-outlined text-[14px]">open_in_new</span> {p.platform}
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-on-surface-variant italic font-serif">No public company social profiles were found.</p>
                )}
              </div>
            </section>

            {/* Section: Digital Gaps */}
            <section className="group">
              <div className="flex items-center justify-between mb-4 border-b border-outline-variant/20 pb-2">
                <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">speed</span> Website Performance & Gaps
                </h2>
              </div>
              
              <div className="mb-6">
                {digitalGaps.length > 0 ? (
                  <div className="space-y-2">
                    {digitalGaps.map((gap: string, idx: number) => (
                      <div key={idx} className="flex items-center gap-2 text-sm text-[#fbbf24] font-serif">
                        <span className="material-symbols-outlined text-[16px]">warning</span> {gap}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-[#4ade80] font-serif">
                    <span className="material-symbols-outlined text-[16px]">check_circle</span> No material digital gaps detected
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-4 flex flex-col items-center justify-center text-center">
                  <div className="relative w-16 h-16 mb-2">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path className="text-surface-container-highest stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeWidth="3"></path>
                      <path className="text-primary stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeLinecap="round" strokeDasharray={`${metrics.mobile || 0}, 100`} strokeWidth="3"></path>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-primary font-serif">{metrics.mobile || "—"}</div>
                  </div>
                  <span className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Mobile</span>
                </div>
                
                <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-4 flex flex-col items-center justify-center text-center">
                  <div className="relative w-16 h-16 mb-2">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path className="text-surface-container-highest stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeWidth="3"></path>
                      <path className="text-primary stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeLinecap="round" strokeDasharray={`${metrics.desktop || 0}, 100`} strokeWidth="3"></path>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-primary font-serif">{metrics.desktop || "—"}</div>
                  </div>
                  <span className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Desktop</span>
                </div>

                <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-4 flex flex-col items-center justify-center text-center">
                  <div className="relative w-16 h-16 mb-2">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path className="text-surface-container-highest stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeWidth="3"></path>
                      <path className="text-primary stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeLinecap="round" strokeDasharray={`${metrics.ux || 0}, 100`} strokeWidth="3"></path>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-primary font-serif">{metrics.ux || "—"}</div>
                  </div>
                  <span className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">UX</span>
                </div>
                
                <div className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-4 flex flex-col items-center justify-center text-center">
                  <div className="relative w-16 h-16 mb-2">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path className="text-surface-container-highest stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeWidth="3"></path>
                      <path className="text-primary stroke-current" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeLinecap="round" strokeDasharray={`${metrics.conversion || 0}, 100`} strokeWidth="3"></path>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-primary font-serif">{metrics.conversion || "—"}</div>
                  </div>
                  <span className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Conversion</span>
                </div>
              </div>
            </section>
          </div>
        </div>

        {/* Right Sidebar (Properties/Metadata) */}
        <div className="w-full lg:w-[320px] shrink-0">
          <div className="sticky top-[80px] bg-surface-container-low/50 border border-outline-variant/30 rounded-xl p-5 space-y-6">
            <h3 className="text-xs font-semibold text-on-surface-variant uppercase tracking-widest border-b border-outline-variant/30 pb-2">Properties</h3>
            <div className="space-y-4">
              
              <div className="group flex items-start flex-col gap-1">
                <label className="text-xs text-outline flex items-center gap-1.5 w-24 shrink-0"><span className="material-symbols-outlined text-[14px]">person</span> Owner</label>
                <div className="flex items-center gap-2 w-full p-1.5 -ml-1.5 rounded hover:bg-surface-container cursor-pointer transition-colors">
                  <div className="w-5 h-5 rounded-full bg-surface-container-highest flex items-center justify-center text-[10px] text-primary font-medium">
                    {lead.owner_name ? lead.owner_name.substring(0, 2).toUpperCase() : "U"}
                  </div>
                  <span className="text-sm text-primary">{lead.owner_name || "Unassigned"}</span>
                </div>
              </div>

              <div className="group flex items-start flex-col gap-1">
                <label className="text-xs text-outline flex items-center gap-1.5 w-24 shrink-0"><span className="material-symbols-outlined text-[14px]">phone</span> Phone</label>
                <div className="w-full p-1.5 -ml-1.5 rounded hover:bg-surface-container cursor-pointer transition-colors font-serif">
                  {lead.phone ? (
                    <span className="text-sm text-[#4ade80]">{lead.phone}</span>
                  ) : (
                    <span className="text-sm text-outline italic">Empty</span>
                  )}
                </div>
              </div>

              <div className="group flex items-start flex-col gap-1">
                <label className="text-xs text-outline flex items-center gap-1.5 w-24 shrink-0"><span className="material-symbols-outlined text-[14px]">domain</span> Industry</label>
                <div className="w-full p-1.5 -ml-1.5 rounded hover:bg-surface-container cursor-pointer transition-colors">
                  {lead.industry ? (
                    <span className="text-sm text-primary bg-surface-container-high px-2 py-0.5 rounded border border-outline-variant/30">{lead.industry}</span>
                  ) : (
                    <span className="text-sm text-outline italic">Empty</span>
                  )}
                </div>
              </div>

              <div className="group flex items-start flex-col gap-1 mt-4 pt-4 border-t border-outline-variant/20">
                <div className="w-full p-1.5 -ml-1.5 rounded hover:bg-surface-container cursor-pointer transition-colors flex items-center gap-2 text-outline hover:text-primary">
                  <span className="material-symbols-outlined text-[16px]">add</span>
                  <span className="text-sm">Add a property</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}


