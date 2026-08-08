export interface CRMLead {
  id: number;
  customer_name: string;
  phone_number: string;
  pincode?: string;
  district?: string;
  state?: string;
  status: string;
  solar_pipeline_status?: string;
  solar_pipeline_status_updated_at?: string;
  installation_date?: string;
  complete_date?: string;
  submit_date?: string;
  created_at: string;
  category_id?: number;
  category_name?: string;
  handler_staff_id?: number;
  handler_name?: string;
  ground_source_name?: string;
  capacity_kw?: number;
  deal_value?: number;
}

export interface TrendMonthRow {
  month: string;
  year: number;
  total_leads: number;
  submitted: number;
  at_bank: number;
  inst_pending: number;
  installed: number;
  bal_pending: number;
  subsidy_pending: number;
  completed: number;
  comp_sub_pct: number;
  comp_value: number;
  vs_prev: string;
}

export interface ExecutiveTrendResponse {
  months: TrendMonthRow[];
  total: TrendMonthRow;
}

export interface HandlerStatusRow {
  staff_id: number;
  staff_name: string;
  employee_code: string;
  total_leads: number;
  won_leads: number;
  progress_leads: number;
  lost_leads: number;
  win_pct: number;
  deal_value: number;
}
