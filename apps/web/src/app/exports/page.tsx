"use client";

import { useState } from "react";

export default function ExportsPage() {
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = (type: string) => {
    setExporting(type);
    setTimeout(() => setExporting(null), 2000);
  };

  const options = [
    { id: "sheets", title: "Google Sheets", leads: "87 leads", status: "Ready", statusColor: "text-[#34d399]" },
    { id: "csv", title: "CSV", leads: "87 leads", status: "Ready", statusColor: "text-[#34d399]" },
    { id: "webhook", title: "CRM webhook", leads: "30 qualified", status: "Connected", statusColor: "text-[#34d399]" },
    { id: "json", title: "JSON", leads: "87 leads", status: "Ready", statusColor: "text-[#34d399]" },
  ];

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col font-sans pb-32">
      <main className="flex-1 p-4 md:p-8 max-w-2xl w-full mx-auto flex flex-col">
        
        {/* Header */}
        <div className="mt-4 mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Exports</h1>
          <p className="text-sm text-zinc-400">Send clean lead datasets to your sales workflow.</p>
        </div>

        {/* Export Options */}
        <div className="space-y-4 mb-8">
          {options.map((opt) => (
            <div key={opt.id} className="bg-[#121214] rounded-2xl p-5 flex items-center justify-between hover:bg-[#18181b] transition-colors">
              <div>
                <h2 className="text-lg font-bold text-white mb-1">{opt.title}</h2>
                <p className="text-sm text-zinc-400">{opt.leads}</p>
              </div>
              <div className="flex flex-col items-end gap-3">
                <span className={`text-xs font-semibold ${opt.statusColor}`}>{opt.status}</span>
                <button 
                  onClick={() => handleExport(opt.id)}
                  disabled={exporting !== null}
                  className="bg-[#a855f7] hover:bg-[#9333ea] disabled:opacity-50 text-white text-sm font-semibold px-6 py-2 rounded-full transition-colors w-28 text-center"
                >
                  {exporting === opt.id ? "..." : "Export"}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Columns Included */}
        <div className="bg-[#18181b] rounded-2xl p-6">
          <h2 className="text-sm font-bold text-white mb-4">Columns included</h2>
          <div className="space-y-3 text-sm text-zinc-400 leading-relaxed font-serif">
            <p>Company ï¿½ Location ï¿½ Website ï¿½ Audit ï¿½ Contact</p>
            <p>Decision maker ï¿½ Email ï¿½ Phone ï¿½ Social ï¿½ Score</p>
            <p>Evidence ï¿½ Opportunity ï¿½ Outreach angle</p>
          </div>
        </div>

      </main>
    </div>
  );
}
