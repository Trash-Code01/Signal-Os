'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { useSession } from '@/components/SessionProvider';
import { ContactOptions, LookupOptions } from '@/components/ContactOptions';
import { DISCOVERY_CHANNELS, WEBSITE_OPTIONS } from '@/lib/discovery';

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

export default function NewCampaignPage() {
  const router = useRouter();
  const { user } = useSession();
  const [error, setError] = useState('');
  const [options, setOptions] = useState<LookupOptions>({ personal_email_enabled: false, phone_enabled: false });
  useEffect(() => {
    if (user) {
      setOptions({
        personal_email_enabled: Boolean(user.personal_email_enabled),
        phone_enabled: Boolean(user.phone_enabled),
      });
    }
  }, [user]);

  const [channels, setChannels] = useState<string[]>(DISCOVERY_CHANNELS.map(c => c.id));
  const [websiteFilter, setWebsiteFilter] = useState('no_website');
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    country: 'USA',
    state: '',
    cities: '',
    industry: '',
    sub_industry: '',
    raw_target: 10,
    min_score: 60,
  });

  const selectedIndustry = INDUSTRIES.find(i => i.value === form.industry);

  async function handleSubmit() {
    if (loading) return;
    if (!channels.length) { setError('Select at least one discovery channel.'); return; }
    if (!Number.isInteger(form.min_score) || form.min_score < 0 || form.min_score > 100) { setError('Minimum score must be between 0 and 100.'); return; }
    setLoading(true);
    setError('');

    const requestedTarget = Number(form.raw_target);
    if (!Number.isInteger(requestedTarget) || requestedTarget < 1 || requestedTarget > 500) {
      setError('Qualified lead target must be a whole number between 1 and 500.');
      setLoading(false);
      return;
    }

    const parsedCities = form.cities
      .split(',')
      .map(c => c.trim())
      .filter(Boolean);

    if (!form.country.trim() || parsedCities.length === 0) {
      setError('Choose a country and add at least one target city. State / province is optional.');
      setLoading(false);
      return;
    }

    if (!form.industry.trim()) {
      setError('Please select or specify an industry / vertical.');
      setLoading(false);
      return;
    }

    const targetCities = [...new Set(parsedCities)];
    const campaignName = (
      form.name.trim() ||
      `${form.country} ${targetCities.join(', ')} ${selectedIndustry?.label || form.industry}`
    ).slice(0, 120);

    try {
      const apiUrl = "";
      const res = await fetch(`${apiUrl}/api/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name: campaignName,
          country: form.country,
          state_province: form.state.trim() || undefined,
          cities: targetCities,
          industry: form.industry,
          target_quantity: requestedTarget,
          min_quality_score: form.min_score,
          discovery_channels: channels,
          website_filter: websiteFilter,
          sub_industry: form.sub_industry || undefined,
          personal_email_enabled: Boolean(options.personal_email_enabled),
          phone_enabled: Boolean(options.phone_enabled),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        router.push(`/jobs?campaign=${data.campaign_id}`);
      } else {
        const data = await res.json().catch(() => ({}));
        let errorMsg = 'Could not launch campaign.';
        if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMsg = data.detail
            .map((issue: { loc?: Array<string | number>; msg?: string }) =>
              `${issue.loc?.slice(-1)[0] || 'field'}: ${issue.msg || 'Invalid value'}`,
            )
            .join(', ');
        }
        setError(errorMsg);
      }
    } catch {
      setError('Unable to launch campaign. Please retry.');
    }
    setLoading(false);
  }

  if (user?.role === 'viewer') return <div className="p-10 text-zinc-400">Your Viewer role can read and export your data. Ask an admin for Member access to run campaigns.</div>;

  const STEPS = ['Geography', 'Industry', 'Opportunity', 'Channels'];

  return (
    <div className="p-4 md:p-10 max-w-4xl pb-24 md:pb-10 mx-auto">
      {error && <p role="alert" className="mb-4 text-red-400 bg-red-950/40 border border-red-800/50 p-3 rounded-xl text-sm">{error}</p>}
      {process.env.NEXT_PUBLIC_APP_ENV === 'staging' && (
        <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-200">
          <strong>Staging test run:</strong> campaigns create synthetic workflow records only. No real businesses, websites, emails, or phone numbers are scraped. Run production for live lead research.
        </div>
      )}
      {/* Header */}
      <div className="mb-8 md:mb-10">
        <div className="hidden md:flex items-center gap-2 text-zinc-500 text-sm mb-4">
          <a href="/campaigns" className="hover:text-white transition">Campaigns</a>
          <span>/</span>
          <span className="text-white">New Campaign</span>
        </div>
        <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">Find your next business opportunity</h1>
        <p className="text-sm md:text-base text-zinc-400 mt-1 md:mt-2">Discover businesses across public channels, check website presence, and rank contactable leads.</p>
      </div>

      {/* Step Progress - Desktop */}
      <div className="hidden md:flex items-center gap-0 mb-10">
        {STEPS.map((s, i) => (
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
            {i < 3 && <span className="text-zinc-700 px-1">&rarr;</span>}
          </div>
        ))}
      </div>

      {/* Step 1: Geography */}
      {step === 1 && (
        <div className="space-y-6 animate-in fade-in">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-4 md:p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">1</span>
              Target Geography
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Country</label>
                <select
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg md:rounded-md px-3 py-3 md:py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                  value={form.country}
                  onChange={e => setForm({ ...form, country: e.target.value, state: '', cities: '' })}
                >
                  <option>USA</option>
                  <option>UK</option>
                  <option>Australia</option>
                  <option>India</option>
                  <option>Canada</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">State / Province <span className="normal-case text-zinc-600">(optional)</span></label>
                <input
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg md:rounded-md px-3 py-3 md:py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                  placeholder="e.g. Texas"
                  value={form.state}
                  onChange={e => setForm({ ...form, state: e.target.value })}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Cities <span className="text-zinc-600 normal-case">(comma separated)</span></label>
                <input
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg md:rounded-md px-3 py-3 md:py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors"
                  placeholder="e.g. Dallas, Houston, Austin"
                  value={form.cities}
                  onChange={e => setForm({ ...form, cities: e.target.value })}
                />
                <p className="text-xs text-zinc-600 mt-2">Search up to 20 target cities and retain the source behind each lead.</p>
              </div>
            </div>
          </div>
          <div className="flex justify-end">
            <button
              onClick={() => {
                const parsed = form.cities.split(',').map(c => c.trim()).filter(Boolean);
                if (!form.country.trim() || parsed.length === 0) {
                  setError('Choose a country and add at least one target city. State / province is optional.');
                  return;
                }
                setError('');
                setStep(2);
              }}
              className="w-full md:w-auto bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-6 py-3 md:py-2.5 rounded-lg md:rounded-md text-sm font-medium transition shadow-lg shadow-purple-900/20"
            >
              Next: Industry →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Industry */}
      {step === 2 && (
        <div className="space-y-6 animate-in fade-in">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-4 md:p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">2</span>
              Industry & Vertical
            </h2>
            <div className="mb-5">
              <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Custom Industry / Niche</label>
              <input
                type="text"
                value={form.industry}
                onChange={e => setForm({ ...form, industry: e.target.value, sub_industry: '' })}
                placeholder="e.g. Architecture Firm, Solar Panel Installer, Agriculture..."
                className="w-full bg-[#09090b] border border-zinc-800 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-[#8b5cf6]/50 focus:ring-1 focus:ring-[#8b5cf6]/50 placeholder:text-zinc-600 mb-4"
              />
              
              <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Or choose a quick preset:</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {INDUSTRIES.map(ind => (
                  <button
                    key={ind.value}
                    onClick={() => setForm({ ...form, industry: ind.value, sub_industry: '' })}
                    className={`text-xs px-3 py-1.5 rounded-full border transition active:scale-[0.98] ${
                      form.industry === ind.value
                        ? 'border-[#8b5cf6]/60 bg-[#8b5cf6]/10 text-white'
                        : 'border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-white bg-[#09090b]'
                    }`}
                  >
                    {ind.label}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Show Sub-industry only if they clicked a preset that has subs */}
            {selectedIndustry && selectedIndustry.sub && (
              <div className="pt-2 border-t border-zinc-800/60 mt-4">
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-3 block mt-4">Sub-Industry (optional)</label>
                <div className="flex flex-wrap gap-2">
                  {selectedIndustry.sub.map(s => (
                    <button
                      key={s}
                      onClick={() => setForm({ ...form, sub_industry: form.sub_industry === s ? '' : s })}
                      className={`text-xs px-4 py-2 rounded-full border transition active:scale-[0.98] ${
                        form.sub_industry === s
                          ? 'border-[#8b5cf6]/60 bg-[#8b5cf6]/10 text-[#a78bfa]'
                          : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:border-zinc-700 hover:text-zinc-300'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="flex gap-3 md:justify-between">
            <button onClick={() => { setError(''); setStep(1); }} className="flex-1 md:flex-none border border-zinc-800 text-zinc-400 px-6 py-3 md:py-2.5 rounded-lg md:rounded-md text-sm hover:text-white hover:bg-zinc-800/50 transition">← Back</button>
            <button
              onClick={() => {
                if (!form.industry.trim()) {
                  setError('Please select or specify an industry / vertical before proceeding.');
                  return;
                }
                setError('');
                setStep(3);
              }}
              className="flex-[2] md:flex-none bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-6 py-3 md:py-2.5 rounded-lg md:rounded-md text-sm font-medium transition shadow-lg shadow-purple-900/20"
            >
              Next: Targets →
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Targets */}
      {step === 3 && (
        <div className="space-y-6 animate-in fade-in">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-4 md:p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">3</span>
              Opportunity & Quality
            </h2>
            <fieldset className="mb-6 grid gap-3 md:grid-cols-3">
              <legend className="text-xs text-zinc-400 mb-3">Website presence</legend>
              {WEBSITE_OPTIONS.map(option => (
                <label key={option.id} className={`cursor-pointer rounded-xl border p-4 ${websiteFilter === option.id ? 'border-violet-400 bg-violet-500/10' : 'border-zinc-800'}`}>
                  <span className="flex items-center gap-2"><input type="radio" name="websitePresence" checked={websiteFilter === option.id} onChange={() => setWebsiteFilter(option.id)} className="accent-violet-500" /><span className="text-sm text-white">{option.label}</span></span>
                  <p className="mt-2 text-xs text-zinc-400 leading-5">{option.description}</p>
                </label>
              ))}
            </fieldset>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Qualified Lead Target</label>
                <input type="number" min="1" max="500" step="1" className="w-full bg-zinc-900 border border-zinc-800 rounded-lg md:rounded-md px-3 py-3 md:py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors" value={form.raw_target} onChange={e => setForm({ ...form, raw_target: +e.target.value })} />
                <p className="text-xs text-zinc-600 mt-2">1–500 qualified leads. The pipeline discovers reserve candidates to cover duplicates and rejections.</p>
              </div>
              <div>
                <label className="text-xs text-zinc-400 uppercase tracking-wider mb-2 block">Minimum Qualification Score</label>
                <input type="number" min="0" max="100" className="w-full bg-zinc-900 border border-zinc-800 rounded-lg md:rounded-md px-3 py-3 md:py-2.5 text-white text-sm outline-none focus:border-[#8b5cf6]/50 transition-colors" value={form.min_score} onChange={e => setForm({ ...form, min_score: +e.target.value })} />
                <p className="text-xs text-zinc-600 mt-2">Scores use observed business activity, website opportunity and contactability. Targets may be partially filled.</p>
              </div>

            </div>
          </div>
          <div className="flex gap-3 md:justify-between">
            <button onClick={() => setStep(2)} className="flex-1 md:flex-none border border-zinc-800 text-zinc-400 px-6 py-3 md:py-2.5 rounded-lg md:rounded-md text-sm hover:text-white hover:bg-zinc-800/50 transition">← Back</button>
            <button onClick={() => setStep(4)} className="flex-[2] md:flex-none bg-[#8b5cf6] hover:bg-[#7c3aed] text-white px-6 py-3 md:py-2.5 rounded-lg md:rounded-md text-sm font-medium transition shadow-lg shadow-purple-900/20">Next: Channels →</button>
          </div>
        </div>
      )}

      {/* Step 4: Research Depth + Launch */}
      {step === 4 && (
        <div className="space-y-6 animate-in fade-in">
          <div className="bg-[#121214] border border-zinc-800/60 rounded-xl p-4 md:p-6">
            <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-[#8b5cf6]/20 text-[#a78bfa] text-xs flex items-center justify-center">4</span>
              Discovery Channels
            </h2>
            <div className="flex justify-between items-center mb-4">
              <p className="text-sm text-zinc-400">{channels.length} channels selected</p>
              <button type="button" onClick={() => setChannels(DISCOVERY_CHANNELS.map(c => c.id))} className="text-xs text-violet-300">Select all channels</button>
            </div>
            <div className="grid md:grid-cols-2 gap-3 mb-4">
              {DISCOVERY_CHANNELS.map(channel => (
                <label key={channel.id} className={`flex gap-3 cursor-pointer rounded-xl border p-4 ${channels.includes(channel.id) ? 'border-violet-500/60 bg-violet-500/10' : 'border-zinc-800'}`}>
                  <input type="checkbox" className="accent-violet-500" checked={channels.includes(channel.id)} disabled={loading} onChange={() => setChannels(previous => previous.includes(channel.id) ? previous.filter(c => c !== channel.id) : [...previous, channel.id])} />
                  <span><span className="text-sm font-medium text-white">{channel.label}</span><span className="block mt-1 text-xs text-zinc-400 leading-5">{channel.description}</span></span>
                </label>
              ))}
            </div>
            <p className="text-xs leading-5 text-zinc-500 mb-6">All channels use the configured Serper provider. Results depend on public search coverage and provider credits. Social and directory pages are candidates for review; private platform data is not accessed.</p>
            <div className="mb-6"><ContactOptions value={options} onChange={setOptions} disabled={loading} /></div>
            {/* Summary */}
            <div className="border-t border-zinc-800/60 pt-5">
              <h3 className="text-xs text-zinc-400 uppercase tracking-wider mb-3">Campaign Summary</h3>
              <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm bg-zinc-900/30 p-4 rounded-xl border border-zinc-800/50">
                <span className="text-zinc-500">Location</span>
                <span className="text-white text-right md:text-left truncate">{form.cities}{form.state ? `, ${form.state}` : ''}, {form.country}</span>
                <span className="text-zinc-500">Industry</span>
                <span className="text-white text-right md:text-left truncate">{selectedIndustry?.label || form.industry || 'Not selected'} {form.sub_industry ? `(${form.sub_industry})` : ''}</span>
                <span className="text-zinc-500">Qualified target</span>
                <span className="text-white text-right md:text-left">{form.raw_target.toLocaleString()}</span>
                <span className="text-zinc-500">Min score</span>
                <span className="text-white text-right md:text-left">{form.min_score}/100</span>
                <span className="text-zinc-500">Website presence</span>
                <span className="text-white">{WEBSITE_OPTIONS.find(o => o.id === websiteFilter)?.label}</span>
                <span className="text-zinc-500">Discovery channels</span>
                <span className="text-white">{channels.length} selected</span>
              </div>
            </div>
          </div>
          <div className="flex gap-3 md:justify-between">
            <button onClick={() => setStep(3)} className="flex-1 md:flex-none border border-zinc-800 text-zinc-400 px-6 py-3 md:py-2.5 rounded-lg md:rounded-md text-sm hover:text-white hover:bg-zinc-800/50 transition">← Back</button>
            <button
              onClick={handleSubmit}
              disabled={loading || !channels.length}
              className="flex-[2] md:flex-none bg-[#8b5cf6] hover:bg-[#7c3aed] disabled:opacity-50 text-white px-8 py-3 md:py-2.5 rounded-lg md:rounded-md text-sm font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-purple-900/20"
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
