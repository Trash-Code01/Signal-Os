'use client';

export type LookupOptions = { personal_email_enabled: boolean; phone_enabled: boolean };

export function ContactOptions({
  value,
  onChange,
  disabled = false,
}: {
  value: LookupOptions;
  onChange: (value: LookupOptions) => void;
  disabled?: boolean;
}) {
  const items = [
    {
      key: 'personal_email_enabled' as const,
      label: 'Personal work emails',
      description: 'Search Snov.io for verified personal work emails of decision-makers.',
      offNotice: 'Default: Use available public business email (No lookup credits used)',
      onNotice: 'Active: Enriches lead with decision-maker personal email',
    },
    {
      key: 'phone_enabled' as const,
      label: 'Phone research',
      description: 'Search public contact sources for direct decision-maker phone lines.',
      offNotice: 'Default: Use available public business phone (No lookup credits used)',
      onNotice: 'Active: Enriches lead with direct phone line & mobile',
    },
  ];

  return (
    <div
      className={`space-y-4 rounded-2xl border border-zinc-800 bg-[#121214] p-5 shadow-inner ${
        disabled ? 'opacity-60 pointer-events-none' : ''
      }`}
    >
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
        <div>
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <span>Optional Contact Lookups</span>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 font-medium">
              Toggle Mode
            </span>
          </h4>
          <p className="text-xs text-zinc-400 mt-0.5">
            Default is <strong>OFF</strong>. When OFF, the pipeline uses available public listing contacts and, for businesses with a website, website contacts without deducting contact lookup credits.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {items.map(({ key, label, description, offNotice, onNotice }) => {
          const isChecked = Boolean(value[key]);
          return (
            <div
              key={key}
              onClick={() => !disabled && onChange({ ...value, [key]: !isChecked })}
              className={`group flex items-center justify-between gap-4 p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
                isChecked
                  ? 'border-purple-500/40 bg-purple-950/20 shadow-sm shadow-purple-950/40'
                  : 'border-zinc-800/80 bg-[#09090b] hover:border-zinc-700'
              }`}
            >
              <div className="flex-1 min-w-0 pr-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-white group-hover:text-purple-300 transition-colors">
                    {label}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-1.5 py-0.2 rounded tracking-wide transition-colors ${
                      isChecked
                        ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                        : 'bg-zinc-800 text-zinc-400 border border-zinc-700/50'
                    }`}
                  >
                    {isChecked ? 'ON' : 'OFF'}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 leading-snug">{description}</p>
                <p className="text-[11px] text-zinc-500 mt-1 font-mono flex items-center gap-1.5">
                  <span className={isChecked ? 'text-purple-400' : 'text-zinc-400'}>
                    {isChecked ? '⚡' : '🌐'}
                  </span>
                  <span>{isChecked ? onNotice : offNotice}</span>
                </p>
              </div>

              {/* Modern iOS / Tailwind Toggle Switch Button */}
              <button
                type="button"
                role="switch"
                aria-checked={isChecked}
                aria-label={label}
                disabled={disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  onChange({ ...value, [key]: !isChecked });
                }}
                className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-[#121214] ${
                  isChecked
                    ? 'bg-purple-600 shadow-md shadow-purple-600/40'
                    : 'bg-zinc-700 hover:bg-zinc-600'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                    isChecked ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          );
        })}
      </div>

      <div className="pt-2 border-t border-zinc-800/60 flex items-center gap-2 text-[11px] text-zinc-400">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0"></span>
        <span>
          <strong>Toggle OFF (Default):</strong> The campaign still runs. Contact details are included when available from public sources.
        </span>
      </div>
    </div>
  );
}
