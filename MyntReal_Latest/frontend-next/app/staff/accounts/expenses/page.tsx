"use client";

import React, { useState, useEffect, useRef } from "react";
import api, { getApiUrl } from "@/lib/api";
import { useStaffAuth, Employee } from "@/contexts/StaffAuthContext";
import {
  Receipt,
  Plus,
  ArrowRightLeft,
  Coins,
  Tags,
  Search,
  Filter,
  RefreshCw,
  Eye,
  Send,
  Edit,
  CheckCircle2,
  XCircle,
  Banknote,
  Stamp,
  FileText,
  AlertTriangle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Upload,
  User,
  Users,
  Wallet,
  Building2,
  Calendar,
  CreditCard,
  ExternalLink,
  X,
  Clock,
  HandCoins,
  FileCheck,
  Check,
  DollarSign
} from "lucide-react";

// ==========================================
// Types & Interfaces
// ==========================================
interface Company {
  id: number;
  company_name?: string;
  name?: string;
}

interface Category {
  id: number;
  name: string;
  is_active?: boolean;
  sub_categories?: { id: number; name: string; is_active?: boolean }[];
}

interface Vendor {
  id: number;
  vendor_name?: string;
  name?: string;
  vendor_code?: string;
  is_active?: boolean;
}

interface BankAccount {
  id: number;
  bank_name: string;
  account_number: string;
  account_type: string;
  display_label?: string;
  is_primary?: boolean;
  is_active?: boolean;
}

interface FundAllocation {
  id: number;
  company_name: string;
  amount: number;
  balance_used?: number;
  balance_remaining?: number;
}

interface ExpenseEntry {
  id: number;
  entry_number?: string;
  expense_date: string;
  company_id?: number;
  company_name?: string;
  main_category_id?: number;
  category_name?: string;
  main_category_name?: string;
  sub_category_id?: number;
  sub_category_name?: string;
  paid_to?: string;
  vendor_id?: number;
  vendor_name?: string;
  vendor_contact?: string;
  bank_ledger_category?: string;
  custom_category_name?: string;
  narration?: string;
  description?: string;
  notes?: string;
  purpose?: string;
  amount: number;
  net_amount?: number;
  gst_amount?: number;
  tds_amount?: number;
  status: "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED" | "CANCELLED";
  payment_mode?: string;
  payment_reference?: string;
  bank_account_id?: number;
  bank_account_name?: string;
  bill_number?: string;
  bill_date?: string;
  bill_remarks?: string;
  bill_path?: string;
  tally_status?: string;
  tally_voucher_no?: string;
  fund_allocation_id?: number;
  allocation_number?: string;
  is_paid?: boolean;
  payment_utr?: string;
  paid_at?: string;
  show_in_ledger?: boolean;
  created_by_id?: number;
  created_by_name?: string;
  employee_name?: string;
  approved_by_id?: number;
  approved_by_name?: string;
  approved_at?: string;
  created_at?: string;
}

interface ExpenseSummary {
  draft_count?: number;
  draft_amount?: number;
  submitted_count?: number;
  submitted_amount?: number;
  approved_count?: number;
  total_approved_amount?: number;
  rejected_count?: number;
  rejected_amount?: number;
  paid_count?: number;
  total_paid_amount?: number;
  total_amount?: number;
}

interface FundBalanceSummary {
  available_balance: number;
  approved_expenses: number;
  pending_submitted: number;
  pending_draft: number;
  effective_balance_after_submitted: number;
  total_received?: number;
}

interface ConsolidatedRow {
  employee_id: number;
  full_name: string;
  emp_code: string;
  department?: string;
  role?: string;
  fund_allocated: number;
  fund_balance: number;
  fund_used: number;
  fund_transferred_out?: number;
  fund_transferred_in?: number;
  total_in?: number;
  total_out?: number;
  net_balance?: number;
  income_entries?: number;
  bank_alloc_in?: number;
  ledger_exp?: number;
  ext_exp?: number;
  draft_in?: number;
  draft_out?: number;
  draft_balance?: number;
  final_balance?: number;
  cash_received: number;
  cash_balance: number;
  cash_receipt_count?: number;
  total_expenses: number;
  draft_count: number;
  submitted_count: number;
  approved_count: number;
  rejected_count: number;
  paid_count: number;
  approved_amount: number;
  rejected_amount: number;
  paid_amount: number;
  draft_amount: number;
  submitted_amount: number;
}

interface IncomeReceipt {
  id: number;
  entry_number?: string;
  income_date?: string;
  created_at?: string;
  payer_name?: string;
  company_name?: string;
  amount: number;
  payment_mode?: string;
  status: string;
}

export default function ExpensesPage() {
  const { user, token, isAuthenticated } = useStaffAuth();

  // Roles & Permissions
  const hasFullAccess =
    ["VGK Mentor", "VGK4U Supreme", "VGK4U", "Executive Assistant", "EA", "Executive Admin"].includes(
      user?.role_name || ""
    ) || user?.emp_code === "MR10001";

  const hasAccountsAccess =
    hasFullAccess ||
    ["Accounts", "Finance", "VEA"].some((r) => (user?.role_name || "").includes(r)) ||
    ["accounts", "finance"].some((d) => (user?.department_name || "").toLowerCase().includes(d));

  // Active Tab
  const [activeTab, setActiveTab] = useState<"my" | "team" | "consolidated">("my");

  // Master Data
  const [companies, setCompanies] = useState<Company[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [filteredVendors, setFilteredVendors] = useState<Vendor[]>([]);
  const [fundAllocations, setFundAllocations] = useState<FundAllocation[]>([]);
  const [behalfEmployees, setBehalfEmployees] = useState<any[]>([]);
  const [canCreateOnBehalf, setCanCreateOnBehalf] = useState(false);

  // My Expenses State
  const [expenses, setExpenses] = useState<ExpenseEntry[]>([]);
  const [summary, setSummary] = useState<ExpenseSummary>({});
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // My Expenses Filters
  const [filterStatus, setFilterStatus] = useState("");
  const [filterCompany, setFilterCompany] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterFromDate, setFilterFromDate] = useState("");
  const [filterToDate, setFilterToDate] = useState("");
  const [qfPresetMy, setQfPresetMy] = useState("overall");

  // Fund Balance State
  const [balanceSummary, setBalanceSummary] = useState<FundBalanceSummary | null>(null);
  const [balanceLoading, setBalanceLoading] = useState(false);

  // Opening Balance Section
  const [showOpeningBalSection, setShowOpeningBalSection] = useState(false);
  const [obEmployee, setObEmployee] = useState("");
  const [obCompany, setObCompany] = useState("");
  const [obAmount, setObAmount] = useState("");
  const [obExistingText, setObExistingText] = useState("");
  const [obBalanceContext, setObBalanceContext] = useState<FundBalanceSummary | null>(null);
  const [obMsg, setObMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [obSaving, setObSaving] = useState(false);

  // My Team State
  const [teamExpenses, setTeamExpenses] = useState<ExpenseEntry[]>([]);
  const [teamSummary, setTeamSummary] = useState<ExpenseSummary>({});
  const [teamLoading, setTeamLoading] = useState(false);
  const [teamPage, setTeamPage] = useState(1);
  const [teamTotalPages, setTeamTotalPages] = useState(1);
  const [teamFilterCompany, setTeamFilterCompany] = useState("");
  const [teamFilterStatus, setTeamFilterStatus] = useState("");
  const [teamFilterEmployee, setTeamFilterEmployee] = useState("");
  const [teamFilterFrom, setTeamFilterFrom] = useState("");
  const [teamFilterTo, setTeamFilterTo] = useState("");
  const [qfPresetTeam, setQfPresetTeam] = useState("overall");

  // Team Employee Fund Balance Lookup
  const [teamBalEmpSelect, setTeamBalEmpSelect] = useState("");
  const [teamBalData, setTeamBalData] = useState<{ balance?: FundBalanceSummary; ob?: number } | null>(null);
  const [teamBalLoading, setTeamBalLoading] = useState(false);

  // Team Member Income Receipts (Cash Received)
  const [teamIncomeReceipts, setTeamIncomeReceipts] = useState<IncomeReceipt[]>([]);
  const [teamIncomeReceiptsLoading, setTeamIncomeReceiptsLoading] = useState(false);

  // Consolidated State
  const [consoRows, setConsoRows] = useState<ConsolidatedRow[]>([]);
  const [consoLoading, setConsoLoading] = useState(false);
  const [consoCompany, setConsoCompany] = useState("");
  const [consoFromDate, setConsoFromDate] = useState("");
  const [consoToDate, setConsoToDate] = useState("");
  const [consoSearch, setConsoSearch] = useState("");
  const [qfPresetConso, setQfPresetConso] = useState("overall");

  // Modals & Drawers
  const [viewExpenseData, setViewExpenseData] = useState<ExpenseEntry | null>(null);
  const [viewExpenseLoading, setViewExpenseLoading] = useState(false);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [payModalOpen, setPayModalOpen] = useState(false);
  const [transferModalOpen, setTransferModalOpen] = useState(false);
  const [drilldownModalOpen, setDrilldownModalOpen] = useState(false);
  const [incomeReceiptsModalOpen, setIncomeReceiptsModalOpen] = useState(false);
  const [catQuickAddModalOpen, setCatQuickAddModalOpen] = useState(false);

  // Selected expense for action modals
  const [selectedExpense, setSelectedExpense] = useState<ExpenseEntry | null>(null);
  const [approveNotes, setApproveNotes] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [payUtr, setPayUtr] = useState("");
  const [payBankAccountId, setPayBankAccountId] = useState<number | "">("");
  const [payNotes, setPayNotes] = useState("");
  const [companyBankAccounts, setCompanyBankAccounts] = useState<BankAccount[]>([]);

  // Edit Modal State
  const [editAmount, setEditAmount] = useState("");
  const [editNotes, setEditNotes] = useState("");

  // Create Form State
  const [formData, setFormData] = useState({
    on_behalf_of_employee_id: "",
    company_id: "",
    expense_date: new Date().toISOString().slice(0, 10),
    main_category_id: "",
    sub_category_id: "",
    amount: "",
    narration: "",
    fund_allocation_id: "",
    vendor_id: "",
    vendor_search: "",
    vendor_name: "",
    bank_ledger_category: "",
    custom_category_name: "",
    payment_mode: "",
    bank_account_id: "",
    bill_number: "",
    bill_path: "",
    show_in_ledger: false
  });
  const [createSubCategories, setCreateSubCategories] = useState<{ id: number; name: string }[]>([]);
  const [formBankAccounts, setFormBankAccounts] = useState<BankAccount[]>([]);
  const [uploadingReceipt, setUploadingReceipt] = useState(false);
  const [receiptUploadSuccess, setReceiptUploadSuccess] = useState<string | null>(null);

  // Transfer Modal State
  const [transferCompany, setTransferCompany] = useState("");
  const [transferFrom, setTransferFrom] = useState("");
  const [transferTo, setTransferTo] = useState("");
  const [transferAmount, setTransferAmount] = useState("");
  const [transferMainCat, setTransferMainCat] = useState("");
  const [transferSubCat, setTransferSubCat] = useState("");
  const [transferSubCats, setTransferSubCats] = useState<{ id: number; name: string }[]>([]);
  const [transferNotes, setTransferNotes] = useState("");
  const [transferFromBalance, setTransferFromBalance] = useState<number | null>(null);
  const [transferBalLoading, setTransferBalLoading] = useState(false);

  // Quick Add Category Modal State
  const [qaCatMode, setQaCatMode] = useState<"sub" | "main">("sub");
  const [qaMainName, setQaMainName] = useState("");
  const [qaParentId, setQaParentId] = useState("");
  const [qaSubName, setQaSubName] = useState("");
  const [qaSaving, setQaSaving] = useState(false);

  // Drilldown Modal State
  const [drilldownTitle, setDrilldownTitle] = useState("");
  const [drilldownEntries, setDrilldownEntries] = useState<ExpenseEntry[]>([]);
  const [drilldownLoading, setDrilldownLoading] = useState(false);
  const [expandedDrilldownRows, setExpandedDrilldownRows] = useState<Record<number, boolean>>({});

  // Income Receipts Drilldown State
  const [incomeDrilldownTitle, setIncomeDrilldownTitle] = useState("");
  const [incomeDrilldownReceipts, setIncomeDrilldownReceipts] = useState<IncomeReceipt[]>([]);
  const [incomeDrilldownLoading, setIncomeDrilldownLoading] = useState(false);

  // Status Alerts / Messages
  const [toastMsg, setToastMsg] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  const showToast = (text: string, type: "success" | "error" | "info" = "success") => {
    setToastMsg({ type, text });
    setTimeout(() => setToastMsg(null), 4000);
  };

  // ==========================================
  // Date Helpers for Quick Filters
  // ==========================================
  const getQFDates = (preset: string) => {
    const today = new Date();
    const fmt = (d: Date) => d.toISOString().slice(0, 10);
    if (preset === "today") return { from: fmt(today), to: fmt(today) };
    const yest = new Date(today);
    yest.setDate(today.getDate() - 1);
    if (preset === "yesterday") return { from: fmt(yest), to: fmt(yest) };
    const dow = (today.getDay() + 6) % 7; // Monday = 0
    const mon = new Date(today);
    mon.setDate(today.getDate() - dow);
    if (preset === "this_week") return { from: fmt(mon), to: fmt(today) };
    const lsun = new Date(mon);
    lsun.setDate(mon.getDate() - 1);
    const lmon = new Date(lsun);
    lmon.setDate(lsun.getDate() - 6);
    if (preset === "last_week") return { from: fmt(lmon), to: fmt(lsun) };
    return { from: "", to: "" };
  };

  const handleQuickFilter = (tab: "my" | "team" | "consolidated", preset: string) => {
    const { from, to } = getQFDates(preset);
    if (tab === "my") {
      setQfPresetMy(preset);
      setFilterFromDate(from);
      setFilterToDate(to);
      setCurrentPage(1);
    } else if (tab === "team") {
      setQfPresetTeam(preset);
      setTeamFilterFrom(from);
      setTeamFilterTo(to);
      setTeamPage(1);
    } else if (tab === "consolidated") {
      setQfPresetConso(preset);
      setConsoFromDate(from);
      setConsoToDate(to);
    }
  };

  // ==========================================
  // Data Fetching: Master Data
  // ==========================================
  const fetchCompanies = async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      if (res.data && res.data.companies) {
        setCompanies(res.data.companies);
      }
    } catch (err) {
      console.error("Failed to load companies:", err);
    }
  };

  const fetchCategories = async () => {
    try {
      const res = await api.get("/staff/accounts/expense-categories/main");
      if (res.data && res.data.categories) {
        setCategories(res.data.categories.filter((c: any) => c.is_active !== false));
      }
    } catch (err) {
      console.error("Failed to load categories:", err);
    }
  };

  const fetchVendors = async () => {
    try {
      const res = await api.get("/staff/accounts/vendors?page_size=500");
      if (res.data && res.data.vendors) {
        const vList = res.data.vendors.filter((v: any) => v.is_active !== false);
        setVendors(vList);
        setFilteredVendors(vList);
      }
    } catch (err) {
      console.error("Failed to load vendors:", err);
    }
  };

  const fetchFundAllocations = async (targetEmpId?: number) => {
    const empId = targetEmpId || user?.id;
    if (!empId) return;
    try {
      const res = await api.get(
        `/staff/accounts/fund-allocations?status=CONFIRMED&to_employee_id=${empId}&page_size=100`
      );
      if (res.data && res.data.allocations) {
        setFundAllocations(res.data.allocations);
      }
    } catch (err) {
      console.error("Failed to load fund allocations:", err);
    }
  };

  const fetchBehalfEmployees = async () => {
    try {
      const res = await api.get("/staff/accounts/expense-behalf-employees");
      if (res.data && res.data.employees) {
        const list = res.data.employees;
        setBehalfEmployees(list);
        setCanCreateOnBehalf(list.length > 0);
      }
    } catch (err) {
      console.warn("Could not load behalf employees:", err);
    }
  };

  const fetchMyBalance = async () => {
    if (!user?.id) return;
    setBalanceLoading(true);
    try {
      const res = await api.get(`/staff/accounts/fund-ledger/${user.id}/balance`);
      if (res.data && res.data.balance_summary) {
        setBalanceSummary(res.data.balance_summary);
      }
    } catch (err) {
      console.error("Failed to load fund balance:", err);
    } finally {
      setBalanceLoading(false);
    }
  };

  // ==========================================
  // ==========================================
  // Data Fetching: My Expenses
  // ==========================================
  const fetchMyExpenses = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("page", currentPage.toString());
      params.append("page_size", "20");
      if (filterStatus) params.append("status", filterStatus);
      if (filterCompany) params.append("company_id", filterCompany);
      if (filterCategory) params.append("category_id", filterCategory);
      const fromDate = qfPresetMy === "overall" ? "" : filterFromDate;
      const toDate = qfPresetMy === "overall" ? "" : filterToDate;
      if (fromDate) params.append("from_date", fromDate);
      if (toDate) params.append("to_date", toDate);

      const res = await api.get(`/staff/accounts/expense-entries?${params.toString()}`);
      if (res.data) {
        const entries = res.data.entries || [];
        setExpenses(entries);
        setTotalCount(res.data.total || entries.length);
        setTotalPages(Math.ceil((res.data.total || entries.length) / 20) || 1);
        setSummary(res.data.summary || {});
      }
    } catch (err) {
      console.error("Failed to load expenses:", err);
      setExpenses([]);
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // Data Fetching: Team Expenses
  // ==========================================
  const fetchTeamExpenses = async () => {
    setTeamLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("team_view", "true");
      params.append("page", teamPage.toString());
      params.append("page_size", "30");
      if (teamFilterCompany) params.append("company_id", teamFilterCompany);
      if (teamFilterStatus) params.append("status", teamFilterStatus);
      if (teamFilterEmployee) params.append("employee_id", teamFilterEmployee);
      const fromDate = qfPresetTeam === "overall" ? "" : teamFilterFrom;
      const toDate = qfPresetTeam === "overall" ? "" : teamFilterTo;
      if (fromDate) params.append("from_date", fromDate);
      if (toDate) params.append("to_date", toDate);

      const res = await api.get(`/staff/accounts/expense-entries?${params.toString()}`);
      if (res.data) {
        const entries = res.data.entries || [];
        setTeamExpenses(entries);
        setTeamTotalPages(Math.ceil((res.data.total || entries.length) / 30) || 1);
        setTeamSummary(res.data.summary || {});
      }
    } catch (err) {
      console.error("Failed to load team expenses:", err);
      setTeamExpenses([]);
    } finally {
      setTeamLoading(false);
    }
  };

  const fetchTeamIncomeReceipts = async (empId: string) => {
    if (!empId) {
      setTeamIncomeReceipts([]);
      return;
    }
    setTeamIncomeReceiptsLoading(true);
    try {
      const res = await api.get(
        `/staff/accounts/income-entries?destination_employee_id=${empId}&page_size=200&page=1`
      );
      if (res.data) {
        setTeamIncomeReceipts(res.data.income_entries || res.data.entries || []);
      }
    } catch (err) {
      console.error("Failed to load team member income receipts:", err);
      setTeamIncomeReceipts([]);
    } finally {
      setTeamIncomeReceiptsLoading(false);
    }
  };

  const fetchTeamMemberBalance = async (empId: string) => {
    if (!empId) {
      setTeamBalData(null);
      return;
    }
    setTeamBalLoading(true);
    try {
      const res = await api.get(`/staff/accounts/fund-ledger/${empId}/balance`);
      if (res.data) {
        setTeamBalData({
          balance: res.data.balance_summary,
          ob: res.data.opening_balance
        });
      }
    } catch (err) {
      console.error("Failed to load team member balance:", err);
      setTeamBalData(null);
    } finally {
      setTeamBalLoading(false);
    }
  };

  // ==========================================
  // Data Fetching: Consolidated Summary
  // ==========================================
  const fetchConsolidatedSummary = async () => {
    setConsoLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("_", Date.now().toString());
      if (consoCompany) params.append("company_id", consoCompany);
      const fromDate = qfPresetConso === "overall" ? "" : consoFromDate;
      const toDate = qfPresetConso === "overall" ? "" : consoToDate;
      if (fromDate) params.append("from_date", fromDate);
      if (toDate) params.append("to_date", toDate);
      if (consoSearch.trim()) params.append("search", consoSearch.trim());

      const res = await api.get(`/staff/accounts/expense-consolidated?${params.toString()}`);
      if (res.data && res.data.rows) {
        setConsoRows(res.data.rows);
      } else {
        setConsoRows([]);
      }
    } catch (err) {
      console.error("Failed to load consolidated summary:", err);
      setConsoRows([]);
      showToast("Failed to load consolidated summary", "error");
    } finally {
      setConsoLoading(false);
    }
  };

  // ==========================================
  // Init Hooks
  // ==========================================
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchCompanies();
      fetchCategories();
      fetchVendors();
      fetchFundAllocations();
      fetchBehalfEmployees();
      fetchMyBalance();
    }
  }, [isAuthenticated, token]);

  useEffect(() => {
    if (isAuthenticated && token) {
      if (activeTab === "my") {
        fetchMyExpenses();
      } else if (activeTab === "team") {
        fetchTeamExpenses();
      } else if (activeTab === "consolidated") {
        fetchConsolidatedSummary();
      }
    }
  }, [
    isAuthenticated,
    token,
    activeTab,
    currentPage,
    filterStatus,
    filterCompany,
    filterCategory,
    filterFromDate,
    filterToDate,
    teamPage,
    teamFilterCompany,
    teamFilterStatus,
    teamFilterEmployee,
    teamFilterFrom,
    teamFilterTo
  ]);

  useEffect(() => {
    if (isAuthenticated && token && activeTab === "consolidated") {
      fetchConsolidatedSummary();
    }
  }, [isAuthenticated, token, activeTab, consoCompany, consoFromDate, consoToDate, qfPresetConso, consoSearch]);

  useEffect(() => {
    if (teamFilterEmployee) {
      fetchTeamIncomeReceipts(teamFilterEmployee);
    } else {
      setTeamIncomeReceipts([]);
    }
  }, [teamFilterEmployee]);

  // Formatters
  const fmt = (val?: number | string) => {
    const n = Number(val || 0);
    return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const fmtInt = (val?: number | string) => {
    const n = Number(val || 0);
    return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "—";
    try {
      return new Date(dateStr).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
      });
    } catch {
      return dateStr;
    }
  };

  // Status Badge Helper
  const renderStatusBadge = (status: string, isPaid?: boolean) => {
    const colorMap: Record<string, string> = {
      DRAFT: "bg-gray-100 text-gray-700 border-gray-200",
      SUBMITTED: "bg-amber-100 text-amber-800 border-amber-200",
      APPROVED: "bg-emerald-100 text-emerald-800 border-emerald-200",
      REJECTED: "bg-rose-100 text-rose-800 border-rose-200",
      PAID: "bg-purple-100 text-purple-800 border-purple-200"
    };

    return (
      <div className="flex items-center gap-1.5">
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
            colorMap[status] || "bg-gray-100 text-gray-700 border-gray-200"
          }`}
        >
          {status}
        </span>
        {isPaid && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
            PAID
          </span>
        )}
      </div>
    );
  };

  // ==========================================
  // Action Handlers
  // ==========================================

  // View Slide-over
  const handleOpenViewExpense = async (exp: ExpenseEntry) => {
    setViewExpenseData(exp);
    setViewExpenseLoading(true);
    try {
      const res = await api.get(`/staff/accounts/expense-entries/${exp.id}`);
      if (res.data) {
        setViewExpenseData(res.data.expense_entry || res.data);
      }
    } catch (err) {
      console.error("Failed to load expense details:", err);
    } finally {
      setViewExpenseLoading(false);
    }
  };

  // Show In Ledger Toggle
  const handleToggleShowInLedger = async (id: number, currentVal: boolean) => {
    try {
      const res = await api.patch(`/staff/accounts/expense-entries/${id}/show-in-ledger`, {
        show_in_ledger: !currentVal
      });
      if (res.data) {
        showToast(`Show in Ledger ${!currentVal ? "enabled" : "disabled"}`);
        if (viewExpenseData && viewExpenseData.id === id) {
          setViewExpenseData({ ...viewExpenseData, show_in_ledger: !currentVal });
        }
        fetchMyExpenses();
      }
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to update ledger visibility", "error");
    }
  };

  // Submit Draft
  const handleSubmitExpense = async (id: number) => {
    if (!confirm("Submit this expense for approval?")) return;
    try {
      await api.post(`/staff/accounts/expense-entries/${id}/submit`);
      showToast("Expense submitted for approval");
      fetchMyExpenses();
      fetchMyBalance();
      if (viewExpenseData?.id === id) setViewExpenseData(null);
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to submit expense", "error");
    }
  };

  // Open Edit Modal
  const handleOpenEdit = (exp: ExpenseEntry) => {
    setSelectedExpense(exp);
    setEditAmount(exp.amount.toString());
    setEditNotes(exp.narration || exp.description || exp.notes || "");
    setEditModalOpen(true);
  };

  // Save Edit
  const handleSaveEdit = async () => {
    if (!selectedExpense) return;
    const amt = parseFloat(editAmount);
    if (!amt || amt <= 0) {
      alert("Please enter a valid amount");
      return;
    }
    try {
      await api.put(`/staff/accounts/expense-entries/${selectedExpense.id}/edit`, {
        amount: amt,
        notes: editNotes
      });
      showToast("Expense updated successfully");
      setEditModalOpen(false);
      fetchMyExpenses();
      fetchMyBalance();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to save edits", "error");
    }
  };

  // Open Approve Modal
  const handleOpenApprove = (exp: ExpenseEntry) => {
    setSelectedExpense(exp);
    setApproveNotes("");
    setApproveModalOpen(true);
  };

  // Approve Action
  const handleApproveExpense = async () => {
    if (!selectedExpense) return;
    try {
      await api.post(`/staff/accounts/expense-entries/${selectedExpense.id}/approve`, {
        action: "APPROVE",
        remarks: approveNotes
      });
      showToast("Expense approved successfully");
      setApproveModalOpen(false);
      fetchMyExpenses();
      fetchMyBalance();
      if (activeTab === "team") fetchTeamExpenses();
      if (viewExpenseData?.id === selectedExpense.id) setViewExpenseData(null);
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to approve expense", "error");
    }
  };

  // Open Reject Modal
  const handleOpenReject = (exp: ExpenseEntry) => {
    setSelectedExpense(exp);
    setRejectReason("");
    setRejectModalOpen(true);
  };

  // Reject Action
  const handleRejectExpense = async () => {
    if (!selectedExpense) return;
    if (!rejectReason.trim()) {
      alert("Please provide a rejection reason");
      return;
    }
    try {
      await api.post(`/staff/accounts/expense-entries/${selectedExpense.id}/approve`, {
        action: "REJECT",
        remarks: rejectReason
      });
      showToast("Expense rejected", "info");
      setRejectModalOpen(false);
      fetchMyExpenses();
      fetchMyBalance();
      if (activeTab === "team") fetchTeamExpenses();
      if (viewExpenseData?.id === selectedExpense.id) setViewExpenseData(null);
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to reject expense", "error");
    }
  };

  // Open Pay Modal
  const handleOpenPay = async (exp: ExpenseEntry) => {
    setSelectedExpense(exp);
    setPayUtr("");
    setPayBankAccountId("");
    setPayNotes("");
    setCompanyBankAccounts([]);
    if (exp.company_id) {
      try {
        const res = await api.get(`/staff/accounts/companies/${exp.company_id}/bank-accounts`);
        if (res.data && res.data.bank_accounts) {
          setCompanyBankAccounts(res.data.bank_accounts.filter((b: any) => b.is_active));
        }
      } catch (err) {
        console.error("Failed to load company bank accounts:", err);
      }
    }
    setPayModalOpen(true);
  };

  // Confirm Payment
  const handleConfirmPayment = async () => {
    if (!selectedExpense) return;
    try {
      await api.post(`/staff/accounts/expense-entries/${selectedExpense.id}/mark-paid`, {
        payment_utr: payUtr.trim() || null,
        bank_account_id: payBankAccountId ? Number(payBankAccountId) : null,
        notes: payNotes.trim() || null
      });
      showToast("Expense marked as PAID and auto-approved");
      setPayModalOpen(false);
      fetchMyExpenses();
      fetchMyBalance();
      if (activeTab === "team") fetchTeamExpenses();
      if (viewExpenseData?.id === selectedExpense.id) setViewExpenseData(null);
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to mark expense as paid", "error");
    }
  };

  // Tally Action
  const handleTallyAction = async (id: number, action: "confirm" | "exception" | "tally_done") => {
    const actionLabels = {
      confirm: "confirm tally status",
      exception: "mark as tally exception",
      tally_done: "mark tally as completed"
    };
    if (!confirm(`Are you sure you want to ${actionLabels[action]} for this expense?`)) return;
    try {
      await api.patch(`/staff/accounts/expense-entries/${id}/tally-action`, { action });
      showToast(`Tally status updated`);
      fetchMyExpenses();
      if (activeTab === "team") fetchTeamExpenses();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to update tally status", "error");
    }
  };

  // Open Create Modal
  const handleOpenCreateModal = () => {
    setFormData({
      on_behalf_of_employee_id: "",
      company_id: companies.length > 0 ? companies[0].id.toString() : "",
      expense_date: new Date().toISOString().slice(0, 10),
      main_category_id: "",
      sub_category_id: "",
      amount: "",
      narration: "",
      fund_allocation_id: "",
      vendor_id: "",
      vendor_search: "",
      vendor_name: "",
      bank_ledger_category: "",
      custom_category_name: "",
      payment_mode: "CASH",
      bank_account_id: "",
      bill_number: "",
      bill_path: "",
      show_in_ledger: false
    });
    setCreateSubCategories([]);
    setFormBankAccounts([]);
    setReceiptUploadSuccess(null);
    if (user?.id) fetchFundAllocations(user.id);
    setCreateModalOpen(true);
  };

  // Handle Receipt Upload
  const handleReceiptUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingReceipt(true);
    setReceiptUploadSuccess(null);
    try {
      const data = new FormData();
      data.append("file", file);

      const res = await api.post("/staff/accounts/expense-entries/upload-receipt", data, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      if (res.data && res.data.success) {
        const url = res.data.file_path || res.data.url;
        setFormData((prev) => ({ ...prev, bill_path: url }));
        setReceiptUploadSuccess("Receipt uploaded successfully");
      } else {
        throw new Error(res.data?.detail || "Upload failed");
      }
    } catch (err: any) {
      console.error("Receipt upload error:", err);
      showToast(err.response?.data?.detail || err.message || "Failed to upload receipt", "error");
    } finally {
      setUploadingReceipt(false);
    }
  };

  // Save / Submit Expense Create Form
  const handleSaveExpenseForm = async (statusToSet: "DRAFT" | "SUBMITTED") => {
    if (
      !formData.company_id ||
      !formData.main_category_id ||
      !formData.amount ||
      !formData.narration.trim() ||
      !formData.payment_mode
    ) {
      alert("Please fill in all required fields: Company, Category, Amount, Description, and Payment Mode.");
      return;
    }

    const payload = {
      company_id: parseInt(formData.company_id),
      expense_date: formData.expense_date,
      main_category_id: parseInt(formData.main_category_id),
      sub_category_id: formData.sub_category_id ? parseInt(formData.sub_category_id) : null,
      amount: parseFloat(formData.amount),
      narration: formData.narration.trim(),
      payment_mode: formData.payment_mode,
      fund_allocation_id: formData.fund_allocation_id ? parseInt(formData.fund_allocation_id) : null,
      vendor_id: formData.vendor_id ? parseInt(formData.vendor_id) : null,
      vendor_name: formData.vendor_name || formData.vendor_search || null,
      bill_number: formData.bill_number.trim() || null,
      bill_path: formData.bill_path || null,
      bank_ledger_category: formData.bank_ledger_category || null,
      custom_category_name:
        formData.bank_ledger_category === "CUSTOM" ? formData.custom_category_name.trim() || null : null,
      bank_account_id: formData.bank_account_id ? parseInt(formData.bank_account_id) : null,
      on_behalf_of_employee_id: formData.on_behalf_of_employee_id
        ? parseInt(formData.on_behalf_of_employee_id)
        : null,
      show_in_ledger: formData.show_in_ledger,
      status: statusToSet
    };

    try {
      await api.post("/staff/accounts/expense-entries", payload);
      showToast(statusToSet === "DRAFT" ? "Expense saved as draft" : "Expense submitted for approval");
      setCreateModalOpen(false);
      fetchMyExpenses();
      fetchMyBalance();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to create expense entry", "error");
    }
  };

  // Opening Balance Save
  const handleSaveOpeningBalance = async () => {
    if (!obEmployee) {
      setObMsg({ type: "error", text: "Please select an employee." });
      return;
    }
    const amt = parseFloat(obAmount);
    if (!amt || amt <= 0) {
      setObMsg({ type: "error", text: "Please enter a valid amount." });
      return;
    }

    setObSaving(true);
    setObMsg(null);
    try {
      await api.post("/staff/accounts/fund-ledger/opening-balance", {
        employee_id: parseInt(obEmployee),
        company_id: obCompany ? parseInt(obCompany) : null,
        amount: amt,
        ledger_type: "EMPLOYEE"
      });
      setObMsg({ type: "success", text: "Opening balance saved successfully." });
      showToast("Opening balance updated");
      // Refresh context
      const res = await api.get(`/staff/accounts/fund-ledger/${obEmployee}/balance`);
      if (res.data) setObBalanceContext(res.data.balance_summary);
    } catch (err: any) {
      setObMsg({ type: "error", text: err.response?.data?.detail || "Failed to save opening balance" });
    } finally {
      setObSaving(false);
    }
  };

  const handleObEmployeeChange = async (empId: string) => {
    setObEmployee(empId);
    setObAmount("");
    setObExistingText("");
    setObBalanceContext(null);
    setObMsg(null);
    if (!empId) return;

    try {
      const res = await api.get(`/staff/accounts/fund-ledger/${empId}/balance`);
      if (res.data) {
        setObBalanceContext(res.data.balance_summary);
        if (res.data.opening_balance != null && res.data.opening_balance > 0) {
          setObAmount(res.data.opening_balance.toString());
          setObExistingText(`(existing: ${fmt(res.data.opening_balance)} — editing)`);
        }
      }
    } catch (err) {
      console.error("Failed to load employee fund balance for OB:", err);
    }
  };

  // Fund Transfer
  const handleOpenTransferModal = () => {
    setTransferCompany(companies.length > 0 ? companies[0].id.toString() : "");
    setTransferFrom(user?.id ? user.id.toString() : "");
    setTransferTo("");
    setTransferAmount("");
    setTransferMainCat("");
    setTransferSubCat("");
    setTransferSubCats([]);
    setTransferNotes("");
    setTransferFromBalance(null);
    setTransferModalOpen(true);
    if (user?.id) fetchTransferFromBalance(user.id.toString());
  };

  const fetchTransferFromBalance = async (empId: string) => {
    if (!empId) return;
    setTransferBalLoading(true);
    try {
      const res = await api.get(`/staff/accounts/fund-ledger/${empId}/balance`);
      if (res.data && res.data.balance_summary) {
        setTransferFromBalance(res.data.balance_summary.available_balance);
      }
    } catch (err) {
      setTransferFromBalance(null);
    } finally {
      setTransferBalLoading(false);
    }
  };

  const handleSaveTransfer = async () => {
    if (!transferCompany || !transferFrom || !transferTo || !transferAmount) {
      alert("Please fill in Company, From Employee, To Employee, and Amount.");
      return;
    }
    if (transferFrom === transferTo) {
      alert("From and To employees must be different.");
      return;
    }
    const amt = parseFloat(transferAmount);
    if (!amt || amt <= 0) {
      alert("Please enter a valid amount.");
      return;
    }

    try {
      const payload: any = {
        company_id: parseInt(transferCompany),
        from_employee_id: parseInt(transferFrom),
        to_employee_id: parseInt(transferTo),
        amount: amt,
        purpose: transferNotes.trim() || null
      };
      if (transferSubCat) payload.category_id = parseInt(transferSubCat);

      await api.post("/staff/accounts/fund-transfers", payload);
      showToast("Fund transfer completed successfully");
      setTransferModalOpen(false);
      fetchMyBalance();
      if (activeTab === "consolidated") fetchConsolidatedSummary();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Transfer failed", "error");
    }
  };

  // Quick Add Category
  const handleSaveQuickAddCategory = async () => {
    if (qaCatMode === "main" && !qaMainName.trim()) {
      alert("Please enter a main category name.");
      return;
    }
    if (qaCatMode === "sub" && (!qaParentId || !qaSubName.trim())) {
      alert("Please select a parent main category and enter a sub-category name.");
      return;
    }

    setQaSaving(true);
    try {
      const payload: any = {
        name: qaCatMode === "main" ? qaMainName.trim() : qaSubName.trim(),
        parent_id: qaCatMode === "sub" ? parseInt(qaParentId) : null,
        is_active: true
      };
      await api.post("/staff/accounts/expense-categories", payload);
      showToast("Category added successfully");
      setCatQuickAddModalOpen(false);
      setQaMainName("");
      setQaSubName("");
      setQaParentId("");
      fetchCategories();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to add category", "error");
    } finally {
      setQaSaving(false);
    }
  };

  // Drilldown Modal Opener
  const handleOpenDrilldown = async (title: string, statusFilter: string, tab: "my" | "team", paidOnly?: boolean) => {
    setDrilldownTitle(title);
    setDrilldownModalOpen(true);
    setDrilldownLoading(true);
    setDrilldownEntries([]);
    setExpandedDrilldownRows({});

    try {
      const params = new URLSearchParams();
      params.append("page", "1");
      params.append("page_size", "200");
      if (statusFilter) params.append("status", statusFilter);
      if (paidOnly) params.append("is_paid", "true");
      if (tab === "team") params.append("team_view", "true");

      const from = tab === "my" ? (qfPresetMy === "overall" ? "" : filterFromDate) : (qfPresetTeam === "overall" ? "" : teamFilterFrom);
      const to = tab === "my" ? (qfPresetMy === "overall" ? "" : filterToDate) : (qfPresetTeam === "overall" ? "" : teamFilterTo);
      const comp = tab === "my" ? filterCompany : teamFilterCompany;

      if (from) params.append("from_date", from);
      if (to) params.append("to_date", to);
      if (comp) params.append("company_id", comp);

      const res = await api.get(`/staff/accounts/expense-entries?${params.toString()}`);
      if (res.data) {
        setDrilldownEntries(res.data.entries || []);
      }
    } catch (err) {
      console.error("Failed to load drilldown entries:", err);
    } finally {
      setDrilldownLoading(false);
    }
  };

  // Income Receipts Drilldown Opener
  const handleOpenIncomeReceiptsDrilldown = async (empId: number, empName: string) => {
    setIncomeDrilldownTitle(`Cash Receipts — ${empName}`);
    setIncomeReceiptsModalOpen(true);
    setIncomeDrilldownLoading(true);
    setIncomeDrilldownReceipts([]);

    try {
      const res = await api.get(
        `/staff/accounts/income-entries?destination_employee_id=${empId}&page_size=200&page=1`
      );
      if (res.data) {
        setIncomeDrilldownReceipts(res.data.income_entries || res.data.entries || []);
      }
    } catch (err) {
      console.error("Failed to load income receipts:", err);
    } finally {
      setIncomeDrilldownLoading(false);
    }
  };

  // Export Consolidated CSV
  const handleExportConsolidatedCSV = () => {
    if (!consoRows.length) {
      alert("No data available to export.");
      return;
    }
    const headers = [
      "#",
      "Employee",
      "Emp Code",
      "Department",
      "Role",
      // Section 1: Confirmed Flow
      "Income (IN)",
      "Bank Alloc (IN)",
      "Transfer (IN)",
      "Total Confirmed (IN)",
      "Transfer (OUT)",
      "Bank Alloc Exp (OUT)",
      "Ext Ledger Exp (OUT)",
      "Total Confirmed (OUT)",
      "Confirmed Net Balance",
      // Section 2: Drafts Only Flow
      "Drafts (IN)",
      "Drafts (OUT)",
      "Drafts Net Balance",
      "Final Balance (Net + Drafts)",
      // Section 3: Status Breakdown
      "Draft Count",
      "Draft Amount",
      "Submitted Count",
      "Submitted Amount",
      "Approved Count",
      "Approved Amount",
      "Rejected Count",
      "Rejected Amount",
      "Paid Count",
      "Paid Amount"
    ];

    const rows = consoRows.map((r, i) => {
      const totIn = r.total_in != null ? r.total_in : (Number(r.income_entries || 0) + Number(r.bank_alloc_in || 0) + Number(r.fund_transferred_in || 0));
      const totOut = r.total_out != null ? r.total_out : (Number(r.ledger_exp || 0) + Number(r.ext_exp || 0) + Number(r.fund_transferred_out || 0));
      const netBal = r.net_balance != null ? r.net_balance : (r.balance || 0);
      const draftIn = r.draft_in != null ? r.draft_in : 0;
      const draftOut = r.draft_out != null ? r.draft_out : (r.draft_amount || 0);
      const draftBal = r.draft_balance != null ? r.draft_balance : (draftIn - draftOut);
      const finalBal = r.final_balance != null ? r.final_balance : (netBal + draftBal);

      return [
        i + 1,
        `"${r.full_name}"`,
        `"${r.emp_code}"`,
        `"${r.department || ""}"`,
        `"${r.role || ""}"`,
        // Section 1
        r.income_entries || 0,
        r.bank_alloc_in || 0,
        r.fund_transferred_in || 0,
        totIn,
        r.fund_transferred_out || 0,
        r.ledger_exp || 0,
        r.ext_exp || 0,
        totOut,
        netBal,
        // Section 2
        draftIn,
        draftOut,
        draftBal,
        finalBal,
        // Section 3
        r.draft_count || 0,
        r.draft_amount || 0,
        r.submitted_count || 0,
        r.submitted_amount || 0,
        r.approved_count || 0,
        r.approved_amount || 0,
        r.rejected_count || 0,
        r.rejected_amount || 0,
        r.paid_count || 0,
        r.paid_amount || 0
      ];
    });

    const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `expense_consolidated_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
  };

  // Consolidated Totals
  const consolidatedTotals = consoRows.reduce(
    (acc, r) => {
      acc.fund_allocated += Number(r.fund_allocated || 0);
      acc.fund_balance += Number(r.fund_balance || 0);
      acc.fund_used += Number(r.fund_used || 0);
      acc.cash_received += Number(r.cash_received || 0);
      acc.cash_balance += Number(r.cash_balance || 0);
      acc.total_in += Number(r.total_in || (Number(r.income_entries || 0) + Number(r.bank_alloc_in || 0) + Number(r.fund_transferred_in || 0)));
      acc.total_out += Number(r.total_out || (Number(r.ledger_exp || 0) + Number(r.ext_exp || 0) + Number(r.fund_transferred_out || 0)));
      acc.net_balance += Number(r.net_balance || r.balance || 0);
      acc.draft_in += Number(r.draft_in || 0);
      acc.draft_out += Number(r.draft_out || (r.draft_amount || 0));
      acc.draft_balance += Number(r.draft_balance || (Number(r.draft_in || 0) - Number(r.draft_out || (r.draft_amount || 0))));
      acc.final_balance += Number(r.final_balance || (Number(r.net_balance || 0) + Number(r.draft_balance || 0)));
      acc.total_expenses += Number(r.total_expenses || 0);
      acc.draft_count += Number(r.draft_count || 0);
      acc.submitted_count += Number(r.submitted_count || 0);
      acc.approved_count += Number(r.approved_count || 0);
      acc.rejected_count += Number(r.rejected_count || 0);
      acc.paid_count += Number(r.paid_count || 0);
      acc.approved_amount += Number(r.approved_amount || 0);
      acc.rejected_amount += Number(r.rejected_amount || 0);
      acc.paid_amount += Number(r.paid_amount || 0);
      acc.draft_amount += Number(r.draft_amount || 0);
      acc.submitted_amount += Number(r.submitted_amount || 0);
      return acc;
    },
    {
      fund_allocated: 0,
      fund_balance: 0,
      fund_used: 0,
      cash_received: 0,
      cash_balance: 0,
      total_in: 0,
      total_out: 0,
      net_balance: 0,
      draft_in: 0,
      draft_out: 0,
      draft_balance: 0,
      final_balance: 0,
      total_expenses: 0,
      draft_count: 0,
      submitted_count: 0,
      approved_count: 0,
      rejected_count: 0,
      paid_count: 0,
      approved_amount: 0,
      rejected_amount: 0,
      paid_amount: 0,
      draft_amount: 0,
      submitted_amount: 0
    }
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Toast Alert Banner */}
      {toastMsg && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-xl flex items-center gap-3 text-sm font-medium transition-all transform animate-in fade-in slide-in-from-bottom-3 ${
            toastMsg.type === "success"
              ? "bg-emerald-600 text-white"
              : toastMsg.type === "error"
              ? "bg-rose-600 text-white"
              : "bg-gray-800 text-white"
          }`}
        >
          {toastMsg.type === "success" && <CheckCircle2 className="w-5 h-5 text-white" />}
          {toastMsg.type === "error" && <AlertTriangle className="w-5 h-5 text-white" />}
          {toastMsg.type === "info" && <Banknote className="w-5 h-5 text-white" />}
          <span>{toastMsg.text}</span>
          <button onClick={() => setToastMsg(null)} className="ml-2 text-white/80 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-500 to-red-600 flex items-center justify-center text-white shadow-md shadow-red-500/20">
              <Receipt className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Expense Entries</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                Record, track, and approve company expenditures with full fund governance.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {hasAccountsAccess && (
            <button
              onClick={() => {
                if (activeTab !== "my") setActiveTab("my");
                setShowOpeningBalSection(!showOpeningBalSection);
              }}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-lg transition-colors shadow-xs"
            >
              <Coins className="w-4 h-4 text-amber-600" />
              Opening Balance
            </button>
          )}

          <a
            href="/staff/accounts/expense-categories"
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg transition-colors shadow-xs"
          >
            <Tags className="w-4 h-4 text-gray-500" />
            Categories
          </a>

          <button
            onClick={handleOpenTransferModal}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors shadow-xs"
          >
            <ArrowRightLeft className="w-4 h-4 text-indigo-600" />
            Transfer
          </button>

          <button
            onClick={handleOpenCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 rounded-lg shadow-md shadow-red-500/25 transition-all transform active:scale-95"
          >
            <Plus className="w-4 h-4" />
            New Expense
          </button>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="border-b border-gray-200">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab("my")}
            className={`pb-3.5 px-1 border-b-2 font-semibold text-sm transition-colors flex items-center gap-2 ${
              activeTab === "my"
                ? "border-red-500 text-red-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <Receipt className="w-4 h-4" />
            My Expenses
          </button>

          <button
            onClick={() => setActiveTab("team")}
            className={`pb-3.5 px-1 border-b-2 font-semibold text-sm transition-colors flex items-center gap-2 ${
              activeTab === "team"
                ? "border-red-500 text-red-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <Users className="w-4 h-4" />
            My Team
          </button>

          {(hasAccountsAccess || canCreateOnBehalf) && (
            <button
              onClick={() => setActiveTab("consolidated")}
              className={`pb-3.5 px-1 border-b-2 font-semibold text-sm transition-colors flex items-center gap-2 ${
                activeTab === "consolidated"
                  ? "border-red-500 text-red-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <Building2 className="w-4 h-4" />
              Consolidated Summary
            </button>
          )}
        </div>
      </div>

      {/* =========================================================================
          TAB 1: MY EXPENSES
      ========================================================================= */}
      {activeTab === "my" && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Fund Balance Banner Card */}
          <div className="bg-gradient-to-br from-emerald-50/70 via-teal-50/50 to-white border border-emerald-200 rounded-2xl p-5 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center shadow-xs">
                  <Wallet className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-emerald-900">My Fund Balance</h3>
                  <p className="text-xs text-emerald-700">Real-time allocated cash balance and pending commitments</p>
                </div>
              </div>
              <button
                onClick={fetchMyBalance}
                disabled={balanceLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-100/80 hover:bg-emerald-200/80 rounded-lg transition-colors border border-emerald-300/50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${balanceLoading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="bg-white rounded-xl p-3.5 border border-emerald-100 text-center shadow-2xs">
                <div className="text-lg font-bold text-emerald-600">
                  {balanceSummary ? fmt(balanceSummary.available_balance) : "—"}
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-0.5">Available Balance</div>
              </div>

              <div className="bg-white rounded-xl p-3.5 border border-emerald-100 text-center shadow-2xs">
                <div className="text-lg font-bold text-rose-600">
                  {balanceSummary ? fmt(balanceSummary.approved_expenses) : "—"}
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-0.5">Approved Expenses</div>
              </div>

              <div className="bg-white rounded-xl p-3.5 border border-emerald-100 text-center shadow-2xs">
                <div className="text-lg font-bold text-amber-600">
                  {balanceSummary ? fmt(balanceSummary.pending_submitted) : "—"}
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-0.5">Pending Review</div>
              </div>

              <div className="bg-white rounded-xl p-3.5 border border-emerald-100 text-center shadow-2xs">
                <div className="text-lg font-bold text-gray-600">
                  {balanceSummary ? fmt(balanceSummary.pending_draft) : "—"}
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-0.5">Draft Expenses</div>
              </div>

              <div className="bg-emerald-600/10 rounded-xl p-3.5 border border-emerald-300 text-center shadow-2xs col-span-2 sm:col-span-1">
                <div className="text-lg font-extrabold text-emerald-800">
                  {balanceSummary ? fmt(balanceSummary.effective_balance_after_submitted) : "—"}
                </div>
                <div className="text-[11px] font-bold text-emerald-900 mt-0.5">Effective Balance</div>
              </div>
            </div>
          </div>

          {/* Opening Balance Collapsible Section */}
          {showOpeningBalSection && (
            <div className="bg-white border border-amber-200 rounded-2xl p-5 shadow-sm space-y-4 animate-in fade-in duration-200">
              <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                <div className="flex items-center gap-2">
                  <Coins className="w-5 h-5 text-amber-600" />
                  <h3 className="text-base font-bold text-gray-900">Set Opening Balance</h3>
                </div>
                <button
                  onClick={() => setShowOpeningBalSection(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Employee *</label>
                  <select
                    value={obEmployee}
                    onChange={(e) => handleObEmployeeChange(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  >
                    <option value="">Select Employee</option>
                    {behalfEmployees.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.full_name || e.name} ({e.emp_code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Company</label>
                  <select
                    value={obCompany}
                    onChange={(e) => setObCompany(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  >
                    <option value="">Select Company (Optional)</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">
                    Opening Balance (₹) <span className="text-gray-400 font-normal">{obExistingText}</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={obAmount}
                    onChange={(e) => setObAmount(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  />
                </div>

                <div>
                  <button
                    onClick={handleSaveOpeningBalance}
                    disabled={obSaving}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors"
                  >
                    <Check className="w-4 h-4" />
                    {obSaving ? "Saving..." : "Save Opening Balance"}
                  </button>
                </div>
              </div>

              {/* Selected Employee Fund Summary */}
              {obBalanceContext && (
                <div className="bg-emerald-50/80 border border-emerald-200 rounded-xl p-3.5 text-xs text-emerald-900 flex items-center gap-6 flex-wrap">
                  <span className="font-bold flex items-center gap-1.5">
                    <Wallet className="w-4 h-4 text-emerald-700" />
                    Current Balance Summary:
                  </span>
                  <span>Available: <strong className="text-emerald-700">{fmt(obBalanceContext.available_balance)}</strong></span>
                  <span>Allocated: <strong className="text-indigo-700">{fmt(obBalanceContext.total_received)}</strong></span>
                  <span>Approved Exp: <strong className="text-rose-700">{fmt(obBalanceContext.approved_expenses)}</strong></span>
                  <span>Effective: <strong className="text-purple-700">{fmt(obBalanceContext.effective_balance_after_submitted)}</strong></span>
                </div>
              )}

              {obMsg && (
                <div
                  className={`text-xs font-medium px-3 py-2 rounded-lg ${
                    obMsg.type === "success" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                  }`}
                >
                  {obMsg.text}
                </div>
              )}
            </div>
          )}

          {/* Quick Date Filter Pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mr-1">Quick Date:</span>
            {[
              { label: "Overall", value: "overall" },
              { label: "Today", value: "today" },
              { label: "Yesterday", value: "yesterday" },
              { label: "This Week", value: "this_week" },
              { label: "Last Week", value: "last_week" },
              { label: "Custom", value: "custom" }
            ].map((p) => (
              <button
                key={p.value}
                onClick={() => handleQuickFilter("my", p.value)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                  qfPresetMy === p.value
                    ? "bg-red-600 text-white shadow-xs"
                    : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {p.label}
              </button>
            ))}

            {qfPresetMy === "custom" && (
              <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1">
                <span className="text-xs font-semibold text-gray-600">From:</span>
                <input
                  type="date"
                  value={filterFromDate}
                  onChange={(e) => {
                    setFilterFromDate(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="px-2 py-0.5 text-xs border border-gray-300 rounded bg-white"
                />
                <span className="text-xs font-semibold text-gray-600">To:</span>
                <input
                  type="date"
                  value={filterToDate}
                  onChange={(e) => {
                    setFilterToDate(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="px-2 py-0.5 text-xs border border-gray-300 rounded bg-white"
                />
              </div>
            )}
          </div>

          {/* Detailed Filters Row */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => {
                  setFilterStatus(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50/50 focus:ring-2 focus:ring-red-500 focus:outline-none"
              >
                <option value="">All Status</option>
                <option value="DRAFT">Draft</option>
                <option value="SUBMITTED">Submitted</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Company</label>
              <select
                value={filterCompany}
                onChange={(e) => {
                  setFilterCompany(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50/50 focus:ring-2 focus:ring-red-500 focus:outline-none"
              >
                <option value="">All Companies</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name || c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Category</label>
              <select
                value={filterCategory}
                onChange={(e) => {
                  setFilterCategory(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50/50 focus:ring-2 focus:ring-red-500 focus:outline-none"
              >
                <option value="">All Categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Interactive Stat Cards Row */}
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3.5">
            <div
              onClick={() => handleOpenDrilldown("Draft Expenses", "DRAFT", "my")}
              className="bg-white border border-gray-200 hover:border-gray-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="text-xl font-bold text-gray-800">{summary.draft_count || 0}</div>
              <div className="text-xs font-semibold text-gray-600 mt-0.5">{fmtInt(summary.draft_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1 flex items-center justify-between">
                <span>Drafts</span>
                <Search className="w-3 h-3 opacity-60" />
              </div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Submitted Expenses", "SUBMITTED", "my")}
              className="bg-white border border-amber-200 hover:border-amber-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="text-xl font-bold text-amber-600">{summary.submitted_count || 0}</div>
              <div className="text-xs font-semibold text-amber-700 mt-0.5">{fmtInt(summary.submitted_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1 flex items-center justify-between">
                <span>Submitted</span>
                <Search className="w-3 h-3 opacity-60" />
              </div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Approved Expenses", "APPROVED", "my")}
              className="bg-white border border-emerald-200 hover:border-emerald-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="text-xl font-bold text-emerald-600">{summary.approved_count || 0}</div>
              <div className="text-xs font-semibold text-emerald-700 mt-0.5">{fmtInt(summary.total_approved_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1 flex items-center justify-between">
                <span>Approved</span>
                <Search className="w-3 h-3 opacity-60" />
              </div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Rejected Expenses", "REJECTED", "my")}
              className="bg-white border border-rose-200 hover:border-rose-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="text-xl font-bold text-rose-600">{summary.rejected_count || 0}</div>
              <div className="text-xs font-semibold text-rose-700 mt-0.5">{fmtInt(summary.rejected_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1 flex items-center justify-between">
                <span>Rejected</span>
                <Search className="w-3 h-3 opacity-60" />
              </div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Paid Expenses", "APPROVED", "my", true)}
              className="bg-white border border-purple-200 hover:border-purple-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="text-xl font-bold text-purple-700">{summary.paid_count || 0}</div>
              <div className="text-xs font-semibold text-purple-800 mt-0.5">{fmtInt(summary.total_paid_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1 flex items-center justify-between">
                <span>Paid</span>
                <Search className="w-3 h-3 opacity-60" />
              </div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("All Expenses", "", "my")}
              className="bg-white border border-indigo-200 hover:border-indigo-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="text-xl font-bold text-indigo-700">{totalCount}</div>
              <div className="text-xs font-semibold text-indigo-800 mt-0.5">
                {fmtInt(
                  summary.total_amount != null
                    ? summary.total_amount
                    : (summary.draft_amount || 0) +
                      (summary.submitted_amount || 0) +
                      (summary.total_approved_amount || 0) +
                      (summary.rejected_amount || 0)
                )}
              </div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1 flex items-center justify-between">
                <span>Total Recorded</span>
                <Search className="w-3 h-3 opacity-60" />
              </div>
            </div>
          </div>

          {/* Expenses Table Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-500" />
                <span className="font-bold text-gray-900 text-sm">Expense Records</span>
              </div>
              <span className="text-xs font-medium text-gray-500">{totalCount} total entries</span>
            </div>

            {loading ? (
              <div className="p-12 text-center text-gray-400 space-y-3">
                <RefreshCw className="w-8 h-8 mx-auto animate-spin text-red-500" />
                <p className="text-sm font-medium text-gray-500">Loading expenses...</p>
              </div>
            ) : expenses.length === 0 ? (
              <div className="p-12 text-center text-gray-400 space-y-3">
                <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto text-gray-400">
                  <Receipt className="w-7 h-7" />
                </div>
                <h4 className="text-base font-bold text-gray-800">No Expense Entries Found</h4>
                <p className="text-sm text-gray-500 max-w-sm mx-auto">
                  Click "New Expense" above to record expenditures and route for approval.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                      <th className="px-4 py-3.5">ID</th>
                      <th className="px-4 py-3.5">Date</th>
                      <th className="px-4 py-3.5">Company</th>
                      <th className="px-4 py-3.5">Category</th>
                      <th className="px-4 py-3.5">Paid To</th>
                      <th className="px-4 py-3.5">Ledger Cat</th>
                      <th className="px-4 py-3.5">Description</th>
                      <th className="px-4 py-3.5 text-right">Amount</th>
                      <th className="px-4 py-3.5 text-center">Status</th>
                      <th className="px-4 py-3.5 text-center">Tally</th>
                      <th className="px-4 py-3.5 text-center">Alloc #</th>
                      <th className="px-4 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {expenses.map((exp) => {
                      const isCreator = exp.created_by_id === user?.id;
                      return (
                        <tr key={exp.id} className="hover:bg-gray-50/60 transition-colors">
                          <td className="px-4 py-3 font-mono font-bold text-xs text-indigo-600">
                            #{exp.entry_number || exp.id}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                            {formatDate(exp.expense_date)}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-800 font-medium">
                            {exp.company_name || "—"}
                          </td>
                          <td className="px-4 py-3 text-xs">
                            <span className="font-medium text-gray-900">{exp.category_name || "—"}</span>
                            {exp.sub_category_name && (
                              <span className="text-[11px] text-gray-400 block">{exp.sub_category_name}</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-xs font-medium text-gray-700">
                            {exp.vendor_name || exp.paid_to || "—"}
                          </td>
                          <td className="px-4 py-3 text-xs">
                            {exp.bank_ledger_category ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-200">
                                {exp.bank_ledger_category === "CUSTOM"
                                  ? exp.custom_category_name || "CUSTOM"
                                  : exp.bank_ledger_category}
                              </span>
                            ) : (
                              <span className="text-gray-400 text-xs">—</span>
                            )}
                          </td>
                          <td
                            className="px-4 py-3 text-xs text-gray-600 max-w-[200px] truncate"
                            title={exp.narration || exp.description || ""}
                          >
                            {exp.narration || exp.description || "—"}
                          </td>
                          <td className="px-4 py-3 text-xs font-mono font-bold text-rose-600 text-right whitespace-nowrap">
                            - {fmt(exp.amount)}
                          </td>
                          <td className="px-4 py-3 text-center whitespace-nowrap">
                            {renderStatusBadge(exp.status, exp.is_paid)}
                          </td>
                          <td className="px-4 py-3 text-center whitespace-nowrap">
                            {exp.tally_status ? (
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                  exp.tally_status === "SYNCED" || exp.tally_status === "CONFIRMED"
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : exp.tally_status === "EXCEPTION"
                                    ? "bg-amber-50 text-amber-700 border-amber-200"
                                    : "bg-purple-50 text-purple-700 border-purple-200"
                                }`}
                              >
                                {exp.tally_status.replace("_", " ")}
                              </span>
                            ) : (
                              <span className="text-gray-400 text-xs">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center font-mono text-xs text-gray-500">
                            {exp.fund_allocation_id ? `#${exp.fund_allocation_id}` : "—"}
                          </td>
                          <td className="px-4 py-3 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1.5">
                              {/* View Action */}
                              <button
                                onClick={() => handleOpenViewExpense(exp)}
                                title="View Details"
                                className="p-1.5 rounded-lg text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                              >
                                <Eye className="w-4 h-4" />
                              </button>

                              {/* Draft Actions */}
                              {exp.status === "DRAFT" && (isCreator || hasFullAccess) && (
                                <button
                                  onClick={() => handleSubmitExpense(exp.id)}
                                  title="Submit for Approval"
                                  className="p-1.5 rounded-lg text-amber-600 hover:bg-amber-50 transition-colors"
                                >
                                  <Send className="w-4 h-4" />
                                </button>
                              )}
                              {exp.status === "DRAFT" && (isCreator || hasAccountsAccess) && (
                                <button
                                  onClick={() => handleOpenEdit(exp)}
                                  title="Edit Draft"
                                  className="p-1.5 rounded-lg text-blue-600 hover:bg-blue-50 transition-colors"
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                              )}

                              {/* Submitted Actions */}
                              {exp.status === "SUBMITTED" && hasAccountsAccess && (
                                <>
                                  <button
                                    onClick={() => handleOpenApprove(exp)}
                                    title="Approve"
                                    className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors"
                                  >
                                    <CheckCircle2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => handleOpenReject(exp)}
                                    title="Reject"
                                    className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 transition-colors"
                                  >
                                    <XCircle className="w-4 h-4" />
                                  </button>
                                </>
                              )}

                              {/* Pay Action */}
                              {!exp.is_paid &&
                                ["DRAFT", "SUBMITTED", "APPROVED"].includes(exp.status) &&
                                hasAccountsAccess && (
                                  <button
                                    onClick={() => handleOpenPay(exp)}
                                    title="Mark Paid"
                                    className="p-1.5 rounded-lg text-purple-600 hover:bg-purple-50 transition-colors"
                                  >
                                    <Banknote className="w-4 h-4" />
                                  </button>
                                )}

                              {/* Tally Actions */}
                              {exp.status === "APPROVED" && hasAccountsAccess && exp.tally_status !== "SYNCED" && (
                                <button
                                  onClick={() => handleTallyAction(exp.id, "confirm")}
                                  title="Tally Confirm"
                                  className="p-1.5 rounded-lg text-emerald-700 hover:bg-emerald-100 transition-colors"
                                >
                                  <Stamp className="w-4 h-4" />
                                </button>
                              )}

                              {/* Receipt View */}
                              {exp.bill_path && (
                                <a
                                  href={exp.bill_path}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  title="View Receipt"
                                  className="p-1.5 rounded-lg text-sky-600 hover:bg-sky-50 transition-colors"
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </a>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="px-6 py-3.5 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
                <div className="text-xs text-gray-500">
                  Page {currentPage} of {totalPages}
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    className="p-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 disabled:opacity-40 hover:bg-gray-50 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const p = i + 1;
                    return (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p)}
                        className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors ${
                          currentPage === p
                            ? "bg-red-600 text-white shadow-xs"
                            : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"
                        }`}
                      >
                        {p}
                      </button>
                    );
                  })}
                  <button
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    className="p-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 disabled:opacity-40 hover:bg-gray-50 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 2: MY TEAM EXPENSES
      ========================================================================= */}
      {activeTab === "team" && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Employee Balance Lookup for privileged/Accounts */}
          {hasAccountsAccess && (
            <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-xs flex items-center gap-4 flex-wrap">
              <span className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                <Wallet className="w-4 h-4 text-indigo-600" />
                Employee Fund Balance Lookup:
              </span>
              <select
                value={teamBalEmpSelect}
                onChange={(e) => {
                  setTeamBalEmpSelect(e.target.value);
                  fetchTeamMemberBalance(e.target.value);
                }}
                className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white min-w-[220px] focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="">— Select Employee —</option>
                {behalfEmployees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.full_name || e.name} ({e.emp_code})
                  </option>
                ))}
              </select>

              {teamBalLoading ? (
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <RefreshCw className="w-3 h-3 animate-spin" /> Loading balance...
                </span>
              ) : teamBalData?.balance ? (
                <div className="flex items-center gap-4 text-xs font-medium text-gray-700 bg-indigo-50/60 px-3 py-1 rounded-lg border border-indigo-100">
                  <span>Available: <strong className="text-emerald-700">{fmt(teamBalData.balance.available_balance)}</strong></span>
                  <span>Allocated: <strong className="text-indigo-700">{fmt(teamBalData.balance.total_received)}</strong></span>
                  <span>Approved: <strong className="text-rose-700">{fmt(teamBalData.balance.approved_expenses)}</strong></span>
                  <span>Effective: <strong className="text-purple-700">{fmt(teamBalData.balance.effective_balance_after_submitted)}</strong></span>
                </div>
              ) : null}
            </div>
          )}

          {/* Quick Date Filter Pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mr-1">Quick Date:</span>
            {[
              { label: "Overall", value: "overall" },
              { label: "Today", value: "today" },
              { label: "Yesterday", value: "yesterday" },
              { label: "This Week", value: "this_week" },
              { label: "Last Week", value: "last_week" },
              { label: "Custom", value: "custom" }
            ].map((p) => (
              <button
                key={p.value}
                onClick={() => handleQuickFilter("team", p.value)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                  qfPresetTeam === p.value
                    ? "bg-red-600 text-white shadow-xs"
                    : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {p.label}
              </button>
            ))}

            {qfPresetTeam === "custom" && (
              <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1">
                <span className="text-xs font-semibold text-gray-600">From:</span>
                <input
                  type="date"
                  value={teamFilterFrom}
                  onChange={(e) => {
                    setTeamFilterFrom(e.target.value);
                    setTeamPage(1);
                  }}
                  className="px-2 py-0.5 text-xs border border-gray-300 rounded bg-white"
                />
                <span className="text-xs font-semibold text-gray-600">To:</span>
                <input
                  type="date"
                  value={teamFilterTo}
                  onChange={(e) => {
                    setTeamFilterTo(e.target.value);
                    setTeamPage(1);
                  }}
                  className="px-2 py-0.5 text-xs border border-gray-300 rounded bg-white"
                />
              </div>
            )}
          </div>

          {/* Team Stat Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3.5">
            <div
              onClick={() => handleOpenDrilldown("Team — Draft Expenses", "DRAFT", "team")}
              className="bg-white border border-gray-200 hover:border-gray-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5"
            >
              <div className="text-xl font-bold text-gray-800">{teamSummary.draft_count || 0}</div>
              <div className="text-xs font-semibold text-gray-600 mt-0.5">{fmtInt(teamSummary.draft_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1">Drafts</div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Team — Submitted Expenses", "SUBMITTED", "team")}
              className="bg-white border border-amber-200 hover:border-amber-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5"
            >
              <div className="text-xl font-bold text-amber-600">{teamSummary.submitted_count || 0}</div>
              <div className="text-xs font-semibold text-amber-700 mt-0.5">{fmtInt(teamSummary.submitted_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1">Submitted</div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Team — Approved Expenses", "APPROVED", "team")}
              className="bg-white border border-emerald-200 hover:border-emerald-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5"
            >
              <div className="text-xl font-bold text-emerald-600">{teamSummary.approved_count || 0}</div>
              <div className="text-xs font-semibold text-emerald-700 mt-0.5">
                {fmtInt(teamSummary.total_approved_amount)}
              </div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1">Approved</div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Team — Rejected Expenses", "REJECTED", "team")}
              className="bg-white border border-rose-200 hover:border-rose-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5"
            >
              <div className="text-xl font-bold text-rose-600">{teamSummary.rejected_count || 0}</div>
              <div className="text-xs font-semibold text-rose-700 mt-0.5">{fmtInt(teamSummary.rejected_amount)}</div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1">Rejected</div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Team — All Expenses", "", "team")}
              className="bg-white border border-indigo-200 hover:border-indigo-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5"
            >
              <div className="text-xl font-bold text-indigo-700">
                {(teamSummary.draft_count || 0) +
                  (teamSummary.submitted_count || 0) +
                  (teamSummary.approved_count || 0) +
                  (teamSummary.rejected_count || 0)}
              </div>
              <div className="text-xs font-semibold text-indigo-800 mt-0.5">
                {fmtInt(
                  teamSummary.total_amount != null
                    ? teamSummary.total_amount
                    : (teamSummary.draft_amount || 0) +
                      (teamSummary.submitted_amount || 0) +
                      (teamSummary.total_approved_amount || 0) +
                      (teamSummary.rejected_amount || 0)
                )}
              </div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1">Total Entries</div>
            </div>

            <div
              onClick={() => handleOpenDrilldown("Team — Approved Amount", "APPROVED", "team")}
              className="bg-white border border-emerald-200 hover:border-emerald-400 p-4 rounded-xl shadow-xs cursor-pointer transition-all transform hover:-translate-y-0.5"
            >
              <div className="text-lg font-bold text-emerald-700 truncate">
                {fmtInt(teamSummary.total_approved_amount)}
              </div>
              <div className="text-[11px] font-semibold text-gray-400 mt-1">Approved Amt</div>
            </div>
          </div>

          {/* Team Table Header Filters */}
          <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-xs flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2.5">
              <Users className="w-5 h-5 text-gray-600" />
              <span className="font-bold text-gray-900 text-sm">Team Expense Entries</span>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={teamFilterCompany}
                onChange={(e) => {
                  setTeamFilterCompany(e.target.value);
                  setTeamPage(1);
                }}
                className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
              >
                <option value="">All Companies</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name || c.name}
                  </option>
                ))}
              </select>

              <select
                value={teamFilterStatus}
                onChange={(e) => {
                  setTeamFilterStatus(e.target.value);
                  setTeamPage(1);
                }}
                className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
              >
                <option value="">All Status</option>
                <option value="DRAFT">Draft</option>
                <option value="SUBMITTED">Submitted</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
              </select>

              <select
                value={teamFilterEmployee}
                onChange={(e) => {
                  setTeamFilterEmployee(e.target.value);
                  setTeamPage(1);
                }}
                className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg bg-white min-w-[160px]"
              >
                <option value="">All Members</option>
                {behalfEmployees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.full_name || e.name} ({e.emp_code})
                  </option>
                ))}
              </select>

              <button
                onClick={fetchTeamExpenses}
                className="p-1.5 text-gray-600 hover:text-indigo-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Team Table Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
            {teamLoading ? (
              <div className="p-12 text-center text-gray-400 space-y-3">
                <RefreshCw className="w-8 h-8 mx-auto animate-spin text-red-500" />
                <p className="text-sm font-medium text-gray-500">Loading team expenses...</p>
              </div>
            ) : teamExpenses.length === 0 ? (
              <div className="p-12 text-center text-gray-400 space-y-3">
                <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto text-gray-400">
                  <Users className="w-7 h-7" />
                </div>
                <h4 className="text-base font-bold text-gray-800">No Team Expenses Found</h4>
                <p className="text-sm text-gray-500 max-w-sm mx-auto">
                  Team members' expense submissions will appear here once recorded.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                      <th className="px-4 py-3.5">ID</th>
                      <th className="px-4 py-3.5">Date</th>
                      <th className="px-4 py-3.5">Employee</th>
                      <th className="px-4 py-3.5">Company</th>
                      <th className="px-4 py-3.5">Category</th>
                      <th className="px-4 py-3.5">Paid To</th>
                      <th className="px-4 py-3.5">Description</th>
                      <th className="px-4 py-3.5 text-right">Amount</th>
                      <th className="px-4 py-3.5 text-center">Status</th>
                      <th className="px-4 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {teamExpenses.map((exp) => (
                      <tr key={exp.id} className="hover:bg-gray-50/60 transition-colors">
                        <td className="px-4 py-3 font-mono font-bold text-xs text-indigo-600">
                          #{exp.entry_number || exp.id}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                          {formatDate(exp.expense_date)}
                        </td>
                        <td className="px-4 py-3 text-xs font-bold text-gray-900">
                          {exp.created_by_name || exp.employee_name || "—"}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-800 font-medium">
                          {exp.company_name || "—"}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-700">
                          {exp.category_name || exp.main_category_name || "—"}
                        </td>
                        <td className="px-4 py-3 text-xs font-medium text-gray-700">
                          {exp.vendor_name || exp.paid_to || "—"}
                        </td>
                        <td
                          className="px-4 py-3 text-xs text-gray-600 max-w-[200px] truncate"
                          title={exp.narration || exp.description || ""}
                        >
                          {exp.narration || exp.description || "—"}
                        </td>
                        <td className="px-4 py-3 text-xs font-mono font-bold text-gray-900 text-right whitespace-nowrap">
                          {fmt(exp.amount)}
                        </td>
                        <td className="px-4 py-3 text-center whitespace-nowrap">
                          {renderStatusBadge(exp.status, exp.is_paid)}
                        </td>
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleOpenViewExpense(exp)}
                              title="View Details"
                              className="p-1.5 rounded-lg text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                            >
                              <Eye className="w-4 h-4" />
                            </button>

                            {exp.status === "SUBMITTED" && hasAccountsAccess && (
                              <>
                                <button
                                  onClick={() => handleOpenApprove(exp)}
                                  title="Approve"
                                  className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors"
                                >
                                  <CheckCircle2 className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleOpenReject(exp)}
                                  title="Reject"
                                  className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 transition-colors"
                                >
                                  <XCircle className="w-4 h-4" />
                                </button>
                              </>
                            )}

                            {!exp.is_paid &&
                              ["DRAFT", "SUBMITTED", "APPROVED"].includes(exp.status) &&
                              hasAccountsAccess && (
                                <button
                                  onClick={() => handleOpenPay(exp)}
                                  title="Mark Paid"
                                  className="p-1.5 rounded-lg text-purple-600 hover:bg-purple-50 transition-colors"
                                >
                                  <Banknote className="w-4 h-4" />
                                </button>
                              )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Team Pagination */}
            {teamTotalPages > 1 && (
              <div className="px-6 py-3.5 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
                <div className="text-xs text-gray-500">
                  Page {teamPage} of {teamTotalPages}
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    disabled={teamPage <= 1}
                    onClick={() => setTeamPage((p) => Math.max(1, p - 1))}
                    className="p-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 disabled:opacity-40 hover:bg-gray-50"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    disabled={teamPage >= teamTotalPages}
                    onClick={() => setTeamPage((p) => Math.min(teamTotalPages, p + 1))}
                    className="p-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 disabled:opacity-40 hover:bg-gray-50"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Filtered Employee Income Receipts Section */}
          {teamFilterEmployee && (
            <div className="bg-white border border-cyan-200 rounded-2xl overflow-hidden shadow-xs">
              <div className="bg-gradient-to-r from-sky-800 to-cyan-700 px-5 py-3.5 flex items-center justify-between text-white">
                <div className="flex items-center gap-2">
                  <HandCoins className="w-5 h-5 text-cyan-200" />
                  <h4 className="font-bold text-sm">Cash Received (Income Entries) for Selected Employee</h4>
                </div>
                <span className="bg-white/20 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
                  {teamIncomeReceipts.length} receipts
                </span>
              </div>

              {teamIncomeReceiptsLoading ? (
                <div className="p-8 text-center text-gray-400">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-cyan-600 mb-2" />
                  <p className="text-xs">Loading income receipts...</p>
                </div>
              ) : teamIncomeReceipts.length === 0 ? (
                <div className="p-8 text-center text-gray-400 text-xs">
                  No cash receipts found for this employee.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-sky-50/50 border-b border-sky-100 text-sky-900 font-bold uppercase">
                        <th className="px-4 py-2.5">Entry #</th>
                        <th className="px-4 py-2.5">Date</th>
                        <th className="px-4 py-2.5">Payer</th>
                        <th className="px-4 py-2.5">Company</th>
                        <th className="px-4 py-2.5 text-right">Amount</th>
                        <th className="px-4 py-2.5 text-center">Mode</th>
                        <th className="px-4 py-2.5 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {teamIncomeReceipts.map((inc) => (
                        <tr key={inc.id} className="hover:bg-sky-50/30">
                          <td className="px-4 py-2.5 font-mono font-bold text-indigo-600">
                            {inc.entry_number || `#${inc.id}`}
                          </td>
                          <td className="px-4 py-2.5 text-gray-600">{formatDate(inc.income_date || inc.created_at)}</td>
                          <td className="px-4 py-2.5 font-medium text-gray-900">{inc.payer_name || "—"}</td>
                          <td className="px-4 py-2.5 text-gray-700">{inc.company_name || "—"}</td>
                          <td className="px-4 py-2.5 font-bold text-emerald-700 text-right">{fmt(inc.amount)}</td>
                          <td className="px-4 py-2.5 text-center font-medium text-gray-600">
                            {inc.payment_mode || "—"}
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              {inc.status}
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
        </div>
      )}

      {/* =========================================================================
          TAB 3: CONSOLIDATED SUMMARY
      ========================================================================= */}
      {activeTab === "consolidated" && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Quick Date Filter Pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mr-1">Quick Date:</span>
            {[
              { label: "Overall", value: "overall" },
              { label: "Today", value: "today" },
              { label: "Yesterday", value: "yesterday" },
              { label: "This Week", value: "this_week" },
              { label: "Last Week", value: "last_week" },
              { label: "Custom", value: "custom" }
            ].map((p) => (
              <button
                key={p.value}
                onClick={() => handleQuickFilter("consolidated", p.value)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                  qfPresetConso === p.value
                    ? "bg-red-600 text-white shadow-xs"
                    : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {p.label}
              </button>
            ))}

            {qfPresetConso === "custom" && (
              <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1">
                <span className="text-xs font-semibold text-gray-600">From:</span>
                <input
                  type="date"
                  value={consoFromDate}
                  onChange={(e) => setConsoFromDate(e.target.value)}
                  className="px-2 py-0.5 text-xs border border-gray-300 rounded bg-white"
                />
                <span className="text-xs font-semibold text-gray-600">To:</span>
                <input
                  type="date"
                  value={consoToDate}
                  onChange={(e) => setConsoToDate(e.target.value)}
                  className="px-2 py-0.5 text-xs border border-gray-300 rounded bg-white"
                />
              </div>
            )}
          </div>

          {/* Consolidated Filter Card */}
          <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-xs flex items-end gap-3 flex-wrap">
            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Company</label>
              <select
                value={consoCompany}
                onChange={(e) => setConsoCompany(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white min-w-[150px]"
              >
                <option value="">All Companies</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name || c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Search Employee</label>
              <input
                type="text"
                placeholder="Search name or code..."
                value={consoSearch}
                onChange={(e) => setConsoSearch(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white min-w-[170px]"
              />
            </div>

            <button
              onClick={fetchConsolidatedSummary}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded-lg shadow-xs transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${consoLoading ? "animate-spin" : ""}`} />
              Load / Refresh
            </button>

            <button
              onClick={handleExportConsolidatedCSV}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 border border-gray-300 rounded-lg shadow-xs transition-colors"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>

          {/* Consolidated Stat Strip */}
          {consoRows.length > 0 && (
            <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-blue-950 rounded-2xl p-5 text-white shadow-md grid grid-cols-2 sm:grid-cols-6 gap-4">
              <div>
                <div className="text-2xl font-bold">{consoRows.length}</div>
                <div className="text-xs text-blue-200 mt-0.5">Total Employees</div>
              </div>
              <div>
                <div className="text-lg font-bold text-blue-300">{fmt(consolidatedTotals.fund_allocated)}</div>
                <div className="text-xs text-blue-200 mt-0.5">Total Allocated</div>
              </div>
              <div>
                <div className="text-lg font-bold text-emerald-300">{fmt(consolidatedTotals.fund_balance)}</div>
                <div className="text-xs text-blue-200 mt-0.5">Total Balance</div>
              </div>
              <div>
                <div className="text-lg font-bold text-cyan-300">{fmt(consolidatedTotals.cash_received)}</div>
                <div className="text-xs text-blue-200 mt-0.5">Cash Received (IN)</div>
              </div>
              <div>
                <div className="text-lg font-bold text-purple-300">{fmt(consolidatedTotals.cash_balance)}</div>
                <div className="text-xs text-blue-200 mt-0.5">Cash Balance</div>
              </div>
              <div>
                <div className="text-lg font-bold text-rose-300">{fmt(consolidatedTotals.approved_amount)}</div>
                <div className="text-xs text-blue-200 mt-0.5">Approved Expenses</div>
              </div>
            </div>
          )}

          {/* Consolidated Table Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
            {consoLoading ? (
              <div className="p-16 text-center text-gray-400 space-y-3">
                <RefreshCw className="w-8 h-8 mx-auto animate-spin text-blue-600" />
                <p className="text-sm font-medium text-gray-500">Loading consolidated financial matrix...</p>
              </div>
            ) : consoRows.length === 0 ? (
              <div className="p-16 text-center text-gray-400 space-y-3">
                <Building2 className="w-10 h-10 mx-auto text-gray-300" />
                <h4 className="text-base font-bold text-gray-700">No Consolidated Data</h4>
                <p className="text-sm text-gray-500">Click "Load / Refresh" to fetch the summary.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    {/* Tier 1 Group Headers */}
                    <tr className="border-b border-gray-200 text-xs uppercase font-bold tracking-wider whitespace-nowrap">
                      <th colSpan={3} className="bg-gray-100 text-gray-700 p-2 text-left border-r border-gray-200">
                        Staff Details
                      </th>
                      <th colSpan={3} className="bg-emerald-50 text-emerald-800 p-2 text-center border-r border-emerald-200">
                        Section 1: Confirmed IN (Inflow)
                      </th>
                      <th colSpan={3} className="bg-rose-50 text-rose-800 p-2 text-center border-r border-rose-200">
                        Section 1: Confirmed OUT (Outflow)
                      </th>
                      <th colSpan={1} className="bg-blue-50 text-blue-800 p-2 text-right border-r border-blue-200">
                        Net Balance
                      </th>
                      <th colSpan={4} className="bg-amber-50 text-amber-800 p-2 text-center border-r border-amber-200">
                        Section 2: Drafts Only Flow
                      </th>
                      <th colSpan={5} className="bg-gray-50 text-gray-700 p-2 text-center border-r border-gray-200">
                        Section 3: Expense Counts
                      </th>
                      <th colSpan={5} className="bg-gray-50 text-gray-700 p-2 text-center">
                        Section 3: Expense Amounts
                      </th>
                    </tr>
                    {/* Tier 2 Column Headers */}
                    <tr className="bg-gray-50 border-b-2 border-gray-200 text-gray-700 font-bold uppercase whitespace-nowrap">
                      <th className="p-3">#</th>
                      <th className="p-3">Employee</th>
                      <th className="p-3 border-r border-gray-200">Dept / Role</th>
                      
                      {/* Section 1 Inflow */}
                      <th className="p-3 text-right text-cyan-700">Income Entries</th>
                      <th className="p-3 text-right text-blue-700">Bank Ledgers</th>
                      <th className="p-3 text-right text-emerald-700 bg-emerald-50 border-r border-emerald-200">Total IN</th>
                      
                      {/* Section 1 Outflow */}
                      <th className="p-3 text-right text-rose-700">Ledger Exp</th>
                      <th className="p-3 text-right text-orange-700">External Exp</th>
                      <th className="p-3 text-right text-rose-800 bg-rose-50 border-r border-rose-200">Total OUT</th>
                      
                      {/* Section 1 Net Balance */}
                      <th className="p-3 text-right text-blue-800 bg-blue-50 border-r border-blue-200">Net Balance</th>
                      
                      {/* Section 2 Drafts Flow */}
                      <th className="p-3 text-right text-emerald-700 bg-amber-50/50">Drafts IN</th>
                      <th className="p-3 text-right text-amber-700 bg-amber-50/50">Drafts OUT</th>
                      <th className="p-3 text-right text-amber-900 bg-amber-100">Drafts Bal</th>
                      <th className="p-3 text-right text-purple-800 font-extrabold bg-purple-50 border-r border-purple-200">Final Balance</th>

                      {/* Section 3 Counts */}
                      <th className="p-3 text-center text-gray-500">Draft</th>
                      <th className="p-3 text-center text-amber-600">Submitted</th>
                      <th className="p-3 text-center text-emerald-600">Approved</th>
                      <th className="p-3 text-center text-rose-600">Rejected</th>
                      <th className="p-3 text-center text-purple-600 border-r border-gray-200">Paid</th>
                      
                      {/* Section 3 Amounts */}
                      <th className="p-3 text-right text-gray-500">Draft Amt</th>
                      <th className="p-3 text-right text-amber-600">Submitted Amt</th>
                      <th className="p-3 text-right text-emerald-700">Approved Amt</th>
                      <th className="p-3 text-right text-rose-700">Rejected Amt</th>
                      <th className="p-3 text-right text-purple-700">Paid Amt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {consoRows.map((row, idx) => (
                      <tr
                        key={row.employee_id}
                        onClick={() => handleOpenIncomeReceiptsDrilldown(row.employee_id, row.full_name)}
                        title={`Click to view cash receipts for ${row.full_name}`}
                        className="hover:bg-blue-50/50 cursor-pointer transition-colors whitespace-nowrap"
                      >
                        <td className="p-3 text-gray-400">{idx + 1}</td>
                        <td className="p-3">
                          <div className="font-bold text-blue-700 flex items-center gap-1.5">
                            {row.full_name}
                            <ExternalLink className="w-3 h-3 opacity-40" />
                          </div>
                          <div className="text-[11px] text-gray-400">{row.emp_code}</div>
                        </td>
                        <td className="p-3 border-r border-gray-200">
                          <div className="text-gray-800 font-medium">{row.department || "—"}</div>
                          <div className="text-[11px] text-gray-400">{row.role || "—"}</div>
                        </td>

                        {/* Section 1 Inflow */}
                        <td className="p-3 text-right font-medium text-cyan-700">{fmt(row.income_entries ?? row.cash_received)}</td>
                        <td className="p-3 text-right font-medium text-blue-700">{fmt(row.bank_alloc_in ?? row.fund_allocated)}</td>
                        <td className="p-3 text-right font-bold text-emerald-700 bg-emerald-50/50 border-r border-emerald-200">{fmt(row.total_in ?? row.cash_received)}</td>

                        {/* Section 1 Outflow */}
                        <td className="p-3 text-right font-medium text-rose-600">{fmt(row.ledger_exp ?? row.fund_used)}</td>
                        <td className="p-3 text-right font-medium text-orange-600">{fmt(row.ext_exp || 0)}</td>
                        <td className="p-3 text-right font-bold text-rose-800 bg-rose-50/50 border-r border-rose-200">{fmt(row.total_out ?? row.fund_used)}</td>

                        {/* Section 1 Net Balance */}
                        <td className={`p-3 text-right font-bold bg-blue-50/50 border-r border-blue-200 ${(row.net_balance ?? row.fund_balance) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                          {fmt(row.net_balance ?? row.fund_balance)}
                        </td>

                        {/* Section 2 Drafts Flow */}
                        <td className="p-3 text-right font-medium text-emerald-700 bg-amber-50/30">{fmt(row.draft_in || 0)}</td>
                        <td className="p-3 text-right font-medium text-amber-700 bg-amber-50/30">{fmt(row.draft_out ?? row.draft_amount)}</td>
                        <td className="p-3 text-right font-bold text-amber-900 bg-amber-100/60">{fmt(row.draft_balance ?? -(row.draft_amount || 0))}</td>
                        <td className={`p-3 text-right font-extrabold bg-purple-50/60 border-r border-purple-200 ${(row.final_balance ?? 0) >= 0 ? "text-emerald-700" : "text-purple-800"}`}>
                          {fmt(row.final_balance ?? ((row.net_balance ?? row.fund_balance) - (row.draft_amount || 0)))}
                        </td>

                        {/* Section 3 Counts */}
                        <td className="p-3 text-center">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-100 text-gray-700">
                            {row.draft_count}
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                            {row.submitted_count}
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            {row.approved_count}
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">
                            {row.rejected_count}
                          </span>
                        </td>
                        <td className="p-3 text-center border-r border-gray-200">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800">
                            {row.paid_count}
                          </span>
                        </td>

                        {/* Section 3 Amounts */}
                        <td className="p-3 text-right text-gray-500">{fmt(row.draft_amount)}</td>
                        <td className="p-3 text-right text-amber-700">{fmt(row.submitted_amount)}</td>
                        <td className="p-3 text-right font-semibold text-emerald-700">{fmt(row.approved_amount)}</td>
                        <td className="p-3 text-right font-semibold text-rose-600">{fmt(row.rejected_amount)}</td>
                        <td className="p-3 text-right font-semibold text-purple-700">{fmt(row.paid_amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-blue-50/80 border-t-2 border-blue-200 font-bold whitespace-nowrap">
                    <tr>
                      <td className="p-3" colSpan={3}>
                        TOTAL ({consoRows.length} Employees)
                      </td>
                      <td className="p-3 text-right text-cyan-800">{fmt(consolidatedTotals.cash_received)}</td>
                      <td className="p-3 text-right text-blue-800">{fmt(consolidatedTotals.fund_allocated)}</td>
                      <td className="p-3 text-right text-emerald-800 bg-emerald-100/50 border-r border-emerald-200">{fmt(consolidatedTotals.total_in)}</td>
                      <td className="p-3 text-right text-rose-800">{fmt(consolidatedTotals.fund_used)}</td>
                      <td className="p-3 text-right text-orange-800">₹0.00</td>
                      <td className="p-3 text-right text-rose-900 bg-rose-100/50 border-r border-rose-200">{fmt(consolidatedTotals.total_out)}</td>
                      <td className="p-3 text-right text-blue-900 bg-blue-100/50 border-r border-blue-200">{fmt(consolidatedTotals.net_balance)}</td>
                      <td className="p-3 text-right text-emerald-800 bg-amber-50/50">{fmt(consolidatedTotals.draft_in)}</td>
                      <td className="p-3 text-right text-amber-800 bg-amber-50/50">{fmt(consolidatedTotals.draft_out)}</td>
                      <td className="p-3 text-right text-amber-950 bg-amber-100">{fmt(consolidatedTotals.draft_balance)}</td>
                      <td className="p-3 text-right text-purple-900 bg-purple-100 border-r border-purple-200">{fmt(consolidatedTotals.final_balance)}</td>
                      <td className="p-3 text-center">{consolidatedTotals.draft_count}</td>
                      <td className="p-3 text-center">{consolidatedTotals.submitted_count}</td>
                      <td className="p-3 text-center">{consolidatedTotals.approved_count}</td>
                      <td className="p-3 text-center">{consolidatedTotals.rejected_count}</td>
                      <td className="p-3 text-center border-r border-gray-200">{consolidatedTotals.paid_count}</td>
                      <td className="p-3 text-right text-gray-600">{fmt(consolidatedTotals.draft_amount)}</td>
                      <td className="p-3 text-right text-amber-800">{fmt(consolidatedTotals.submitted_amount)}</td>
                      <td className="p-3 text-right text-emerald-800">{fmt(consolidatedTotals.approved_amount)}</td>
                      <td className="p-3 text-right text-rose-800">{fmt(consolidatedTotals.rejected_amount)}</td>
                      <td className="p-3 text-right text-purple-800">{fmt(consolidatedTotals.paid_amount)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================================================
          SLIDE-OVER DRAWER: VIEW EXPENSE DETAILS (DC-EXP-VIEW-001)
      ========================================================================= */}
      {viewExpenseData && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col overflow-y-auto animate-in slide-in-from-right duration-300">
            {/* Drawer Header */}
            <div className="bg-gradient-to-r from-blue-900 to-indigo-800 p-5 flex items-center justify-between text-white sticky top-0 z-10 shadow-md">
              <div className="flex items-center gap-2.5">
                <Receipt className="w-5 h-5 text-blue-300" />
                <h3 className="font-bold text-base">Expense #{viewExpenseData.entry_number || viewExpenseData.id}</h3>
              </div>
              <button
                onClick={() => setViewExpenseData(null)}
                className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4 text-white" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="p-6 space-y-5 flex-1">
              {/* Status Badges */}
              <div className="flex items-center gap-2 flex-wrap">
                {renderStatusBadge(viewExpenseData.status, viewExpenseData.is_paid)}
                {viewExpenseData.tally_status && viewExpenseData.tally_status !== "NOT_SYNCED" && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                    TALLY: {viewExpenseData.tally_status.replace("_", " ")}
                  </span>
                )}
              </div>

              {/* Amount Hero Banner */}
              <div className="bg-gradient-to-br from-blue-700 to-indigo-800 rounded-2xl p-5 text-white shadow-sm flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase font-semibold tracking-wider text-blue-200 mb-1">Total Amount</div>
                  <div className="text-3xl font-extrabold">{fmt(viewExpenseData.amount)}</div>
                  {(Number(viewExpenseData.gst_amount || 0) > 0 || Number(viewExpenseData.tds_amount || 0) > 0) && (
                    <div className="text-[11px] text-blue-200 mt-2">
                      Net: {fmt(viewExpenseData.net_amount)} &nbsp;|&nbsp; GST: {fmt(viewExpenseData.gst_amount)} &nbsp;|&nbsp; TDS: {fmt(viewExpenseData.tds_amount)}
                    </div>
                  )}
                </div>
                <div className="text-right text-xs text-blue-100 space-y-1">
                  <div>{formatDate(viewExpenseData.expense_date)}</div>
                  <div className="font-semibold">{viewExpenseData.payment_mode || "—"}</div>
                </div>
              </div>

              {/* Core Details Card */}
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs space-y-2.5 divide-y divide-gray-200/60">
                <div className="flex justify-between items-center pt-1 first:pt-0">
                  <span className="font-semibold text-gray-500">Company</span>
                  <span className="font-medium text-gray-900">{viewExpenseData.company_name || viewExpenseData.company_id}</span>
                </div>
                <div className="flex justify-between items-center pt-2">
                  <span className="font-semibold text-gray-500">Category</span>
                  <span className="font-medium text-gray-900">{viewExpenseData.category_name || viewExpenseData.main_category_id}</span>
                </div>
                {viewExpenseData.sub_category_name && (
                  <div className="flex justify-between items-center pt-2">
                    <span className="font-semibold text-gray-500">Sub-Category</span>
                    <span className="font-medium text-gray-900">{viewExpenseData.sub_category_name}</span>
                  </div>
                )}
                <div className="flex justify-between items-center pt-2">
                  <span className="font-semibold text-gray-500">Ledger Category</span>
                  <span className="font-medium text-gray-900">
                    {viewExpenseData.bank_ledger_category === "CUSTOM"
                      ? viewExpenseData.custom_category_name || "CUSTOM"
                      : viewExpenseData.bank_ledger_category || "—"}
                  </span>
                </div>
                <div className="pt-2">
                  <span className="font-semibold text-gray-500 block mb-1">Description / Narration</span>
                  <span className="font-medium text-gray-900">{viewExpenseData.narration || viewExpenseData.description || "—"}</span>
                </div>
                <div className="flex justify-between items-center pt-2">
                  <span className="font-semibold text-gray-500">Payment Mode</span>
                  <span className="font-medium text-gray-900">{viewExpenseData.payment_mode || "—"}</span>
                </div>
                {viewExpenseData.bank_account_name && (
                  <div className="flex justify-between items-center pt-2">
                    <span className="font-semibold text-gray-500">Bank Account</span>
                    <span className="font-medium text-gray-900">{viewExpenseData.bank_account_name}</span>
                  </div>
                )}
              </div>

              {/* Vendor Details */}
              {(viewExpenseData.vendor_name || viewExpenseData.paid_to || viewExpenseData.bill_number) && (
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs space-y-2.5 divide-y divide-gray-200/60">
                  <div className="flex justify-between items-center pt-1 first:pt-0">
                    <span className="font-semibold text-gray-500">Paid To / Vendor</span>
                    <span className="font-medium text-gray-900">{viewExpenseData.vendor_name || viewExpenseData.paid_to || "—"}</span>
                  </div>
                  {viewExpenseData.bill_number && (
                    <div className="flex justify-between items-center pt-2">
                      <span className="font-semibold text-gray-500">Invoice / Bill #</span>
                      <span className="font-medium text-gray-900">{viewExpenseData.bill_number}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Uploaded Receipt Preview */}
              {viewExpenseData.bill_path && (
                <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
                  <span className="text-xs font-bold text-gray-700 uppercase flex items-center gap-1.5">
                    <FileCheck className="w-4 h-4 text-sky-600" />
                    Payment Receipt / Invoice
                  </span>
                  {viewExpenseData.bill_path.match(/\.(jpg|jpeg|png|webp|gif)$/i) ||
                  viewExpenseData.bill_path.startsWith("data:image/") ? (
                    <img
                      src={viewExpenseData.bill_path}
                      alt="Receipt"
                      className="max-h-56 rounded-lg border border-gray-200 object-contain cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => window.open(viewExpenseData.bill_path, "_blank")}
                    />
                  ) : (
                    <a
                      href={viewExpenseData.bill_path}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
                    >
                      <ExternalLink className="w-4 h-4" /> Open Attached Document
                    </a>
                  )}
                </div>
              )}

              {/* Workflow Metadata */}
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Created By:</span>
                  <span className="font-semibold text-gray-900">{viewExpenseData.created_by_name || "—"}</span>
                </div>
                {viewExpenseData.approved_by_name && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Approved By:</span>
                    <span className="font-semibold text-emerald-700">
                      {viewExpenseData.approved_by_name} ({formatDate(viewExpenseData.approved_at)})
                    </span>
                  </div>
                )}
                {viewExpenseData.payment_utr && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Payment UTR:</span>
                    <span className="font-mono font-semibold text-purple-700">{viewExpenseData.payment_utr}</span>
                  </div>
                )}
              </div>

              {/* Show In Ledger Toggle */}
              <div className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <label className="text-xs font-bold text-gray-800 flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={viewExpenseData.show_in_ledger || false}
                      onChange={() => handleToggleShowInLedger(viewExpenseData.id, !!viewExpenseData.show_in_ledger)}
                      className="w-4 h-4 text-blue-600 rounded-sm border-gray-300 focus:ring-blue-500"
                    />
                    Show in Ledger
                  </label>
                  <p className="text-[11px] text-gray-400 mt-0.5">Toggle visibility on the general ledger</p>
                </div>
              </div>

              {/* Quick Actions Footer inside drawer */}
              <div className="flex items-center gap-2 pt-2 flex-wrap">
                {viewExpenseData.status === "DRAFT" && (
                  <>
                    <button
                      onClick={() => {
                        handleOpenEdit(viewExpenseData);
                        setViewExpenseData(null);
                      }}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
                    >
                      <Edit className="w-3.5 h-3.5 inline mr-1" /> Edit
                    </button>
                    <button
                      onClick={() => {
                        handleSubmitExpense(viewExpenseData.id);
                      }}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded-lg shadow-xs transition-colors"
                    >
                      <Send className="w-3.5 h-3.5 inline mr-1" /> Submit
                    </button>
                  </>
                )}

                {viewExpenseData.status === "SUBMITTED" && hasAccountsAccess && (
                  <>
                    <button
                      onClick={() => {
                        handleOpenApprove(viewExpenseData);
                      }}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" /> Approve
                    </button>
                    <button
                      onClick={() => {
                        handleOpenReject(viewExpenseData);
                      }}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-xs transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5 inline mr-1" /> Reject
                    </button>
                  </>
                )}

                {!viewExpenseData.is_paid &&
                  ["DRAFT", "SUBMITTED", "APPROVED"].includes(viewExpenseData.status) &&
                  hasAccountsAccess && (
                    <button
                      onClick={() => {
                        handleOpenPay(viewExpenseData);
                      }}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-700 rounded-lg shadow-xs transition-colors"
                    >
                      <Banknote className="w-3.5 h-3.5 inline mr-1" /> Mark Paid
                    </button>
                  )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: CREATE NEW EXPENSE
      ========================================================================= */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-red-600 to-rose-700 px-6 py-4 flex items-center justify-between text-white">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5" />
                <h3 className="font-bold text-base">New Expense Entry</h3>
              </div>
              <button onClick={() => setCreateModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
              {/* On Behalf Of selector for privileged users */}
              {canCreateOnBehalf && (
                <div className="bg-indigo-50/70 border border-indigo-200 rounded-xl p-3.5 space-y-1.5">
                  <label className="block text-xs font-bold text-indigo-900">
                    <User className="w-3.5 h-3.5 inline mr-1 text-indigo-600" />
                    Expense For (Employee)
                  </label>
                  <select
                    value={formData.on_behalf_of_employee_id}
                    onChange={(e) => {
                      const empId = e.target.value;
                      setFormData((prev) => ({ ...prev, on_behalf_of_employee_id: empId }));
                      fetchFundAllocations(empId ? parseInt(empId) : user?.id);
                    }}
                    className="w-full px-3 py-2 text-sm border border-indigo-300 rounded-lg bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="">— Myself —</option>
                    {behalfEmployees.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.full_name || e.name} ({e.emp_code}) {e.department ? `· ${e.department}` : ""}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-indigo-600">
                    Leave as "— Myself —" to file this expense for your own fund account.
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Company *</label>
                  <select
                    value={formData.company_id}
                    onChange={(e) => {
                      setFormData((prev) => ({ ...prev, company_id: e.target.value }));
                      if (e.target.value) {
                        api
                          .get(`/staff/accounts/companies/${e.target.value}/bank-accounts`)
                          .then((r) => setFormBankAccounts(r.data.bank_accounts || []))
                          .catch(() => {});
                      }
                    }}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
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
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Expense Date *</label>
                  <input
                    type="date"
                    value={formData.expense_date}
                    onChange={(e) => setFormData((prev) => ({ ...prev, expense_date: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Category *</label>
                  <select
                    value={formData.main_category_id}
                    onChange={(e) => {
                      const catId = e.target.value;
                      setFormData((prev) => ({ ...prev, main_category_id: catId, sub_category_id: "" }));
                      const selected = categories.find((c) => c.id.toString() === catId);
                      setCreateSubCategories(selected?.sub_categories || []);
                    }}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                  >
                    <option value="">Select Category</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Sub-Category</label>
                  <select
                    value={formData.sub_category_id}
                    disabled={!createSubCategories.length}
                    onChange={(e) => setFormData((prev) => ({ ...prev, sub_category_id: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg disabled:bg-gray-100 focus:ring-2 focus:ring-red-500 focus:outline-none"
                  >
                    <option value="">Select Sub-Category</option>
                    {createSubCategories.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Amount (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="0.00"
                  value={formData.amount}
                  onChange={(e) => setFormData((prev) => ({ ...prev, amount: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none font-bold text-gray-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Description / Narration *</label>
                <textarea
                  rows={2}
                  placeholder="Enter detailed description of expense..."
                  value={formData.narration}
                  onChange={(e) => setFormData((prev) => ({ ...prev, narration: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                />
              </div>

              {/* Fund Allocation (Optional) */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Fund Allocation (Optional)</label>
                <select
                  value={formData.fund_allocation_id}
                  onChange={(e) => setFormData((prev) => ({ ...prev, fund_allocation_id: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                >
                  <option value="">None - Pay from Company Funds</option>
                  {fundAllocations.map((alloc) => {
                    const remaining = alloc.balance_remaining ?? alloc.amount - (alloc.balance_used || 0);
                    return (
                      <option key={alloc.id} value={alloc.id}>
                        #{alloc.id} - {alloc.company_name} (Balance: {fmt(remaining)})
                      </option>
                    );
                  })}
                </select>
              </div>

              {/* Paid To / Vendor */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Paid To / Vendor / Party (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Type payee name or search vendor..."
                  value={formData.vendor_search}
                  onChange={(e) => {
                    const val = e.target.value;
                    setFormData((prev) => ({ ...prev, vendor_search: val, vendor_name: val }));
                    const filtered = vendors.filter(
                      (v) =>
                        (v.vendor_name || v.name || "").toLowerCase().includes(val.toLowerCase()) ||
                        (v.vendor_code || "").toLowerCase().includes(val.toLowerCase())
                    );
                    setFilteredVendors(filtered);
                  }}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg mb-2 focus:ring-2 focus:ring-red-500 focus:outline-none"
                />
                <select
                  value={formData.vendor_id}
                  onChange={(e) => {
                    const vId = e.target.value;
                    const vObj = vendors.find((v) => v.id.toString() === vId);
                    setFormData((prev) => ({
                      ...prev,
                      vendor_id: vId,
                      vendor_name: vObj ? vObj.vendor_name || vObj.name || "" : prev.vendor_search
                    }));
                  }}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                >
                  <option value="">No Vendor (Direct Payee)</option>
                  {filteredVendors.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.vendor_name || v.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Bank Ledger Category */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Bank Ledger Category</label>
                  <select
                    value={formData.bank_ledger_category}
                    onChange={(e) => setFormData((prev) => ({ ...prev, bank_ledger_category: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                  >
                    <option value="">— None / General —</option>
                    <option value="PURCHASE">Purchase</option>
                    <option value="SALES">Sales</option>
                    <option value="SALARY">Salary</option>
                    <option value="EXPENSES">Expenses</option>
                    <option value="CUSTOM">Custom</option>
                  </select>
                </div>

                {formData.bank_ledger_category === "CUSTOM" && (
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Custom Category Name</label>
                    <input
                      type="text"
                      placeholder="Enter custom category"
                      value={formData.custom_category_name}
                      onChange={(e) => setFormData((prev) => ({ ...prev, custom_category_name: e.target.value }))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                    />
                  </div>
                )}
              </div>

              {/* Payment Mode & Bank Account */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Payment Mode *</label>
                  <select
                    value={formData.payment_mode}
                    onChange={(e) => setFormData((prev) => ({ ...prev, payment_mode: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                  >
                    <option value="CASH">Cash</option>
                    <option value="BANK">Bank Transfer</option>
                    <option value="UPI">UPI</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="NEFT">NEFT</option>
                    <option value="RTGS">RTGS</option>
                    <option value="DD">DD</option>
                    <option value="CARD">Card</option>
                  </select>
                </div>

                {["BANK", "NEFT", "RTGS", "CHEQUE", "DD", "UPI"].includes(formData.payment_mode) && (
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Bank Account</label>
                    <select
                      value={formData.bank_account_id}
                      onChange={(e) => setFormData((prev) => ({ ...prev, bank_account_id: e.target.value }))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                    >
                      <option value="">Select Bank Account</option>
                      {formBankAccounts.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.display_label || `${b.bank_name} — ••${(b.account_number || "").slice(-4)} (${b.account_type})`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Reference Number & Upload Receipt */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Reference / Invoice #</label>
                  <input
                    type="text"
                    placeholder="Optional reference"
                    value={formData.bill_number}
                    onChange={(e) => setFormData((prev) => ({ ...prev, bill_number: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Receipt / Invoice Upload</label>
                  <input
                    type="file"
                    accept="image/*,.pdf"
                    onChange={handleReceiptUpload}
                    className="w-full text-xs text-gray-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
                  />
                  {uploadingReceipt && (
                    <span className="text-[11px] text-blue-600 block mt-1 flex items-center gap-1">
                      <RefreshCw className="w-3 h-3 animate-spin" /> Uploading receipt...
                    </span>
                  )}
                  {receiptUploadSuccess && (
                    <span className="text-[11px] text-emerald-600 font-semibold block mt-1">
                      ✓ {receiptUploadSuccess}
                    </span>
                  )}
                </div>
              </div>

              {/* Show in Ledger Toggle */}
              <div className="pt-2">
                <label className="flex items-center gap-2 text-xs font-semibold text-gray-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.show_in_ledger}
                    onChange={(e) => setFormData((prev) => ({ ...prev, show_in_ledger: e.target.checked }))}
                    className="w-4 h-4 text-red-600 rounded-sm border-gray-300 focus:ring-red-500"
                  />
                  Show in Ledger (Record directly to general ledger)
                </label>
              </div>
            </div>

            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setCreateModalOpen(false)}
                className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleSaveExpenseForm("DRAFT")}
                className="px-4 py-2 text-sm font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors"
              >
                Save as Draft
              </button>
              <button
                type="button"
                onClick={() => handleSaveExpenseForm("SUBMITTED")}
                className="px-5 py-2 text-sm font-semibold text-white bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-700 hover:to-rose-800 rounded-lg shadow-md shadow-red-500/20 transition-all"
              >
                Submit for Approval
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: EDIT DRAFT EXPENSE
      ========================================================================= */}
      {editModalOpen && selectedExpense && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-bold text-base text-gray-900">Edit Expense #{selectedExpense.id}</h3>
              <button onClick={() => setEditModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Amount (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={editAmount}
                  onChange={(e) => setEditAmount(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg font-bold"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Notes / Reason for Edit</label>
                <textarea
                  rows={3}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setEditModalOpen(false)}
                className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: APPROVE EXPENSE
      ========================================================================= */}
      {approveModalOpen && selectedExpense && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-emerald-600 px-6 py-4 flex items-center justify-between text-white">
              <h3 className="font-bold text-base flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5" /> Approve Expense #{selectedExpense.id}
              </h3>
              <button onClick={() => setApproveModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-900 space-y-1">
                <div>Amount: <strong className="text-base text-emerald-700">{fmt(selectedExpense.amount)}</strong></div>
                <div>Payee: <strong>{selectedExpense.vendor_name || selectedExpense.paid_to || "—"}</strong></div>
                <div>Description: <span>{selectedExpense.narration || selectedExpense.description || "—"}</span></div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Approval Notes (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Add optional notes..."
                  value={approveNotes}
                  onChange={(e) => setApproveNotes(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setApproveModalOpen(false)}
                className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveExpense}
                className="px-5 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: REJECT EXPENSE
      ========================================================================= */}
      {rejectModalOpen && selectedExpense && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-rose-600 px-6 py-4 flex items-center justify-between text-white">
              <h3 className="font-bold text-base flex items-center gap-2">
                <XCircle className="w-5 h-5" /> Reject Expense #{selectedExpense.id}
              </h3>
              <button onClick={() => setRejectModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-900 space-y-1">
                <div>Amount: <strong className="text-base text-rose-700">{fmt(selectedExpense.amount)}</strong></div>
                <div>Description: <span>{selectedExpense.narration || selectedExpense.description || "—"}</span></div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Rejection Reason *</label>
                <textarea
                  rows={3}
                  placeholder="Please specify why this expense is rejected..."
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setRejectModalOpen(false)}
                className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleRejectExpense}
                className="px-5 py-2 text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-xs"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: MARK AS PAID
      ========================================================================= */}
      {payModalOpen && selectedExpense && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-purple-700 to-indigo-800 px-6 py-4 flex items-center justify-between text-white">
              <h3 className="font-bold text-base flex items-center gap-2">
                <Banknote className="w-5 h-5" /> Mark Expense as Paid
              </h3>
              <button onClick={() => setPayModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-gray-900 rounded-xl p-4 text-xs text-gray-300 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-gray-400">Expense ID:</span>
                  <span className="font-bold text-white">#{selectedExpense.entry_number || selectedExpense.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Amount:</span>
                  <span className="font-bold text-emerald-400 text-sm">{fmt(selectedExpense.amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Description:</span>
                  <span className="text-gray-300 truncate max-w-[200px]">{selectedExpense.narration || selectedExpense.description || "—"}</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Bank Account (Paid from) <span className="text-[10px] font-bold text-red-600">CR</span>
                </label>
                <select
                  value={payBankAccountId}
                  onChange={(e) => setPayBankAccountId(e.target.value ? Number(e.target.value) : "")}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                >
                  <option value="">— Select Bank Account —</option>
                  {companyBankAccounts.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.display_label || `${b.bank_name} ••${(b.account_number || "").slice(-4)} (${b.account_type})`}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">UTR / Transaction Reference</label>
                <input
                  type="text"
                  placeholder="e.g. UTR123456789, UPI ref..."
                  value={payUtr}
                  onChange={(e) => setPayUtr(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Notes (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Optional payment remarks..."
                  value={payNotes}
                  onChange={(e) => setPayNotes(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setPayModalOpen(false)}
                className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmPayment}
                className="px-5 py-2 text-sm font-semibold text-white bg-purple-600 hover:bg-purple-700 rounded-lg shadow-xs"
              >
                Confirm Payment
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: FUND TRANSFER
      ========================================================================= */}
      {transferModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-indigo-700 to-blue-800 px-6 py-4 flex items-center justify-between text-white">
              <h3 className="font-bold text-base flex items-center gap-2">
                <ArrowRightLeft className="w-5 h-5" /> Transfer Funds
              </h3>
              <button onClick={() => setTransferModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Company *</label>
                <select
                  value={transferCompany}
                  onChange={(e) => setTransferCompany(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
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
                <label className="block text-xs font-semibold text-gray-700 mb-1">From Employee *</label>
                <select
                  value={transferFrom}
                  onChange={(e) => {
                    setTransferFrom(e.target.value);
                    fetchTransferFromBalance(e.target.value);
                  }}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                >
                  <option value="">Select Employee</option>
                  {user?.id && <option value={user.id}>{user.full_name || "Me"} (Myself)</option>}
                  {behalfEmployees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.full_name || e.name} ({e.emp_code})
                    </option>
                  ))}
                </select>
              </div>

              {transferFromBalance !== null && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs text-emerald-900 flex items-center justify-between">
                  <span className="font-semibold">From Employee Available Balance:</span>
                  <span className="font-bold text-emerald-700 text-sm">{fmt(transferFromBalance)}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">To Employee *</label>
                <select
                  value={transferTo}
                  onChange={(e) => setTransferTo(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                >
                  <option value="">Select Employee</option>
                  {behalfEmployees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.full_name || e.name} ({e.emp_code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Amount (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="0.00"
                  value={transferAmount}
                  onChange={(e) => setTransferAmount(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg font-bold"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-gray-700">Category (Optional)</label>
                  <button
                    type="button"
                    onClick={() => setCatQuickAddModalOpen(true)}
                    className="text-[11px] font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" /> Add Category
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <select
                    value={transferMainCat}
                    onChange={(e) => {
                      setTransferMainCat(e.target.value);
                      const cat = categories.find((c) => c.id.toString() === e.target.value);
                      setTransferSubCats(cat?.sub_categories || []);
                    }}
                    className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg"
                  >
                    <option value="">— Main Category —</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <select
                    value={transferSubCat}
                    disabled={!transferSubCats.length}
                    onChange={(e) => setTransferSubCat(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg disabled:bg-gray-100"
                  >
                    <option value="">— Sub Category —</option>
                    {transferSubCats.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Notes / Purpose</label>
                <textarea
                  rows={2}
                  placeholder="Reason for transfer..."
                  value={transferNotes}
                  onChange={(e) => setTransferNotes(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setTransferModalOpen(false)}
                className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTransfer}
                className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs"
              >
                Transfer Funds
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: QUICK ADD CATEGORY
      ========================================================================= */}
      {catQuickAddModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-emerald-700 px-6 py-4 flex items-center justify-between text-white">
              <h3 className="font-bold text-base flex items-center gap-2">
                <Plus className="w-5 h-5" /> Add Category
              </h3>
              <button onClick={() => setCatQuickAddModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Category Type</label>
                <select
                  value={qaCatMode}
                  onChange={(e) => setQaCatMode(e.target.value as "sub" | "main")}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                >
                  <option value="sub">Sub-Category (under existing main)</option>
                  <option value="main">New Main Category</option>
                </select>
              </div>

              {qaCatMode === "main" ? (
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Main Category Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. Travel Expenses"
                    value={qaMainName}
                    onChange={(e) => setQaMainName(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                  />
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Under Main Category *</label>
                    <select
                      value={qaParentId}
                      onChange={(e) => setQaParentId(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    >
                      <option value="">Select Main Category</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Sub-Category Name *</label>
                    <input
                      type="text"
                      placeholder="e.g. Fuel / Petrol"
                      value={qaSubName}
                      onChange={(e) => setQaSubName(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    />
                  </div>
                </>
              )}
            </div>
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setCatQuickAddModalOpen(false)}
                className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveQuickAddCategory}
                disabled={qaSaving}
                className="px-5 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs"
              >
                {qaSaving ? "Saving..." : "Save Category"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: DRILLDOWN MODAL (DC_DRILLDOWN_001)
      ========================================================================= */}
      {drilldownModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-blue-900 to-indigo-800 px-6 py-4 flex items-center justify-between text-white">
              <h3 className="font-bold text-base flex items-center gap-2">
                <FileText className="w-5 h-5" /> {drilldownTitle}
              </h3>
              <button onClick={() => setDrilldownModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              {/* Drilldown Stats Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-gray-900">{drilldownEntries.length}</div>
                  <div className="text-[11px] font-semibold text-gray-500">Total Entries</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-emerald-600">
                    {fmt(drilldownEntries.reduce((s, e) => s + parseFloat((e.amount as any) || 0), 0))}
                  </div>
                  <div className="text-[11px] font-semibold text-gray-500">Total Amount</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-blue-600">
                    {fmt(
                      drilldownEntries
                        .filter((e) => e.status === "APPROVED")
                        .reduce((s, e) => s + parseFloat((e.amount as any) || 0), 0)
                    )}
                  </div>
                  <div className="text-[11px] font-semibold text-gray-500">Approved Amount</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-purple-600">
                    {fmt(
                      drilldownEntries.length
                        ? drilldownEntries.reduce((s, e) => s + parseFloat((e.amount as any) || 0), 0) /
                            drilldownEntries.length
                        : 0
                    )}
                  </div>
                  <div className="text-[11px] font-semibold text-gray-500">Avg per Entry</div>
                </div>
              </div>

              {drilldownLoading ? (
                <div className="p-12 text-center text-gray-400 space-y-2">
                  <RefreshCw className="w-7 h-7 animate-spin mx-auto text-indigo-600" />
                  <p className="text-xs">Loading filtered records...</p>
                </div>
              ) : drilldownEntries.length === 0 ? (
                <div className="p-12 text-center text-gray-400 text-xs">No records found for this filter.</div>
              ) : (
                <div className="border border-gray-200 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600 uppercase">
                        <th className="p-2.5">ID</th>
                        <th className="p-2.5">Date</th>
                        {drilldownEntries.some((e) => e.created_by_name || e.employee_name) && (
                          <th className="p-2.5">Employee</th>
                        )}
                        <th className="p-2.5">Company</th>
                        <th className="p-2.5">Category</th>
                        <th className="p-2.5 text-right">Amount</th>
                        <th className="p-2.5 text-center">Status</th>
                        <th className="p-2.5 text-center">Age</th>
                        <th className="p-2.5"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {drilldownEntries.map((e, idx) => {
                        const expDate = new Date(e.expense_date || e.created_at || Date.now());
                        const ageDays = Math.floor((Date.now() - expDate.getTime()) / 86400000);
                        const isExpanded = !!expandedDrilldownRows[idx];

                        return (
                          <React.Fragment key={e.id || idx}>
                            <tr className="hover:bg-gray-50">
                              <td className="p-2.5 font-mono font-bold text-indigo-600">#{e.entry_number || e.id}</td>
                              <td className="p-2.5 text-gray-600 whitespace-nowrap">{formatDate(e.expense_date)}</td>
                              {(e.created_by_name || e.employee_name) && (
                                <td className="p-2.5 font-bold text-gray-900">
                                  {e.created_by_name || e.employee_name}
                                </td>
                              )}
                              <td className="p-2.5 text-gray-700">{e.company_name || "—"}</td>
                              <td className="p-2.5 font-medium text-gray-900">
                                {e.category_name || e.main_category_name || "—"}
                              </td>
                              <td className="p-2.5 text-right font-bold text-gray-900">{fmt(e.amount)}</td>
                              <td className="p-2.5 text-center">{renderStatusBadge(e.status, e.is_paid)}</td>
                              <td className="p-2.5 text-center text-gray-400 whitespace-nowrap">
                                {ageDays === 0 ? "Today" : `${ageDays}d ago`}
                              </td>
                              <td className="p-2.5 text-center">
                                <button
                                  onClick={() =>
                                    setExpandedDrilldownRows((prev) => ({ ...prev, [idx]: !prev[idx] }))
                                  }
                                  className="w-6 h-6 rounded-md border border-gray-300 font-bold text-gray-600 hover:bg-gray-100 flex items-center justify-center"
                                >
                                  {isExpanded ? "−" : "+"}
                                </button>
                              </td>
                            </tr>
                            {isExpanded && (
                              <tr className="bg-gray-50/80">
                                <td colSpan={9} className="p-3 text-xs text-gray-700 border-l-4 border-indigo-500 space-y-1">
                                  <div><strong>Description:</strong> {e.narration || e.description || "—"}</div>
                                  {e.vendor_name && <div><strong>Vendor / Payee:</strong> {e.vendor_name}</div>}
                                  {e.payment_mode && <div><strong>Payment Mode:</strong> {e.payment_mode}</div>}
                                  {e.bank_ledger_category && <div><strong>Ledger Cat:</strong> {e.bank_ledger_category}</div>}
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: CASH RECEIPTS / INCOME DRILLDOWN
      ========================================================================= */}
      {incomeReceiptsModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full shadow-2xl border border-gray-200 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-sky-800 to-cyan-700 px-6 py-4 flex items-center justify-between text-white">
              <h3 className="font-bold text-base flex items-center gap-2">
                <HandCoins className="w-5 h-5 text-cyan-200" /> {incomeDrilldownTitle}
              </h3>
              <button onClick={() => setIncomeReceiptsModalOpen(false)} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-gray-900">{incomeDrilldownReceipts.length}</div>
                  <div className="text-[11px] font-semibold text-gray-500">Total Receipts</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-cyan-700">
                    {fmt(incomeDrilldownReceipts.reduce((s, e) => s + parseFloat((e.amount as any) || 0), 0))}
                  </div>
                  <div className="text-[11px] font-semibold text-gray-500">Total Cash Received</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center col-span-2 sm:col-span-1">
                  <div className="text-lg font-bold text-emerald-600">
                    {incomeDrilldownReceipts.filter((e) => e.status === "CONFIRMED").length}
                  </div>
                  <div className="text-[11px] font-semibold text-gray-500">Confirmed</div>
                </div>
              </div>

              {incomeDrilldownLoading ? (
                <div className="p-12 text-center text-gray-400 space-y-2">
                  <RefreshCw className="w-7 h-7 animate-spin mx-auto text-cyan-600" />
                  <p className="text-xs">Loading cash receipts...</p>
                </div>
              ) : incomeDrilldownReceipts.length === 0 ? (
                <div className="p-12 text-center text-gray-400 text-xs">No cash receipts found for this employee.</div>
              ) : (
                <div className="border border-gray-200 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-sky-50/70 border-b border-sky-100 text-sky-900 font-bold uppercase">
                        <th className="p-2.5">Entry #</th>
                        <th className="p-2.5">Date</th>
                        <th className="p-2.5">Payer</th>
                        <th className="p-2.5">Company</th>
                        <th className="p-2.5 text-right">Amount</th>
                        <th className="p-2.5 text-center">Mode</th>
                        <th className="p-2.5 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {incomeDrilldownReceipts.map((inc) => (
                        <tr key={inc.id} className="hover:bg-sky-50/30">
                          <td className="p-2.5 font-mono font-bold text-indigo-600">
                            {inc.entry_number || `#${inc.id}`}
                          </td>
                          <td className="p-2.5 text-gray-600 whitespace-nowrap">
                            {formatDate(inc.income_date || inc.created_at)}
                          </td>
                          <td className="p-2.5 font-medium text-gray-900">{inc.payer_name || "—"}</td>
                          <td className="p-2.5 text-gray-700">{inc.company_name || "—"}</td>
                          <td className="p-2.5 font-bold text-emerald-700 text-right">{fmt(inc.amount)}</td>
                          <td className="p-2.5 text-center font-medium text-gray-600">{inc.payment_mode || "—"}</td>
                          <td className="p-2.5 text-center">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              {inc.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
