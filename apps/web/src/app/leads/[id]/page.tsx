
"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { SidebarTrigger } from "@/components/ui/sidebar";

export default function LeadDossier() {
  const { id } = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLead() {
      try {
        const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
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
            {/* Section: Decision Makers */}
            <section className="group">
              <div className="flex items-center justify-between mb-4 border-b border-outline-variant/20 pb-2">
                <h2 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">manage_accounts</span> Decision Makers & Contact Data
                </h2>
                <button className="text-xs text-outline hover:text-primary border border-outline-variant/40 px-2 py-1 rounded transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">refresh</span> Refresh contact research
                </button>
              </div>
              <div className="grid grid-cols-1 gap-4">
                {lead.contacts && lead.contacts.length > 0 ? (
                  lead.contacts.map((c: any, idx: number) => (
                    <div key={idx} className="bg-surface-container-low border border-outline-variant/40 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 p-5 hover:border-outline-variant transition-colors relative group/card">
                      <button className="absolute top-4 right-4 text-outline hover:text-primary opacity-0 group-hover/card:opacity-100 transition-opacity">
                        <span className="material-symbols-outlined text-[18px]">edit</span>
                      </button>
                      <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-medium border border-outline-variant/50">
                          {c.name ? c.name.split(" ").map((n: string) => n[0]).join("").substring(0, 2).toUpperCase() : "?"}
                        </div>
                        <div className="w-full">
                          <div className="flex items-center justify-between mb-1">
                            <h3 className="text-base font-medium text-primary font-serif">{c.name || "Unknown"}</h3>
                            {c.verification_status === "verified" && <span className="text-xs text-[#4ade80]">Verified</span>}
                          </div>
                          <p className="text-sm text-on-surface-variant flex items-center flex-wrap gap-2 mb-3">
                            {c.title || (c.contact_type === "company" ? "Website contact" : "Decision maker")}
                            {c.source && (
                              <>
                                <span className="text-outline">|</span>
                                <span className="text-xs bg-surface-container px-1.5 py-0.5 rounded text-outline border border-outline-variant/30">{c.source}</span>
                              </>
                            )}
                            {c.source_url && (
                              <a className="text-xs text-primary/80 hover:text-primary flex items-center shrink-0 gap-1 ml-1" href={c.source_url} target="_blank" rel="noreferrer">
                                <span className="material-symbols-outlined text-[12px]">open_in_new</span> Evidence
                              </a>
                            )}
                          </p>
                          <div className="space-y-2 mt-4 pt-4 border-t border-outline-variant/20 font-serif w-full">
                            <div className="flex items-center gap-3 text-sm">
                              <span className={`material-symbols-outlined shrink-0 text-[16px] ${c.email ? "text-[#4ade80]" : "text-outline"}`}>mail</span>
                              <span className={c.email ? "text-[#4ade80] break-all" : "text-outline italic"}>{c.email || "Email not found"}</span>
                            </div>
                            <div className="flex items-center gap-3 text-sm">
                              <span className={`material-symbols-outlined shrink-0 text-[16px] ${c.phone ? "text-[#4ade80]" : "text-outline"}`}>phone</span>
                              <span className={c.phone ? "text-[#4ade80] break-words" : "text-outline italic"}>{c.phone || "Phone not found"}</span>
                            </div>
                            <div className="flex items-center gap-3 text-sm">
                              <span className={`material-symbols-outlined shrink-0 text-[16px] ${c.linkedin_url ? "text-[#4ade80]" : "text-outline"}`}>work</span>
                              {c.linkedin_url ? (
                                <a href={c.linkedin_url} target="_blank" rel="noreferrer" className="text-[#4ade80] hover:underline break-all">LinkedIn</a>
                              ) : (
                                <span className="text-outline italic">LinkedIn not found</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-on-surface-variant italic py-4">No decision makers captured yet.</div>
                )}
              </div>
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


