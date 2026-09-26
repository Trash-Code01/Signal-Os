import type { LeadExportData } from '@/lib/exportUtils';

interface LeadsPage {
  leads?: LeadExportData[];
  total?: number;
}

export async function fetchAllCrmLeads(
  filters: Record<string, string | number | boolean | undefined> = {},
): Promise<LeadExportData[]> {
  const pageSize = 200;
  const leadsById = new Map<number, LeadExportData>();
  let page = 1;
  let expectedTotal = 0;

  while (page <= 10_000) {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined) params.set(key, String(value));
    }

    const response = await fetch(`/api/crm/leads?${params.toString()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Lead export request failed (${response.status})`);

    const payload = (await response.json()) as LeadsPage;
    const pageLeads = Array.isArray(payload.leads) ? payload.leads : [];
    expectedTotal = Number(payload.total || 0);
    for (const lead of pageLeads) leadsById.set(lead.id, lead);

    if (pageLeads.length === 0 || leadsById.size >= expectedTotal) break;
    page += 1;
  }

  if (leadsById.size < expectedTotal) {
    throw new Error(`Export stopped before all leads were loaded (${leadsById.size}/${expectedTotal})`);
  }

  return Array.from(leadsById.values());
}

