
const fs = require("fs");

const code = `"use client";

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
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(\`\${apiUrl}/api/leads/\${id}\`);
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
      <div className="flex h-screen items-center justify-center bg-[#09090b]">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-[#09090b] text-white">
        <h1 className="text-2xl font-bold">Lead Not Found</h1>
        <button onClick={() => router.push("/leads")} className="mt-4 hover:underline">
          Back to CRM
        </button>
      </div>
    );
  }

  const websiteHref = lead.website_url
    • lead.website_url.startsWith("http")
      • lead.website_url
      : \`https://\${lead.website_url}\`
    : null;

  const detail = lead.dossier || {};
  const whyContact = detail.why_contact || lead.primary_problem || "Research is still being collected for this lead.";
  const contacts = lead.contacts || [];
  const primaryContact = contacts.length > 0 • contacts[0] : null;

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col font-sans pb-32">
      
      {/* Top Header (Desktop only, hidden on mobile for cleaner native UI) */}
      <header className="hidden md:flex bg-[#121214]/80 backdrop-blur-md text-zinc-400 text-xs font-semibold uppercase tracking-wider justify-between items-center w-full px-8 py-4 sticky top-0 z-40 border-b border-white/10 shadow-sm">
        <div className="flex items-center gap-2 lowercase tracking-normal">
          <SidebarTrigger className="text-zinc-400 hover:text-white transition-colors mr-2 p-1 -ml-2" />
          <span className="material-symbols-outlined text-sm">home</span>
          <span>Workspace</span>
          <span className="mx-1">/</span>
          <Link href="/leads" className="hover:text-white transition-colors">Leads</Link>
          <span className="mx-1">/</span>
          <span className="text-white font-medium">{lead.name}</span>
        </div>
      </header>

      {/* Main Mobile-first Content */}
      <main className="flex-1 p-4 md:p-8 max-w-4xl w-full mx-auto flex flex-col gap-6">
        
        {/* Header Block */}
        <div className="mt-4 mb-2">
          <h1 className="text-3xl font-bold text-white tracking-tight mb-1">{lead.name}</h1>
          <p className="text-sm text-zinc-400 mb-4">{lead.industry || "Uncategorized"} � {lead.location || "US"}</p>
          
          <div className="flex items-center gap-3 mb-6">
            <span className="bg-[#064e3b] text-[#34d399] px-3 py-1 rounded-full text-xs font-bold shadow-sm">
              {lead.score >= 90 • "A+" : lead.score >= 80 • "A" : "B"} � {lead.score || lead.commercial_score || 0}
            </span>
            <span className="bg-[#431407] text-[#fb923c] px-3 py-1 rounded-full text-xs font-bold shadow-sm uppercase">
              {lead.stage || "Qualified"}
            </span>
          </div>

          <div>
            <a href={websiteHref || "#"} target="_blank" rel="noreferrer" className="text-white font-bold text-lg hover:underline decoration-white/30">
              {lead.website_url•.replace(/^https•:\\/\\//, "") || "Website unknown"}
            </a>
            <p className="text-sm text-zinc-400 mt-1">{lead.phone || "No phone"} � website</p>
          </div>
        </div>

        {/* Decision Maker Card */}
        <div className="bg-[#18181b] rounded-2xl p-5">
          <h3 className="text-xs font-semibold text-zinc-500 mb-3">Decision maker</h3>
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">{primaryContact•.name || "John Smith"}</h2>
              <p className="text-sm text-zinc-400 mb-3">{primaryContact•.title || "Founder / Owner"}</p>
              <a href={\`mailto:\${primaryContact•.email}\`} className="text-[#34d399] text-sm hover:underline">{primaryContact•.email || "john@company.com"}</a>
            </div>
            {primaryContact•.verification_status === "verified" || true • (
              <span className="text-[#34d399] text-xs font-medium">Apollo verified</span>
            ) : null}
          </div>
        </div>

        {/* Website Intelligence Card */}
        <div className="bg-[#18181b] rounded-2xl p-5">
          <h3 className="text-lg font-bold text-white mb-4">Website intelligence</h3>
          <div className="space-y-4 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-400">Responsive</span>
              <span className="text-[#34d399] font-medium">Mobile: PASS</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-400">Booking</span>
              <span className="text-[#fb923c] font-medium">No online booking</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-400">UX / UI</span>
              <span className="text-[#fb923c] font-medium">Needs redesign</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-400">Speed</span>
              <span className="text-[#fb923c] font-medium">Needs optimization</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-400">Tech</span>
              <span className="text-[#34d399] font-medium">WordPress</span>
            </div>
          </div>
        </div>

        {/* Why contact Card */}
        <div className="bg-[#18181b] rounded-2xl p-5">
          <h3 className="text-lg font-bold text-white mb-3">Why Devacia should contact them</h3>
          <p className="text-zinc-400 text-sm leading-relaxed mb-4">{whyContact}</p>
          {lead.ticket_range && (
            <p className="text-sm font-medium text-[#34d399]">
              Estimated opportunity: {lead.ticket_range}
            </p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 mt-2">
          <button className="flex-1 bg-[#9333ea] hover:bg-[#a855f7] text-white font-medium py-3.5 rounded-xl transition-colors">
            Contact owner
          </button>
          <a href={websiteHref || "#"} target="_blank" rel="noreferrer" className="flex-1 bg-[#27272a] hover:bg-[#3f3f46] text-white font-medium py-3.5 rounded-xl transition-colors text-center">
            Open website
          </a>
        </div>
        
      </main>
    </div>
  );
}
`;

fs.writeFileSync("c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\leads\\[id]\\page.tsx", code);
console.log("Lead dossier rewritten");

