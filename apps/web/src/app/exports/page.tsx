"use client";

import { useState, useEffect } from "react";
import { Download, FileSpreadsheet, FileText, Code2, Check, Loader2, Database, Rocket } from "lucide-react";
import { exportLeads, exportCampaignsWithLeads, type LeadExportData, type CampaignExportData } from "@/lib/exportUtils";
import { fetchAllCrmLeads } from "@/lib/fetchAllCrmLeads";

export default function ExportsPage() {
  const [exporting, setExporting] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [leads, setLeads] = useState<LeadExportData[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignExportData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [allLeads, campaignsRes] = await Promise.all([
          fetchAllCrmLeads({ status: 'active' }),
          fetch(`/api/campaigns?status=active`),
        ]);

        setLeads(allLeads);
        if (campaignsRes.ok) {
          const campaignsData = (await campaignsRes.json()) as CampaignExportData[];
          setCampaigns(campaignsData || []);
        }
      } catch (err) {
        console.error("Failed to load export data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleExport = async (type: string, dataset: "leads" | "campaigns", format: "xlsx" | "csv" | "json") => {
    try {
      setExporting(type);
      if (dataset === "leads") {
        exportLeads(leads, format, `devacia-leads-${leads.length}`);
      } else {
        exportCampaignsWithLeads({
          campaigns,
          leads,
          format,
          filenamePrefix: `devacia-all-campaign-leads-${leads.length}`,
        });
      }
      setSuccess(type);
      setTimeout(() => setSuccess(null), 2500);
    } catch (e) {
      console.error("Export failed:", e);
    } finally {
      setExporting(null);
    }
  };

  const qualifiedLeads = leads.filter((l) => (l.stage || "").toLowerCase() === "qualified");

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col font-sans pb-32">
      <main className="flex-1 p-4 md:p-8 max-w-4xl w-full mx-auto flex flex-col">
        {/* Header */}
        <div className="mt-4 mb-8">
          <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight mb-2">
            Data Exports Hub
          </h1>
          <p className="text-sm text-zinc-400">
            Export enriched leads and campaign datasets into Excel spreadsheets, CSVs, or JSON files.
          </p>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-zinc-400 font-medium">Total CRM Leads</div>
              <div className="text-xl font-bold text-white">
                {loading ? "..." : leads.length}
              </div>
            </div>
          </div>

          <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Check className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-zinc-400 font-medium">Qualified Leads</div>
              <div className="text-xl font-bold text-emerald-400">
                {loading ? "..." : qualifiedLeads.length}
              </div>
            </div>
          </div>

          <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Rocket className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-zinc-400 font-medium">Active Campaigns</div>
              <div className="text-xl font-bold text-white">
                {loading ? "..." : campaigns.length}
              </div>
            </div>
          </div>
        </div>

        {/* Section 1: Leads Exports */}
        <div className="mb-8">
          <h2 className="text-sm uppercase tracking-wider font-semibold text-zinc-400 mb-4 flex items-center gap-2">
            <Database className="w-4 h-4 text-purple-400" />
            Leads CRM Exports
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Excel (.xlsx) */}
            <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition">
              <div>
                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-3">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base mb-1 flex items-center gap-2">
                  Excel Workbook
                  <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded">
                    .xlsx
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                  Full formatted spreadsheet with auto-calculated column widths and styled sheets.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleExport("leads-xlsx", "leads", "xlsx")}
                disabled={loading || exporting !== null}
                className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 rounded-lg transition"
              >
                {exporting === "leads-xlsx" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : success === "leads-xlsx" ? (
                  <>
                    <Check className="w-4 h-4" /> Downloaded
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Export Excel ({leads.length})
                  </>
                )}
              </button>
            </div>

            {/* CSV (.csv) */}
            <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition">
              <div>
                <div className="w-9 h-9 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center mb-3">
                  <FileText className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base mb-1 flex items-center gap-2">
                  CSV Spreadsheet
                  <span className="text-xs font-mono text-blue-400 bg-blue-950/60 px-1.5 py-0.5 rounded">
                    .csv
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                  UTF-8 BOM formatted for instant import into Google Sheets, Excel, or Notion.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleExport("leads-csv", "leads", "csv")}
                disabled={loading || exporting !== null}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 rounded-lg transition"
              >
                {exporting === "leads-csv" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : success === "leads-csv" ? (
                  <>
                    <Check className="w-4 h-4" /> Downloaded
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Export CSV ({leads.length})
                  </>
                )}
              </button>
            </div>

            {/* JSON (.json) */}
            <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition">
              <div>
                <div className="w-9 h-9 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center mb-3">
                  <Code2 className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base mb-1 flex items-center gap-2">
                  JSON Raw Data
                  <span className="text-xs font-mono text-purple-400 bg-purple-950/60 px-1.5 py-0.5 rounded">
                    .json
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                  Complete structured objects with contacts, phone numbers, and AI dossiers.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleExport("leads-json", "leads", "json")}
                disabled={loading || exporting !== null}
                className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 rounded-lg transition"
              >
                {exporting === "leads-json" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : success === "leads-json" ? (
                  <>
                    <Check className="w-4 h-4" /> Downloaded
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Export JSON ({leads.length})
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Section 2: Campaigns Exports */}
        <div className="mb-8">
          <h2 className="text-sm uppercase tracking-wider font-semibold text-zinc-400 mb-4 flex items-center gap-2">
            <Rocket className="w-4 h-4 text-purple-400" />
            Campaigns Exports
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Excel (.xlsx) */}
            <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition">
              <div>
                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-3">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base mb-1 flex items-center gap-2">
                  Campaigns Excel
                  <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded">
                    .xlsx
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                  Complete campaign pipelines with targets, geos, and execution statuses.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleExport("campaigns-xlsx", "campaigns", "xlsx")}
                disabled={loading || exporting !== null}
                className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 rounded-lg transition"
              >
                {exporting === "campaigns-xlsx" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : success === "campaigns-xlsx" ? (
                  <>
                    <Check className="w-4 h-4" /> Downloaded
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Export Excel ({campaigns.length})
                  </>
                )}
              </button>
            </div>

            {/* CSV (.csv) */}
            <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition">
              <div>
                <div className="w-9 h-9 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center mb-3">
                  <FileText className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base mb-1 flex items-center gap-2">
                  Campaigns CSV
                  <span className="text-xs font-mono text-blue-400 bg-blue-950/60 px-1.5 py-0.5 rounded">
                    .csv
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                  Tabular CSV of all campaign pipelines for reporting and spreadsheets.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleExport("campaigns-csv", "campaigns", "csv")}
                disabled={loading || exporting !== null}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 rounded-lg transition"
              >
                {exporting === "campaigns-csv" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : success === "campaigns-csv" ? (
                  <>
                    <Check className="w-4 h-4" /> Downloaded
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Export CSV ({campaigns.length})
                  </>
                )}
              </button>
            </div>

            {/* JSON (.json) */}
            <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition">
              <div>
                <div className="w-9 h-9 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center mb-3">
                  <Code2 className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base mb-1 flex items-center gap-2">
                  Campaigns JSON
                  <span className="text-xs font-mono text-purple-400 bg-purple-950/60 px-1.5 py-0.5 rounded">
                    .json
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
                  Raw campaign records for external dashboards or database imports.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleExport("campaigns-json", "campaigns", "json")}
                disabled={loading || exporting !== null}
                className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 rounded-lg transition"
              >
                {exporting === "campaigns-json" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : success === "campaigns-json" ? (
                  <>
                    <Check className="w-4 h-4" /> Downloaded
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Export JSON ({campaigns.length})
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Columns Included Reference */}
        <div className="bg-[#121214] border border-zinc-800/80 rounded-xl p-5">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
            Exported Data Fields
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-zinc-400">
            <div>
              <div className="text-white font-medium mb-1.5">Leads CRM Schema:</div>
              <p className="leading-relaxed">
                Lead ID, Company Name, Website URL, Industry, Location, City, State, Country, Commercial Score, Grade, Stage, Campaign, Primary Contact (Name, Title, Email, Phone, LinkedIn), All Emails, All Phones, AI Outreach Angle, Recommended Offer, Created Date.
              </p>
            </div>
            <div>
              <div className="text-white font-medium mb-1.5">Campaigns Schema:</div>
              <p className="leading-relaxed">
                Campaign ID, Campaign Name, Target Geo, City, Country, Industry / Niche, Target Leads, Status, Created Date.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
