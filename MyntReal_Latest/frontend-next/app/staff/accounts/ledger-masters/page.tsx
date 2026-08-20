"use client";

import React, { useState, useEffect, useMemo, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import api, { getApiUrl } from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  BookOpen,
  Building2,
  Landmark,
  Coins,
  CreditCard,
  Layers,
  Plus,
  Search,
  RefreshCw,
  Download,
  Edit,
  Trash2,
  Eye,
  ExternalLink,
  CheckCircle2,
  XCircle,
  AlertCircle,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Filter,
  Check,
  X,
  Smartphone,
  Package,
  Users,
  PieChart,
  ShieldAlert,
  SlidersHorizontal,
  Info,
  Calendar,
  Sparkles,
  ArrowRightLeft,
  ChevronRight,
  Receipt,
  FileSpreadsheet
} from "lucide-react";

// Types
export interface LedgerMaster {
  id: number;
  company_id: number;
  account_type: string;
  account_name: string;
  account_code?: string | null;
  description?: string | null;
  parent_group?: string | null;
  opening_balance: number;
  opening_balance_type: "DEBIT" | "CREDIT";
  opening_balance_date?: string | null;
  opening_balance_posted: boolean;
  is_active: boolean;
  account_number?: string | null;
  ifsc_code?: string | null;
  bank_name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Company {
  id: number;
  company_name?: string;
  name?: string;
  company_code?: string;
  code?: string;
  is_active?: boolean;
}

const ACCOUNT_TYPES = [
  { value: "CASH", label: "Cash in Hand", icon: Coins, color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { value: "BANK", label: "Bank Account", icon: Landmark, color: "bg-blue-50 text-blue-700 border-blue-200" },
  { value: "UPI", label: "UPI / Digital Wallet", icon: Smartphone, color: "bg-purple-50 text-purple-700 border-purple-200" },
  { value: "INCOME", label: "Income / Revenue", icon: TrendingUp, color: "bg-teal-50 text-teal-700 border-teal-200" },
  { value: "EXPENSE", label: "Expense Account", icon: TrendingDown, color: "bg-rose-50 text-rose-700 border-rose-200" },
  { value: "ASSET", label: "Fixed / Current Asset", icon: Layers, color: "bg-sky-50 text-sky-700 border-sky-200" },
  { value: "LIABILITY", label: "Current Liability", icon: ShieldAlert, color: "bg-amber-50 text-amber-700 border-amber-200" },
  { value: "LOAN", label: "Loan Account", icon: CreditCard, color: "bg-orange-50 text-orange-700 border-orange-200" },
  { value: "CAPITAL", label: "Capital / Equity", icon: PieChart, color: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  { value: "STOCK", label: "Stock / Inventory", icon: Package, color: "bg-amber-50 text-amber-700 border-amber-200" },
  { value: "PARTY", label: "Party / Customer / Vendor", icon: Users, color: "bg-cyan-50 text-cyan-700 border-cyan-200" },
];

const COMMON_PARENT_GROUPS: Record<string, string[]> = {
  ASSET: ["Fixed Assets", "Current Assets", "Deposits & Advances", "Investments", "Stock in Hand"],
  LIABILITY: ["Current Liabilities", "Sundry Creditors", "Duties & Taxes", "Provisions", "Outstanding Expenses"],
  CAPITAL: ["Capital Account", "Reserves & Surplus", "Retained Earnings", "Owner's Equity"],
  LOAN: ["Secured Loans", "Unsecured Loans", "Bank Overdraft", "Director Loans"],
  INCOME: ["Direct Income", "Sales Revenue", "Service Income", "Indirect Income", "Interest Received"],
  EXPENSE: ["Direct Expenses", "Administrative Expenses", "Operating Expenses", "Employee Benefits", "Marketing", "Financial Expenses"],
  BANK: ["Bank Accounts", "Current Accounts", "Savings Accounts"],
  CASH: ["Cash-in-Hand", "Petty Cash", "Field Cash Float"],
  UPI: ["UPI Accounts", "Digital Wallets", "Payment Gateways"],
  STOCK: ["Finished Goods", "Raw Materials", "Work-in-Progress", "Trading Stock"],
  PARTY: ["Sundry Debtors", "Sundry Creditors", "Trade Partners"]
};

// Helper Currency Formatter
const formatCurrency = (amount: number | string | null | undefined, includeDrCr = false, type = "DEBIT") => {
  const val = typeof amount === "string" ? parseFloat(amount) : amount;
  const num = isNaN(Number(val)) || val === null || val === undefined ? 0 : Number(val);
  const abs = Math.abs(num);
  const formatted = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(abs);

  if (includeDrCr && abs > 0) {
    return `${formatted} ${type === "DEBIT" ? "Dr" : "Cr"}`;
  }
  return formatted;
};

// Main Component Content
function LedgerMastersContent() {
  const { token, user } = useStaffAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL Context / Deep link filters
  const initialCompany = searchParams.get("company_id") || "ALL";
  const initialType = searchParams.get("account_type") || "ALL";
  const initialSearch = searchParams.get("search") || "";

  // Core Data States
  const [masters, setMasters] = useState<LedgerMaster[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Filters State
  const [selectedCompany, setSelectedCompany] = useState<string>(initialCompany);
  const [selectedType, setSelectedType] = useState<string>(initialType);
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>(initialSearch);
  const [activeTab, setActiveTab] = useState<string>("all");

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createForm, setCreateForm] = useState({
    company_id: "",
    account_type: "EXPENSE",
    account_name: "",
    account_code: "",
    parent_group: "",
    description: "",
    opening_balance: "",
    opening_balance_type: "DEBIT" as "DEBIT" | "CREDIT",
    opening_balance_date: new Date().toISOString().slice(0, 10),
    account_number: "",
    ifsc_code: "",
    bank_name: "",
  });

  // Edit Modal State
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editingMaster, setEditingMaster] = useState<LedgerMaster | null>(null);
  const [editForm, setEditForm] = useState({
    account_name: "",
    account_code: "",
    parent_group: "",
    description: "",
    opening_balance: "",
    opening_balance_type: "DEBIT" as "DEBIT" | "CREDIT",
    opening_balance_date: "",
    is_active: true,
    account_number: "",
    ifsc_code: "",
    bank_name: "",
  });

  // Delete Modal State
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [deletingMaster, setDeletingMaster] = useState<LedgerMaster | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // Helper to fetch companies
  const fetchCompanies = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      const list = res.data?.companies || [];
      setCompanies(list);
      if (list.length > 0 && selectedCompany === "ALL" && initialCompany !== "ALL") {
        setSelectedCompany(initialCompany);
      }
    } catch (err: any) {
      console.error("Failed to load companies:", err);
    }
  }, [initialCompany, selectedCompany]);

  // Main Masters Fetcher
  const fetchMasters = useCallback(async (isRefresh = false) => {
    if (!token) return;
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setErrorMsg("");

    try {
      let url = "/staff/accounts/ledger-masters?page_size=500";
      if (selectedCompany && selectedCompany !== "ALL" && selectedCompany !== "0") {
        url += `&company_id=${selectedCompany}`;
      }
      if (selectedType && selectedType !== "ALL") {
        url += `&account_type=${selectedType}`;
      }
      if (selectedStatus !== "ALL") {
        url += `&is_active=${selectedStatus === "ACTIVE"}`;
      }
      if (searchQuery.trim()) {
        url += `&search=${encodeURIComponent(searchQuery.trim())}`;
      }

      const res = await api.get(url);
      setMasters(res.data?.masters || []);
    } catch (err: any) {
      console.error("Failed to fetch ledger masters:", err);
      setErrorMsg(err.response?.data?.detail || err.message || "Failed to load ledger masters");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, selectedCompany, selectedType, selectedStatus, searchQuery]);

  // Initial Load
  useEffect(() => {
    if (token) {
      fetchCompanies();
    }
  }, [token, fetchCompanies]);

  useEffect(() => {
    if (token) {
      fetchMasters();
    }
  }, [token, fetchMasters]);

  // Auto-dismiss alert notifications after 6s
  useEffect(() => {
    if (successMsg) {
      const timer = setTimeout(() => setSuccessMsg(""), 6000);
      return () => clearTimeout(timer);
    }
  }, [successMsg]);

  // Company Name Resolver
  const getCompanyName = useCallback((coId: number | string) => {
    const numId = Number(coId);
    const co = companies.find((c) => c.id === numId);
    return co ? co.company_name || co.name || `Company #${numId}` : `Company #${numId}`;
  }, [companies]);

  // Account Type Metadata Resolver
  const getTypeMeta = (type: string) => {
    const found = ACCOUNT_TYPES.find((t) => t.value === (type || "").toUpperCase());
    return found || {
      value: type,
      label: type,
      icon: BookOpen,
      color: "bg-slate-50 text-slate-700 border-slate-200",
    };
  };

  // KPI Calculations
  const stats = useMemo(() => {
    const totalCount = masters.length;
    const activeCount = masters.filter((m) => m.is_active).length;
    const inactiveCount = totalCount - activeCount;

    let totalDr = 0;
    let totalCr = 0;
    let bankCashCount = 0;

    masters.forEach((m) => {
      const ob = Number(m.opening_balance || 0);
      if (ob > 0) {
        if (m.opening_balance_type === "DEBIT") totalDr += ob;
        else totalCr += ob;
      }
      if (["BANK", "CASH", "UPI"].includes(m.account_type)) {
        bankCashCount += 1;
      }
    });

    const netBal = totalDr - totalCr;

    return {
      totalCount,
      activeCount,
      inactiveCount,
      totalDr,
      totalCr,
      netBal,
      bankCashCount,
    };
  }, [masters]);

  // Filtered Masters by active Tab view
  const displayMasters = useMemo(() => {
    if (activeTab === "bank-cash") {
      return masters.filter((m) => ["BANK", "CASH", "UPI"].includes(m.account_type));
    }
    if (activeTab === "revenue-expense") {
      return masters.filter((m) => ["INCOME", "EXPENSE"].includes(m.account_type));
    }
    if (activeTab === "balance-sheet") {
      return masters.filter((m) => ["ASSET", "LIABILITY", "CAPITAL", "LOAN", "STOCK"].includes(m.account_type));
    }
    return masters;
  }, [masters, activeTab]);

  // Grouped by Account Type for Matrix View
  const groupedByType = useMemo(() => {
    const groups: Record<string, LedgerMaster[]> = {};
    ACCOUNT_TYPES.forEach((t) => {
      groups[t.value] = [];
    });
    masters.forEach((m) => {
      const t = m.account_type?.toUpperCase() || "OTHER";
      if (!groups[t]) groups[t] = [];
      groups[t].push(m);
    });
    return groups;
  }, [masters]);

  // Handlers for Create Master
  const handleOpenCreate = () => {
    setCreateForm({
      company_id: companies.length > 0 ? String(companies[0].id) : "",
      account_type: "EXPENSE",
      account_name: "",
      account_code: "",
      parent_group: "",
      description: "",
      opening_balance: "",
      opening_balance_type: "DEBIT",
      opening_balance_date: new Date().toISOString().slice(0, 10),
      account_number: "",
      ifsc_code: "",
      bank_name: "",
    });
    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.company_id) {
      alert("Please select a company.");
      return;
    }
    if (!createForm.account_name.trim()) {
      alert("Please enter account name.");
      return;
    }

    setCreateSubmitting(true);
    try {
      const ob = parseFloat(createForm.opening_balance) || 0;
      const payload: any = {
        company_id: parseInt(createForm.company_id),
        account_type: createForm.account_type,
        account_name: createForm.account_name.trim(),
        account_code: createForm.account_code.trim() || null,
        parent_group: createForm.parent_group.trim() || null,
        description: createForm.description.trim() || null,
        opening_balance: ob > 0 ? ob : 0,
        opening_balance_type: createForm.opening_balance_type,
        opening_balance_date: createForm.opening_balance_date || null,
      };

      if (["BANK", "UPI"].includes(createForm.account_type)) {
        payload.bank_name = createForm.bank_name.trim() || null;
        payload.account_number = createForm.account_number.trim() || null;
        payload.ifsc_code = createForm.ifsc_code.trim().toUpperCase() || null;
      }

      const res = await api.post("/staff/accounts/ledger-masters", payload);
      if (res.data?.success) {
        setSuccessMsg(
          `Ledger Master "${createForm.account_name}" created successfully!` +
            (ob > 0 ? ` Opening balance of ${formatCurrency(ob)} (${createForm.opening_balance_type}) posted to General Ledger.` : "")
        );
        setIsCreateOpen(false);
        fetchMasters(true);
      }
    } catch (err: any) {
      console.error("Create failed:", err);
      alert(err.response?.data?.detail || err.message || "Failed to create ledger master");
    } finally {
      setCreateSubmitting(false);
    }
  };

  // Handlers for Edit Master
  const handleOpenEdit = (master: LedgerMaster) => {
    setEditingMaster(master);
    setEditForm({
      account_name: master.account_name || "",
      account_code: master.account_code || "",
      parent_group: master.parent_group || "",
      description: master.description || "",
      opening_balance: master.opening_balance > 0 ? String(master.opening_balance) : "",
      opening_balance_type: master.opening_balance_type || "DEBIT",
      opening_balance_date: master.opening_balance_date || new Date().toISOString().slice(0, 10),
      is_active: master.is_active,
      account_number: master.account_number || "",
      ifsc_code: master.ifsc_code || "",
      bank_name: master.bank_name || "",
    });
    setIsEditOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMaster) return;
    if (!editForm.account_name.trim()) {
      alert("Account name is required.");
      return;
    }

    setEditSubmitting(true);
    try {
      const ob = parseFloat(editForm.opening_balance);
      const payload: any = {
        account_name: editForm.account_name.trim(),
        account_code: editForm.account_code.trim() || null,
        parent_group: editForm.parent_group.trim() || null,
        description: editForm.description.trim() || null,
        opening_balance: !isNaN(ob) && ob >= 0 ? ob : 0,
        opening_balance_type: editForm.opening_balance_type,
        opening_balance_date: editForm.opening_balance_date || null,
        is_active: editForm.is_active,
      };

      if (["BANK", "UPI"].includes(editingMaster.account_type)) {
        payload.bank_name = editForm.bank_name.trim() || null;
        payload.account_number = editForm.account_number.trim() || null;
        payload.ifsc_code = editForm.ifsc_code.trim().toUpperCase() || null;
      }

      const res = await api.put(`/staff/accounts/ledger-masters/${editingMaster.id}`, payload);
      if (res.data?.success) {
        setSuccessMsg(`Ledger account "${editForm.account_name}" updated successfully.`);
        setIsEditOpen(false);
        setEditingMaster(null);
        fetchMasters(true);
      }
    } catch (err: any) {
      console.error("Update failed:", err);
      alert(err.response?.data?.detail || err.message || "Failed to update ledger master");
    } finally {
      setEditSubmitting(false);
    }
  };

  // Toggle Active Status
  const handleToggleActive = async (master: LedgerMaster) => {
    const newState = !master.is_active;
    try {
      const res = await api.put(`/staff/accounts/ledger-masters/${master.id}`, {
        is_active: newState,
      });
      if (res.data?.success) {
        setMasters((prev) =>
          prev.map((m) => (m.id === master.id ? { ...m, is_active: newState } : m))
        );
        setSuccessMsg(
          `Account "${master.account_name}" marked as ${newState ? "Active" : "Inactive"}.`
        );
      }
    } catch (err: any) {
      alert("Failed to update status: " + (err.response?.data?.detail || err.message));
    }
  };

  // Delete Handlers
  const handleOpenDelete = (master: LedgerMaster) => {
    setDeletingMaster(master);
    setIsDeleteOpen(true);
  };

  const handleDeleteSubmit = async () => {
    if (!deletingMaster) return;
    setDeleteSubmitting(true);
    try {
      const res = await api.delete(`/staff/accounts/ledger-masters/${deletingMaster.id}`);
      if (res.data?.success) {
        setSuccessMsg(`Ledger account "${deletingMaster.account_name}" deleted successfully.`);
        setIsDeleteOpen(false);
        setDeletingMaster(null);
        fetchMasters(true);
      }
    } catch (err: any) {
      console.error("Delete error:", err);
      alert(
        "Cannot delete ledger account:\n" +
          (err.response?.data?.detail || err.message || "Forbidden or transactions linked")
      );
    } finally {
      setDeleteSubmitting(false);
    }
  };

  // Export to CSV
  const handleExportCSV = () => {
    if (masters.length === 0) {
      alert("No data available to export.");
      return;
    }
    const headers = [
      "ID",
      "Company",
      "Account Type",
      "Account Name",
      "Account Code",
      "Parent Group",
      "Opening Balance",
      "Dr/Cr",
      "OB Date",
      "OB Posted",
      "Bank Name",
      "Account Number",
      "IFSC Code",
      "Status",
      "Description",
    ];

    const rows = masters.map((m) => [
      m.id,
      `"${getCompanyName(m.company_id).replace(/"/g, '""')}"`,
      m.account_type,
      `"${m.account_name.replace(/"/g, '""')}"`,
      m.account_code || "",
      `"${(m.parent_group || "").replace(/"/g, '""')}"`,
      m.opening_balance || 0,
      m.opening_balance_type || "DEBIT",
      m.opening_balance_date || "",
      m.opening_balance_posted ? "YES" : "NO",
      `"${(m.bank_name || "").replace(/"/g, '""')}"`,
      `"${(m.account_number || "").replace(/"/g, '""')}"`,
      m.ifsc_code || "",
      m.is_active ? "ACTIVE" : "INACTIVE",
      `"${(m.description || "").replace(/"/g, '""')}"`,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `Ledger_Masters_${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-slate-50/50 pb-16">
      {/* ── Enterprise Header ── */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 bg-gradient-to-tr from-indigo-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-md shadow-indigo-100 text-white">
                <BookOpen className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                    Chart of Accounts & Ledger Masters
                  </h1>
                  <Badge variant="outline" className="bg-indigo-50/80 text-indigo-700 border-indigo-200/60 font-semibold text-xs">
                    Double-Entry
                  </Badge>
                </div>
                <p className="text-sm text-slate-500 font-medium mt-0.5">
                  Manage master ledger accounts, opening balances, account hierarchies, and banking details
                </p>
              </div>
            </div>

            <div className="flex items-center flex-wrap gap-2.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchMasters(true)}
                disabled={loading || refreshing}
                className="bg-white border-slate-300 text-slate-700 hover:bg-slate-50 font-medium"
              >
                <RefreshCw className={`w-4 h-4 mr-2 text-slate-500 ${refreshing ? "animate-spin text-indigo-600" : ""}`} />
                {refreshing ? "Refreshing…" : "Refresh"}
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleExportCSV}
                className="bg-white border-slate-300 text-slate-700 hover:bg-slate-50 font-medium"
              >
                <FileSpreadsheet className="w-4 h-4 mr-2 text-emerald-600" />
                Export CSV
              </Button>

              <Link href="/staff/accounts/general-ledger">
                <Button variant="outline" size="sm" className="bg-white border-slate-300 text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 font-medium">
                  <ArrowRightLeft className="w-4 h-4 mr-2 text-indigo-600" />
                  General Ledger
                </Button>
              </Link>

              <Button
                onClick={handleOpenCreate}
                size="sm"
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium shadow-sm"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Add Ledger Account
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Success Alert */}
        {successMsg && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl flex items-start gap-3 shadow-xs animate-in fade-in slide-in-from-top-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 mt-0.5 shrink-0" />
            <div className="flex-1 text-sm font-medium">{successMsg}</div>
            <button onClick={() => setSuccessMsg("")} className="text-emerald-500 hover:text-emerald-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-xl flex items-start gap-3 shadow-xs">
            <AlertCircle className="w-5 h-5 text-rose-600 mt-0.5 shrink-0" />
            <div className="flex-1 text-sm font-medium">{errorMsg}</div>
            <button onClick={() => setErrorMsg("")} className="text-rose-500 hover:text-rose-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── KPI Summary Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-slate-200/80 shadow-xs hover:border-indigo-300 transition-colors">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Total Ledger Accounts
                  </p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{stats.totalCount}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
                  <BookOpen className="w-5 h-5" />
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100 text-xs font-medium text-slate-500">
                <span className="inline-flex items-center text-emerald-600 font-semibold">
                  <Check className="w-3.5 h-3.5 mr-1" /> {stats.activeCount} Active
                </span>
                <span>•</span>
                <span className="text-slate-400">{stats.inactiveCount} Inactive</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200/80 shadow-xs hover:border-rose-300 transition-colors">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Opening Balance (Debit / Dr)
                  </p>
                  <p className="text-2xl font-bold text-rose-600 mt-1">
                    {formatCurrency(stats.totalDr)}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center text-rose-600">
                  <TrendingUp className="w-5 h-5" />
                </div>
              </div>
              <div className="flex items-center gap-1 mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                <span>Assets, Expenses & Receivable Dr</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200/80 shadow-xs hover:border-emerald-300 transition-colors">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Opening Balance (Credit / Cr)
                  </p>
                  <p className="text-2xl font-bold text-emerald-600 mt-1">
                    {formatCurrency(stats.totalCr)}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
                  <TrendingDown className="w-5 h-5" />
                </div>
              </div>
              <div className="flex items-center gap-1 mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                <span>Capital, Liabilities & Payable Cr</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200/80 shadow-xs hover:border-blue-300 transition-colors">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Bank, Cash & UPI Ledgers
                  </p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{stats.bankCashCount}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
                  <Landmark className="w-5 h-5" />
                </div>
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                <span>Net OB: {formatCurrency(stats.netBal)}</span>
                <button
                  onClick={() => setActiveTab("bank-cash")}
                  className="text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center"
                >
                  View <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                </button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ── Search & Filter Controls ── */}
        <Card className="border-slate-200 shadow-xs">
          <CardContent className="p-4 sm:p-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
              {/* Company Selector */}
              <div>
                <Label className="text-xs font-semibold text-slate-600 mb-1.5 block">
                  Filter by Company
                </Label>
                <Select value={selectedCompany} onValueChange={(val) => setSelectedCompany(val)}>
                  <SelectTrigger className="w-full bg-white border-slate-200">
                    <SelectValue placeholder="All Companies" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Companies</SelectItem>
                    {companies.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.company_name || c.name || `Company #${c.id}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Account Type Filter */}
              <div>
                <Label className="text-xs font-semibold text-slate-600 mb-1.5 block">
                  Account Type
                </Label>
                <Select value={selectedType} onValueChange={(val) => setSelectedType(val)}>
                  <SelectTrigger className="w-full bg-white border-slate-200">
                    <SelectValue placeholder="All Account Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Account Types</SelectItem>
                    {ACCOUNT_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label} ({t.value})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Status Filter */}
              <div>
                <Label className="text-xs font-semibold text-slate-600 mb-1.5 block">
                  Active Status
                </Label>
                <Select value={selectedStatus} onValueChange={(val) => setSelectedStatus(val)}>
                  <SelectTrigger className="w-full bg-white border-slate-200">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Status</SelectItem>
                    <SelectItem value="ACTIVE">Active Only</SelectItem>
                    <SelectItem value="INACTIVE">Inactive Only</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Search Bar */}
              <div>
                <Label className="text-xs font-semibold text-slate-600 mb-1.5 block">
                  Search Ledgers
                </Label>
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <Input
                    placeholder="Search name, code, group, bank…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 bg-white border-slate-200"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Active Filters summary pills */}
            {(selectedCompany !== "ALL" || selectedType !== "ALL" || selectedStatus !== "ALL" || searchQuery) && (
              <div className="flex items-center flex-wrap gap-2 mt-3 pt-3 border-t border-slate-100 text-xs">
                <span className="text-slate-400 font-medium flex items-center">
                  <Filter className="w-3.5 h-3.5 mr-1" /> Active filters:
                </span>
                {selectedCompany !== "ALL" && (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-700 gap-1 font-normal">
                    Company: {getCompanyName(selectedCompany)}
                    <X className="w-3 h-3 cursor-pointer hover:text-rose-600" onClick={() => setSelectedCompany("ALL")} />
                  </Badge>
                )}
                {selectedType !== "ALL" && (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-700 gap-1 font-normal">
                    Type: {selectedType}
                    <X className="w-3 h-3 cursor-pointer hover:text-rose-600" onClick={() => setSelectedType("ALL")} />
                  </Badge>
                )}
                {selectedStatus !== "ALL" && (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-700 gap-1 font-normal">
                    Status: {selectedStatus}
                    <X className="w-3 h-3 cursor-pointer hover:text-rose-600" onClick={() => setSelectedStatus("ALL")} />
                  </Badge>
                )}
                {searchQuery && (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-700 gap-1 font-normal">
                    Search: &quot;{searchQuery}&quot;
                    <X className="w-3 h-3 cursor-pointer hover:text-rose-600" onClick={() => setSearchQuery("")} />
                  </Badge>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelectedCompany("ALL");
                    setSelectedType("ALL");
                    setSelectedStatus("ALL");
                    setSearchQuery("");
                  }}
                  className="h-6 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-2 ml-auto"
                >
                  Clear all filters
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Main Tabbed Content ── */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <TabsList className="bg-slate-100/90 p-1 border border-slate-200">
              <TabsTrigger value="all" className="data-[state=active]:bg-white data-[state=active]:shadow-xs font-medium text-xs sm:text-sm">
                All Ledgers ({masters.length})
              </TabsTrigger>
              <TabsTrigger value="bank-cash" className="data-[state=active]:bg-white data-[state=active]:shadow-xs font-medium text-xs sm:text-sm">
                Bank & Cash ({stats.bankCashCount})
              </TabsTrigger>
              <TabsTrigger value="revenue-expense" className="data-[state=active]:bg-white data-[state=active]:shadow-xs font-medium text-xs sm:text-sm">
                Revenue & Expenses
              </TabsTrigger>
              <TabsTrigger value="balance-sheet" className="data-[state=active]:bg-white data-[state=active]:shadow-xs font-medium text-xs sm:text-sm">
                Assets & Liabilities
              </TabsTrigger>
              <TabsTrigger value="matrix" className="data-[state=active]:bg-white data-[state=active]:shadow-xs font-medium text-xs sm:text-sm">
                Type Matrix
              </TabsTrigger>
            </TabsList>

            <span className="text-xs text-slate-500 font-medium">
              Showing <span className="text-slate-900 font-bold">{displayMasters.length}</span> of {masters.length} master accounts
            </span>
          </div>

          {/* ── Tab 1: All Ledgers Table ── */}
          <TabsContent value="all" className="m-0">
            <LedgerTable
              loading={loading}
              masters={displayMasters}
              getCompanyName={getCompanyName}
              getTypeMeta={getTypeMeta}
              onOpenEdit={handleOpenEdit}
              onToggleActive={handleToggleActive}
              onOpenDelete={handleOpenDelete}
              onOpenCreate={handleOpenCreate}
            />
          </TabsContent>

          {/* ── Tab 2: Bank & Cash Accounts ── */}
          <TabsContent value="bank-cash" className="m-0">
            <div className="space-y-4">
              <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-4 flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                <div className="text-xs sm:text-sm text-blue-900">
                  <p className="font-semibold">Bank Accounts, Cash-in-Hand & UPI Wallets</p>
                  <p className="text-blue-700/90 mt-0.5">
                    These accounts are linked for receipts, payments, bank reconciliations, contra transfers, and vendor/customer settlement.
                  </p>
                </div>
              </div>

              <LedgerTable
                loading={loading}
                masters={displayMasters}
                getCompanyName={getCompanyName}
                getTypeMeta={getTypeMeta}
                onOpenEdit={handleOpenEdit}
                onToggleActive={handleToggleActive}
                onOpenDelete={handleOpenDelete}
                onOpenCreate={handleOpenCreate}
                showBankDetails={true}
              />
            </div>
          </TabsContent>

          {/* ── Tab 3: Revenue & Expenses ── */}
          <TabsContent value="revenue-expense" className="m-0">
            <LedgerTable
              loading={loading}
              masters={displayMasters}
              getCompanyName={getCompanyName}
              getTypeMeta={getTypeMeta}
              onOpenEdit={handleOpenEdit}
              onToggleActive={handleToggleActive}
              onOpenDelete={handleOpenDelete}
              onOpenCreate={handleOpenCreate}
            />
          </TabsContent>

          {/* ── Tab 4: Assets & Liabilities ── */}
          <TabsContent value="balance-sheet" className="m-0">
            <LedgerTable
              loading={loading}
              masters={displayMasters}
              getCompanyName={getCompanyName}
              getTypeMeta={getTypeMeta}
              onOpenEdit={handleOpenEdit}
              onToggleActive={handleToggleActive}
              onOpenDelete={handleOpenDelete}
              onOpenCreate={handleOpenCreate}
            />
          </TabsContent>

          {/* ── Tab 5: Type Matrix / Breakdown View ── */}
          <TabsContent value="matrix" className="m-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {ACCOUNT_TYPES.map((typeMeta) => {
                const list = groupedByType[typeMeta.value] || [];
                const totalTypeDr = list.reduce(
                  (sum, m) => sum + (m.opening_balance_type === "DEBIT" ? Number(m.opening_balance || 0) : 0),
                  0
                );
                const totalTypeCr = list.reduce(
                  (sum, m) => sum + (m.opening_balance_type === "CREDIT" ? Number(m.opening_balance || 0) : 0),
                  0
                );
                const IconComponent = typeMeta.icon;

                return (
                  <Card key={typeMeta.value} className="border-slate-200 shadow-xs flex flex-col justify-between">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className={`p-2 rounded-lg border ${typeMeta.color}`}>
                            <IconComponent className="w-4 h-4" />
                          </div>
                          <div>
                            <CardTitle className="text-base font-bold text-slate-900">
                              {typeMeta.label}
                            </CardTitle>
                            <CardDescription className="text-xs">
                              Type Code: <span className="font-mono font-semibold">{typeMeta.value}</span>
                            </CardDescription>
                          </div>
                        </div>
                        <Badge variant="secondary" className="font-semibold text-xs bg-slate-100 text-slate-700">
                          {list.length} {list.length === 1 ? "ledger" : "ledgers"}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="pt-0 space-y-3">
                      <div className="bg-slate-50 rounded-lg p-3 text-xs space-y-1.5 border border-slate-100">
                        <div className="flex justify-between text-slate-600">
                          <span>Total Opening Dr:</span>
                          <span className="font-semibold text-rose-600">{formatCurrency(totalTypeDr)}</span>
                        </div>
                        <div className="flex justify-between text-slate-600">
                          <span>Total Opening Cr:</span>
                          <span className="font-semibold text-emerald-600">{formatCurrency(totalTypeCr)}</span>
                        </div>
                      </div>

                      {/* Top Accounts Preview */}
                      <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                        {list.length === 0 ? (
                          <p className="text-xs text-slate-400 italic py-2 text-center">No accounts created in this type</p>
                        ) : (
                          list.map((m) => (
                            <div
                              key={m.id}
                              className="flex items-center justify-between p-2 rounded-md hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-colors text-xs"
                            >
                              <div className="truncate mr-2">
                                <p className="font-semibold text-slate-800 truncate">{m.account_name}</p>
                                <p className="text-[10px] text-slate-400 truncate">{getCompanyName(m.company_id)}</p>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                {m.opening_balance > 0 ? (
                                  <span className={`font-mono font-semibold ${m.opening_balance_type === "DEBIT" ? "text-rose-600" : "text-emerald-600"}`}>
                                    {formatCurrency(m.opening_balance)} <span className="text-[10px]">{m.opening_balance_type === "DEBIT" ? "Dr" : "Cr"}</span>
                                  </span>
                                ) : (
                                  <span className="text-slate-300">—</span>
                                )}
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleOpenEdit(m)}
                                  className="h-6 w-6 p-0 text-slate-400 hover:text-indigo-600"
                                >
                                  <Edit className="w-3.5 h-3.5" />
                                </Button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedType(typeMeta.value);
                            setActiveTab("all");
                          }}
                          className="text-xs text-indigo-600 hover:text-indigo-800 p-0 h-auto font-medium"
                        >
                          View filtered table →
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setCreateForm((prev) => ({
                              ...prev,
                              account_type: typeMeta.value,
                              company_id: companies.length > 0 ? String(companies[0].id) : "",
                            }));
                            setIsCreateOpen(true);
                          }}
                          className="text-xs h-7 px-2 border-slate-200"
                        >
                          <Plus className="w-3 h-3 mr-1" /> Add
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ── CREATE LEDGER MASTER DIALOG ── */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleCreateSubmit}>
            <DialogHeader>
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <DialogTitle className="text-xl font-bold text-slate-900">
                    Create New Ledger Account
                  </DialogTitle>
                  <DialogDescription className="text-xs text-slate-500">
                    Add a master account to the Chart of Accounts with double-entry general ledger support.
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* Row 1: Company & Account Type */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                    Company <span className="text-rose-500">*</span>
                  </Label>
                  <Select
                    value={createForm.company_id}
                    onValueChange={(val) => setCreateForm((prev) => ({ ...prev, company_id: val }))}
                  >
                    <SelectTrigger className="bg-white">
                      <SelectValue placeholder="Select company" />
                    </SelectTrigger>
                    <SelectContent>
                      {companies.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.company_name || c.name || `Company #${c.id}`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                    Account Type <span className="text-rose-500">*</span>
                  </Label>
                  <Select
                    value={createForm.account_type}
                    onValueChange={(val) =>
                      setCreateForm((prev) => ({
                        ...prev,
                        account_type: val,
                        // Reset parent group suggestion if switching
                        parent_group: "",
                      }))
                    }
                  >
                    <SelectTrigger className="bg-white">
                      <SelectValue placeholder="Select account type" />
                    </SelectTrigger>
                    <SelectContent>
                      {ACCOUNT_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label} ({t.value})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 2: Account Name & Account Code */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-2">
                  <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                    Account Name <span className="text-rose-500">*</span>
                  </Label>
                  <Input
                    placeholder="e.g. HDFC Bank - Main Current A/c, Office Rent"
                    value={createForm.account_name}
                    onChange={(e) => setCreateForm((prev) => ({ ...prev, account_name: e.target.value }))}
                    className="bg-white"
                    required
                  />
                </div>

                <div>
                  <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                    Account Code (Optional)
                  </Label>
                  <Input
                    placeholder="e.g. GL-1001, EXP-01"
                    value={createForm.account_code}
                    onChange={(e) => setCreateForm((prev) => ({ ...prev, account_code: e.target.value }))}
                    className="bg-white font-mono uppercase text-xs"
                  />
                </div>
              </div>

              {/* Row 3: Parent Group & Suggestions */}
              <div>
                <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                  Parent Group / Category
                </Label>
                <Input
                  placeholder="e.g. Direct Expenses, Current Assets, Secured Loans"
                  value={createForm.parent_group}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, parent_group: e.target.value }))}
                  className="bg-white mb-1.5"
                />
                {/* Suggestions Chips */}
                {COMMON_PARENT_GROUPS[createForm.account_type] && (
                  <div className="flex items-center flex-wrap gap-1.5">
                    <span className="text-[10px] text-slate-400 font-medium">Quick suggestions:</span>
                    {COMMON_PARENT_GROUPS[createForm.account_type].map((grp) => (
                      <button
                        type="button"
                        key={grp}
                        onClick={() => setCreateForm((prev) => ({ ...prev, parent_group: grp }))}
                        className={`text-[10px] px-2 py-0.5 rounded-md border transition-colors ${
                          createForm.parent_group === grp
                            ? "bg-indigo-50 border-indigo-200 text-indigo-700 font-semibold"
                            : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                        }`}
                      >
                        {grp}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Row 4: Description */}
              <div>
                <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                  Description / Purpose (Optional)
                </Label>
                <Textarea
                  placeholder="Details or notes regarding this ledger account…"
                  value={createForm.description}
                  onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="bg-white text-xs h-16 resize-none"
                />
              </div>

              {/* Conditional Bank Details Section */}
              {["BANK", "UPI"].includes(createForm.account_type) && (
                <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Landmark className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                      Banking / UPI Details
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                        Bank Name
                      </Label>
                      <Input
                        placeholder="e.g. HDFC Bank, ICICI Bank"
                        value={createForm.bank_name}
                        onChange={(e) => setCreateForm((prev) => ({ ...prev, bank_name: e.target.value }))}
                        className="bg-white text-xs"
                      />
                    </div>
                    <div>
                      <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                        Account Number / UPI ID
                      </Label>
                      <Input
                        placeholder="e.g. 50200012345678"
                        value={createForm.account_number}
                        onChange={(e) => setCreateForm((prev) => ({ ...prev, account_number: e.target.value }))}
                        className="bg-white text-xs font-mono"
                      />
                    </div>
                    <div>
                      <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                        IFSC Code
                      </Label>
                      <Input
                        placeholder="e.g. HDFC0001234"
                        value={createForm.ifsc_code}
                        onChange={(e) => setCreateForm((prev) => ({ ...prev, ifsc_code: e.target.value.toUpperCase() }))}
                        className="bg-white text-xs font-mono uppercase"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Opening Balance Section */}
              <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Coins className="w-4 h-4 text-indigo-600" /> Opening Balance Setup
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-white font-normal text-slate-500">
                    Auto Double-Entry
                  </Badge>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                      Opening Balance (₹)
                    </Label>
                    <Input
                      type="number"
                      step="any"
                      min="0"
                      placeholder="0.00"
                      value={createForm.opening_balance}
                      onChange={(e) => setCreateForm((prev) => ({ ...prev, opening_balance: e.target.value }))}
                      className="bg-white font-mono font-semibold"
                    />
                  </div>

                  <div>
                    <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                      Balance Type
                    </Label>
                    <Select
                      value={createForm.opening_balance_type}
                      onValueChange={(val: "DEBIT" | "CREDIT") =>
                        setCreateForm((prev) => ({ ...prev, opening_balance_type: val }))
                      }
                    >
                      <SelectTrigger className="bg-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="DEBIT">Debit (Dr) — Assets / Expenses</SelectItem>
                        <SelectItem value="CREDIT">Credit (Cr) — Liabilities / Equity</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                      Opening Balance Date
                    </Label>
                    <Input
                      type="date"
                      value={createForm.opening_balance_date}
                      onChange={(e) => setCreateForm((prev) => ({ ...prev, opening_balance_date: e.target.value }))}
                      className="bg-white text-xs"
                    />
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 leading-relaxed bg-white/70 p-2.5 rounded-lg border border-slate-100">
                  <Info className="w-3.5 h-3.5 inline mr-1 text-indigo-500 -mt-0.5" />
                  When an opening balance &gt; 0 is specified, an Opening Balance entry is immediately posted to the general ledger with an offsetting double-entry contra posted to <strong>Opening Balance Equity (CAPITAL)</strong>.
                </p>
              </div>
            </div>

            <DialogFooter className="border-t border-slate-100 pt-3 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
                disabled={createSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createSubmitting}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
              >
                {createSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Creating…
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-1.5" />
                    Create Ledger Account
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ── EDIT LEDGER MASTER DIALOG ── */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleEditSubmit}>
            <DialogHeader>
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <Edit className="w-5 h-5" />
                </div>
                <div>
                  <DialogTitle className="text-xl font-bold text-slate-900">
                    Edit Ledger Account
                  </DialogTitle>
                  <DialogDescription className="text-xs text-slate-500">
                    {editingMaster && (
                      <>
                        Account ID: <span className="font-mono font-semibold">#{editingMaster.id}</span> · Company:{" "}
                        <span className="font-semibold">{getCompanyName(editingMaster.company_id)}</span> · Type:{" "}
                        <span className="font-semibold text-indigo-600">{editingMaster.account_type}</span>
                      </>
                    )}
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* Row 1: Name & Code */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-2">
                  <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                    Account Name <span className="text-rose-500">*</span>
                  </Label>
                  <Input
                    value={editForm.account_name}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, account_name: e.target.value }))}
                    className="bg-white"
                    required
                  />
                </div>

                <div>
                  <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                    Account Code
                  </Label>
                  <Input
                    value={editForm.account_code}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, account_code: e.target.value }))}
                    className="bg-white font-mono uppercase text-xs"
                  />
                </div>
              </div>

              {/* Row 2: Parent Group & Suggestions */}
              <div>
                <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                  Parent Group / Category
                </Label>
                <Input
                  value={editForm.parent_group}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, parent_group: e.target.value }))}
                  className="bg-white mb-1.5"
                />
                {editingMaster && COMMON_PARENT_GROUPS[editingMaster.account_type] && (
                  <div className="flex items-center flex-wrap gap-1.5">
                    <span className="text-[10px] text-slate-400 font-medium">Quick suggestions:</span>
                    {COMMON_PARENT_GROUPS[editingMaster.account_type].map((grp) => (
                      <button
                        type="button"
                        key={grp}
                        onClick={() => setEditForm((prev) => ({ ...prev, parent_group: grp }))}
                        className={`text-[10px] px-2 py-0.5 rounded-md border transition-colors ${
                          editForm.parent_group === grp
                            ? "bg-indigo-50 border-indigo-200 text-indigo-700 font-semibold"
                            : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                        }`}
                      >
                        {grp}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Row 3: Description */}
              <div>
                <Label className="text-xs font-semibold text-slate-700 mb-1.5 block">
                  Description / Remarks
                </Label>
                <Textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="bg-white text-xs h-16 resize-none"
                />
              </div>

              {/* Conditional Bank Details */}
              {editingMaster && ["BANK", "UPI"].includes(editingMaster.account_type) && (
                <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Landmark className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                      Bank / Digital Account Details
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                        Bank Name
                      </Label>
                      <Input
                        value={editForm.bank_name}
                        onChange={(e) => setEditForm((prev) => ({ ...prev, bank_name: e.target.value }))}
                        className="bg-white text-xs"
                      />
                    </div>
                    <div>
                      <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                        Account Number / UPI ID
                      </Label>
                      <Input
                        value={editForm.account_number}
                        onChange={(e) => setEditForm((prev) => ({ ...prev, account_number: e.target.value }))}
                        className="bg-white text-xs font-mono"
                      />
                    </div>
                    <div>
                      <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                        IFSC Code
                      </Label>
                      <Input
                        value={editForm.ifsc_code}
                        onChange={(e) => setEditForm((prev) => ({ ...prev, ifsc_code: e.target.value.toUpperCase() }))}
                        className="bg-white text-xs font-mono uppercase"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Opening Balance Edit */}
              <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Coins className="w-4 h-4 text-indigo-600" /> Opening Balance
                  </span>
                  {editingMaster?.opening_balance_posted && (
                    <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold">
                      ✓ Posted in Ledger
                    </Badge>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                      Opening Balance (₹)
                    </Label>
                    <Input
                      type="number"
                      step="any"
                      min="0"
                      value={editForm.opening_balance}
                      onChange={(e) => setEditForm((prev) => ({ ...prev, opening_balance: e.target.value }))}
                      className="bg-white font-mono font-semibold"
                    />
                  </div>

                  <div>
                    <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                      Balance Type
                    </Label>
                    <Select
                      value={editForm.opening_balance_type}
                      onValueChange={(val: "DEBIT" | "CREDIT") =>
                        setEditForm((prev) => ({ ...prev, opening_balance_type: val }))
                      }
                    >
                      <SelectTrigger className="bg-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="DEBIT">Debit (Dr)</SelectItem>
                        <SelectItem value="CREDIT">Credit (Cr)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-[11px] font-semibold text-slate-600 mb-1 block">
                      OB Date
                    </Label>
                    <Input
                      type="date"
                      value={editForm.opening_balance_date}
                      onChange={(e) => setEditForm((prev) => ({ ...prev, opening_balance_date: e.target.value }))}
                      className="bg-white text-xs"
                    />
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 leading-relaxed bg-white/70 p-2.5 rounded-lg border border-slate-100">
                  <Info className="w-3.5 h-3.5 inline mr-1 text-indigo-500 -mt-0.5" />
                  Modifying the opening balance automatically reverses previous opening entries and re-posts the new balance with matched equity contras.
                </p>
              </div>

              {/* Status toggle */}
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div>
                  <p className="text-xs font-semibold text-slate-900">Account Active Status</p>
                  <p className="text-[11px] text-slate-500">
                    Inactive accounts are hidden from transaction dropdowns
                  </p>
                </div>
                <Button
                  type="button"
                  variant={editForm.is_active ? "default" : "outline"}
                  size="sm"
                  onClick={() => setEditForm((prev) => ({ ...prev, is_active: !prev.is_active }))}
                  className={
                    editForm.is_active
                      ? "bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-8 px-3"
                      : "text-rose-600 border-rose-200 hover:bg-rose-50 text-xs h-8 px-3"
                  }
                >
                  {editForm.is_active ? "✓ Active" : "✕ Inactive"}
                </Button>
              </div>
            </div>

            <DialogFooter className="border-t border-slate-100 pt-3 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditOpen(false)}
                disabled={editSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={editSubmitting}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
              >
                {editSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Saving Changes…
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ── DELETE CONFIRMATION DIALOG ── */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-2.5 text-rose-600">
              <div className="p-2 bg-rose-50 rounded-lg">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <DialogTitle className="text-lg font-bold text-slate-900">
                Delete Ledger Account
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-slate-500 pt-1">
              Are you sure you want to permanently delete this ledger master account?
            </DialogDescription>
          </DialogHeader>

          {deletingMaster && (
            <div className="space-y-3 py-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                <p className="font-bold text-slate-900 text-sm">{deletingMaster.account_name}</p>
                <p className="text-slate-500">Type: <span className="font-semibold text-slate-700">{deletingMaster.account_type}</span></p>
                <p className="text-slate-500">Company: <span className="font-semibold text-slate-700">{getCompanyName(deletingMaster.company_id)}</span></p>
                {deletingMaster.opening_balance > 0 && (
                  <p className="text-slate-500">
                    Opening Balance:{" "}
                    <span className="font-mono font-semibold text-rose-600">
                      {formatCurrency(deletingMaster.opening_balance)} ({deletingMaster.opening_balance_type})
                    </span>
                  </p>
                )}
              </div>

              <div className="bg-amber-50 border border-amber-200 text-amber-900 p-3 rounded-lg text-xs space-y-1 leading-relaxed">
                <p className="font-semibold flex items-center gap-1 text-amber-950">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0" /> Authorization & Restriction Note:
                </p>
                <p>
                  • Restricted to administrators <strong>MR10001</strong> and <strong>MR10025</strong>.
                </p>
                <p>
                  • Deletion will fail if any journal entries or financial transactions are linked to this ledger.
                </p>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setIsDeleteOpen(false)}
              disabled={deleteSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteSubmit}
              disabled={deleteSubmitting}
              className="bg-rose-600 hover:bg-rose-700"
            >
              {deleteSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Deleting…
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-1.5" />
                  Confirm Delete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// ── SUB-COMPONENT: LEDGER TABLE ──
// ══════════════════════════════════════════════════════════════════════════════
interface LedgerTableProps {
  loading: boolean;
  masters: LedgerMaster[];
  getCompanyName: (id: number | string) => string;
  getTypeMeta: (type: string) => { value: string; label: string; icon: any; color: string };
  onOpenEdit: (master: LedgerMaster) => void;
  onToggleActive: (master: LedgerMaster) => void;
  onOpenDelete: (master: LedgerMaster) => void;
  onOpenCreate: () => void;
  showBankDetails?: boolean;
}

function LedgerTable({
  loading,
  masters,
  getCompanyName,
  getTypeMeta,
  onOpenEdit,
  onToggleActive,
  onOpenDelete,
  onOpenCreate,
  showBankDetails = false,
}: LedgerTableProps) {
  if (loading) {
    return (
      <Card className="border-slate-200 shadow-xs">
        <CardContent className="p-12 text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-700">Loading ledger master accounts…</p>
          <p className="text-xs text-slate-400">Fetching chart of accounts with balances from accounting books</p>
        </CardContent>
      </Card>
    );
  }

  if (masters.length === 0) {
    return (
      <Card className="border-slate-200 shadow-xs">
        <CardContent className="p-12 text-center space-y-4">
          <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto shadow-xs">
            <BookOpen className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">No Ledger Accounts Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              No ledger accounts match the active filter criteria. You can create a new ledger account or reset your filters.
            </p>
          </div>
          <Button
            onClick={onOpenCreate}
            size="sm"
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Add First Ledger Account
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-slate-200 shadow-xs overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="bg-slate-50/80 border-b border-slate-200">
            <TableRow>
              <TableHead className="w-12 text-center text-xs font-bold text-slate-600">#</TableHead>
              <TableHead className="text-xs font-bold text-slate-600 min-w-[130px]">Type</TableHead>
              <TableHead className="text-xs font-bold text-slate-600 min-w-[200px]">Account Name & Code</TableHead>
              <TableHead className="text-xs font-bold text-slate-600 min-w-[150px]">Parent Group</TableHead>
              {showBankDetails && (
                <>
                  <TableHead className="text-xs font-bold text-slate-600 min-w-[140px]">Bank Name</TableHead>
                  <TableHead className="text-xs font-bold text-slate-600 min-w-[160px]">Account / IFSC</TableHead>
                </>
              )}
              <TableHead className="text-xs font-bold text-slate-600 min-w-[160px]">Company</TableHead>
              <TableHead className="text-xs font-bold text-slate-600 text-right min-w-[150px]">Opening Bal</TableHead>
              <TableHead className="text-xs font-bold text-slate-600 text-center min-w-[100px]">OB Date</TableHead>
              <TableHead className="text-xs font-bold text-slate-600 text-center min-w-[90px]">Status</TableHead>
              <TableHead className="text-xs font-bold text-slate-600 text-right min-w-[170px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-100">
            {masters.map((master, idx) => {
              const meta = getTypeMeta(master.account_type);
              const ob = Number(master.opening_balance || 0);
              const isDr = master.opening_balance_type === "DEBIT";

              return (
                <TableRow
                  key={master.id}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    !master.is_active ? "bg-slate-50/40 opacity-70" : ""
                  }`}
                >
                  {/* # Index */}
                  <TableCell className="text-center font-mono text-xs text-slate-400">
                    {idx + 1}
                  </TableCell>

                  {/* Account Type Badge */}
                  <TableCell>
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${meta.color}`}
                    >
                      <meta.icon className="w-3.5 h-3.5" />
                      {master.account_type}
                    </span>
                  </TableCell>

                  {/* Account Name & Code */}
                  <TableCell>
                    <div className="space-y-0.5">
                      <div className="font-semibold text-slate-900 text-sm flex items-center gap-1.5">
                        {master.account_name}
                      </div>
                      {master.account_code && (
                        <span className="inline-block font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded font-medium">
                          {master.account_code}
                        </span>
                      )}
                      {master.description && (
                        <p className="text-[11px] text-slate-400 line-clamp-1 max-w-xs">
                          {master.description}
                        </p>
                      )}
                    </div>
                  </TableCell>

                  {/* Parent Group */}
                  <TableCell>
                    <span className="text-xs text-slate-600 font-medium">
                      {master.parent_group || <span className="text-slate-300 italic">—</span>}
                    </span>
                  </TableCell>

                  {/* Conditional Bank Details */}
                  {showBankDetails && (
                    <>
                      <TableCell className="text-xs text-slate-700 font-medium">
                        {master.bank_name || <span className="text-slate-300">—</span>}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-slate-600">
                        {master.account_number ? (
                          <div>
                            <div>{master.account_number}</div>
                            {master.ifsc_code && (
                              <div className="text-[10px] text-slate-400 font-semibold uppercase">
                                {master.ifsc_code}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </TableCell>
                    </>
                  )}

                  {/* Company */}
                  <TableCell>
                    <span className="text-xs font-medium text-slate-700 flex items-center gap-1">
                      <Building2 className="w-3 h-3 text-slate-400 shrink-0" />
                      {getCompanyName(master.company_id)}
                    </span>
                  </TableCell>

                  {/* Opening Balance */}
                  <TableCell className="text-right">
                    {ob > 0 ? (
                      <div className="space-y-0.5">
                        <span
                          className={`font-mono text-sm font-bold ${
                            isDr ? "text-rose-600" : "text-emerald-600"
                          }`}
                        >
                          {formatCurrency(ob)}
                        </span>
                        <div className="text-[10px] font-semibold text-slate-500">
                          {isDr ? (
                            <span className="text-rose-500">Debit (Dr)</span>
                          ) : (
                            <span className="text-emerald-500">Credit (Cr)</span>
                          )}
                          {master.opening_balance_posted && (
                            <span className="ml-1 text-emerald-600 font-bold" title="Posted to ledger">
                              ✓
                            </span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-300 font-mono">—</span>
                    )}
                  </TableCell>

                  {/* OB Date */}
                  <TableCell className="text-center text-xs text-slate-500 font-mono">
                    {master.opening_balance_date || <span className="text-slate-300">—</span>}
                  </TableCell>

                  {/* Status */}
                  <TableCell className="text-center">
                    <button
                      onClick={() => onToggleActive(master)}
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border transition-colors cursor-pointer ${
                        master.is_active
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                          : "bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100"
                      }`}
                      title={master.is_active ? "Click to deactivate" : "Click to activate"}
                    >
                      {master.is_active ? "Active" : "Inactive"}
                    </button>
                  </TableCell>

                  {/* Actions */}
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* View General Ledger */}
                      <Link
                        href={`/staff/accounts/general-ledger?account_name=${encodeURIComponent(
                          master.account_name
                        )}&company_id=${master.company_id}`}
                      >
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50"
                          title="View in General Ledger"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </Button>
                      </Link>

                      {/* Edit Master */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onOpenEdit(master)}
                        className="h-7 w-7 p-0 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50"
                        title="Edit Account Details"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </Button>

                      {/* Delete Master */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onOpenDelete(master)}
                        className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                        title="Delete Account (MR10001/MR10025 only)"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// ── EXPORT DEFAULT WRAPPER WITH SUSPENSE ──
// ══════════════════════════════════════════════════════════════════════════════
export default function LedgerMastersPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
          <div className="text-center space-y-3">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
            <p className="text-sm font-semibold text-slate-700">Loading Chart of Accounts…</p>
          </div>
        </div>
      }
    >
      <LedgerMastersContent />
    </Suspense>
  );
}
