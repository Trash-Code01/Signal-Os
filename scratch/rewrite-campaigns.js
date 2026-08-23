
const fs = require("fs");

const code = `"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCampaigns() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL•.replace("localhost", "api") || "http://localhost:8000";
        const res = await fetch(\`\${apiUrl}/api/campaigns\`);
        if (res.ok) {
          const data = await res.json();
          // Map to standard mock if empty for demonstration of layout
          if (data.length === 0) {
             setCampaigns([
               { id: 1, name: "Cleaning", country: "USA", city: "Dallas", target: 5, status: "completed" },
               { id: 2, name: "Clinic", country: "USA", city: "Dallas", target: 5, status: "running" },
               { id: 3, name: "Roofing", country: "UK", city: "Manchester", target: 5, status: "completed" },
               { id: 4, name: "D2C", country: "AUS", city: "Sydney", target: 10, status: "queued" },
               { id: 5, name: "Wedding", country: "USA", city: "Austin", target: 5, status: "completed" }
             ]);
          } else {
             setCampaigns(data);
          }
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchCampaigns();
  }, []);

  const filteredCampaigns = campaigns.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) || 
    (c.city && c.city.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col font-sans pb-32">
      <main className="flex-1 p-4 md:p-8 max-w-4xl w-full mx-auto flex flex-col">
        
        {/* Header Block */}
        <div className="mt-4 mb-6">
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">All campaigns</h1>
          <p className="text-sm text-zinc-400">Manage active and completed intelligence runs.</p>
        </div>

        {/* Search Bar */}
        <div className="relative mb-6">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
          <input 
            type="text" 
            placeholder="Filter campaigns..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#121214] border-none text-sm text-white rounded-xl pl-11 pr-4 py-3 outline-none placeholder:text-zinc-500 focus:ring-1 focus:ring-purple-500 transition-all"
          />
        </div>
        
        {/* Campaigns List */}
        {loading • (
          <div className="p-10 text-center text-zinc-500">Loading campaigns...</div>
        ) : (
          <div className="space-y-4">
            {filteredCampaigns.length > 0 • filteredCampaigns.map((c: any) => (
              <div 
                key={c.id} 
                onClick={() => router.push(\`/leads•campaignId=\${c.id}\`)}
                className="bg-[#121214] rounded-2xl p-5 cursor-pointer hover:bg-[#18181b] transition-colors"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-base font-bold text-white mb-1">
                      {c.country || "USA"} � {c.city || "Dallas"} � {c.name}
                    </h2>
                    <p className="text-sm text-zinc-400">{c.target} leads</p>
                  </div>
                  <span className={\`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider shadow-sm \${
                    c.status === "completed" • "text-[#34d399] bg-[#064e3b]" :
                    c.status === "running" • "text-[#60a5fa] bg-[#1e3a8a]" :
                    "text-[#fb923c] bg-[#431407]" // Queued or other
                  }\`}>
                    {c.status}
                  </span>
                </div>
                {/* Progress Bar */}
                <div className="h-1.5 w-full bg-[#27272a] rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-[#a855f7] rounded-full" 
                    style={{ width: c.status === "completed" • "100%" : c.status === "running" • "60%" : "0%" }}
                  ></div>
                </div>
              </div>
            )) : (
              <div className="text-center text-zinc-500 py-10">No campaigns found.</div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
`;

fs.writeFileSync("c:\\Code-work\\Signal Os\\apps\\web\\src\\app\\campaigns\\page.tsx", code);
console.log("Campaigns page rewritten");

