import * as XLSX from 'xlsx';

export interface LeadExportData {
  id: number;
  name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  city?: string | null;
  state_province?: string | null;
  country?: string | null;
  stage?: string | null;
  commercial_score?: number | null;
  grade?: string | null;
  campaign_id?: number | null;
  campaign_name?: string | null;
  primary_problem?: string | null;
  recommended_offer?: string | null;
  outreach_angle?: string | null;
  created_at?: string | null;
  phone?: string | null;
  contacts?: Array<{
    name?: string | null;
    title?: string | null;
    email?: string | null;
    phone?: string | null;
    linkedin_url?: string | null;
    source?: string | null;
  }>;
  [key: string]: any;
}

export interface CampaignExportData {
  id: number;
  name: string;
  status: string;
  target?: number | null;
  city?: string | null;
  country?: string | null;
  industry?: string | null;
  created_at?: string | null;
  [key: string]: any;
}

/**
 * Download a file in the browser using a Blob and anchor link
 */
function downloadFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Format a list of leads into flat rows suitable for spreadsheets
 */
export function formatLeadsForExport(leads: LeadExportData[]) {
  return leads.map((lead) => {
    const contacts = Array.isArray(lead.contacts) ? lead.contacts : [];
    const primaryContact = contacts.find((c) => c.email) || contacts[0] || {};

    const allEmails = Array.from(
      new Set(contacts.map((c) => c.email).filter(Boolean))
    ).join('; ');

    const allPhones = Array.from(
      new Set([lead.phone, ...contacts.map((c) => c.phone)].filter(Boolean))
    ).join('; ');

    const allLinkedIn = Array.from(
      new Set(contacts.map((c) => c.linkedin_url).filter(Boolean))
    ).join('; ');

    return {
      'Lead ID': lead.id,
      'Company Name': lead.name || '',
      'Website': lead.website_url || '',
      'Industry': lead.industry || '',
      'Location': lead.location || `${lead.city || ''}${lead.city && lead.country ? ', ' : ''}${lead.country || ''}`,
      'City': lead.city || '',
      'State/Province': lead.state_province || '',
      'Country': lead.country || '',
      'Commercial Score': lead.commercial_score ?? 0,
      'Grade': lead.grade || 'U',
      'Stage': (lead.stage || 'new').toUpperCase(),
      'Campaign': lead.campaign_name || '',
      'Primary Contact Name': primaryContact.name || '',
      'Primary Contact Title': primaryContact.title || '',
      'Primary Contact Email': primaryContact.email || '',
      'Primary Contact Phone': primaryContact.phone || '',
      'Primary Contact LinkedIn': primaryContact.linkedin_url || '',
      'Contact Source': primaryContact.source || '',
      'All Emails': allEmails,
      'All Phone Numbers': allPhones,
      'LinkedIn Profiles': allLinkedIn,
      'Primary Pain Point': lead.primary_problem || '',
      'Recommended Offer': lead.recommended_offer || '',
      'AI Outreach Angle': lead.outreach_angle || '',
      'Created Date': lead.created_at ? new Date(lead.created_at).toISOString().split('T')[0] : '',
    };
  });
}

/**
 * Format a list of campaigns into flat rows suitable for spreadsheets
 */
export function formatCampaignsForExport(campaigns: CampaignExportData[]) {
  return campaigns.map((c) => ({
    'Campaign ID': c.id,
    'Campaign Name': c.name || '',
    'Status': (c.status || '').toUpperCase(),
    'Target Leads': c.target || 0,
    'City': c.city || '',
    'Country': c.country || '',
    'Target Geo': `${c.city || ''}${c.city && c.country ? ', ' : ''}${c.country || ''}`,
    'Industry / Niche': c.industry || 'Any',
    'Created Date': c.created_at ? new Date(c.created_at).toISOString().split('T')[0] : '',
  }));
}

/**
 * Auto-calculate column widths for XLSX worksheet
 */
function calculateColWidths(rows: Record<string, any>[]) {
  if (!rows.length) return [];
  const keys = Object.keys(rows[0]);
  return keys.map((key) => {
    let maxLen = key.length;
    for (let i = 0; i < Math.min(rows.length, 100); i++) {
      const val = rows[i][key];
      const strVal = val !== null && val !== undefined ? String(val) : '';
      if (strVal.length > maxLen) {
        maxLen = Math.min(strVal.length, 60);
      }
    }
    return { wch: Math.max(maxLen + 3, 10) };
  });
}

/**
 * Export Leads to Excel (.xlsx), CSV (.csv), or JSON (.json)
 */
export function exportLeads(
  leads: LeadExportData[],
  format: 'xlsx' | 'csv' | 'json',
  filenamePrefix: string = 'devacia-leads'
) {
  const timestamp = new Date().toISOString().split('T')[0];
  const filename = `${filenamePrefix}-${timestamp}`;

  if (format === 'json') {
    const jsonBlob = new Blob([JSON.stringify(leads, null, 2)], {
      type: 'application/json;charset=utf-8;',
    });
    downloadFile(jsonBlob, `${filename}.json`);
    return;
  }

  const rows = formatLeadsForExport(leads);

  if (format === 'csv') {
    const ws = XLSX.utils.json_to_sheet(rows);
    const csvContent = XLSX.utils.sheet_to_csv(ws);
    // Add UTF-8 BOM so Excel opens CSV without character encoding glitches
    const blob = new Blob(['\uFEFF' + csvContent], {
      type: 'text/csv;charset=utf-8;',
    });
    downloadFile(blob, `${filename}.csv`);
    return;
  }

  if (format === 'xlsx') {
    const ws = XLSX.utils.json_to_sheet(rows);
    ws['!cols'] = calculateColWidths(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Leads CRM');
    XLSX.writeFile(wb, `${filename}.xlsx`);
    return;
  }
}

/**
 * Export Campaigns to Excel (.xlsx), CSV (.csv), or JSON (.json)
 */
export function exportCampaigns(
  campaigns: CampaignExportData[],
  format: 'xlsx' | 'csv' | 'json',
  filenamePrefix: string = 'devacia-campaigns'
) {
  const timestamp = new Date().toISOString().split('T')[0];
  const filename = `${filenamePrefix}-${timestamp}`;

  if (format === 'json') {
    const jsonBlob = new Blob([JSON.stringify(campaigns, null, 2)], {
      type: 'application/json;charset=utf-8;',
    });
    downloadFile(jsonBlob, `${filename}.json`);
    return;
  }

  const rows = formatCampaignsForExport(campaigns);

  if (format === 'csv') {
    const ws = XLSX.utils.json_to_sheet(rows);
    const csvContent = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob(['\uFEFF' + csvContent], {
      type: 'text/csv;charset=utf-8;',
    });
    downloadFile(blob, `${filename}.csv`);
    return;
  }

  if (format === 'xlsx') {
    const ws = XLSX.utils.json_to_sheet(rows);
    ws['!cols'] = calculateColWidths(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Campaigns');
    XLSX.writeFile(wb, `${filename}.xlsx`);
    return;
  }
}
