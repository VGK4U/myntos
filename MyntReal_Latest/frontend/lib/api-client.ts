import { ExecutiveTrendResponse, CRMLead } from '@/types/crm';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

export async function fetchExecutiveTrend(dateFrom?: string, dateTo?: string): Promise<ExecutiveTrendResponse> {
  const query = new URLSearchParams();
  if (dateFrom) query.append('date_from', dateFrom);
  if (dateTo) query.append('date_to', dateTo);

  const res = await fetch(`${BACKEND_URL}/api/v1/crm/exec-trend-leads?${query.toString()}`, {
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch executive trends: ${res.statusText}`);
  }

  return res.json();
}

export async function fetchCategoryLeads(categoryCode: string = 'SOLAR'): Promise<CRMLead[]> {
  const res = await fetch(`${BACKEND_URL}/api/v1/crm/leads-by-category?category_code=${categoryCode}`, {
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch category leads: ${res.statusText}`);
  }

  return res.json();
}
