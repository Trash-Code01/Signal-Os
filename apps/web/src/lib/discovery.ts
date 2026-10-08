export const DISCOVERY_CHANNELS = [
  { id: 'google_maps', label: 'Google Maps', description: 'Local listings, phones, ratings and reviews.' },
  { id: 'google_search', label: 'Google Search', description: 'Business websites with location evidence.' },
  { id: 'directories', label: 'Business directories', description: 'Indexed Yelp, Yellow Pages, Justdial and BBB listings.' },
  { id: 'facebook', label: 'Facebook', description: 'Public business pages indexed by search engines.' },
  { id: 'instagram', label: 'Instagram', description: 'Public business profiles indexed by search engines.' },
  { id: 'linkedin', label: 'LinkedIn', description: 'Public company pages indexed by search engines.' },
] as const;

export const WEBSITE_OPTIONS = [
  { id: 'no_website', label: 'No website found', description: 'No official site found in listing and follow-up search. Confirm before outreach.' },
  { id: 'has_website', label: 'Has a website', description: 'Find businesses whose existing website may need improvement.' },
  { id: 'all', label: 'All businesses', description: 'Research both groups. Incomplete checks stay in needs review.' },
] as const;
