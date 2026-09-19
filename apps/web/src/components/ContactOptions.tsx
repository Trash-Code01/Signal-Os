'use client';
export type LookupOptions = { personal_email_enabled: boolean; phone_enabled: boolean };
export function ContactOptions({ value, onChange, disabled = false }: { value: LookupOptions; onChange: (value: LookupOptions) => void; disabled?: boolean }) {
  return <fieldset disabled={disabled} className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4 disabled:opacity-60">
    <legend className="px-1 text-sm font-semibold text-white">Optional contact lookups</legend>
    {([
      ['personal_email_enabled', 'Personal work emails', 'Search Snov.io for individual email addresses.'],
      ['phone_enabled', 'Phone research', 'Search public contact sources for phone details; availability varies.'],
    ] as const).map(([key, label, description]) => <label key={key} className="flex items-start justify-between gap-4 cursor-pointer">
      <span><span className="block text-sm text-white">{label}</span><span className="text-xs text-zinc-400">{description}</span></span>
      <input type="checkbox" role="switch" aria-label={label} checked={value[key]} onChange={e => onChange({ ...value, [key]: e.target.checked })} className="mt-1 h-5 w-5 accent-violet-500" />
    </label>)}
    <p className="text-xs text-zinc-500">Off skips the associated contact API requests to save credits. Public website contacts remain available. Discovery and AI analysis have separate usage.</p>
  </fieldset>;
}
