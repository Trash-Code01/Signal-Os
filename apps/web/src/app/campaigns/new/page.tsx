'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const INDUSTRIES = [
  { value: 'roofing', label: 'Roofing', sub: ['Residential', 'Commercial', 'Storm Damage'] },
  { value: 'hvac', label: 'HVAC', sub: ['Residential', 'Commercial'] },
  { value: 'cleaning', label: 'Cleaning', sub: ['Residential', 'Commercial', 'Industrial'] },
  { value: 'restaurant', label: 'Restaurant', sub: ['Fine Dining', 'Fast Casual', 'Cafe'] },
  { value: 'clinic', label: 'Clinic / Medical', sub: ['Dental', 'Physiotherapy', 'GP', 'Specialist'] },
  { value: 'real_estate', label: 'Real Estate', sub: ['Residential', 'Commercial'] },
  { value: 'd2c', label: 'D2C / Ecommerce', sub: ['Fashion', 'Beauty', 'Health', 'Food'] },
  { value: 'wedding', label: 'Wedding Photography', sub: ['Photography', 'Videography'] },
];

const RESEARCH_DEPTHS = [
  { value: 'basic', label: 'Basic', desc: 'Business data + phone + website check only' },
  { value: 'standard', label: 'Standard', desc: '+ CTA audit, contact extraction, social media' },
  { value: 'deep', label: 'Deep', desc: '+ Full Playwright crawl, UX audit, AI SDR analysis, decision-maker enrichment' },
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    country: 'USA',
    state: 'Texas',
    cities: 'Dallas',
    industry: 'roofing',
    sub_industry: '',
    raw_target: 500,
    min_score: 75,
    a_plus_target: 50,
    a_target: 50,
    research_depth: 'deep',
  });

  const selectedIndustry = INDUSTRIES.find(i => i.value === form.industry);

  async function handleSubmit() {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name || `${form.country} ${form.cities} ${selectedIndustry?.label}`,
          country: form.country,
          state_province: form.state,
          cities: form.cities.split(',').map(c => c.trim()),
          industry: form.industry,
          target_quantity: form.raw_target,
          min_quality_score: form.min_score,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        router.push(`/jobs?campaign=${data.id}`);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  return (
    <div className="p-10 max-w-4xl">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 text-zinc-500 text-sm mb-4">
          <a href="/campaigns" className="hover:text-white transition">Campaigns</a>
          <span>/</span>
          <span className="text-white">New Campaign</span>
        </div>
        <h1 className="text-3xl font-bold text-white">Create Campaign</h1>
        <p className="text-zinc-400 mt-2">Configure your lead intelligence pipeline</p>
      </div>

      {/* Step Progress */}
      <div className="flex items-center gap-0 mb-10">
        {['Geography', 'Industry', 'Targets', 'Research'].map((s, i) => (
          <div key={s} className="flex items-center">
            <button
              onClick={() => setStep(i + 1)}
              className={`flex items-center gap-2.5 px-4 py-2 rounded-md text-sm font-medium transition ${
                step === i + 1
                  ? 'bg-[#8b5cf6]/20 text-[#a78bfa] border border-[#8b5cf6]/40'
                  : step > i + 1
                  ? 'text-green-500'
                  : 'text-zinc-500'
              }`}
            >
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs border ${
                step > i + 1 ? 'bg-green-500/20 border-green-500/40 text-green-500' :
                step === i + 1 ? 'bg-[#8b5cf6]/20 border-[#8b5cf6]/40 text-[#a78bfa]' :
                'border-zinc-700 text-zinc-600'
              }`}>
                {step > i + 1 ? '✓' : i + 1}
              </span>
              {s}
            </button>
            {i < 3 && <span className="text-zinc-700 px-1">—</span>}
          </div>
        ))}
      </div>

      {/* Step 1: Geography */}
      {step === 1 && (
        <div className="space-y-6">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">1</span>
              Target Geography
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Country</label>
                <select
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50"
                  value={form.country}
                  onChange={e => setForm({ ...form, country: e.target.value })}
                >
                  <option>USA</option>
                  <option>UK</option>
                  <option>Australia</option>
                  <option>India</option>
                  <option>Canada</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">State / Province</label>
                <input
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50"
                  placeholder="e.g. Texas"
                  value={form.state}
                  onChange={e => setForm({ ...form, state: e.target.value })}
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Cities <span className="text-zinc-600 normal-case">(comma separated)</span></label>
                <input
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50"
                  placeholder="e.g. Dallas, Houston, Austin"
                  value={form.cities}
                  onChange={e => setForm({ ...form, cities: e.target.value })}
                />
                <p className="text-xs text-zinc-600 mt-1.5">The pipeline will search all specified cities in parallel</p>
              </div>
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={() => setStep(2)} className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-6 py-2.5 rounded-md text-sm font-medium transition">
              Next: Industry →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Industry */}
      {step === 2 && (
        <div className="space-y-6">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">2</span>
              Industry & Vertical
            </h2>
            <div className="grid grid-cols-2 gap-3 mb-5">
              {INDUSTRIES.map(ind => (
                <button
                  key={ind.value}
                  onClick={() => setForm({ ...form, industry: ind.value, sub_industry: '' })}
                  className={`text-left p-4 rounded-xl border transition ${
                    form.industry === ind.value
                      ? 'border-[#8b5cf6]/60 bg-[#8b5cf6]/10 text-white'
                      : 'border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-white'
                  }`}
                >
                  <span className="font-medium text-sm">{ind.label}</span>
                  <p className="text-xs text-zinc-600 mt-0.5">{ind.sub.slice(0, 2).join(', ')}</p>
                </button>
              ))}
            </div>
            {selectedIndustry && (
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Sub-Industry (optional)</label>
                <div className="flex flex-wrap gap-2">
                  {selectedIndustry.sub.map(s => (
                    <button
                      key={s}
                      onClick={() => setForm({ ...form, sub_industry: form.sub_industry === s ? '' : s })}
                      className={`text-xs px-3 py-1.5 rounded-full border transition ${
                        form.sub_industry === s
                          ? 'border-[#8b5cf6]/60 bg-[#8b5cf6]/10 text-[#a78bfa]'
                          : 'border-zinc-800 text-zinc-500 hover:border-zinc-700'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(1)} className="border border-zinc-800 text-zinc-400 px-6 py-2.5 rounded-md text-sm hover:text-white transition">← Back</button>
            <button onClick={() => setStep(3)} className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-6 py-2.5 rounded-md text-sm font-medium transition">Next: Targets →</button>
          </div>
        </div>
      )}

      {/* Step 3: Targets */}
      {step === 3 && (
        <div className="space-y-6">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">3</span>
              Lead Targets
            </h2>
            <div className="grid grid-cols-2 gap-5">
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Raw Businesses to Discover</label>
                <input type="number" className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50" value={form.raw_target} onChange={e => setForm({ ...form, raw_target: +e.target.value })} />
                <p className="text-xs text-zinc-600 mt-1.5">Total businesses to discover before qualification</p>
              </div>
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Minimum Qualification Score</label>
                <input type="number" min="0" max="100" className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50" value={form.min_score} onChange={e => setForm({ ...form, min_score: +e.target.value })} />
                <p className="text-xs text-zinc-600 mt-1.5">Leads below this score are rejected</p>
              </div>
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">A+ Target <span className="text-zinc-600 font-normal">(score ≥ 90)</span></label>
                <input type="number" className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50" value={form.a_plus_target} onChange={e => setForm({ ...form, a_plus_target: +e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">A Target <span className="text-zinc-600 font-normal">(score 80–89)</span></label>
                <input type="number" className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50" value={form.a_target} onChange={e => setForm({ ...form, a_target: +e.target.value })} />
              </div>
            </div>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="border border-zinc-800 text-zinc-400 px-6 py-2.5 rounded-md text-sm hover:text-white transition">← Back</button>
            <button onClick={() => setStep(4)} className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-6 py-2.5 rounded-md text-sm font-medium transition">Next: Research →</button>
          </div>
        </div>
      )}

      {/* Step 4: Research Depth + Launch */}
      {step === 4 && (
        <div className="space-y-6">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">4</span>
              Research Depth
            </h2>
            <div className="space-y-3 mb-6">
              {RESEARCH_DEPTHS.map(d => (
                <button
                  key={d.value}
                  onClick={() => setForm({ ...form, research_depth: d.value })}
                  className={`w-full text-left p-4 rounded-xl border transition ${
                    form.research_depth === d.value
                      ? 'border-[#8b5cf6]/60 bg-[#8b5cf6]/10'
                      : 'border-zinc-800 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`font-medium text-sm ${form.research_depth === d.value ? 'text-white' : 'text-zinc-400'}`}>{d.label}</span>
                    {form.research_depth === d.value && <span className="text-[#a78bfa] text-xs">Selected</span>}
                  </div>
                  <p className="text-xs text-zinc-600 mt-1">{d.desc}</p>
                </button>
              ))}
            </div>

            {/* Summary */}
            <div className="border-t border-zinc-800 pt-5">
              <h3 className="text-xs text-zinc-400 uppercase tracking-wider mb-3">Campaign Summary</h3>
              <div className="grid grid-cols-2 gap-y-2 text-sm">
                <span className="text-zinc-500">Location</span>
                <span className="text-white">{form.cities}, {form.state}, {form.country}</span>
                <span className="text-zinc-500">Industry</span>
                <span className="text-white">{selectedIndustry?.label} {form.sub_industry ? `(${form.sub_industry})` : ''}</span>
                <span className="text-zinc-500">Raw target</span>
                <span className="text-white">{form.raw_target.toLocaleString()} businesses</span>
                <span className="text-zinc-500">Minimum score</span>
                <span className="text-white">{form.min_score}/100</span>
                <span className="text-zinc-500">A+ / A targets</span>
                <span className="text-white">{form.a_plus_target} / {form.a_target} leads</span>
                <span className="text-zinc-500">Research depth</span>
                <span className="text-[#a78bfa] font-medium">{form.research_depth.charAt(0).toUpperCase() + form.research_depth.slice(1)}</span>
              </div>
            </div>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(3)} className="border border-zinc-800 text-zinc-400 px-6 py-2.5 rounded-md text-sm hover:text-white transition">← Back</button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="bg-[#8b5cf6] hover:bg-[#7c3aed] disabled:opacity-50 text-white px-8 py-2.5 rounded-md text-sm font-medium transition flex items-center gap-2"
            >
              {loading ? (
                <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>Launching...</>
              ) : (
                <>🚀 Launch Campaign</>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
