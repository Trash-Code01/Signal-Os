
const fs = require("fs");

const code = `"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";

export default function NewCampaignPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(\`\${apiUrl}/api/campaigns\`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "USA Dallas Roofing",
          country: "USA",
          state_province: "Texas",
          cities: ["Dallas"],
          industry: "roofing",
          target_quantity: 500,
          min_quality_score: 75,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        router.push(\`/jobsâ€¢campaign=\${data.campaign_id}\`);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  const steps = [
    { num: 1, title: "Geography", desc: "Country • state • cities" },
    { num: 2, title: "Industry", desc: "Industry + subcategory" },
    { num: 3, title: "Targets", desc: "Lead quantity + minimum score" },
    { num: 4, title: "Research", desc: "Sources + enrichment" },
  ];

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col font-sans pb-32">
      <main className="flex-1 p-4 md:p-8 max-w-2xl w-full mx-auto flex flex-col">
        
        {/* Header Block */}
        <div className="mt-4 mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Create campaign</h1>
          <p className="text-sm text-zinc-400">Configure the intelligence pipeline.</p>
        </div>

        {/* Stacked Steps */}
        <div className="space-y-4 mb-8">
          {steps.map((s) => (
            <div key={s.num} className="bg-[#121214] rounded-2xl p-5 flex items-center gap-5 cursor-pointer hover:bg-[#18181b] transition-colors">
              <div className="w-10 h-10 rounded-full bg-[#a855f7] text-white flex items-center justify-center font-bold text-sm shrink-0">
                {s.num}
              </div>
              <div>
                <h2 className="text-base font-bold text-white mb-1">{s.title}</h2>
                <p className="text-sm text-zinc-400">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Summary Card */}
        <div className="bg-[#18181b] rounded-2xl p-5 mb-4">
          <h2 className="text-base font-bold text-white">USA • Texas • Dallas</h2>
        </div>

        {/* Start Button */}
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full bg-[#a855f7] hover:bg-[#9333ea] disabled:opacity-50 text-white py-4 rounded-2xl text-base font-bold transition-colors flex items-center justify-center gap-2"
        >
          {loading â€¢ (
            <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          ) : (
            <>Start campaign <ArrowRight className="w-5 h-5" /></>
          )}
        </button>

      </main>
    </div>
  );
}
`;

fs.writeFileSync("c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\campaigns\\new\\page.tsx", code);
console.log("Create Campaign rewritten");

