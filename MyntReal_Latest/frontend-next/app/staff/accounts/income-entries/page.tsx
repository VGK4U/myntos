"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import {
  Plus,
  Search,
  Filter,
  RefreshCw,
  Calendar,
  Building2,
  User,
  Users,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  Calculator,
  Sun,
  BarChart3,
  Trash2,
  Edit,
  RotateCcw,
  FileText,
  Printer,
  Download,
  CreditCard,
  ArrowDownLeft,
  ArrowUpRight,
  Wallet,
  ChevronRight,
  ChevronDown,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  MapPin,
  Check,
  X,
  ExternalLink,
  ShieldAlert,
  SlidersHorizontal,
  Briefcase,
  Layers,
  Banknote,
  Eye,
  Package,
  HelpCircle,
} from "lucide-react";

// ============================================================================
// Types & Interfaces
// ============================================================================

interface Company {
  id: number;
  company_name?: string;
  name?: string;
  bank_name?: string;
}

interface IncomeSourceType {
  id: number;
  source_name?: string;
  name?: string;
}

interface RevenueCategory {
  id: number;
  category_name: string;
  company_id?: number;
}

interface AssignableEmployee {
  id: number;
  full_name?: string;
  name?: string;
  employee_code?: string;
  emp_code?: string;
}

interface SolarVendor {
  id: number;
  vendor_name: string;
  vendor_code?: string;
  is_active?: boolean;
}

interface BankAccount {
  id: number;
  account_name: string;
  account_type?: string;
  bank_name?: string;
}

interface IncomeEntry {
  id: number;
  entry_number?: string;
  income_date: string;
  company_id?: number;
  company_name?: string;
  income_source_id?: number;
  income_source_name?: string;
  revenue_category_id?: number;
  revenue_category_name?: string;
  amount: number;
  payment_mode: string;
  payment_type?: string;
  transaction_type?: string;
  payer_name?: string;
  payer_city?: string;
  lead_name?: string;
  lead_city?: string;
  lead_state?: string;
  lead_phone?: string;
  lead_id?: number;
  deal_code?: string;
  collected_by_name?: string;
  collected_by_emp_code?: string;
  lead_owner_name?: string;
  lead_owner_emp_code?: string;
  lead_owner_id?: number;
  updated_by_name?: string;
  updated_by_emp_code?: string;
  status: "PENDING" | "CONFIRMED" | "ESTIMATED" | "EXCEPTION_TALLY" | "ADJUSTMENT" | "TALLY_DONE" | "REJECTED";
  confirmation_type?: "TAXED" | "ESTIMATED";
  crm_transaction_id?: number;
  destination_type?: "COMPANY_ACCOUNT" | "EMPLOYEE" | "SOLAR_VENDOR" | null;
  destination_company_id?: number;
  destination_company_name?: string;
  destination_employee_id?: number;
  destination_employee_name?: string;
  destination_employee_emp_code?: string;
  solar_vendor_id?: number;
  bank_account_id?: number;
  bank_account_name?: string;
  show_in_ledger?: boolean;
  payment_reference?: string;
  narration?: string;
  created_at?: string;
  deleted_by_name?: string;
  deleted_by_emp_code?: string;
  deleted_at?: string;
  is_deleted?: boolean;
}

interface SolarVendorLedgerRow {
  id: number;
  transaction_date: string;
  vendor_name?: string;
  solar_vendor_id?: number;
  customer_name?: string;
  direction: "RECEIVED" | "RETURNED";
  amount: number;
  payment_mode?: string;
  utr_reference?: string;
  notes?: string;
}

interface SolarVendorLedgerSummary {
  total_received?: number;
  total_returned?: number;
  balance?: number;
  count_received?: number;
  count_returned?: number;
}

interface EstOutRecord {
  id: number;
  company_id?: number;
  entry_date: string;
  description: string;
  estimated_amount: number;
  party_name?: string;
  account_name?: string;
  notes?: string;
  status?: string;
}

interface EstPaymentRecord {
  id: number;
  income_entry_id: number;
  _entry_number?: string;
  payment_date: string;
  amount: number;
  payment_mode?: string;
  party_name?: string;
  account_received?: string;
  notes?: string;
}

interface EstStockMovement {
  id?: number;
  transaction_date: string;
  item_name: string;
  item_code: string;
  quantity_out: number;
  reference_number?: string;
}

interface EstSummary {
  in_estimates: { count: number; total: number };
  out_estimates: { count: number; total: number };
  payments: { count: number; total: number };
  net_estimated: number;
}

interface FundBalanceSummary {
  available_balance: number;
  approved_expenses?: number;
  pending_submitted?: number;
  pending_draft?: number;
  effective_balance_after_submitted?: number;
}

// ============================================================================
// Formatting Helpers
// ============================================================================

const fmt = (amt?: number | string | null) => {
  const num = typeof amt === "string" ? parseFloat(amt) : amt;
  return "₹" + new Intl.NumberFormat("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(num || 0);
};

const fmt2 = (amt?: number | string | null) => {
  const num = typeof amt === "string" ? parseFloat(amt) : amt;
  return "₹" + new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num || 0);
};

const fmtDate = (d?: string | null) => {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return d;
  }
};

const STATUS_MAP: Record<string, { label: string; bg: string; text: string; border: string }> = {
  PENDING: { label: "Pending", bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  CONFIRMED: { label: "Confirmed", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  ESTIMATED: { label: "Estimated", bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  EXCEPTION_TALLY: { label: "Exception for Tally", bg: "bg-pink-50", text: "text-pink-700", border: "border-pink-200" },
  ADJUSTMENT: { label: "Adjustment", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  TALLY_DONE: { label: "Tally Entry Done", bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
  REJECTED: { label: "Rejected", bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
};

// ============================================================================
// Main Page Component
// ============================================================================

export default function IncomeEntriesPage() {
  const { user, token } = useStaffAuth();

  // Tab State
  type TabType =
    | "transactions"
    | "dateWise"
    | "customerWise"
    | "leadOwner"
    | "employee"
    | "location"
    | "estimations"
    | "solarvendor"
    | "execDash"
    | "deleted";

  const [activeTab, setActiveTab] = useState<TabType>("transactions");

  // Master Data State
  const [companies, setCompanies] = useState<Company[]>([]);
  const [sourceTypes, setSourceTypes] = useState<IncomeSourceType[]>([]);
  const [filterCategories, setFilterCategories] = useState<string[]>([]);
  const [formCategories, setFormCategories] = useState<RevenueCategory[]>([]);
  const [solarVendors, setSolarVendors] = useState<SolarVendor[]>([]);
  const [assignableEmployees, setAssignableEmployees] = useState<AssignableEmployee[]>([]);

  // Income Entries Data
  const [allIncomes, setAllIncomes] = useState<IncomeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletedIncomes, setDeletedIncomes] = useState<IncomeEntry[]>([]);
  const [deletedLoading, setDeletedLoading] = useState(false);

  // Filters
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterCompany, setFilterCompany] = useState<string>("");
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [filterPaymentMode, setFilterPaymentMode] = useState<string>("");
  const [filterPaymentType, setFilterPaymentType] = useState<string>("");
  const [filterTxnType, setFilterTxnType] = useState<string>("");
  const [filterSource, setFilterSource] = useState<string>("");
  const [filterDestType, setFilterDestType] = useState<string>("");
  const [filterDestSearch, setFilterDestSearch] = useState<string>("");
  const [filterFromDate, setFilterFromDate] = useState<string>("");
  const [filterToDate, setFilterToDate] = useState<string>("");
  const [filterSearch, setFilterSearch] = useState<string>("");

  // Sort State
  const [sortField, setSortField] = useState<keyof IncomeEntry | "entry_number">("income_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Date Wise Accordion Open Map
  const [openDateGroups, setOpenDateGroups] = useState<Record<string, boolean>>({});

  // View Detail Modal (Customer / Lead Owner)
  const [detailModalTitle, setDetailModalTitle] = useState("");
  const [detailModalItems, setDetailModalItems] = useState<IncomeEntry[]>([]);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Create Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    company_id: "",
    income_date: new Date().toISOString().split("T")[0],
    income_source_id: "",
    revenue_category_id: "",
    amount: "",
    payment_mode: "UPI",
    payment_type: "",
    payer_name: "",
    payment_reference: "",
    narration: "",
    show_in_ledger: false,
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);

  // Confirm Modal
  const [confirmingEntry, setConfirmingEntry] = useState<IncomeEntry | null>(null);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [confCompanyId, setConfCompanyId] = useState<string>("");
  const [confDestType, setConfDestType] = useState<string>("");
  const [confDestCompanyId, setConfDestCompanyId] = useState<string>("");
  const [confDestEmployeeId, setConfDestEmployeeId] = useState<string>("");
  const [confSolarVendorId, setConfSolarVendorId] = useState<string>("");
  const [confBankAccountId, setConfBankAccountId] = useState<string>("");
  const [confPayerName, setConfPayerName] = useState<string>("");
  const [confBankAccounts, setConfBankAccounts] = useState<BankAccount[]>([]);
  const [confEmployeeBalance, setConfEmployeeBalance] = useState<{
    prevBal: number;
    txnAmt: number;
    afterBal: number;
    name: string;
  } | null>(null);
  const [confirmSubmitting, setConfirmSubmitting] = useState(false);

  // Edit Destination Modal
  const [editingEntry, setEditingEntry] = useState<IncomeEntry | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editIncomeDate, setEditIncomeDate] = useState("");
  const [editDestType, setEditDestType] = useState("");
  const [editDestCompanyId, setEditDestCompanyId] = useState("");
  const [editDestEmployeeId, setEditDestEmployeeId] = useState("");
  const [editEmployeeBalance, setEditEmployeeBalance] = useState<FundBalanceSummary | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);

  // Estimations Tab State
  type EstSubTab = "in" | "out" | "payments" | "stock" | "executive";
  const [estSubTab, setEstSubTab] = useState<EstSubTab>("in");
  const [estInEntries, setEstInEntries] = useState<IncomeEntry[]>([]);
  const [estOutRecords, setEstOutRecords] = useState<EstOutRecord[]>([]);
  const [estPayments, setEstPayments] = useState<EstPaymentRecord[]>([]);
  const [estStock, setEstStock] = useState<EstStockMovement[]>([]);
  const [estSummary, setEstSummary] = useState<EstSummary | null>(null);
  const [estLoading, setEstLoading] = useState(false);

  // Add/Edit OUT Record Modal
  const [isOutModalOpen, setIsOutModalOpen] = useState(false);
  const [editingOutId, setEditingOutId] = useState<number | null>(null);
  const [outForm, setOutForm] = useState({
    entry_date: new Date().toISOString().split("T")[0],
    amount: "",
    description: "",
    party_name: "",
    account_name: "",
    notes: "",
  });

  // Solar Vendor Ledger State
  const [svlVendorFilter, setSvlVendorFilter] = useState<string>("");
  const [svlDirectionFilter, setSvlDirectionFilter] = useState<string>("");
  const [svlFromDate, setSvlFromDate] = useState<string>("");
  const [svlToDate, setSvlToDate] = useState<string>("");
  const [svlPage, setSvlPage] = useState(1);
  const [svlTotal, setSvlTotal] = useState(0);
  const [svlRows, setSvlRows] = useState<SolarVendorLedgerRow[]>([]);
  const [svlSummary, setSvlSummary] = useState<SolarVendorLedgerSummary>({});
  const [svlLoading, setSvlLoading] = useState(false);

  // Solar Vendor Return Modal
  const [isSvlReturnModalOpen, setIsSvlReturnModalOpen] = useState(false);
  const [svlReturnForm, setSvlReturnForm] = useState({
    solar_vendor_id: "",
    transaction_date: new Date().toISOString().split("T")[0],
    amount: "",
    customer_name: "",
    payment_mode: "",
    utr_reference: "",
    notes: "",
  });

  // Solar Vendor Edit Modal
  const [isSvlEditModalOpen, setIsSvlEditModalOpen] = useState(false);
  const [svlEditRow, setSvlEditRow] = useState<SolarVendorLedgerRow | null>(null);
  const [svlEditForm, setSvlEditForm] = useState({
    transaction_date: "",
    payment_mode: "",
    customer_name: "",
    utr_reference: "",
    notes: "",
  });

  // Executive Dashboard State
  type EdPeriod = "ftd" | "week" | "month" | "fy" | "all" | "custom";
  const [edPeriod, setEdPeriod] = useState<EdPeriod>("month");
  const [edFrom, setEdFrom] = useState<string>("");
  const [edTo, setEdTo] = useState<string>("");

  // ============================================================================
  // Permissions
  // ============================================================================

  const canReject = useMemo(() => {
    if (!user) return false;
    const role = (user.role_name || user.role_code || "").toLowerCase();
    const designation = (user.designation || "").toUpperCase();
    const allowed = ["vgk4u", "ea", "accounts", "executive_assistant", "executive assistant", "vgk mentor", "mentor"];
    return allowed.some((r) => role.includes(r)) || designation.includes("MENTOR");
  }, [user]);

  const canDelete = useMemo(() => {
    if (!user) return false;
    const empCode = (user.emp_code || user.employee_code || "").toUpperCase().trim();
    const role = (user.role_name || user.role_code || "").toLowerCase().trim();
    const allowed = ["vgk4u", "ea", "executive_assistant", "accounts", "accounts_staff", "accounts_manager", "finance"];
    return empCode === "MR10001" || allowed.some((r) => role.includes(r));
  }, [user]);

  // ============================================================================
  // Initial Data Fetching
  // ============================================================================

  useEffect(() => {
    fetchInitialData();
  }, [token]);

  const fetchInitialData = async () => {
    try {
      const [compRes, srcRes, catRes, vendorRes, empRes] = await Promise.allSettled([
        api.get("/staff/accounts/companies"),
        api.get("/staff/accounts/income-sources"),
        api.get("/staff/accounts/revenue-categories/all-names?active_only=true"),
        api.get("/crm/solar-vendors"),
        api.get("/staff/tasks/assignable-employees?limit=500"),
      ]);

      if (compRes.status === "fulfilled" && compRes.value.data) {
        setCompanies(compRes.value.data.companies || compRes.value.data.data || []);
      }
      if (srcRes.status === "fulfilled" && srcRes.value.data) {
        const d = srcRes.value.data;
        setSourceTypes(d.source_types || d.income_source_types || d.sources || []);
      }
      if (catRes.status === "fulfilled" && catRes.value.data) {
        setFilterCategories(catRes.value.data.names || []);
      }
      if (vendorRes.status === "fulfilled" && vendorRes.value.data) {
        setSolarVendors(vendorRes.value.data.vendors || []);
      }
      if (empRes.status === "fulfilled" && empRes.value.data) {
        setAssignableEmployees(empRes.value.data.employees || empRes.value.data.data || []);
      }
    } catch (e) {
      console.error("Error loading master data", e);
    }
  };

  // Fetch Incomes when filters change
  const fetchIncomes = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: "500" });
      if (filterStatus) params.append("status", filterStatus);
      if (filterCompany) params.append("company_id", filterCompany);
      if (filterCategory) params.append("category_name", filterCategory);
      if (filterPaymentMode) params.append("payment_mode", filterPaymentMode);
      if (filterTxnType) params.append("transaction_type", filterTxnType);
      if (filterSource) params.append("source", filterSource);
      if (filterFromDate) params.append("date_from", filterFromDate);
      if (filterToDate) params.append("date_to", filterToDate);
      if (filterSearch.trim()) params.append("search", filterSearch.trim());

      const res = await api.get(`/staff/accounts/income-entries?${params.toString()}`);
      if (res.data) {
        const list: IncomeEntry[] = res.data.incomes || res.data.income_entries || [];
        setAllIncomes(list);
      }
    } catch (err) {
      console.error("Failed to load income entries", err);
      setAllIncomes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchIncomes();
    }, 200);
    return () => clearTimeout(timer);
  }, [
    filterStatus,
    filterCompany,
    filterCategory,
    filterPaymentMode,
    filterTxnType,
    filterSource,
    filterFromDate,
    filterToDate,
    filterSearch,
  ]);

  // Dynamic filter category loader when company filter changes
  useEffect(() => {
    const updateCategories = async () => {
      if (!filterCompany) {
        try {
          const res = await api.get("/staff/accounts/revenue-categories/all-names?active_only=true");
          if (res.data?.names) setFilterCategories(res.data.names);
        } catch {}
      } else {
        try {
          const res = await api.get(`/staff/accounts/revenue-categories?company_id=${filterCompany}&active_only=true`);
          if (res.data?.categories) {
            const names = Array.from(new Set(res.data.categories.map((c: any) => c.category_name).filter(Boolean)));
            setFilterCategories(names as string[]);
          }
        } catch {}
      }
    };
    updateCategories();
  }, [filterCompany]);

  // Dynamic form category loader when modal company select changes
  const loadFormCategories = async (compId: string) => {
    if (!compId) {
      setFormCategories([]);
      return;
    }
    try {
      const res = await api.get(`/staff/accounts/revenue-categories?company_id=${compId}&active_only=true`);
      if (res.data?.categories) {
        setFormCategories(res.data.categories);
      }
    } catch {
      setFormCategories([]);
    }
  };

  // Filtered and Sorted Incomes
  const filteredIncomes = useMemo(() => {
    let list = [...allIncomes];

    if (filterPaymentType) {
      list = list.filter((i) => i.payment_type === filterPaymentType);
    }

    if (filterDestType) {
      if (filterDestType === "UNASSIGNED") {
        list = list.filter((i) => !i.destination_type);
      } else {
        list = list.filter((i) => i.destination_type === filterDestType);
      }
    }

    if (filterDestSearch.trim()) {
      const q = filterDestSearch.trim().toLowerCase();
      list = list.filter((i) => {
        const empName = (i.destination_employee_name || "").toLowerCase();
        const empCode = (i.destination_employee_emp_code || "").toLowerCase();
        const compName = (i.destination_company_name || "").toLowerCase();
        return empName.includes(q) || empCode.includes(q) || compName.includes(q);
      });
    }

    // Sort
    list.sort((a, b) => {
      let va: any = a[sortField];
      let vb: any = b[sortField];
      if (va == null) va = "";
      if (vb == null) vb = "";
      if (typeof va === "number" && typeof vb === "number") {
        return sortOrder === "desc" ? vb - va : va - vb;
      }
      va = String(va).toLowerCase();
      vb = String(vb).toLowerCase();
      return sortOrder === "desc" ? vb.localeCompare(va) : va.localeCompare(vb);
    });

    return list;
  }, [allIncomes, filterPaymentType, filterDestType, filterDestSearch, sortField, sortOrder]);

  // Viewable Incomes (Excludes ESTIMATED for grouping tabs unless explicitly filtered)
  const viewableIncomes = useMemo(() => {
    return filterStatus === "ESTIMATED"
      ? filteredIncomes
      : filteredIncomes.filter((i) => i.status !== "ESTIMATED");
  }, [filteredIncomes, filterStatus]);

  // Summary Metrics
  const summaryMetrics = useMemo(() => {
    const active = filteredIncomes.filter((i) => i.status !== "REJECTED" && i.status !== "ESTIMATED");
    const activeAmount = active.reduce((sum, i) => sum + (Number(i.amount) || 0), 0);
    return {
      totalCount: filteredIncomes.length,
      activeAmount,
      pendingCount: filteredIncomes.filter((i) => i.status === "PENDING").length,
      confirmedCount: filteredIncomes.filter((i) => i.status === "CONFIRMED").length,
      tallyDoneCount: filteredIncomes.filter((i) => i.status === "TALLY_DONE").length,
      rejectedCount: filteredIncomes.filter((i) => i.status === "REJECTED").length,
      estimatedCount: filteredIncomes.filter((i) => i.status === "ESTIMATED").length,
    };
  }, [filteredIncomes]);

  // ============================================================================
  // Status Update & Action Handlers
  // ============================================================================

  const handleUpdateStatus = async (id: number, newStatus: string) => {
    try {
      const res = await api.patch(`/staff/accounts/income-entries/${id}/status`, {
        status: newStatus,
      });
      if (res.data?.success || res.status === 200) {
        fetchIncomes();
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.response?.data?.message || "Failed to update status");
    }
  };

  const handleToggleLedger = async (id: number, checked: boolean) => {
    try {
      const res = await api.patch(`/staff/accounts/income-entries/${id}/show-in-ledger`, {
        show_in_ledger: checked,
      });
      if (res.status === 200) {
        setAllIncomes((prev) =>
          prev.map((item) => (item.id === id ? { ...item, show_in_ledger: checked } : item))
        );
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to toggle show in ledger");
      fetchIncomes();
    }
  };

  const handleRejectIncome = async (inc: IncomeEntry) => {
    const entryNum = inc.entry_number || inc.id;
    const payer = inc.lead_name || inc.payer_name || "—";
    const msg = `Reject income entry ${entryNum} for ${fmt(inc.amount)}${
      payer !== "—" ? ` from ${payer}` : ""
    }?\n\nThis will:\n• Exclude it from ALL income totals and financial reports\n• Remove it from performance KPIs\n• Mark the linked CRM transaction as rejected\n\nThis action cannot be undone.`;
    if (!confirm(msg)) return;

    try {
      const res = await api.post(`/staff/accounts/income-entries/${inc.id}/reject`);
      if (res.data?.success || res.status === 200) {
        fetchIncomes();
        alert(`Entry ${entryNum} rejected successfully.`);
      }
    } catch (err: any) {
      alert(err.response?.data?.message || "Error rejecting entry.");
    }
  };

  const handleDeleteIncome = async (inc: IncomeEntry) => {
    const entryNum = inc.entry_number || inc.id;
    const msg = `Delete income entry ${entryNum} for ${fmt(
      inc.amount
    )}?\n\nThis entry will be removed from the active list. The audit history will be preserved.\n\nThis action cannot be undone.`;
    if (!confirm(msg)) return;

    try {
      const res = await api.delete(`/staff/accounts/income-entries/${inc.id}`);
      if (res.data?.success || res.status === 200) {
        fetchIncomes();
        alert(`Entry ${entryNum} deleted successfully.`);
      }
    } catch (err: any) {
      alert(err.response?.data?.message || "Error deleting entry.");
    }
  };

  // ============================================================================
  // Confirm Modal Handler
  // ============================================================================

  const openConfirmModal = async (inc: IncomeEntry) => {
    setConfirmingEntry(inc);
    setConfCompanyId(inc.company_id ? String(inc.company_id) : "");
    setConfDestType(inc.destination_type || "");
    setConfDestCompanyId(inc.destination_company_id ? String(inc.destination_company_id) : "");
    setConfDestEmployeeId(inc.destination_employee_id ? String(inc.destination_employee_id) : "");
    setConfSolarVendorId(inc.solar_vendor_id ? String(inc.solar_vendor_id) : "");
    setConfPayerName(inc.payer_name || inc.lead_name || "");
    setConfBankAccountId(inc.bank_account_id ? String(inc.bank_account_id) : "");
    setConfEmployeeBalance(null);

    // Fetch Bank accounts for current company
    if (inc.company_id) {
      loadConfBankAccounts(inc.company_id);
    } else {
      setConfBankAccounts([]);
    }

    // Load initial employee balance if assigned
    if (inc.destination_type === "EMPLOYEE" && inc.destination_employee_id) {
      loadEmployeeBalancePreview(inc.destination_employee_id, inc.amount);
    }

    setIsConfirmModalOpen(true);
  };

  const loadConfBankAccounts = async (compId: number) => {
    try {
      const res = await api.get(`/staff/accounts/ledger-masters/bank-accounts?company_id=${compId}`);
      if (res.data?.accounts) {
        setConfBankAccounts(res.data.accounts);
      } else {
        setConfBankAccounts([]);
      }
    } catch {
      setConfBankAccounts([]);
    }
  };

  const loadEmployeeBalancePreview = async (empId: number, txnAmt: number) => {
    try {
      const res = await api.get(`/staff/accounts/fund-ledger/${empId}/balance`);
      if (res.data?.balance_summary) {
        const b = res.data.balance_summary;
        const prevBal = parseFloat(b.available_balance) || 0;
        setConfEmployeeBalance({
          name: res.data.employee_name || "Employee",
          prevBal,
          txnAmt,
          afterBal: prevBal + txnAmt,
        });
      }
    } catch {
      setConfEmployeeBalance(null);
    }
  };

  const submitConfirm = async () => {
    if (!confirmingEntry) return;

    if (confDestType === "COMPANY_ACCOUNT" && !confDestCompanyId) {
      alert("Please select a Company Account");
      return;
    }
    if (confDestType === "EMPLOYEE" && !confDestEmployeeId) {
      alert("Please select an Employee");
      return;
    }
    if (confDestType === "SOLAR_VENDOR" && !confSolarVendorId) {
      alert("Please select a Solar Vendor");
      return;
    }

    setConfirmSubmitting(true);
    try {
      const payload: any = {
        status: "CONFIRMED",
        confirmation_type: "TAXED",
        company_id: confCompanyId ? parseInt(confCompanyId) : null,
        destination_type: confDestType || null,
      };

      if (confDestType === "COMPANY_ACCOUNT") {
        payload.destination_company_id = parseInt(confDestCompanyId) || null;
      } else if (confDestType === "EMPLOYEE") {
        payload.destination_employee_id = parseInt(confDestEmployeeId) || null;
      } else if (confDestType === "SOLAR_VENDOR") {
        payload.solar_vendor_id = parseInt(confSolarVendorId) || null;
      }

      if (confBankAccountId) {
        payload.bank_account_id = parseInt(confBankAccountId);
        const selAcc = confBankAccounts.find((a) => a.id === parseInt(confBankAccountId));
        if (selAcc) payload.bank_account_name = selAcc.account_name;
      }

      if (confPayerName.trim()) {
        payload.payer_name = confPayerName.trim();
      }

      const res = await api.patch(`/staff/accounts/income-entries/${confirmingEntry.id}/status`, payload);
      if (res.data?.success || res.status === 200) {
        setIsConfirmModalOpen(false);
        setIsDetailModalOpen(false);
        fetchIncomes();
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.response?.data?.message || "Failed to confirm entry");
    } finally {
      setConfirmSubmitting(false);
    }
  };

  // ============================================================================
  // Edit Destination Modal Handler
  // ============================================================================

  const openEditModal = async (inc: IncomeEntry) => {
    setEditingEntry(inc);
    setEditIncomeDate(inc.income_date ? inc.income_date.slice(0, 10) : "");
    setEditDestType(inc.destination_type || "");
    setEditDestCompanyId(inc.destination_company_id ? String(inc.destination_company_id) : "");
    setEditDestEmployeeId(inc.destination_employee_id ? String(inc.destination_employee_id) : "");
    setEditEmployeeBalance(null);

    if (inc.destination_type === "EMPLOYEE" && inc.destination_employee_id) {
      loadEditEmployeeBalance(inc.destination_employee_id, inc.company_id);
    }

    setIsEditModalOpen(true);
  };

  const loadEditEmployeeBalance = async (empId: number, compId?: number) => {
    try {
      const cq = compId ? `?company_id=${compId}` : "";
      const res = await api.get(`/staff/accounts/fund-ledger/${empId}/balance${cq}`);
      if (res.data?.balance_summary) {
        setEditEmployeeBalance(res.data.balance_summary);
      }
    } catch {
      setEditEmployeeBalance(null);
    }
  };

  const submitEdit = async () => {
    if (!editingEntry) return;

    if (editDestType === "COMPANY_ACCOUNT" && !editDestCompanyId) {
      alert("Please select a Company Account");
      return;
    }
    if (editDestType === "EMPLOYEE" && !editDestEmployeeId) {
      alert("Please select an Employee");
      return;
    }

    setEditSubmitting(true);
    try {
      const payload: any = {
        income_date: editIncomeDate || undefined,
        destination_type: editDestType || null,
        destination_company_id: editDestType === "COMPANY_ACCOUNT" ? parseInt(editDestCompanyId) || null : null,
        destination_employee_id: editDestType === "EMPLOYEE" ? parseInt(editDestEmployeeId) || null : null,
      };

      const res = await api.put(`/staff/accounts/income-entries/${editingEntry.id}`, payload);
      if (res.data?.success || res.status === 200) {
        setIsEditModalOpen(false);
        fetchIncomes();
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.response?.data?.message || "Failed to update entry");
    } finally {
      setEditSubmitting(false);
    }
  };

  // ============================================================================
  // Create Income Entry Modal Handler
  // ============================================================================

  const handleCreateIncome = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.company_id || !createForm.income_date || !createForm.income_source_id || !createForm.amount) {
      alert("Please fill all required fields");
      return;
    }

    setCreateSubmitting(true);
    try {
      const payload = {
        company_id: parseInt(createForm.company_id),
        income_date: createForm.income_date,
        income_source_id: parseInt(createForm.income_source_id),
        revenue_category_id: createForm.revenue_category_id ? parseInt(createForm.revenue_category_id) : null,
        amount: parseFloat(createForm.amount),
        payment_mode: createForm.payment_mode,
        payment_type: createForm.payment_type || null,
        payer_name: createForm.payer_name.trim() || null,
        payment_reference: createForm.payment_reference.trim() || null,
        narration: createForm.narration.trim() || null,
        show_in_ledger: createForm.show_in_ledger,
      };

      const res = await api.post("/staff/accounts/income-entries", payload);
      if (res.status === 200 || res.status === 201) {
        setIsCreateModalOpen(false);
        setCreateForm({
          company_id: "",
          income_date: new Date().toISOString().split("T")[0],
          income_source_id: "",
          revenue_category_id: "",
          amount: "",
          payment_mode: "UPI",
          payment_type: "",
          payer_name: "",
          payment_reference: "",
          narration: "",
          show_in_ledger: false,
        });
        fetchIncomes();
        alert("Income entry created successfully.");
      }
    } catch (err: any) {
      if (err.response?.status === 409) {
        const data = err.response.data || {};
        const dupRef = data.duplicate_entry ? ` (Existing: ${data.duplicate_entry})` : "";
        alert(
          `⚠️ Duplicate Entry Blocked${dupRef}\n\n${
            data.message || "A similar entry already exists for this customer, amount, date, and payment mode."
          }\n\nIf this is a separate collection, please adjust the date or amount before saving.`
        );
      } else {
        alert(err.response?.data?.message || err.response?.data?.detail || "Failed to create income entry");
      }
    } finally {
      setCreateSubmitting(false);
    }
  };

  // ============================================================================
  // Tab Switching & Sub-Tab Loaders
  // ============================================================================

  useEffect(() => {
    if (activeTab === "estimations") {
      fetchEstimationData();
    } else if (activeTab === "solarvendor") {
      fetchSolarVendorLedger(1);
    } else if (activeTab === "deleted") {
      fetchDeletedIncomes();
    }
  }, [activeTab]);

  // Estimations Data Loader
  const fetchEstimationData = async () => {
    setEstLoading(true);
    try {
      const cq = filterCompany ? `?company_id=${filterCompany}` : "";
      const [rIn, rOut, rStock, rSummary] = await Promise.allSettled([
        api.get(`/staff/accounts/income-entries/estimations${cq}`),
        api.get(`/staff/accounts/income-entries/estimations/out${cq}`),
        api.get(`/staff/accounts/income-entries/estimations/stock${cq}`),
        api.get(`/staff/accounts/income-entries/estimations/executive-summary${cq}`),
      ]);

      let inList: IncomeEntry[] = [];
      if (rIn.status === "fulfilled" && rIn.value.data) {
        inList = rIn.value.data.entries || [];
        setEstInEntries(inList);
      }
      if (rOut.status === "fulfilled" && rOut.value.data) {
        setEstOutRecords(rOut.value.data.records || []);
      }
      if (rStock.status === "fulfilled" && rStock.value.data) {
        setEstStock(rStock.value.data.stock_movements || []);
      }
      if (rSummary.status === "fulfilled" && rSummary.value.data) {
        setEstSummary(rSummary.value.data.summary || null);
      }

      // Aggregate payments
      const paymentsArr: EstPaymentRecord[] = [];
      for (const e of inList.slice(0, 30)) {
        try {
          const rp = await api.get(`/staff/accounts/income-entries/${e.id}/estimation-payments`);
          if (rp.data?.payments) {
            rp.data.payments.forEach((p: any) => {
              p._entry_number = e.entry_number;
              paymentsArr.push(p);
            });
          }
        } catch {}
      }
      setEstPayments(paymentsArr);
    } catch (e) {
      console.error("Error loading estimation data", e);
    } finally {
      setEstLoading(false);
    }
  };

  // OUT Records Modal & Actions
  const handleSaveOutRecord = async () => {
    const compId = filterCompany || (companies[0] ? String(companies[0].id) : "");
    if (!compId) {
      alert("Please select a company from the Company filter.");
      return;
    }
    if (!outForm.entry_date || !outForm.description || !outForm.amount) {
      alert("Please enter Date, Description, and Amount.");
      return;
    }

    try {
      const payload = {
        company_id: parseInt(compId),
        entry_date: outForm.entry_date,
        description: outForm.description.trim(),
        estimated_amount: parseFloat(outForm.amount) || 0,
        party_name: outForm.party_name.trim() || null,
        account_name: outForm.account_name.trim() || null,
        notes: outForm.notes.trim() || null,
      };

      if (editingOutId) {
        await api.put(`/staff/accounts/income-entries/estimations/out/${editingOutId}`, payload);
      } else {
        await api.post("/staff/accounts/income-entries/estimations/out", payload);
      }
      setIsOutModalOpen(false);
      setEditingOutId(null);
      fetchEstimationData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to save OUT record");
    }
  };

  const handleDeleteOutRecord = async (id: number) => {
    if (!confirm("Delete this OUT planning record?")) return;
    try {
      await api.delete(`/staff/accounts/income-entries/estimations/out/${id}`);
      fetchEstimationData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete");
    }
  };

  const handleDeleteEstPayment = async (entryId: number, paymentId: number) => {
    if (!confirm("Delete this estimate payment record?")) return;
    try {
      await api.delete(`/staff/accounts/income-entries/${entryId}/estimation-payments/${paymentId}`);
      fetchEstimationData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete payment");
    }
  };

  // Solar Vendor Ledger Actions
  const fetchSolarVendorLedger = async (page = 1) => {
    setSvlLoading(true);
    setSvlPage(page);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "30" });
      if (svlVendorFilter) params.append("vendor_id", svlVendorFilter);
      if (svlDirectionFilter) params.append("direction", svlDirectionFilter);
      if (svlFromDate) params.append("date_from", svlFromDate);
      if (svlToDate) params.append("date_to", svlToDate);

      const res = await api.get(`/staff/accounts/solar-vendor-ledger?${params.toString()}`);
      if (res.data) {
        setSvlRows(res.data.rows || []);
        setSvlSummary(res.data.summary || {});
        setSvlTotal(res.data.total || 0);
      }
    } catch (e) {
      console.error(e);
      setSvlRows([]);
    } finally {
      setSvlLoading(false);
    }
  };

  const handleRecordSvlReturn = async () => {
    if (!svlReturnForm.solar_vendor_id || !svlReturnForm.transaction_date || !svlReturnForm.amount) {
      alert("Please select a vendor and fill in Date and Amount.");
      return;
    }
    try {
      const payload = {
        solar_vendor_id: parseInt(svlReturnForm.solar_vendor_id),
        transaction_date: svlReturnForm.transaction_date,
        amount: parseFloat(svlReturnForm.amount),
        customer_name: svlReturnForm.customer_name.trim() || null,
        payment_mode: svlReturnForm.payment_mode || null,
        utr_reference: svlReturnForm.utr_reference.trim() || null,
        notes: svlReturnForm.notes.trim() || null,
      };

      await api.post("/staff/accounts/solar-vendor-ledger/return", payload);
      setIsSvlReturnModalOpen(false);
      setSvlReturnForm({
        solar_vendor_id: "",
        transaction_date: new Date().toISOString().split("T")[0],
        amount: "",
        customer_name: "",
        payment_mode: "",
        utr_reference: "",
        notes: "",
      });
      fetchSolarVendorLedger(1);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to record return");
    }
  };

  const handleSaveSvlEdit = async () => {
    if (!svlEditRow) return;
    if (!svlEditForm.transaction_date) {
      alert("Date is required.");
      return;
    }
    try {
      const payload = {
        transaction_date: svlEditForm.transaction_date,
        customer_name: svlEditForm.customer_name.trim() || null,
        payment_mode: svlEditForm.payment_mode || null,
        utr_reference: svlEditForm.utr_reference.trim() || null,
        notes: svlEditForm.notes.trim() || null,
      };

      await api.patch(`/staff/accounts/solar-vendor-ledger/${svlEditRow.id}`, payload);
      setIsSvlEditModalOpen(false);
      setSvlEditRow(null);
      fetchSolarVendorLedger(svlPage);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Save failed");
    }
  };

  const handleDeleteSvlRow = async (id: number) => {
    if (!confirm("Delete this return entry?")) return;
    try {
      await api.delete(`/staff/accounts/solar-vendor-ledger/${id}`);
      fetchSolarVendorLedger(svlPage);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Delete failed");
    }
  };

  const exportSvlStatement = async () => {
    try {
      let allRows: SolarVendorLedgerRow[] = [];
      let summary: SolarVendorLedgerSummary = {};
      let curPage = 1;
      let totalPages = 1;

      do {
        const params = new URLSearchParams({ page: String(curPage), page_size: "500" });
        if (svlVendorFilter) params.append("vendor_id", svlVendorFilter);
        if (svlDirectionFilter) params.append("direction", svlDirectionFilter);
        if (svlFromDate) params.append("date_from", svlFromDate);
        if (svlToDate) params.append("date_to", svlToDate);

        const res = await api.get(`/staff/accounts/solar-vendor-ledger?${params.toString()}`);
        if (res.data) {
          allRows = allRows.concat(res.data.rows || []);
          if (curPage === 1) summary = res.data.summary || {};
          totalPages = Math.ceil((res.data.total || 0) / 500) || 1;
          curPage++;
        }
      } while (curPage <= totalPages);

      if (!allRows.length) {
        alert("No entries to export.");
        return;
      }

      const vendorName = svlVendorFilter
        ? solarVendors.find((v) => String(v.id) === String(svlVendorFilter))?.vendor_name ||
          allRows[0]?.vendor_name ||
          "All Vendors"
        : "All Vendors";

      const generatedOn = new Date().toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      });

      const periodLabel =
        svlFromDate || svlToDate
          ? `${svlFromDate ? fmtDate(svlFromDate) : "Beginning"} – ${svlToDate ? fmtDate(svlToDate) : "Today"}`
          : "All Dates";

      let tableRows = "";
      allRows.forEach((row) => {
        const isRec = row.direction === "RECEIVED";
        const dr = isRec
          ? `<td class="amt dr">${fmt2(row.amount)}</td><td class="amt"></td>`
          : `<td class="amt"></td><td class="amt cr">${fmt2(row.amount)}</td>`;
        tableRows += `<tr>
          <td>${fmtDate(row.transaction_date)}</td>
          <td>${row.vendor_name || "—"}</td>
          <td>${row.customer_name || "—"}</td>
          ${dr}
          <td>${row.payment_mode || "—"}</td>
          <td>${row.utr_reference || "—"}</td>
          <td>${[row.utr_reference ? "UTR: " + row.utr_reference : "", row.notes || ""].filter(Boolean).join(" | ") || "—"}</td>
        </tr>`;
      });

      const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
      <title>Cash Transaction Records — ${vendorName}</title>
      <style>
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; color-adjust: exact !important; }
        body { font-family: Arial, sans-serif; font-size: 12px; color: #1a1a1a; margin: 0; padding: 24px; background: #fff; }
        .letterhead { display: flex; align-items: flex-start; justify-content: space-between; border-bottom: 3px solid #0369a1; padding-bottom: 12px; margin-bottom: 16px; }
        .brand-name { font-size: 24px; font-weight: 800; color: #0369a1; letter-spacing: -0.5px; }
        .brand-sub  { font-size: 11px; color: #475569; margin-top: 2px; }
        .stmt-title { text-align: right; }
        .stmt-title h2 { margin: 0; font-size: 16px; font-weight: 700; color: #1e293b; }
        .stmt-title p  { margin: 3px 0 0; font-size: 11px; color: #475569; }
        .meta-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; background: #f8fafc !important; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; }
        .meta-item label { font-size: 9px; text-transform: uppercase; letter-spacing: .6px; color: #475569; font-weight: 700; display: block; margin-bottom: 3px; }
        .meta-item span  { font-size: 13px; font-weight: 700; color: #0f172a; }
        table { width: 100%; border-collapse: collapse; font-size: 11px; border: 1px solid #cbd5e1; }
        thead tr { background: #1e293b !important; }
        thead th { padding: 9px 10px; text-align: left; font-weight: 700; white-space: nowrap; color: #ffffff !important; border-right: 1px solid #334155; }
        thead th.amt { text-align: right; }
        tbody tr { border-bottom: 1px solid #e2e8f0; }
        tbody tr:nth-child(even) { background: #f8fafc !important; }
        td { padding: 7px 10px; vertical-align: top; color: #1a1a1a; border-right: 1px solid #e2e8f0; }
        td.amt { text-align: right; font-weight: 600; white-space: nowrap; }
        td.dr  { color: #166534 !important; font-weight: 700; }
        td.cr  { color: #92400e !important; font-weight: 700; }
        .summary-row { margin-top: 16px; display: flex; gap: 12px; justify-content: flex-end; }
        .sum-box { border: 1.5px solid #cbd5e1; border-radius: 6px; padding: 10px 16px; text-align: right; min-width: 180px; background: #f8fafc !important; }
        .sum-box label { font-size: 9px; text-transform: uppercase; letter-spacing: .5px; color: #475569; font-weight: 700; display: block; margin-bottom: 4px; }
        .sum-box span  { font-size: 16px; font-weight: 800; }
        .sum-box.dr-box { background: #f0fdf4 !important; border-color: #86efac; }
        .sum-box.dr-box span { color: #166534 !important; }
        .sum-box.cr-box { background: #fffbeb !important; border-color: #fcd34d; }
        .sum-box.cr-box span { color: #92400e !important; }
        .sum-box.bl-box { background: #eff6ff !important; border-color: #93c5fd; }
        .sum-box.bl-box span { color: #1d4ed8 !important; }
        .footer { margin-top: 24px; border-top: 1px solid #cbd5e1; padding-top: 8px; font-size: 10px; color: #475569; text-align: center; }
        @media print { body { padding: 10px; } @page { margin: 12mm; size: A4 landscape; } }
      </style></head><body>
      <div class="letterhead">
        <div>
          <div class="brand-name">Myntreal</div>
          <div class="brand-sub">SFMS — Smart Financial Management System</div>
        </div>
        <div class="stmt-title">
          <h2>Cash Transaction Records</h2>
          <p>Generated on: ${generatedOn}</p>
        </div>
      </div>
      <div class="meta-grid">
        <div class="meta-item"><label>Vendor</label><span>${vendorName}</span></div>
        <div class="meta-item"><label>Period</label><span>${periodLabel}</span></div>
        <div class="meta-item"><label>Total Entries</label><span>${allRows.length}</span></div>
      </div>
      <table>
        <thead><tr>
          <th>Date</th><th>Vendor</th><th>Customer</th>
          <th class="amt">DR (Received)</th><th class="amt">CR (Returned)</th>
          <th>Mode</th><th>UTR / Ref</th><th>Notes</th>
        </tr></thead>
        <tbody>${tableRows}</tbody>
      </table>
      <div class="summary-row">
        <div class="sum-box dr-box"><label>Total DR (Received)</label><span>${fmt2(summary.total_received)}</span></div>
        <div class="sum-box cr-box"><label>Total CR (Returned)</label><span>${fmt2(summary.total_returned)}</span></div>
        <div class="sum-box bl-box"><label>Balance Due from Vendor</label><span>${fmt2(summary.balance)}</span></div>
      </div>
      <div style="margin-top:18px;padding:10px 14px;background:#fefce8 !important;border:1px solid #fde68a;border-radius:6px;font-size:10px;color:#78350f;line-height:1.6;">
        <strong>⚠ Important Note:</strong> This document reflects cash transaction records only (payments received from customers and returns from vendors). For formal invoice reconciliation, refer to the Ledger Master records in Myntreal SFMS.
      </div>
      <div class="footer">Myntreal SFMS &nbsp;|&nbsp; Cash Transaction Records &nbsp;|&nbsp; Confidential</div>
      <script>window.onload = function(){ window.print(); }<\/script>
      </body></html>`;

      const win = window.open("", "_blank");
      if (!win) {
        alert("Pop-up blocked. Please allow pop-ups for this site.");
        return;
      }
      win.document.write(html);
      win.document.close();
    } catch (e: any) {
      alert("Export failed: " + e.message);
    }
  };

  // Deleted Incomes Loader
  const fetchDeletedIncomes = async () => {
    setDeletedLoading(true);
    try {
      const res = await api.get("/staff/accounts/income-entries/deleted");
      if (res.data?.income_entries) {
        setDeletedIncomes(res.data.income_entries);
      }
    } catch {
      setDeletedIncomes([]);
    } finally {
      setDeletedLoading(false);
    }
  };

  // ============================================================================
  // Render Tab Content Handlers
  // ============================================================================

  // 1. Transaction Wise
  const renderTransactionsTab = () => {
    if (loading) {
      return (
        <div className="p-16 flex flex-col items-center justify-center text-gray-500">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-600 mb-3" />
          <p className="font-medium text-sm">Loading income transactions...</p>
        </div>
      );
    }

    if (!filteredIncomes.length) {
      return (
        <div className="p-16 text-center text-gray-500 bg-white rounded-xl border border-gray-100 shadow-sm">
          <Layers className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-800">No Income Entries Found</h3>
          <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
            Create your first income entry or wait for CRM transactions to auto-sync.
          </p>
        </div>
      );
    }

    const estimatedCount = filteredIncomes.filter((i) => i.status === "ESTIMATED").length;

    return (
      <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-600" />
            <h3 className="font-bold text-sm text-gray-900">All Transactions</h3>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full font-medium">
              {filteredIncomes.length} records
            </span>
            {estimatedCount > 0 && (
              <span className="text-xs text-orange-700 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded-full flex items-center gap-1 font-medium">
                <Calculator className="w-3 h-3" />
                {estimatedCount} estimated
              </span>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50/80 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100 select-none">
                <th
                  className="py-3 px-3.5 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    if (sortField === "entry_number") setSortOrder(sortOrder === "asc" ? "desc" : "asc");
                    else {
                      setSortField("entry_number");
                      setSortOrder("desc");
                    }
                  }}
                >
                  <div className="flex items-center gap-1">
                    Entry #
                    <ArrowUpDown className="w-3 h-3 text-gray-400" />
                  </div>
                </th>
                <th
                  className="py-3 px-3.5 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    if (sortField === "income_date") setSortOrder(sortOrder === "asc" ? "desc" : "asc");
                    else {
                      setSortField("income_date");
                      setSortOrder("desc");
                    }
                  }}
                >
                  <div className="flex items-center gap-1">
                    Date
                    <ArrowUpDown className="w-3 h-3 text-gray-400" />
                  </div>
                </th>
                <th className="py-3 px-3.5">Company</th>
                <th className="py-3 px-3.5">Category</th>
                <th className="py-3 px-3.5">Deal #</th>
                <th className="py-3 px-3.5">Customer / Payer</th>
                <th className="py-3 px-3.5">City</th>
                <th
                  className="py-3 px-3.5 text-right cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    if (sortField === "amount") setSortOrder(sortOrder === "asc" ? "desc" : "asc");
                    else {
                      setSortField("amount");
                      setSortOrder("desc");
                    }
                  }}
                >
                  <div className="flex items-center justify-end gap-1">
                    Amount
                    <ArrowUpDown className="w-3 h-3 text-gray-400" />
                  </div>
                </th>
                <th className="py-3 px-3.5">Mode</th>
                <th className="py-3 px-3.5">Pay Type</th>
                <th className="py-3 px-3.5">Txn Type</th>
                <th className="py-3 px-3.5">Collected By</th>
                <th className="py-3 px-3.5">Owner</th>
                <th className="py-3 px-3.5">Staff Updated</th>
                <th className="py-3 px-3.5">Status</th>
                <th className="py-3 px-3.5">CRM</th>
                <th className="py-3 px-3.5">Destination</th>
                <th className="py-3 px-3.5 text-center">Ledger</th>
                <th className="py-3 px-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredIncomes.map((inc) => {
                const isRejected = inc.status === "REJECTED";
                const isEstimated = inc.status === "ESTIMATED";
                const st = STATUS_MAP[inc.status] || {
                  label: inc.status,
                  bg: "bg-gray-50",
                  text: "text-gray-700",
                  border: "border-gray-200",
                };

                return (
                  <tr
                    key={inc.id}
                    className={`hover:bg-emerald-50/20 transition-colors ${
                      isRejected ? "opacity-60 bg-red-50/20" : isEstimated ? "bg-amber-50/20" : ""
                    }`}
                  >
                    <td className="py-3 px-3.5 font-mono text-[11px] font-medium text-gray-800">
                      {inc.entry_number || `#${inc.id}`}
                    </td>
                    <td className="py-3 px-3.5 whitespace-nowrap text-gray-600">{fmtDate(inc.income_date)}</td>
                    <td className="py-3 px-3.5 text-gray-800 max-w-[130px] truncate" title={inc.company_name}>
                      {inc.company_name || "—"}
                    </td>
                    <td className="py-3 px-3.5">
                      {inc.revenue_category_name ? (
                        <span className="px-2 py-0.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded text-[10px] font-medium">
                          {inc.revenue_category_name}
                        </span>
                      ) : inc.income_source_name ? (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-[10px] font-medium">
                          {inc.income_source_name}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3.5">
                      {inc.deal_code ? (
                        <code className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-[10px] font-mono font-semibold">
                          {inc.deal_code}
                        </code>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3.5 font-medium text-gray-900 max-w-[160px] truncate">
                      {inc.lead_name || inc.payer_name || "—"}
                    </td>
                    <td className="py-3 px-3.5 text-gray-500 text-[11px]">{inc.lead_city || inc.payer_city || "—"}</td>
                    <td
                      className={`py-3 px-3.5 text-right font-mono font-bold text-[13px] ${
                        isRejected ? "line-through text-gray-400" : "text-emerald-600"
                      }`}
                    >
                      {fmt(inc.amount)}
                    </td>
                    <td className="py-3 px-3.5 text-gray-700 text-[11px] font-medium">{inc.payment_mode || "—"}</td>
                    <td className="py-3 px-3.5">
                      {inc.payment_type ? (
                        <span className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-[10px] font-medium">
                          {inc.payment_type}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3.5">
                      {inc.transaction_type ? (
                        <span className="capitalize px-1.5 py-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded text-[10px] font-medium">
                          {inc.transaction_type}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3.5 text-gray-600 text-[11px]">{inc.collected_by_name || "—"}</td>
                    <td className="py-3 px-3.5">
                      {inc.lead_owner_name ? (
                        <div>
                          <span className="text-[9px] text-gray-400 block leading-tight">
                            {(inc.revenue_category_name || "").toLowerCase().includes("service")
                              ? "Raised by"
                              : "Assigned to"}
                          </span>
                          <span className="font-medium text-gray-700 text-[11px]">{inc.lead_owner_name}</span>
                        </div>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3.5 text-purple-700 text-[11px]">
                      {inc.updated_by_name
                        ? `${inc.updated_by_name}${
                            inc.updated_by_emp_code ? ` (${inc.updated_by_emp_code})` : ""
                          }`
                        : "—"}
                    </td>
                    <td className="py-3 px-3.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${st.bg} ${st.text} ${st.border}`}
                      >
                        {inc.status === "CONFIRMED"
                          ? inc.confirmation_type === "ESTIMATED"
                            ? "Estimated ✓"
                            : "Confirmed ✓"
                          : st.label}
                      </span>
                    </td>
                    <td className="py-3 px-3.5">
                      {inc.crm_transaction_id ? (
                        <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded text-[10px] font-semibold">
                          #{inc.crm_transaction_id}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-[10px]">Manual</span>
                      )}
                    </td>
                    <td className="py-3 px-3.5 whitespace-nowrap">
                      {!inc.destination_type ? (
                        <span className="inline-flex items-center gap-1 text-[10px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded font-medium">
                          <HelpCircle className="w-2.5 h-2.5" /> Unassigned
                        </span>
                      ) : inc.destination_type === "COMPANY_ACCOUNT" ? (
                        <span className="inline-flex items-center gap-1 text-[10px] text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded font-medium">
                          <Building2 className="w-2.5 h-2.5" /> {inc.destination_company_name || "Company"}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-medium">
                          <User className="w-2.5 h-2.5" /> {inc.destination_employee_name || "Employee"}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3.5 text-center">
                      <input
                        type="checkbox"
                        checked={!!inc.show_in_ledger}
                        onChange={(e) => handleToggleLedger(inc.id, e.target.checked)}
                        className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 w-3.5 h-3.5 cursor-pointer"
                        title="Toggle Show in Ledger"
                      />
                    </td>
                    <td className="py-3 px-3.5 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        {isRejected ? (
                          <span className="text-[10px] text-gray-400 font-medium">Rejected</span>
                        ) : (
                          <>
                            <button
                              onClick={() => openEditModal(inc)}
                              className="p-1 text-sky-600 hover:text-sky-800 hover:bg-sky-50 rounded transition-colors"
                              title="Edit destination & date"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>

                            {inc.status === "PENDING" && (
                              <>
                                <button
                                  onClick={() => openConfirmModal(inc)}
                                  className="px-2 py-0.5 bg-emerald-600 text-white rounded text-[10px] font-semibold hover:bg-emerald-700 transition-colors shadow-2xs"
                                >
                                  Confirm
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "EXCEPTION_TALLY")}
                                  className="px-1.5 py-0.5 border border-pink-500 text-pink-600 rounded text-[10px] font-medium hover:bg-pink-50 transition-colors"
                                >
                                  Exception
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "ADJUSTMENT")}
                                  className="px-1.5 py-0.5 border border-blue-500 text-blue-600 rounded text-[10px] font-medium hover:bg-blue-50 transition-colors"
                                >
                                  Adjust
                                </button>
                              </>
                            )}

                            {inc.status === "ESTIMATED" && (
                              <>
                                <button
                                  onClick={() => openConfirmModal(inc)}
                                  className="px-2 py-0.5 bg-orange-600 text-white rounded text-[10px] font-semibold hover:bg-orange-700 transition-colors"
                                >
                                  Confirm Now
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "PENDING")}
                                  className="px-1.5 py-0.5 border border-amber-500 text-amber-600 rounded text-[10px] font-medium hover:bg-amber-50 transition-colors"
                                >
                                  Revert
                                </button>
                              </>
                            )}

                            {inc.status === "CONFIRMED" && (
                              <>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "TALLY_DONE")}
                                  className="px-2 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-semibold hover:bg-indigo-700 transition-colors"
                                >
                                  Tally Done
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "EXCEPTION_TALLY")}
                                  className="px-1.5 py-0.5 border border-pink-500 text-pink-600 rounded text-[10px] font-medium hover:bg-pink-50 transition-colors"
                                >
                                  Exception
                                </button>
                              </>
                            )}

                            {(inc.status === "EXCEPTION_TALLY" || inc.status === "ADJUSTMENT") && (
                              <>
                                <button
                                  onClick={() => openConfirmModal(inc)}
                                  className="px-2 py-0.5 bg-emerald-600 text-white rounded text-[10px] font-semibold hover:bg-emerald-700 transition-colors"
                                >
                                  Confirm
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "TALLY_DONE")}
                                  className="px-2 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-semibold hover:bg-indigo-700 transition-colors"
                                >
                                  Tally Done
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "PENDING")}
                                  className="px-1.5 py-0.5 border border-amber-500 text-amber-600 rounded text-[10px] font-medium hover:bg-amber-50 transition-colors"
                                >
                                  Revert
                                </button>
                              </>
                            )}

                            {inc.status === "TALLY_DONE" && (
                              <>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "EXCEPTION_TALLY")}
                                  className="px-1.5 py-0.5 border border-pink-500 text-pink-600 rounded text-[10px] font-medium hover:bg-pink-50 transition-colors"
                                >
                                  Exception
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(inc.id, "ADJUSTMENT")}
                                  className="px-1.5 py-0.5 border border-blue-500 text-blue-600 rounded text-[10px] font-medium hover:bg-blue-50 transition-colors"
                                >
                                  Adjust
                                </button>
                              </>
                            )}

                            {canReject && (
                              <button
                                onClick={() => handleRejectIncome(inc)}
                                className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                                title="Reject entry"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                              </button>
                            )}

                            {canDelete && (
                              <button
                                onClick={() => handleDeleteIncome(inc)}
                                className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                                title="Delete entry"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 2. Date Wise
  const renderDateWiseTab = () => {
    const groups: Record<string, IncomeEntry[]> = {};
    viewableIncomes.forEach((inc) => {
      const dateKey = inc.income_date || "Unknown";
      if (!groups[dateKey]) groups[dateKey] = [];
      groups[dateKey].push(inc);
    });

    const sortedDates = Object.keys(groups).sort((a, b) => b.localeCompare(a));
    if (!sortedDates.length) {
      return (
        <div className="p-12 text-center text-gray-500 bg-white rounded-xl border border-gray-100">
          No records found.
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {sortedDates.map((dateKey, idx) => {
          const items = groups[dateKey];
          const totalAmt = items.reduce((s, i) => s + (Number(i.amount) || 0), 0);
          const pending = items.filter((i) => i.status === "PENDING").length;
          const confirmed = items.filter((i) => i.status === "CONFIRMED").length;
          const tallyDone = items.filter((i) => i.status === "TALLY_DONE").length;
          const isOpen = openDateGroups[dateKey] ?? idx === 0;

          return (
            <div
              key={dateKey}
              className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden transition-all"
            >
              <div
                onClick={() =>
                  setOpenDateGroups((prev) => ({
                    ...prev,
                    [dateKey]: !isOpen,
                  }))
                }
                className="px-5 py-3.5 bg-emerald-50/30 hover:bg-emerald-50/60 cursor-pointer flex items-center justify-between transition-colors border-b border-gray-100"
              >
                <div className="flex items-center gap-3">
                  <ChevronRight
                    className={`w-4 h-4 text-emerald-600 transition-transform duration-200 ${
                      isOpen ? "rotate-90" : ""
                    }`}
                  />
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-emerald-700" />
                    <span className="font-bold text-sm text-gray-900">{fmtDate(dateKey)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs font-semibold">
                  <span className="text-gray-500">{items.length} txns</span>
                  <span className="text-emerald-600 font-mono text-sm">{fmt(totalAmt)}</span>
                  {pending > 0 && <span className="text-amber-600">{pending} Pending</span>}
                  {confirmed > 0 && <span className="text-emerald-600">{confirmed} Confirmed</span>}
                  {tallyDone > 0 && <span className="text-indigo-600">{tallyDone} Tally Done</span>}
                </div>
              </div>

              {isOpen && (
                <div className="p-0 overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                        <th className="py-2.5 px-4">Entry #</th>
                        <th className="py-2.5 px-4">Deal #</th>
                        <th className="py-2.5 px-4">Customer</th>
                        <th className="py-2.5 px-4">City</th>
                        <th className="py-2.5 px-4 text-right">Amount</th>
                        <th className="py-2.5 px-4">Mode</th>
                        <th className="py-2.5 px-4">Type</th>
                        <th className="py-2.5 px-4">Collected By</th>
                        <th className="py-2.5 px-4">Status</th>
                        <th className="py-2.5 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {items.map((i) => (
                        <tr key={i.id} className="hover:bg-gray-50/60 transition-colors">
                          <td className="py-2.5 px-4 font-mono font-medium text-gray-800">{i.entry_number || `#${i.id}`}</td>
                          <td className="py-2.5 px-4 font-mono text-emerald-700 font-semibold">{i.deal_code || "—"}</td>
                          <td className="py-2.5 px-4 font-medium text-gray-900">{i.lead_name || i.payer_name || "—"}</td>
                          <td className="py-2.5 px-4 text-gray-500">{i.lead_city || i.payer_city || "—"}</td>
                          <td className="py-2.5 px-4 text-right font-mono font-bold text-emerald-600">{fmt(i.amount)}</td>
                          <td className="py-2.5 px-4 text-gray-600">{i.payment_mode || "—"}</td>
                          <td className="py-2.5 px-4 capitalize">{i.transaction_type || "—"}</td>
                          <td className="py-2.5 px-4 text-gray-600">{i.collected_by_name || "—"}</td>
                          <td className="py-2.5 px-4">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-800">
                              {i.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-4 text-right">
                            <button
                              onClick={() => openConfirmModal(i)}
                              className="text-xs text-emerald-600 hover:text-emerald-800 font-semibold"
                            >
                              Manage
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // 3. Customer Wise
  const renderCustomerWiseTab = () => {
    const groups: Record<string, { items: IncomeEntry[]; city: string }> = {};
    viewableIncomes.forEach((inc) => {
      const name = inc.lead_name || inc.payer_name || "Unknown";
      if (!groups[name]) {
        groups[name] = { items: [], city: inc.lead_city || inc.payer_city || "—" };
      }
      groups[name].items.push(inc);
    });

    const entries = Object.entries(groups).sort(
      (a, b) =>
        b[1].items.reduce((s, i) => s + (Number(i.amount) || 0), 0) -
        a[1].items.reduce((s, i) => s + (Number(i.amount) || 0), 0)
    );

    if (!entries.length) {
      return (
        <div className="p-12 text-center text-gray-500 bg-white rounded-xl border border-gray-100">
          No records found.
        </div>
      );
    }

    return (
      <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-emerald-600" />
            <h3 className="font-bold text-sm text-gray-900">Customer Summary</h3>
          </div>
          <span className="text-xs text-gray-500">{entries.length} customers</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                <th className="py-3 px-4">Customer Name</th>
                <th className="py-3 px-4">City</th>
                <th className="py-3 px-4 text-center">Transactions</th>
                <th className="py-3 px-4 text-right">Total Amount</th>
                <th className="py-3 px-4 text-center">Pending</th>
                <th className="py-3 px-4 text-center">Confirmed</th>
                <th className="py-3 px-4 text-center">Tally Done</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entries.map(([name, g]) => {
                const total = g.items.reduce((s, i) => s + (Number(i.amount) || 0), 0);
                const pending = g.items.filter((i) => i.status === "PENDING").length;
                const confirmed = g.items.filter((i) => i.status === "CONFIRMED").length;
                const tallyDone = g.items.filter((i) => i.status === "TALLY_DONE").length;

                return (
                  <tr key={name} className="hover:bg-gray-50/60 transition-colors">
                    <td className="py-3 px-4 font-bold text-gray-900">{name}</td>
                    <td className="py-3 px-4 text-gray-500">{g.city}</td>
                    <td className="py-3 px-4 text-center font-medium text-gray-700">{g.items.length}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600 text-[13px]">
                      {fmt(total)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-amber-600">{pending}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-emerald-600">{confirmed}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-indigo-600">{tallyDone}</span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => {
                          setDetailModalTitle(`Customer: ${name}`);
                          setDetailModalItems(g.items);
                          setIsDetailModalOpen(true);
                        }}
                        className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded text-xs font-semibold transition-colors inline-flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" /> View
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 4. Lead Owner Wise
  const renderLeadOwnerTab = () => {
    const groups: Record<string, { items: IncomeEntry[]; empCode: string }> = {};
    viewableIncomes.forEach((inc) => {
      const name = inc.lead_owner_name || "Unassigned";
      if (!groups[name]) {
        groups[name] = { items: [], empCode: inc.lead_owner_emp_code || "—" };
      }
      groups[name].items.push(inc);
    });

    const entries = Object.entries(groups).sort(
      (a, b) =>
        b[1].items.reduce((s, i) => s + (Number(i.amount) || 0), 0) -
        a[1].items.reduce((s, i) => s + (Number(i.amount) || 0), 0)
    );

    return (
      <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-emerald-600" />
            <h3 className="font-bold text-sm text-gray-900">Lead Owner Summary</h3>
          </div>
          <span className="text-xs text-gray-500">{entries.length} owners</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                <th className="py-3 px-4">Lead Owner</th>
                <th className="py-3 px-4">Emp Code</th>
                <th className="py-3 px-4 text-center">Transactions</th>
                <th className="py-3 px-4 text-right">Total Amount</th>
                <th className="py-3 px-4 text-center">Pending</th>
                <th className="py-3 px-4 text-center">Confirmed</th>
                <th className="py-3 px-4 text-center">Tally Done</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entries.map(([name, g]) => {
                const total = g.items.reduce((s, i) => s + (Number(i.amount) || 0), 0);
                const pending = g.items.filter((i) => i.status === "PENDING").length;
                const confirmed = g.items.filter((i) => i.status === "CONFIRMED").length;
                const tallyDone = g.items.filter((i) => i.status === "TALLY_DONE").length;

                return (
                  <tr key={name} className="hover:bg-gray-50/60 transition-colors">
                    <td className="py-3 px-4 font-bold text-gray-900">{name}</td>
                    <td className="py-3 px-4">
                      <code className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded font-mono text-[11px]">
                        {g.empCode}
                      </code>
                    </td>
                    <td className="py-3 px-4 text-center font-medium text-gray-700">{g.items.length}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600 text-[13px]">
                      {fmt(total)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-amber-600">{pending}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-emerald-600">{confirmed}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-indigo-600">{tallyDone}</span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => {
                          setDetailModalTitle(`Lead Owner: ${name}`);
                          setDetailModalItems(g.items);
                          setIsDetailModalOpen(true);
                        }}
                        className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded text-xs font-semibold transition-colors inline-flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" /> View
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 5. Employee Wise
  const renderEmployeeTab = () => {
    const groups: Record<string, { items: IncomeEntry[]; empCode: string }> = {};
    viewableIncomes.forEach((inc) => {
      const key =
        inc.collected_by_name ||
        (inc.destination_type === "EMPLOYEE" && inc.destination_employee_name
          ? inc.destination_employee_name
          : null) ||
        "Unknown";
      const empCode =
        inc.collected_by_emp_code ||
        (inc.destination_type === "EMPLOYEE" && inc.destination_employee_emp_code
          ? inc.destination_employee_emp_code
          : null) ||
        "—";
      if (!groups[key]) groups[key] = { items: [], empCode };
      groups[key].push(inc);
    });

    const entries = Object.entries(groups).sort(
      (a, b) =>
        b[1].items.reduce((s, i) => s + (Number(i.amount) || 0), 0) -
        a[1].items.reduce((s, i) => s + (Number(i.amount) || 0), 0)
    );

    return (
      <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-emerald-600" />
            <h3 className="font-bold text-sm text-gray-900">Employee Collection Summary</h3>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                <th className="py-3 px-4">Employee Name</th>
                <th className="py-3 px-4">Emp Code</th>
                <th className="py-3 px-4 text-center">Collections</th>
                <th className="py-3 px-4 text-right">Total Collected</th>
                <th className="py-3 px-4 text-center">Pending</th>
                <th className="py-3 px-4 text-center">Confirmed</th>
                <th className="py-3 px-4 text-center">Tally Done</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entries.map(([name, g]) => {
                const total = g.items.reduce((s, i) => s + (Number(i.amount) || 0), 0);
                const pending = g.items.filter((i) => i.status === "PENDING").length;
                const confirmed = g.items.filter((i) => i.status === "CONFIRMED").length;
                const tallyDone = g.items.filter((i) => i.status === "TALLY_DONE").length;

                return (
                  <tr key={name} className="hover:bg-gray-50/60 transition-colors">
                    <td className="py-3 px-4 font-bold text-gray-900">{name}</td>
                    <td className="py-3 px-4">
                      <code className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded font-mono text-[11px]">
                        {g.empCode}
                      </code>
                    </td>
                    <td className="py-3 px-4 text-center font-medium text-gray-700">{g.items.length}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600 text-[13px]">
                      {fmt(total)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-amber-600">{pending}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-emerald-600">{confirmed}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-indigo-600">{tallyDone}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 6. Location Wise
  const renderLocationTab = () => {
    const groups: Record<string, IncomeEntry[]> = {};
    viewableIncomes.forEach((inc) => {
      const city = inc.lead_city || inc.payer_city || "Unknown";
      const state = inc.lead_state || inc.payer_state || "";
      const locKey = state ? `${city}, ${state}` : city;
      if (!groups[locKey]) groups[locKey] = [];
      groups[locKey].push(inc);
    });

    const entries = Object.entries(groups).sort((a, b) => b[1].length - a[1].length);

    return (
      <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-600" />
            <h3 className="font-bold text-sm text-gray-900">Location Summary</h3>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                <th className="py-3 px-4">Location</th>
                <th className="py-3 px-4 text-center">Transactions</th>
                <th className="py-3 px-4 text-right">Total Amount</th>
                <th className="py-3 px-4 text-center">Pending</th>
                <th className="py-3 px-4 text-center">Confirmed</th>
                <th className="py-3 px-4 text-center">Tally Done</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entries.map(([loc, items]) => {
                const total = items.reduce((s, i) => s + (Number(i.amount) || 0), 0);
                const pending = items.filter((i) => i.status === "PENDING").length;
                const confirmed = items.filter((i) => i.status === "CONFIRMED").length;
                const tallyDone = items.filter((i) => i.status === "TALLY_DONE").length;

                return (
                  <tr key={loc} className="hover:bg-gray-50/60 transition-colors">
                    <td className="py-3 px-4 font-bold text-gray-900 flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-gray-400" /> {loc}
                    </td>
                    <td className="py-3 px-4 text-center font-medium text-gray-700">{items.length}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600 text-[13px]">
                      {fmt(total)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-amber-600">{pending}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-emerald-600">{confirmed}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-semibold text-indigo-600">{tallyDone}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 7. Estimations Tab
  const renderEstimationsTab = () => {
    return (
      <div className="space-y-4">
        {/* Estimations Sub-Navigation */}
        <div className="flex items-center gap-1 border-b border-gray-200 overflow-x-auto pb-px">
          {[
            { key: "in", label: "IN Estimates", icon: ArrowDownLeft, color: "text-emerald-600" },
            { key: "out", label: "OUT Planning", icon: ArrowUpRight, color: "text-red-600" },
            { key: "payments", label: "Payments", icon: CreditCard, color: "text-purple-600" },
            { key: "stock", label: "Stock Movement", icon: Package, color: "text-sky-600" },
            { key: "executive", label: "Executive Summary", icon: BarChart3, color: "text-orange-600" },
          ].map((t) => {
            const Icon = t.icon;
            const active = estSubTab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setEstSubTab(t.key as EstSubTab)}
                className={`px-4 py-2.5 text-xs font-bold rounded-t-lg transition-all flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                  active
                    ? "border-orange-600 text-orange-700 bg-white shadow-2xs"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100/60"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${t.color}`} />
                {t.label}
              </button>
            );
          })}
        </div>

        {estLoading ? (
          <div className="p-12 flex justify-center items-center text-orange-600">
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            <span className="text-xs font-semibold">Loading estimation records...</span>
          </div>
        ) : (
          <>
            {estSubTab === "in" && (
              <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ArrowDownLeft className="w-4 h-4 text-emerald-600" />
                    <h3 className="font-bold text-sm text-gray-900">IN Estimates ({estInEntries.length})</h3>
                  </div>
                  <span className="font-mono font-bold text-emerald-600 text-sm">
                    {fmt(estInEntries.reduce((s, e) => s + (Number(e.amount) || 0), 0))} total
                  </span>
                </div>
                {!estInEntries.length ? (
                  <div className="p-12 text-center text-gray-500">No estimated income entries found.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                          <th className="py-3 px-4">Entry #</th>
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Company</th>
                          <th className="py-3 px-4">Payer</th>
                          <th className="py-3 px-4 text-right">Amount</th>
                          <th className="py-3 px-4">Mode</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {estInEntries.map((e) => (
                          <tr key={e.id} className="hover:bg-gray-50/60 transition-colors">
                            <td className="py-3 px-4 font-mono font-medium text-gray-800">{e.entry_number || `#${e.id}`}</td>
                            <td className="py-3 px-4 text-gray-600">{fmtDate(e.income_date)}</td>
                            <td className="py-3 px-4 text-gray-700">{e.company_name || "—"}</td>
                            <td className="py-3 px-4 font-medium text-gray-900">{e.payer_name || "—"}</td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600">{fmt(e.amount)}</td>
                            <td className="py-3 px-4 text-gray-600">{e.payment_mode || "—"}</td>
                            <td className="py-3 px-4 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  onClick={() => openConfirmModal(e)}
                                  className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold shadow-2xs"
                                >
                                  Confirm
                                </button>
                                <button
                                  onClick={() => handleUpdateStatus(e.id, "PENDING")}
                                  className="px-2.5 py-1 border border-amber-500 text-amber-600 hover:bg-amber-50 rounded text-xs font-medium"
                                >
                                  Revert
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {estSubTab === "out" && (
              <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ArrowUpRight className="w-4 h-4 text-red-600" />
                    <h3 className="font-bold text-sm text-gray-900">OUT Planning ({estOutRecords.length})</h3>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-red-600 text-sm">
                      {fmt(estOutRecords.reduce((s, r) => s + (Number(r.estimated_amount) || 0), 0))} planned
                    </span>
                    <button
                      onClick={() => {
                        setEditingOutId(null);
                        setOutForm({
                          entry_date: new Date().toISOString().split("T")[0],
                          amount: "",
                          description: "",
                          party_name: "",
                          account_name: "",
                          notes: "",
                        });
                        setIsOutModalOpen(true);
                      }}
                      className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 shadow-2xs"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add OUT Record
                    </button>
                  </div>
                </div>
                {!estOutRecords.length ? (
                  <div className="p-12 text-center text-gray-500">No OUT planning records found.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Description</th>
                          <th className="py-3 px-4">Party</th>
                          <th className="py-3 px-4">Account</th>
                          <th className="py-3 px-4 text-right">Amount</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {estOutRecords.map((r) => (
                          <tr key={r.id} className="hover:bg-gray-50/60 transition-colors">
                            <td className="py-3 px-4 text-gray-600">{fmtDate(r.entry_date)}</td>
                            <td className="py-3 px-4 font-medium text-gray-900">{r.description}</td>
                            <td className="py-3 px-4 text-gray-700">{r.party_name || "—"}</td>
                            <td className="py-3 px-4 text-gray-600">{r.account_name || "—"}</td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-red-600">
                              {fmt(r.estimated_amount)}
                            </td>
                            <td className="py-3 px-4">
                              <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-[10px] font-semibold">
                                {r.status || "PENDING"}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  onClick={() => {
                                    setEditingOutId(r.id);
                                    setOutForm({
                                      entry_date: r.entry_date,
                                      amount: String(r.estimated_amount),
                                      description: r.description,
                                      party_name: r.party_name || "",
                                      account_name: r.account_name || "",
                                      notes: r.notes || "",
                                    });
                                    setIsOutModalOpen(true);
                                  }}
                                  className="p-1 text-gray-600 hover:text-gray-900 rounded"
                                >
                                  <Edit className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleDeleteOutRecord(r.id)}
                                  className="p-1 text-red-600 hover:text-red-800 rounded"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {estSubTab === "payments" && (
              <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-purple-600" />
                    <h3 className="font-bold text-sm text-gray-900">Estimate Payments ({estPayments.length})</h3>
                  </div>
                  <span className="font-mono font-bold text-emerald-600 text-sm">
                    {fmt(estPayments.reduce((s, p) => s + (Number(p.amount) || 0), 0))} total
                  </span>
                </div>
                {!estPayments.length ? (
                  <div className="p-12 text-center text-gray-500">No estimate payments recorded.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                          <th className="py-3 px-4">Entry #</th>
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4 text-right">Amount</th>
                          <th className="py-3 px-4">Mode</th>
                          <th className="py-3 px-4">Party</th>
                          <th className="py-3 px-4">Account</th>
                          <th className="py-3 px-4">Notes</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {estPayments.map((p) => (
                          <tr key={p.id} className="hover:bg-gray-50/60 transition-colors">
                            <td className="py-3 px-4 font-mono font-medium text-gray-800">
                              {p._entry_number || `#${p.income_entry_id}`}
                            </td>
                            <td className="py-3 px-4 text-gray-600">{fmtDate(p.payment_date)}</td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600">
                              {fmt(p.amount)}
                            </td>
                            <td className="py-3 px-4 text-gray-600">{p.payment_mode || "—"}</td>
                            <td className="py-3 px-4 font-medium text-gray-900">{p.party_name || "—"}</td>
                            <td className="py-3 px-4 text-gray-600">{p.account_received || "—"}</td>
                            <td className="py-3 px-4 text-gray-500">{p.notes || "—"}</td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => handleDeleteEstPayment(p.income_entry_id, p.id)}
                                className="p-1 text-red-600 hover:text-red-800 rounded"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {estSubTab === "stock" && (
              <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Package className="w-4 h-4 text-sky-600" />
                    <h3 className="font-bold text-sm text-gray-900">
                      Estimate Stock Movements ({estStock.length})
                    </h3>
                  </div>
                  <span className="text-xs text-gray-500">Soft deductions — not reflected in ledger</span>
                </div>
                {!estStock.length ? (
                  <div className="p-12 text-center text-gray-500">No estimate stock movements found.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Item</th>
                          <th className="py-3 px-4">Code</th>
                          <th className="py-3 px-4 text-right">Qty Out</th>
                          <th className="py-3 px-4">Reference</th>
                          <th className="py-3 px-4">Type</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {estStock.map((s, idx) => (
                          <tr key={idx} className="hover:bg-gray-50/60 transition-colors">
                            <td className="py-3 px-4 text-gray-600">{fmtDate(s.transaction_date)}</td>
                            <td className="py-3 px-4 font-medium text-gray-900">{s.item_name || "—"}</td>
                            <td className="py-3 px-4">
                              <code className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded font-mono text-[11px]">
                                {s.item_code || "—"}
                              </code>
                            </td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-red-600">
                              {s.quantity_out || 0}
                            </td>
                            <td className="py-3 px-4 font-mono text-gray-600">{s.reference_number || "—"}</td>
                            <td className="py-3 px-4">
                              <span className="px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded text-[10px] font-semibold">
                                Estimate
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {estSubTab === "executive" && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
                      <ArrowDownLeft className="w-3.5 h-3.5 text-emerald-600" /> IN Estimated Income
                    </div>
                    <div className="text-xl font-extrabold text-emerald-600">
                      {fmt(estSummary?.in_estimates?.total || 0)}
                    </div>
                    <div className="text-[11px] text-gray-400 mt-1">
                      {estSummary?.in_estimates?.count || 0} entries
                    </div>
                  </div>

                  <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
                      <ArrowUpRight className="w-3.5 h-3.5 text-red-600" /> OUT Planned Spend
                    </div>
                    <div className="text-xl font-extrabold text-red-600">
                      {fmt(estSummary?.out_estimates?.total || 0)}
                    </div>
                    <div className="text-[11px] text-gray-400 mt-1">
                      {estSummary?.out_estimates?.count || 0} records
                    </div>
                  </div>

                  <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
                      <CreditCard className="w-3.5 h-3.5 text-purple-600" /> Payments Collected
                    </div>
                    <div className="text-xl font-extrabold text-purple-600">
                      {fmt(estSummary?.payments?.total || 0)}
                    </div>
                    <div className="text-[11px] text-gray-400 mt-1">
                      {estSummary?.payments?.count || 0} payments
                    </div>
                  </div>

                  <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
                    <div className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
                      <Wallet className="w-3.5 h-3.5 text-blue-600" /> Net Estimated Cash
                    </div>
                    <div
                      className={`text-xl font-extrabold ${
                        (estSummary?.net_estimated || 0) >= 0 ? "text-emerald-600" : "text-red-600"
                      }`}
                    >
                      {fmt(Math.abs(estSummary?.net_estimated || 0))}
                    </div>
                    <div className="text-[11px] text-gray-400 mt-1">
                      {(estSummary?.net_estimated || 0) >= 0 ? "Surplus balance" : "Deficit balance"}
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl border border-gray-200/80 p-5 shadow-xs text-xs text-gray-600 leading-relaxed space-y-2">
                  <h4 className="font-bold text-gray-900 text-sm mb-2 flex items-center gap-1.5">
                    <HelpCircle className="w-4 h-4 text-gray-400" /> Understanding Estimations
                  </h4>
                  <p>
                    <strong>IN Estimates:</strong> Income entries currently in the estimation phase. They remain isolated from confirmed financial reports until confirmed with TAXED confirmation.
                  </p>
                  <p>
                    <strong>OUT Planning:</strong> Informational outgoing commitments with <em>zero ledger impact</em>, designed for planning and visibility.
                  </p>
                  <p>
                    <strong>Payments:</strong> Ad-hoc payments recorded against estimation vouchers for operational tracking.
                  </p>
                  <p>
                    <strong>Stock Movement:</strong> Soft allocations of spare parts tied to estimation service tickets.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  // 8. Solar Vendor Ledger Tab
  const renderSolarVendorTab = () => {
    return (
      <div className="space-y-4">
        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-xl border border-gray-200/80 shadow-xs flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Solar Vendor</label>
            <select
              value={svlVendorFilter}
              onChange={(e) => setSvlVendorFilter(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 min-w-[180px] focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Vendors</option>
              {solarVendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.vendor_name} {v.vendor_code ? `(${v.vendor_code})` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Direction</label>
            <select
              value={svlDirectionFilter}
              onChange={(e) => setSvlDirectionFilter(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All</option>
              <option value="RECEIVED">Received (Customer → MNR)</option>
              <option value="RETURNED">Returned (Vendor → MNR)</option>
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">From</label>
            <input
              type="date"
              value={svlFromDate}
              onChange={(e) => setSvlFromDate(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">To</label>
            <input
              type="date"
              value={svlToDate}
              onChange={(e) => setSvlToDate(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5"
            />
          </div>

          <button
            onClick={() => fetchSolarVendorLedger(1)}
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors shadow-2xs"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>

          <button
            onClick={() => {
              setSvlReturnForm({
                solar_vendor_id: svlVendorFilter || "",
                transaction_date: new Date().toISOString().split("T")[0],
                amount: "",
                customer_name: "",
                payment_mode: "",
                utr_reference: "",
                notes: "",
              });
              setIsSvlReturnModalOpen(true);
            }}
            className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors shadow-2xs"
          >
            <Plus className="w-3.5 h-3.5" /> Record Return
          </button>

          <button
            onClick={exportSvlStatement}
            className="px-3.5 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors shadow-2xs"
          >
            <Printer className="w-3.5 h-3.5" /> Export Statement
          </button>
        </div>

        {/* Summary Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4">
            <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 mb-1 flex items-center gap-1">
              <ArrowDownLeft className="w-3.5 h-3.5" /> Total Received
            </div>
            <div className="text-xl font-black text-emerald-700">{fmt2(svlSummary.total_received)}</div>
            <div className="text-[11px] text-gray-500 mt-1">{svlSummary.count_received || 0} entries</div>
          </div>

          <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4">
            <div className="text-[10px] font-bold uppercase tracking-wider text-amber-800 mb-1 flex items-center gap-1">
              <ArrowUpRight className="w-3.5 h-3.5" /> Total Returned
            </div>
            <div className="text-xl font-black text-amber-700">{fmt2(svlSummary.total_returned)}</div>
            <div className="text-[11px] text-gray-500 mt-1">{svlSummary.count_returned || 0} entries</div>
          </div>

          <div className="bg-blue-50/70 border border-blue-200 rounded-xl p-4">
            <div className="text-[10px] font-bold uppercase tracking-wider text-blue-800 mb-1 flex items-center gap-1">
              <Wallet className="w-3.5 h-3.5" /> Balance Due from Vendor
            </div>
            <div className="text-xl font-black text-blue-700">{fmt2(svlSummary.balance)}</div>
            <div className="text-[11px] text-gray-500 mt-1">Pending balance</div>
          </div>
        </div>

        {/* Ledger Table */}
        <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-900 text-white font-bold tracking-wider">
                  <th colSpan={9} className="py-2.5 px-4 text-xs">
                    TRANSACTION STATEMENT — Solar Vendor Ledger
                  </th>
                </tr>
                <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-200">
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Vendor</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4 text-right text-emerald-700">DR (Received)</th>
                  <th className="py-3 px-4 text-right text-amber-700">CR (Returned)</th>
                  <th className="py-3 px-4">Mode</th>
                  <th className="py-3 px-4">UTR/Ref</th>
                  <th className="py-3 px-4">Notes</th>
                  <th className="py-3 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {svlLoading ? (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-gray-500">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-600" />
                      Loading solar vendor transactions...
                    </td>
                  </tr>
                ) : !svlRows.length ? (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-gray-500">
                      No transactions found.
                    </td>
                  </tr>
                ) : (
                  svlRows.map((row) => {
                    const isRec = row.direction === "RECEIVED";
                    return (
                      <tr key={row.id} className="hover:bg-gray-50/60 transition-colors">
                        <td className="py-3 px-4 text-gray-700 whitespace-nowrap">{fmtDate(row.transaction_date)}</td>
                        <td className="py-3 px-4 font-semibold text-gray-900">{row.vendor_name || "—"}</td>
                        <td className="py-3 px-4 text-gray-600">{row.customer_name || "—"}</td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600">
                          {isRec ? fmt2(row.amount) : "—"}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-amber-600">
                          {!isRec ? fmt2(row.amount) : "—"}
                        </td>
                        <td className="py-3 px-4 text-gray-600">{row.payment_mode || "—"}</td>
                        <td className="py-3 px-4">
                          {row.utr_reference ? (
                            <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded font-mono text-[10px] font-semibold">
                              {row.utr_reference}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="py-3 px-4 text-gray-500 max-w-[200px] truncate">{row.notes || "—"}</td>
                        <td className="py-3 px-4 text-center whitespace-nowrap">
                          <button
                            onClick={() => {
                              setSvlEditRow(row);
                              setSvlEditForm({
                                transaction_date: row.transaction_date ? row.transaction_date.slice(0, 10) : "",
                                payment_mode: row.payment_mode || "",
                                customer_name: row.customer_name || "",
                                utr_reference: row.utr_reference || "",
                                notes: row.notes || "",
                              });
                              setIsSvlEditModalOpen(true);
                            }}
                            className="p-1 text-indigo-600 hover:text-indigo-800 rounded"
                            title="Edit"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          {!isRec && (
                            <button
                              onClick={() => handleDeleteSvlRow(row.id)}
                              className="p-1 text-red-600 hover:text-red-800 rounded"
                              title="Delete return"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {svlTotal > 30 && (
            <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span>{svlTotal} total entries</span>
              <div className="flex items-center gap-2">
                <button
                  disabled={svlPage <= 1}
                  onClick={() => fetchSolarVendorLedger(svlPage - 1)}
                  className="px-2.5 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  Prev
                </button>
                <span>
                  Page {svlPage} of {Math.ceil(svlTotal / 30)}
                </span>
                <button
                  disabled={svlPage >= Math.ceil(svlTotal / 30)}
                  onClick={() => fetchSolarVendorLedger(svlPage + 1)}
                  className="px-2.5 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 9. Executive Dashboard Tab
  const renderExecDashboardTab = () => {
    // Filter by period
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    let from: Date | null = null;
    let to: Date = new Date(today);

    if (edPeriod === "ftd") {
      from = new Date(today);
    } else if (edPeriod === "week") {
      from = new Date(today);
      from.setDate(today.getDate() - today.getDay());
    } else if (edPeriod === "month") {
      from = new Date(today.getFullYear(), today.getMonth(), 1);
    } else if (edPeriod === "fy") {
      const m = today.getMonth();
      from = new Date(m >= 3 ? today.getFullYear() : today.getFullYear() - 1, 3, 1);
    } else if (edPeriod === "custom" && edFrom && edTo) {
      from = new Date(edFrom);
      to = new Date(edTo);
    }

    to.setHours(23, 59, 59, 999);

    const periodData = allIncomes.filter((i) => {
      if (i.is_deleted) return false;
      if (!from) return true;
      const d = new Date(i.income_date || i.created_at || "");
      return d >= from && d <= to;
    });

    const active = periodData.filter((i) => i.status !== "REJECTED");
    const totalAmt = active.reduce((s, i) => s + (Number(i.amount) || 0), 0);
    const confirmedAmt = active.filter((i) => i.status === "CONFIRMED").reduce((s, i) => s + (Number(i.amount) || 0), 0);
    const pendingAmt = active.filter((i) => i.status === "PENDING").reduce((s, i) => s + (Number(i.amount) || 0), 0);
    const estimatedAmt = active.filter((i) => i.status === "ESTIMATED").reduce((s, i) => s + (Number(i.amount) || 0), 0);
    const tallyAmt = active.filter((i) => i.status === "TALLY_DONE").reduce((s, i) => s + (Number(i.amount) || 0), 0);
    const cashAmt = active
      .filter((i) => (i.payment_mode || "").toUpperCase() === "CASH")
      .reduce((s, i) => s + (Number(i.amount) || 0), 0);
    const bankAmt = active
      .filter((i) => (i.payment_mode || "").toUpperCase() !== "CASH")
      .reduce((s, i) => s + (Number(i.amount) || 0), 0);

    // Grouping Helper
    const buildGroup = (keyFn: (i: IncomeEntry) => string) => {
      const m: Record<string, IncomeEntry[]> = {};
      active.forEach((i) => {
        const k = keyFn(i) || "Unknown";
        if (!m[k]) m[k] = [];
        m[k].push(i);
      });
      return Object.entries(m)
        .map(([key, items]) => ({
          key,
          count: items.length,
          total: items.reduce((s, i) => s + (Number(i.amount) || 0), 0),
          confirmed: items.filter((i) => i.status === "CONFIRMED").length,
          pending: items.filter((i) => i.status === "PENDING").length,
          tally: items.filter((i) => i.status === "TALLY_DONE").length,
        }))
        .sort((a, b) => b.total - a.total);
    };

    const companyBreakdown = buildGroup((i) => i.company_name || "Unassigned");
    const categoryBreakdown = buildGroup((i) => i.revenue_category_name || i.income_source_name || "General");
    const modeBreakdown = buildGroup((i) => i.payment_mode || "Other");
    const topOwners = buildGroup((i) => i.lead_owner_name || "Unassigned").slice(0, 10);

    return (
      <div className="space-y-5">
        {/* Period Selector */}
        <div className="bg-white p-4 rounded-xl border border-gray-200/80 shadow-xs flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            {[
              { k: "ftd", l: "FTD" },
              { k: "week", l: "This Week" },
              { k: "month", l: "This Month" },
              { k: "fy", l: "This FY" },
              { k: "all", l: "Overall" },
              { k: "custom", l: "Custom Range" },
            ].map(({ k, l }) => (
              <button
                key={k}
                onClick={() => setEdPeriod(k as EdPeriod)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                  edPeriod === k
                    ? "bg-purple-700 text-white shadow-2xs"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {l}
              </button>
            ))}
          </div>

          {edPeriod === "custom" && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-gray-500 font-medium">From:</span>
              <input
                type="date"
                value={edFrom}
                onChange={(e) => setEdFrom(e.target.value)}
                className="border border-gray-300 rounded px-2 py-1"
              />
              <span className="text-gray-500 font-medium">To:</span>
              <input
                type="date"
                value={edTo}
                onChange={(e) => setEdTo(e.target.value)}
                className="border border-gray-300 rounded px-2 py-1"
              />
            </div>
          )}
        </div>

        {/* Executive KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {[
            { label: "Total Collected", val: totalAmt, count: active.length, color: "text-gray-900", icon: Banknote },
            { label: "Confirmed ✓", val: confirmedAmt, count: active.filter((i) => i.status === "CONFIRMED").length, color: "text-emerald-600", icon: CheckCircle2 },
            { label: "Pending", val: pendingAmt, count: active.filter((i) => i.status === "PENDING").length, color: "text-amber-600", icon: Clock },
            { label: "Estimated", val: estimatedAmt, count: active.filter((i) => i.status === "ESTIMATED").length, color: "text-orange-600", icon: Calculator },
            { label: "Tally Done", val: tallyAmt, count: active.filter((i) => i.status === "TALLY_DONE").length, color: "text-indigo-600", icon: Check },
            { label: "Cash In", val: cashAmt, count: active.filter((i) => (i.payment_mode || "").toUpperCase() === "CASH").length, color: "text-sky-600", icon: Wallet },
            { label: "Bank / UPI", val: bankAmt, count: active.filter((i) => (i.payment_mode || "").toUpperCase() !== "CASH").length, color: "text-purple-600", icon: CreditCard },
          ].map((c, idx) => {
            const Icon = c.icon;
            return (
              <div key={idx} className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1 mb-1">
                  <Icon className="w-3 h-3" /> {c.label}
                </div>
                <div className={`text-lg font-black ${c.color}`}>{fmt(c.val)}</div>
                <div className="text-[10px] text-gray-400 mt-0.5">{c.count} entries</div>
              </div>
            );
          })}
        </div>

        {/* Breakdown Grids */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Company Breakdown */}
          <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
            <h4 className="font-bold text-sm text-gray-900 mb-3 flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-purple-600" /> Collection by Company
            </h4>
            <div className="space-y-2">
              {companyBreakdown.map((item) => {
                const pct = totalAmt > 0 ? (item.total / totalAmt) * 100 : 0;
                return (
                  <div key={item.key} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-gray-700">{item.key}</span>
                      <span className="font-mono text-emerald-600">
                        {fmt(item.total)} ({pct.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Revenue Category Breakdown */}
          <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
            <h4 className="font-bold text-sm text-gray-900 mb-3 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-purple-600" /> Revenue Category Breakdown
            </h4>
            <div className="space-y-2">
              {categoryBreakdown.map((item) => {
                const pct = totalAmt > 0 ? (item.total / totalAmt) * 100 : 0;
                return (
                  <div key={item.key} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-gray-700">{item.key}</span>
                      <span className="font-mono text-emerald-600">
                        {fmt(item.total)} ({pct.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div className="bg-cyan-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Payment Mode Breakdown */}
          <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
            <h4 className="font-bold text-sm text-gray-900 mb-3 flex items-center gap-1.5">
              <CreditCard className="w-4 h-4 text-purple-600" /> Payment Mode Share
            </h4>
            <div className="space-y-2">
              {modeBreakdown.map((item) => {
                const pct = totalAmt > 0 ? (item.total / totalAmt) * 100 : 0;
                return (
                  <div key={item.key} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-gray-700">{item.key}</span>
                      <span className="font-mono text-emerald-600">
                        {fmt(item.total)} ({pct.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div className="bg-purple-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Top 10 Lead Owners */}
          <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs">
            <h4 className="font-bold text-sm text-gray-900 mb-3 flex items-center gap-1.5">
              <Briefcase className="w-4 h-4 text-purple-600" /> Top Performing Lead Owners
            </h4>
            <div className="space-y-2">
              {topOwners.map((item) => {
                const pct = totalAmt > 0 ? (item.total / totalAmt) * 100 : 0;
                return (
                  <div key={item.key} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-gray-700">{item.key}</span>
                      <span className="font-mono text-emerald-600">
                        {fmt(item.total)} ({pct.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div className="bg-amber-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 10. Deleted Tab
  const renderDeletedTab = () => {
    if (deletedLoading) {
      return (
        <div className="p-16 flex justify-center items-center text-gray-500">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          <span className="text-xs">Loading deleted transactions audit log...</span>
        </div>
      );
    }

    if (!deletedIncomes.length) {
      return (
        <div className="p-16 text-center text-gray-500 bg-white rounded-xl border border-gray-100">
          <Trash2 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-800">No Deleted Income Entries</h3>
          <p className="text-xs text-gray-500 mt-1">Deleted transactions are logged here for audit purposes.</p>
        </div>
      );
    }

    return (
      <div className="bg-white rounded-xl border border-gray-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trash2 className="w-4 h-4 text-red-600" />
            <h3 className="font-bold text-sm text-gray-900">Deleted Income Entries ({deletedIncomes.length})</h3>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                <th className="py-3 px-4">Entry #</th>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Customer / Payer</th>
                <th className="py-3 px-4 text-right">Amount</th>
                <th className="py-3 px-4">Company</th>
                <th className="py-3 px-4">Mode</th>
                <th className="py-3 px-4">Deleted By</th>
                <th className="py-3 px-4">Deleted At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {deletedIncomes.map((e) => (
                <tr key={e.id} className="hover:bg-red-50/20 transition-colors">
                  <td className="py-3 px-4 font-mono font-medium text-gray-800">{e.entry_number || `#${e.id}`}</td>
                  <td className="py-3 px-4 text-gray-600">{fmtDate(e.income_date)}</td>
                  <td className="py-3 px-4 font-medium text-gray-900">{e.payer_name || e.lead_name || "—"}</td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-red-600">{fmt(e.amount)}</td>
                  <td className="py-3 px-4 text-gray-700">{e.company_name || "—"}</td>
                  <td className="py-3 px-4 text-gray-600">{e.payment_mode || "—"}</td>
                  <td className="py-3 px-4 text-gray-700 font-medium">
                    {e.deleted_by_name || "—"} {e.deleted_by_emp_code ? `(${e.deleted_by_emp_code})` : ""}
                  </td>
                  <td className="py-3 px-4 text-gray-500">{fmtDate(e.deleted_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-5 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight flex items-center gap-2.5">
            <Layers className="w-7 h-7 text-emerald-600" />
            Income Entries
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">
            SFMS income tracking, fund allocations, customer ledger, and CRM auto-sync
          </p>
        </div>

        <button
          onClick={() => {
            setCreateForm({
              company_id: "",
              income_date: new Date().toISOString().split("T")[0],
              income_source_id: "",
              revenue_category_id: "",
              amount: "",
              payment_mode: "UPI",
              payment_type: "",
              payer_name: "",
              payment_reference: "",
              narration: "",
              show_in_ledger: false,
            });
            setFormCategories([]);
            setIsCreateModalOpen(true);
          }}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl font-semibold text-xs sm:text-sm shadow-md hover:shadow-lg transition-all transform active:scale-95"
        >
          <Plus className="w-4 h-4" /> New Income Entry
        </button>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        <div className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs text-center">
          <div className="text-lg sm:text-xl font-extrabold text-gray-900">{summaryMetrics.totalCount}</div>
          <div className="text-[10px] sm:text-[11px] font-semibold text-gray-500 uppercase mt-0.5">Total Entries</div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs text-center">
          <div className="text-lg sm:text-xl font-extrabold text-emerald-600 font-mono">
            {fmt(summaryMetrics.activeAmount)}
          </div>
          <div className="text-[10px] sm:text-[11px] font-semibold text-gray-500 uppercase mt-0.5">Active Amount</div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs text-center">
          <div className="text-lg sm:text-xl font-extrabold text-amber-600">{summaryMetrics.pendingCount}</div>
          <div className="text-[10px] sm:text-[11px] font-semibold text-gray-500 uppercase mt-0.5">Pending</div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs text-center">
          <div className="text-lg sm:text-xl font-extrabold text-emerald-600">{summaryMetrics.confirmedCount}</div>
          <div className="text-[10px] sm:text-[11px] font-semibold text-gray-500 uppercase mt-0.5">Confirmed</div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs text-center">
          <div className="text-lg sm:text-xl font-extrabold text-indigo-600">{summaryMetrics.tallyDoneCount}</div>
          <div className="text-[10px] sm:text-[11px] font-semibold text-gray-500 uppercase mt-0.5">Tally Done</div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs text-center">
          <div className="text-lg sm:text-xl font-extrabold text-red-600">{summaryMetrics.rejectedCount}</div>
          <div className="text-[10px] sm:text-[11px] font-semibold text-gray-500 uppercase mt-0.5">Rejected</div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200/80 p-3.5 shadow-xs text-center">
          <div className="text-lg sm:text-xl font-extrabold text-orange-600">{summaryMetrics.estimatedCount}</div>
          <div className="text-[10px] sm:text-[11px] font-semibold text-gray-500 uppercase mt-0.5">Estimated</div>
        </div>
      </div>

      {/* Filter Section */}
      <div className="bg-white rounded-xl border border-gray-200/80 p-4 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Status */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Status</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Status</option>
              <option value="PENDING">Pending</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="EXCEPTION_TALLY">Exception for Tally</option>
              <option value="ADJUSTMENT">Adjustment</option>
              <option value="TALLY_DONE">Tally Entry Done</option>
              <option value="ESTIMATED">Estimated</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          {/* Company */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Company</label>
            <select
              value={filterCompany}
              onChange={(e) => setFilterCompany(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Companies</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name || c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Category */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Category</label>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Categories</option>
              {filterCategories.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          {/* Payment Mode */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Payment Mode</label>
            <select
              value={filterPaymentMode}
              onChange={(e) => setFilterPaymentMode(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Modes</option>
              <option value="UPI">UPI</option>
              <option value="CASH">Cash</option>
              <option value="NEFT">NEFT</option>
              <option value="RTGS">RTGS</option>
              <option value="CHEQUE">Cheque</option>
              <option value="CARD">Card</option>
              <option value="BANK">Bank</option>
            </select>
          </div>

          {/* Payment Type */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Payment Type</label>
            <select
              value={filterPaymentType}
              onChange={(e) => setFilterPaymentType(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Types</option>
              <option value="BANK">Bank</option>
              <option value="CASH">Cash</option>
            </select>
          </div>

          {/* Txn Type */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Txn Type</label>
            <select
              value={filterTxnType}
              onChange={(e) => setFilterTxnType(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Types</option>
              <option value="advance">Advance</option>
              <option value="partial">Partial</option>
              <option value="final">Final</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 pt-1">
          {/* Source */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Source</label>
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Sources</option>
              <option value="crm">CRM Auto-Sync</option>
              <option value="manual">Manual Entry</option>
            </select>
          </div>

          {/* Destination Type */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Destination Type</label>
            <select
              value={filterDestType}
              onChange={(e) => setFilterDestType(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">All Destinations</option>
              <option value="UNASSIGNED">Unassigned</option>
              <option value="EMPLOYEE">Employee</option>
              <option value="COMPANY_ACCOUNT">Company Account</option>
            </select>
          </div>

          {/* Destination Search */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Destination Match</label>
            <input
              type="text"
              placeholder="Name, emp code, company..."
              value={filterDestSearch}
              onChange={(e) => setFilterDestSearch(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* From Date */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">From Date</label>
            <input
              type="date"
              value={filterFromDate}
              onChange={(e) => setFilterFromDate(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* To Date */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">To Date</label>
            <input
              type="date"
              value={filterToDate}
              onChange={(e) => setFilterToDate(e.target.value)}
              className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Search Text */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Search</label>
            <div className="relative">
              <input
                type="text"
                placeholder="Entry #, Payer, Deal..."
                value={filterSearch}
                onChange={(e) => setFilterSearch(e.target.value)}
                className="text-xs border border-gray-300 rounded-lg pl-7 pr-2.5 py-1.5 w-full focus:ring-emerald-500 focus:border-emerald-500"
              />
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2 top-2.5" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Tab Navigation */}
      <div className="flex items-center gap-1 border-b border-gray-200 overflow-x-auto pb-px">
        {[
          { key: "transactions", label: "Transaction Wise", icon: Layers, color: "text-emerald-600" },
          { key: "dateWise", label: "Date Wise", icon: Calendar, color: "text-emerald-600" },
          { key: "customerWise", label: "Customer Wise", icon: Users, color: "text-emerald-600" },
          { key: "leadOwner", label: "Lead Owner Wise", icon: Briefcase, color: "text-emerald-600" },
          { key: "employee", label: "Employee Wise", icon: User, color: "text-emerald-600" },
          { key: "location", label: "Location Wise", icon: MapPin, color: "text-emerald-600" },
          { key: "estimations", label: "Estimations", icon: Calculator, color: "text-orange-600" },
          { key: "solarvendor", label: "Solar Vendor Ledger", icon: Sun, color: "text-sky-600" },
          { key: "execDash", label: "Executive Dashboard", icon: BarChart3, color: "text-purple-600" },
          { key: "deleted", label: "Deleted Transactions", icon: Trash2, color: "text-red-600" },
        ].map((t) => {
          const Icon = t.icon;
          const active = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key as TabType)}
              className={`px-4 py-2.5 text-xs font-bold rounded-t-lg transition-all flex items-center gap-1.5 whitespace-nowrap border-b-2 ${
                active
                  ? "border-emerald-600 text-emerald-700 bg-white shadow-2xs"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100/60"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${t.color}`} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Active Tab View */}
      <div>
        {activeTab === "transactions" && renderTransactionsTab()}
        {activeTab === "dateWise" && renderDateWiseTab()}
        {activeTab === "customerWise" && renderCustomerWiseTab()}
        {activeTab === "leadOwner" && renderLeadOwnerTab()}
        {activeTab === "employee" && renderEmployeeTab()}
        {activeTab === "location" && renderLocationTab()}
        {activeTab === "estimations" && renderEstimationsTab()}
        {activeTab === "solarvendor" && renderSolarVendorTab()}
        {activeTab === "execDash" && renderExecDashboardTab()}
        {activeTab === "deleted" && renderDeletedTab()}
      </div>

      {/* ========================================================================= */}
      {/* MODALS & DIALOGS */}
      {/* ========================================================================= */}

      {/* 1. Create Income Entry Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-gray-100 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Plus className="w-5 h-5 text-emerald-600" /> New Income Entry
              </h3>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateIncome} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Company *</label>
                  <select
                    required
                    value={createForm.company_id}
                    onChange={(e) => {
                      setCreateForm({ ...createForm, company_id: e.target.value });
                      loadFormCategories(e.target.value);
                    }}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  >
                    <option value="">Select Company</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Income Date *</label>
                  <input
                    type="date"
                    required
                    value={createForm.income_date}
                    onChange={(e) => setCreateForm({ ...createForm, income_date: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Source Type *</label>
                  <select
                    required
                    value={createForm.income_source_id}
                    onChange={(e) => setCreateForm({ ...createForm, income_source_id: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  >
                    <option value="">Select Source Type</option>
                    {sourceTypes.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.source_name || s.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Revenue Category</label>
                  <select
                    value={createForm.revenue_category_id}
                    onChange={(e) => setCreateForm({ ...createForm, revenue_category_id: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  >
                    <option value="">None</option>
                    {formCategories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.category_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Amount (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    placeholder="0.00"
                    value={createForm.amount}
                    onChange={(e) => setCreateForm({ ...createForm, amount: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs font-mono font-bold"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Payment Mode *</label>
                  <select
                    required
                    value={createForm.payment_mode}
                    onChange={(e) => setCreateForm({ ...createForm, payment_mode: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  >
                    <option value="UPI">UPI</option>
                    <option value="CASH">Cash</option>
                    <option value="NEFT">NEFT</option>
                    <option value="RTGS">RTGS</option>
                    <option value="BANK">Bank Transfer</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="CARD">Card</option>
                    <option value="DD">Demand Draft</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Payment Type</label>
                  <select
                    value={createForm.payment_type}
                    onChange={(e) => setCreateForm({ ...createForm, payment_type: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  >
                    <option value="">Not Specified</option>
                    <option value="BANK">Bank</option>
                    <option value="CASH">Cash</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Payer Name</label>
                  <input
                    type="text"
                    placeholder="Name of payer or customer"
                    value={createForm.payer_name}
                    onChange={(e) => setCreateForm({ ...createForm, payer_name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Payment Reference</label>
                  <input
                    type="text"
                    placeholder="Txn ID / UTR / Cheque #"
                    value={createForm.payment_reference}
                    onChange={(e) => setCreateForm({ ...createForm, payment_reference: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Narration / Notes</label>
                <textarea
                  rows={2}
                  placeholder="Additional notes"
                  value={createForm.narration}
                  onChange={(e) => setCreateForm({ ...createForm, narration: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="formShowInLedger"
                  checked={createForm.show_in_ledger}
                  onChange={(e) => setCreateForm({ ...createForm, show_in_ledger: e.target.checked })}
                  className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 w-4 h-4 cursor-pointer"
                />
                <label htmlFor="formShowInLedger" className="font-semibold text-gray-800 cursor-pointer">
                  Show in Ledger <span className="text-gray-400 font-normal">(Optional ledger posting)</span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md disabled:opacity-50"
                >
                  {createSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                  Create Entry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. Confirm Income Entry Modal */}
      {isConfirmModalOpen && confirmingEntry && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 space-y-4 max-h-[92vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" /> Confirm Income Entry
              </h3>
              <button
                onClick={() => setIsConfirmModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Summary Strip */}
            <div className="bg-gray-50 rounded-xl p-3.5 border border-gray-200/80 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">ENTRY #</div>
                <div className="font-bold text-gray-800 font-mono">
                  {confirmingEntry.entry_number || `#${confirmingEntry.id}`}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">AMOUNT</div>
                <div className="font-bold text-emerald-600 font-mono text-sm">{fmt(confirmingEntry.amount)}</div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">DATE</div>
                <div className="text-gray-700">{fmtDate(confirmingEntry.income_date)}</div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">PAYMENT MODE</div>
                <div className="text-gray-700 font-medium">{confirmingEntry.payment_mode || "—"}</div>
              </div>
              <div className="col-span-2 mt-1">
                <div className="text-[10px] font-bold text-gray-500 uppercase mb-1">Company Assignment</div>
                <select
                  value={confCompanyId}
                  onChange={(e) => {
                    setConfCompanyId(e.target.value);
                    if (e.target.value) loadConfBankAccounts(parseInt(e.target.value));
                  }}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-1.5 text-xs bg-white font-semibold text-gray-800"
                >
                  <option value="">Select Company</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Destination Type Selector */}
            <div className="space-y-2 text-xs">
              <label className="font-bold text-gray-800 block">Destination Type</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { val: "", label: "Unassigned", icon: HelpCircle, color: "text-gray-500" },
                  { val: "COMPANY_ACCOUNT", label: "Company", icon: Building2, color: "text-blue-600" },
                  { val: "EMPLOYEE", label: "Employee", icon: User, color: "text-emerald-600" },
                  { val: "SOLAR_VENDOR", label: "Solar Vendor", icon: Sun, color: "text-amber-600" },
                ].map((d) => {
                  const Icon = d.icon;
                  const selected = confDestType === d.val;
                  return (
                    <button
                      key={d.val}
                      type="button"
                      onClick={() => setConfDestType(d.val)}
                      className={`p-2.5 rounded-xl border text-center font-semibold transition-all flex flex-col items-center gap-1 ${
                        selected
                          ? "border-emerald-600 bg-emerald-50 text-emerald-800 shadow-2xs"
                          : "border-gray-200 hover:border-gray-300 text-gray-600"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${d.color}`} />
                      <span className="text-[11px]">{d.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Dynamic Destination Dropdowns */}
            {confDestType === "COMPANY_ACCOUNT" && (
              <div className="space-y-1 text-xs">
                <label className="font-bold text-gray-700 block">Company Account</label>
                <select
                  value={confDestCompanyId}
                  onChange={(e) => setConfDestCompanyId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs bg-white"
                >
                  <option value="">Select Company Account</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name} {c.bank_name ? `— ${c.bank_name}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {confDestType === "EMPLOYEE" && (
              <div className="space-y-2 text-xs">
                <label className="font-bold text-gray-700 block">Employee</label>
                <select
                  value={confDestEmployeeId}
                  onChange={(e) => {
                    setConfDestEmployeeId(e.target.value);
                    if (e.target.value) {
                      loadEmployeeBalancePreview(parseInt(e.target.value), confirmingEntry.amount);
                    } else {
                      setConfEmployeeBalance(null);
                    }
                  }}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs bg-white"
                >
                  <option value="">Select Employee</option>
                  {assignableEmployees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.full_name || e.name} ({e.employee_code || e.emp_code || ""})
                    </option>
                  ))}
                </select>

                {confEmployeeBalance && (
                  <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3 space-y-1.5">
                    <div className="text-[11px] font-bold text-emerald-900">
                      {confEmployeeBalance.name} — Fund Balance Preview
                    </div>
                    <div className="flex justify-between text-gray-600">
                      <span>Previous Balance:</span>
                      <span className="font-mono font-semibold">{fmt(confEmployeeBalance.prevBal)}</span>
                    </div>
                    <div className="flex justify-between text-blue-700">
                      <span>This Collection:</span>
                      <span className="font-mono font-bold">+{fmt(confEmployeeBalance.txnAmt)}</span>
                    </div>
                    <div className="border-t border-emerald-200 pt-1 flex justify-between font-bold text-emerald-800">
                      <span>Balance After:</span>
                      <span className="font-mono">{fmt(confEmployeeBalance.afterBal)}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {confDestType === "SOLAR_VENDOR" && (
              <div className="space-y-1 text-xs">
                <label className="font-bold text-gray-700 block">Solar Vendor</label>
                <select
                  value={confSolarVendorId}
                  onChange={(e) => setConfSolarVendorId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs bg-white"
                >
                  <option value="">Select Solar Vendor</option>
                  {solarVendors.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.vendor_name} {v.vendor_code ? `(${v.vendor_code})` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Bank Account Override */}
            <div className="space-y-1 text-xs pt-1">
              <label className="font-semibold text-gray-700 block">
                Bank / Cash Account Override <span className="text-gray-400 font-normal">(Optional)</span>
              </label>
              <select
                value={confBankAccountId}
                onChange={(e) => setConfBankAccountId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs bg-white"
              >
                <option value="">Auto-resolve from payment mode</option>
                {confBankAccounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.account_name} ({a.account_type || "Bank"})
                  </option>
                ))}
              </select>
            </div>

            {/* Payer Name Override */}
            <div className="space-y-1 text-xs">
              <label className="font-semibold text-gray-700 block">
                Payer Name Override <span className="text-gray-400 font-normal">(Optional party ledger)</span>
              </label>
              <input
                type="text"
                placeholder="Payer / customer name"
                value={confPayerName}
                onChange={(e) => setConfPayerName(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs"
              />
            </div>

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setIsConfirmModalOpen(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={confirmSubmitting}
                onClick={submitConfirm}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md disabled:opacity-50"
              >
                {confirmSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Confirm Entry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Edit Destination Modal */}
      {isEditModalOpen && editingEntry && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Edit className="w-5 h-5 text-sky-600" /> Edit Income Entry
              </h3>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-gray-50 rounded-xl p-3.5 border border-gray-200/80 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">ENTRY #</div>
                <div className="font-bold text-gray-800 font-mono">
                  {editingEntry.entry_number || `#${editingEntry.id}`}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">AMOUNT</div>
                <div className="font-bold text-emerald-600 font-mono text-sm">{fmt(editingEntry.amount)}</div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">INCOME DATE</div>
                <input
                  type="date"
                  value={editIncomeDate}
                  onChange={(e) => setEditIncomeDate(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1 text-xs mt-0.5"
                />
              </div>
              <div>
                <div className="text-[10px] font-bold text-gray-500 uppercase">MODE</div>
                <div className="text-gray-700 font-medium">{editingEntry.payment_mode || "—"}</div>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <label className="font-bold text-gray-800 block">Destination Type</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { val: "", label: "Unassigned" },
                  { val: "COMPANY_ACCOUNT", label: "Company Account" },
                  { val: "EMPLOYEE", label: "Employee Fund" },
                ].map((d) => (
                  <button
                    key={d.val}
                    type="button"
                    onClick={() => setEditDestType(d.val)}
                    className={`p-2.5 rounded-xl border text-center font-semibold transition-all ${
                      editDestType === d.val
                        ? "border-sky-600 bg-sky-50 text-sky-800 shadow-2xs"
                        : "border-gray-200 hover:border-gray-300 text-gray-600"
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            {editDestType === "COMPANY_ACCOUNT" && (
              <div className="space-y-1 text-xs">
                <label className="font-bold text-gray-700 block">Company Account</label>
                <select
                  value={editDestCompanyId}
                  onChange={(e) => setEditDestCompanyId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs bg-white"
                >
                  <option value="">Select Company Account</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name} {c.bank_name ? `— ${c.bank_name}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {editDestType === "EMPLOYEE" && (
              <div className="space-y-2 text-xs">
                <label className="font-bold text-gray-700 block">Employee</label>
                <select
                  value={editDestEmployeeId}
                  onChange={(e) => {
                    setEditDestEmployeeId(e.target.value);
                    if (e.target.value) {
                      loadEditEmployeeBalance(parseInt(e.target.value), editingEntry.company_id);
                    } else {
                      setEditEmployeeBalance(null);
                    }
                  }}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs bg-white"
                >
                  <option value="">Select Employee</option>
                  {assignableEmployees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.full_name || e.name} ({e.employee_code || e.emp_code || ""})
                    </option>
                  ))}
                </select>

                {editEmployeeBalance && (
                  <div className="bg-sky-50/70 border border-sky-200 rounded-xl p-3 space-y-1 text-xs">
                    <div className="font-bold text-sky-900 mb-1">Employee Fund Overview</div>
                    <div className="flex justify-between text-gray-600">
                      <span>Available Balance:</span>
                      <span className="font-mono font-bold text-emerald-600">
                        {fmt(editEmployeeBalance.available_balance)}
                      </span>
                    </div>
                    <div className="flex justify-between text-gray-600">
                      <span>Approved Expenses:</span>
                      <span className="font-mono text-red-600">{fmt(editEmployeeBalance.approved_expenses)}</span>
                    </div>
                    <div className="flex justify-between text-gray-600">
                      <span>Pending (Submitted):</span>
                      <span className="font-mono text-amber-600">{fmt(editEmployeeBalance.pending_submitted)}</span>
                    </div>
                    <div className="border-t border-sky-200 pt-1 flex justify-between font-bold text-sky-900">
                      <span>Effective Balance:</span>
                      <span className="font-mono">
                        {fmt(editEmployeeBalance.effective_balance_after_submitted)}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setIsEditModalOpen(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={editSubmitting}
                onClick={submitEdit}
                className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md disabled:opacity-50"
              >
                {editSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. Customer / Lead Owner Transaction Detail Modal */}
      {isDetailModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-4xl w-full p-6 shadow-2xl border border-gray-100 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-600" /> {detailModalTitle}
              </h3>
              <button
                onClick={() => setIsDetailModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-xs text-gray-500 font-medium">
              {detailModalItems.length} transactions | Total:{" "}
              <strong className="text-emerald-600 font-mono font-bold text-sm">
                {fmt(detailModalItems.reduce((s, i) => s + (Number(i.amount) || 0), 0))}
              </strong>
            </div>

            <div className="overflow-x-auto border border-gray-100 rounded-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50 text-gray-600 font-semibold uppercase tracking-wider border-b border-gray-100">
                    <th className="py-2.5 px-3.5">Date</th>
                    <th className="py-2.5 px-3.5">Deal #</th>
                    <th className="py-2.5 px-3.5">Customer</th>
                    <th className="py-2.5 px-3.5 text-right">Amount</th>
                    <th className="py-2.5 px-3.5">Mode</th>
                    <th className="py-2.5 px-3.5">Type</th>
                    <th className="py-2.5 px-3.5">Status</th>
                    <th className="py-2.5 px-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {detailModalItems.map((i) => (
                    <tr key={i.id} className="hover:bg-gray-50/60 transition-colors">
                      <td className="py-2.5 px-3.5 text-gray-600 whitespace-nowrap">{fmtDate(i.income_date)}</td>
                      <td className="py-2.5 px-3.5 font-mono text-emerald-700 font-semibold">{i.deal_code || "—"}</td>
                      <td className="py-2.5 px-3.5 font-medium text-gray-900">{i.lead_name || i.payer_name || "—"}</td>
                      <td className="py-2.5 px-3.5 text-right font-mono font-bold text-emerald-600">{fmt(i.amount)}</td>
                      <td className="py-2.5 px-3.5 text-gray-600">{i.payment_mode || "—"}</td>
                      <td className="py-2.5 px-3.5 capitalize">{i.transaction_type || "—"}</td>
                      <td className="py-2.5 px-3.5">
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-800 rounded-full text-[10px] font-semibold">
                          {i.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3.5 text-right whitespace-nowrap">
                        <button
                          onClick={() => openConfirmModal(i)}
                          className="px-2 py-0.5 bg-emerald-600 text-white rounded text-[10px] font-semibold hover:bg-emerald-700"
                        >
                          Confirm
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 5. Add / Edit OUT Record Modal */}
      {isOutModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <ArrowUpRight className="w-5 h-5 text-red-600" />
                {editingOutId ? "Edit OUT Record" : "Add OUT Planning Record"}
              </h3>
              <button
                onClick={() => setIsOutModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Date *</label>
                  <input
                    type="date"
                    value={outForm.entry_date}
                    onChange={(e) => setOutForm({ ...outForm, entry_date: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Amount (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={outForm.amount}
                    onChange={(e) => setOutForm({ ...outForm, amount: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 font-mono font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Description *</label>
                <input
                  type="text"
                  placeholder="e.g. Spare parts procurement"
                  value={outForm.description}
                  onChange={(e) => setOutForm({ ...outForm, description: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Party Name</label>
                  <input
                    type="text"
                    placeholder="Vendor / Payee"
                    value={outForm.party_name}
                    onChange={(e) => setOutForm({ ...outForm, party_name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Account</label>
                  <input
                    type="text"
                    placeholder="Account name"
                    value={outForm.account_name}
                    onChange={(e) => setOutForm({ ...outForm, account_name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Notes</label>
                <textarea
                  rows={2}
                  placeholder="Additional notes"
                  value={outForm.notes}
                  onChange={(e) => setOutForm({ ...outForm, notes: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                />
              </div>

              <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-[11px] text-red-800 leading-normal">
                <ShieldAlert className="w-3.5 h-3.5 text-red-600 inline mr-1" />
                OUT records are <strong>informational only</strong>. They have no ledger impact and do not affect balance sheets.
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsOutModalOpen(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveOutRecord}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold shadow-md"
                >
                  Save Record
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6. Record Solar Vendor Return Modal */}
      {isSvlReturnModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <ArrowUpRight className="w-5 h-5 text-amber-600" /> Record Solar Vendor Return
              </h3>
              <button
                onClick={() => setIsSvlReturnModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-gray-700 block mb-1">Solar Vendor *</label>
                <select
                  value={svlReturnForm.solar_vendor_id}
                  onChange={(e) => setSvlReturnForm({ ...svlReturnForm, solar_vendor_id: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 text-xs bg-white"
                >
                  <option value="">— Select Vendor —</option>
                  {solarVendors.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.vendor_name} {v.vendor_code ? `(${v.vendor_code})` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Date *</label>
                  <input
                    type="date"
                    value={svlReturnForm.transaction_date}
                    onChange={(e) => setSvlReturnForm({ ...svlReturnForm, transaction_date: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Amount (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="0.00"
                    value={svlReturnForm.amount}
                    onChange={(e) => setSvlReturnForm({ ...svlReturnForm, amount: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2 font-mono font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Customer Name</label>
                  <input
                    type="text"
                    placeholder="Customer (optional)"
                    value={svlReturnForm.customer_name}
                    onChange={(e) => setSvlReturnForm({ ...svlReturnForm, customer_name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Payment Mode</label>
                  <select
                    value={svlReturnForm.payment_mode}
                    onChange={(e) => setSvlReturnForm({ ...svlReturnForm, payment_mode: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  >
                    <option value="">— Select —</option>
                    <option value="BANK">Bank Transfer</option>
                    <option value="UPI">UPI</option>
                    <option value="CASH">Cash</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="NEFT">NEFT</option>
                    <option value="RTGS">RTGS</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">UTR / Reference</label>
                <input
                  type="text"
                  placeholder="UTR or txn reference"
                  value={svlReturnForm.utr_reference}
                  onChange={(e) => setSvlReturnForm({ ...svlReturnForm, utr_reference: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 font-mono"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Notes</label>
                <textarea
                  rows={2}
                  placeholder="Remarks"
                  value={svlReturnForm.notes}
                  onChange={(e) => setSvlReturnForm({ ...svlReturnForm, notes: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsSvlReturnModalOpen(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleRecordSvlReturn}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md"
                >
                  Record Return
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 7. Edit Solar Vendor Row Modal */}
      {isSvlEditModalOpen && svlEditRow && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Edit className="w-5 h-5 text-indigo-600" /> Edit Solar Entry
              </h3>
              <button
                onClick={() => setIsSvlEditModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Date *</label>
                  <input
                    type="date"
                    value={svlEditForm.transaction_date}
                    onChange={(e) => setSvlEditForm({ ...svlEditForm, transaction_date: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-gray-700 block mb-1">Payment Mode</label>
                  <select
                    value={svlEditForm.payment_mode}
                    onChange={(e) => setSvlEditForm({ ...svlEditForm, payment_mode: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                  >
                    <option value="">— Select —</option>
                    <option value="BANK">Bank Transfer</option>
                    <option value="UPI">UPI</option>
                    <option value="CASH">Cash</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="NEFT">NEFT</option>
                    <option value="RTGS">RTGS</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Customer Name</label>
                <input
                  type="text"
                  placeholder="Customer name"
                  value={svlEditForm.customer_name}
                  onChange={(e) => setSvlEditForm({ ...svlEditForm, customer_name: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">UTR / Reference</label>
                <input
                  type="text"
                  placeholder="UTR number"
                  value={svlEditForm.utr_reference}
                  onChange={(e) => setSvlEditForm({ ...svlEditForm, utr_reference: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2 font-mono"
                />
              </div>

              <div>
                <label className="font-semibold text-gray-700 block mb-1">Notes</label>
                <textarea
                  rows={2}
                  placeholder="Notes"
                  value={svlEditForm.notes}
                  onChange={(e) => setSvlEditForm({ ...svlEditForm, notes: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-2"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsSvlEditModalOpen(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveSvlEdit}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
