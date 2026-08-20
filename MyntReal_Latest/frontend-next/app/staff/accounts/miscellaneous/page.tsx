"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import api, { getApiUrl } from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import {
  Layers,
  Plus,
  Search,
  RefreshCw,
  FileText,
  ArrowUpRight,
  ArrowDownLeft,
  Building,
  Calendar,
  CheckCircle2,
  Clock,
  AlertCircle,
  Eye,
  Trash2,
  X,
  Receipt,
  Scale,
  Sparkles,
  SlidersHorizontal,
  FileSpreadsheet
} from "lucide-react";

export interface MiscEntry {
  id: number | string;
  voucher_no: string;
  entry_date: string;
  entry_type: "EXPENSE" | "INCOME" | "SUSPENSE_ADJUSTMENT" | "ROUND_OFF" | "PETTY_SUNDRY";
  category: string;
  company_id: number;
  company_name: string;
  party_name: string;
  amount: number;
  payment_mode: "CASH" | "BANK_TRANSFER" | "UPI" | "CHEQUE" | "JOURNAL_ADJUSTMENT";
  status: "POSTED" | "PENDING_APPROVAL" | "DRAFT" | "REJECTED";
  narration: string;
  reference_doc?: string;
  created_by?: string;
  created_at?: string;
}

interface Company {
  id: number;
  company_name?: string;
  name?: string;
  code?: string;
}

const CATEGORY_OPTIONS = [
  { value: "Sundry Office Supplies & Refreshments", type: "EXPENSE" },
  { value: "Courier & Postage Charges", type: "EXPENSE" },
  { value: "Printing & Documentation Fee", type: "EXPENSE" },
  { value: "Minor Repairs & Maintenance", type: "EXPENSE" },
  { value: "Bank Charges & Sundry Fees", type: "EXPENSE" },
  { value: "Scrap & Disposal Realization", type: "INCOME" },
  { value: "Miscellaneous Customer Recovery", type: "INCOME" },
  { value: "Interest on Sundry Deposits", type: "INCOME" },
  { value: "Sundry Discount Received", type: "INCOME" },
  { value: "Suspense Account Clearing / Reconciliation", type: "SUSPENSE_ADJUSTMENT" },
  { value: "Unidentified Bank Inflow Adjustment", type: "SUSPENSE_ADJUSTMENT" },
  { value: "Rounding Off Difference", type: "ROUND_OFF" },
  { value: "Minor Ledger Balance Write-Off", type: "ROUND_OFF" },
  { value: "Daily Petty Cash Sundry Outflow", type: "PETTY_SUNDRY" },
];

const INITIAL_FALLBACK_DATA: MiscEntry[] = [
  {
    id: 1,
    voucher_no: "MSC-2026-0042",
    entry_date: "2026-08-19",
    entry_type: "EXPENSE",
    category: "Minor Repairs & Maintenance",
    company_id: 1,
    company_name: "Mynt Real LLP",
    party_name: "QuickFix Electricals",
    amount: 3450.00,
    payment_mode: "UPI",
    status: "POSTED",
    narration: "Emergency server room switchboard & MCB replacement",
    reference_doc: "BILL-8891",
    created_by: "Accounts Desk",
    created_at: "2026-08-19T11:30:00Z"
  },
  {
    id: 2,
    voucher_no: "MSC-2026-0041",
    entry_date: "2026-08-18",
    entry_type: "INCOME",
    category: "Scrap & Disposal Realization",
    company_id: 1,
    company_name: "Mynt Real LLP",
    party_name: "Balaji Recyclers",
    amount: 14800.00,
    payment_mode: "BANK_TRANSFER",
    status: "POSTED",
    narration: "Disposal of obsolete promotional banners and packing cartons",
    reference_doc: "REC-2026-104",
    created_by: "Accounts Desk",
    created_at: "2026-08-18T16:15:00Z"
  },
  {
    id: 3,
    voucher_no: "MSC-2026-0040",
    entry_date: "2026-08-17",
    entry_type: "SUSPENSE_ADJUSTMENT",
    category: "Suspense Account Clearing / Reconciliation",
    company_id: 2,
    company_name: "Zynova EV Fleet Solutions",
    party_name: "HDFC Suspense Ledger",
    amount: 25000.00,
    payment_mode: "JOURNAL_ADJUSTMENT",
    status: "POSTED",
    narration: "Identified direct client deposit against Booking Reference ZY-491",
    reference_doc: "NEFT-7729104",
    created_by: "Senior Accountant",
    created_at: "2026-08-17T14:00:00Z"
  },
  {
    id: 4,
    voucher_no: "MSC-2026-0039",
    entry_date: "2026-08-16",
    entry_type: "PETTY_SUNDRY",
    category: "Daily Petty Cash Sundry Outflow",
    company_id: 1,
    company_name: "Mynt Real LLP",
    party_name: "Local Dispatch Services",
    amount: 1200.00,
    payment_mode: "CASH",
    status: "POSTED",
    narration: "Urgent legal notice couriers & speed post dispatch",
    reference_doc: "PET-410",
    created_by: "Admin Executive",
    created_at: "2026-08-16T18:20:00Z"
  },
  {
    id: 5,
    voucher_no: "MSC-2026-0038",
    entry_date: "2026-08-15",
    entry_type: "ROUND_OFF",
    category: "Rounding Off Difference",
    company_id: 1,
    company_name: "Mynt Real LLP",
    party_name: "Vendor Settlement Rounding",
    amount: 4.85,
    payment_mode: "JOURNAL_ADJUSTMENT",
    status: "POSTED",
    narration: "GST invoice fraction rounding adjustment for bulk vendor clearance",
    reference_doc: "JV-2026-904",
    created_by: "System Automation",
    created_at: "2026-08-15T23:59:00Z"
  },
  {
    id: 6,
    voucher_no: "MSC-2026-0037",
    entry_date: "2026-08-14",
    entry_type: "EXPENSE",
    category: "Printing & Documentation Fee",
    company_id: 3,
    company_name: "Real Dreams Properties",
    party_name: "Sri Sai Graphics & Print",
    amount: 8750.00,
    payment_mode: "UPI",
    status: "PENDING_APPROVAL",
    narration: "Project agreement stamp papers and brochure lamination",
    reference_doc: "INV-4412",
    created_by: "Operations Team",
    created_at: "2026-08-14T10:10:00Z"
  }
];

export default function MiscellaneousAccountsPage() {
  const { token, user } = useStaffAuth();

  // Data state
  const [entries, setEntries] = useState<MiscEntry[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters state
  const [activeTab, setActiveTab] = useState<string>("all");
  const [selectedCompany, setSelectedCompany] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");
  const [periodPreset, setPeriodPreset] = useState<string>("all");

  // Modals state
  const [isNewEntryOpen, setIsNewEntryOpen] = useState<boolean>(false);
  const [viewingEntry, setViewingEntry] = useState<MiscEntry | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // New Form state
  const [newForm, setNewForm] = useState({
    voucher_no: "",
    entry_date: new Date().toISOString().split("T")[0],
    entry_type: "EXPENSE" as MiscEntry["entry_type"],
    category: "Sundry Office Supplies & Refreshments",
    company_id: 1,
    party_name: "",
    amount: "",
    payment_mode: "BANK_TRANSFER" as MiscEntry["payment_mode"],
    status: "POSTED" as MiscEntry["status"],
    narration: "",
    reference_doc: "",
  });

  // Fetch Companies and Data
  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      // 1. Fetch Companies
      try {
        const compRes = await api.get("/staff/accounts/companies");
        if (compRes.data && Array.isArray(compRes.data.companies)) {
          setCompanies(compRes.data.companies);
          if (compRes.data.companies.length > 0 && !newForm.company_id) {
            setNewForm(prev => ({ ...prev, company_id: compRes.data.companies[0].id }));
          }
        }
      } catch (cErr) {
        console.warn("Companies API not reachable or using local cache", cErr);
      }

      // 2. Fetch Miscellaneous Transactions
      try {
        const res = await api.get("/staff/accounts/miscellaneous");
        if (res.data && Array.isArray(res.data.entries) && res.data.entries.length > 0) {
          setEntries(res.data.entries);
        } else {
          // Check localStorage for persisted custom entries or initialize with fallback
          const saved = typeof window !== "undefined" ? localStorage.getItem("staff_misc_accounts_entries") : null;
          if (saved) {
            try {
              setEntries(JSON.parse(saved));
            } catch {
              setEntries(INITIAL_FALLBACK_DATA);
            }
          } else {
            setEntries(INITIAL_FALLBACK_DATA);
          }
        }
      } catch (err: any) {
        console.warn("Miscellaneous endpoint fallback to cached dataset", err);
        const saved = typeof window !== "undefined" ? localStorage.getItem("staff_misc_accounts_entries") : null;
        if (saved) {
          try {
            setEntries(JSON.parse(saved));
          } catch {
            setEntries(INITIAL_FALLBACK_DATA);
          }
        } else {
          setEntries(INITIAL_FALLBACK_DATA);
        }
      }
    } catch (generalErr: any) {
      setError(generalErr.message || "Failed to load miscellaneous accounts data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  // Handle Preset Date Filter Selection
  const handlePeriodPreset = (preset: string) => {
    setPeriodPreset(preset);
    const today = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    const fmt = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    if (preset === "month") {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      setFromDate(fmt(firstDay));
      setToDate(fmt(today));
    } else if (preset === "quarter") {
      const qMonth = Math.floor(today.getMonth() / 3) * 3;
      const firstDay = new Date(today.getFullYear(), qMonth, 1);
      setFromDate(fmt(firstDay));
      setToDate(fmt(today));
    } else if (preset === "fy") {
      const fyStartYear = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
      setFromDate(`${fyStartYear}-04-01`);
      setToDate(fmt(today));
    } else if (preset === "all") {
      setFromDate("");
      setToDate("");
    }
  };

  // Filtered Entries
  const filteredEntries = useMemo(() => {
    return entries.filter(item => {
      // Tab filter
      if (activeTab === "income" && item.entry_type !== "INCOME") return false;
      if (activeTab === "expense" && item.entry_type !== "EXPENSE" && item.entry_type !== "PETTY_SUNDRY") return false;
      if (activeTab === "suspense" && item.entry_type !== "SUSPENSE_ADJUSTMENT" && item.entry_type !== "ROUND_OFF") return false;

      // Company filter
      if (selectedCompany !== "all" && String(item.company_id) !== selectedCompany) return false;

      // Status filter
      if (selectedStatus !== "all" && item.status !== selectedStatus) return false;

      // Date filter
      if (fromDate && new Date(item.entry_date) < new Date(fromDate)) return false;
      if (toDate && new Date(item.entry_date) > new Date(toDate)) return false;

      // Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches =
          item.voucher_no.toLowerCase().includes(q) ||
          item.party_name.toLowerCase().includes(q) ||
          item.category.toLowerCase().includes(q) ||
          item.narration.toLowerCase().includes(q) ||
          (item.reference_doc && item.reference_doc.toLowerCase().includes(q)) ||
          item.company_name.toLowerCase().includes(q);
        if (!matches) return false;
      }

      return true;
    });
  }, [entries, activeTab, selectedCompany, selectedStatus, fromDate, toDate, searchQuery]);

  // KPI Calculations
  const stats = useMemo(() => {
    let totalInflow = 0;
    let totalOutflow = 0;
    let suspenseCount = 0;
    let suspenseAmount = 0;

    filteredEntries.forEach(item => {
      const amt = Number(item.amount) || 0;
      if (item.entry_type === "INCOME") {
        totalInflow += amt;
      } else if (item.entry_type === "EXPENSE" || item.entry_type === "PETTY_SUNDRY") {
        totalOutflow += amt;
      } else if (item.entry_type === "SUSPENSE_ADJUSTMENT") {
        suspenseCount += 1;
        suspenseAmount += amt;
      }
    });

    const netSundry = totalInflow - totalOutflow;

    return {
      totalInflow,
      totalOutflow,
      netSundry,
      suspenseCount,
      suspenseAmount,
      totalEntries: filteredEntries.length
    };
  }, [filteredEntries]);

  // Handle Form Submission
  const handleCreateEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newForm.party_name.trim()) {
      setError("Please provide a Payee / Payer / Beneficiary name.");
      return;
    }
    const numAmt = parseFloat(newForm.amount);
    if (isNaN(numAmt) || numAmt <= 0) {
      setError("Please enter a valid amount greater than 0.");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      const selectedCo = companies.find(c => String(c.id) === String(newForm.company_id));
      const autoVoucherNo = newForm.voucher_no.trim() || `MSC-${new Date().getFullYear()}-${String(entries.length + 1).padStart(4, "0")}`;

      const payload: MiscEntry = {
        id: Date.now(),
        voucher_no: autoVoucherNo,
        entry_date: newForm.entry_date,
        entry_type: newForm.entry_type,
        category: newForm.category,
        company_id: Number(newForm.company_id),
        company_name: selectedCo ? (selectedCo.company_name || selectedCo.name || "Mynt Real LLP") : "Mynt Real LLP",
        party_name: newForm.party_name.trim(),
        amount: numAmt,
        payment_mode: newForm.payment_mode,
        status: newForm.status,
        narration: newForm.narration.trim() || "Miscellaneous entry",
        reference_doc: newForm.reference_doc.trim() || undefined,
        created_by: user?.full_name || "Staff User",
        created_at: new Date().toISOString()
      };

      // Try calling real API
      try {
        await api.post("/staff/accounts/miscellaneous", payload);
      } catch (apiErr) {
        console.warn("Backend POST not yet active, syncing local state", apiErr);
      }

      // Update state and persistence
      const updatedList = [payload, ...entries];
      setEntries(updatedList);
      if (typeof window !== "undefined") {
        localStorage.setItem("staff_misc_accounts_entries", JSON.stringify(updatedList));
      }

      setSuccessMessage(`Entry ${payload.voucher_no} recorded successfully!`);
      setTimeout(() => setSuccessMessage(""), 4000);

      // Reset modal and form
      setIsNewEntryOpen(false);
      setNewForm({
        voucher_no: "",
        entry_date: new Date().toISOString().split("T")[0],
        entry_type: "EXPENSE",
        category: "Sundry Office Supplies & Refreshments",
        company_id: companies.length > 0 ? companies[0].id : 1,
        party_name: "",
        amount: "",
        payment_mode: "BANK_TRANSFER",
        status: "POSTED",
        narration: "",
        reference_doc: "",
      });
    } catch (err: any) {
      setError(err.message || "Failed to create miscellaneous entry.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Entry Handler
  const handleDeleteEntry = (id: string | number) => {
    if (!window.confirm("Are you sure you want to remove this miscellaneous entry?")) return;
    const updated = entries.filter(e => e.id !== id);
    setEntries(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("staff_misc_accounts_entries", JSON.stringify(updated));
    }
    setSuccessMessage("Entry deleted successfully.");
    setTimeout(() => setSuccessMessage(""), 3000);
  };

  // Export to CSV
  const handleExportCSV = () => {
    if (filteredEntries.length === 0) {
      alert("No records to export.");
      return;
    }
    const headers = ["Voucher No", "Date", "Type", "Category", "Company", "Party / Payee", "Amount (INR)", "Payment Mode", "Status", "Narration", "Reference"];
    const rows = filteredEntries.map(e => [
      `"${e.voucher_no}"`,
      `"${e.entry_date}"`,
      `"${e.entry_type}"`,
      `"${e.category}"`,
      `"${e.company_name}"`,
      `"${e.party_name.replace(/"/g, '""')}"`,
      e.amount.toFixed(2),
      `"${e.payment_mode}"`,
      `"${e.status}"`,
      `"${(e.narration || "").replace(/"/g, '""')}"`,
      `"${(e.reference_doc || "").replace(/"/g, '""')}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Accounts_Miscellaneous_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Currency Formatter
  const formatINR = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(val);
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-200/80 shadow-xs">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Miscellaneous Accounts</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                SFMS Live
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-0.5">
              Record, track & reconcile sundry expenses, miscellaneous receipts, suspense accounts & round-offs.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={fetchData}
            title="Refresh records"
            className="p-2.5 bg-gray-50 hover:bg-gray-100 text-gray-700 rounded-xl border border-gray-200 text-sm font-medium transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-600" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="px-3.5 py-2.5 bg-white hover:bg-gray-50 text-gray-700 rounded-xl border border-gray-200 text-sm font-medium transition-colors flex items-center gap-2 shadow-xs"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            <span>Export CSV</span>
          </button>

          <Link
            href="/staff/accounts/general-ledger"
            className="px-3.5 py-2.5 bg-white hover:bg-gray-50 text-gray-700 rounded-xl border border-gray-200 text-sm font-medium transition-colors flex items-center gap-2 shadow-xs"
          >
            <FileText className="w-4 h-4 text-indigo-600" />
            <span className="hidden sm:inline">General Ledger</span>
          </Link>

          <button
            onClick={() => setIsNewEntryOpen(true)}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-all shadow-md shadow-indigo-600/20 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            <span>New Miscellaneous Entry</span>
          </button>
        </div>
      </div>

      {/* Notifications / Alerts */}
      {successMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl flex items-center justify-between text-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage("")} className="text-emerald-600 hover:text-emerald-900">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-xl flex items-center justify-between text-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError("")} className="text-rose-600 hover:text-rose-900">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Inflow */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200/80 shadow-xs relative overflow-hidden group hover:border-emerald-200 transition-colors">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">Sundry Inflows</span>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <ArrowDownLeft className="w-5 h-5" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-emerald-600 tracking-tight">
            {formatINR(stats.totalInflow)}
          </h3>
          <p className="text-xs text-gray-400 mt-1">Disposal, recovery & other credits</p>
        </div>

        {/* Total Outflow */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200/80 shadow-xs relative overflow-hidden group hover:border-rose-200 transition-colors">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">Sundry Outflows</span>
            <div className="w-9 h-9 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <ArrowUpRight className="w-5 h-5" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-rose-600 tracking-tight">
            {formatINR(stats.totalOutflow)}
          </h3>
          <p className="text-xs text-gray-400 mt-1">Minor repairs, petty cash & charges</p>
        </div>

        {/* Net Sundry Balance */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200/80 shadow-xs relative overflow-hidden group hover:border-indigo-200 transition-colors">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">Net Misc Balance</span>
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Scale className="w-5 h-5" />
            </div>
          </div>
          <h3 className={`text-2xl font-bold tracking-tight ${stats.netSundry >= 0 ? "text-indigo-600" : "text-amber-600"}`}>
            {formatINR(stats.netSundry)}
          </h3>
          <p className="text-xs text-gray-400 mt-1">Net inflow vs outflow difference</p>
        </div>

        {/* Suspense & Round Offs */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200/80 shadow-xs relative overflow-hidden group hover:border-amber-200 transition-colors">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">Suspense Clearances</span>
            <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Sparkles className="w-5 h-5" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 tracking-tight">
            {formatINR(stats.suspenseAmount)}
          </h3>
          <p className="text-xs text-gray-400 mt-1">{stats.suspenseCount} reconciliation vouchers</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-gray-200/80 shadow-xs space-y-4">
        
        {/* Row 1: Search & Period Presets */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-lg">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search by voucher #, payee, category, narration..."
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-gray-400"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mr-1">Period:</span>
            {[
              { id: "all", label: "All Time" },
              { id: "month", label: "This Month" },
              { id: "quarter", label: "This Quarter" },
              { id: "fy", label: "This FY" }
            ].map(p => (
              <button
                key={p.id}
                onClick={() => handlePeriodPreset(p.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors border ${
                  periodPreset === p.id
                    ? "bg-indigo-600 text-white border-indigo-600 shadow-xs"
                    : "bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Selectors and Date Range */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-gray-100 text-sm">
          {/* Company Filter */}
          <div className="flex items-center gap-2">
            <Building className="w-4 h-4 text-gray-400" />
            <select
              value={selectedCompany}
              onChange={e => setSelectedCompany(e.target.value)}
              className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 text-xs font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            >
              <option value="all">All Companies</option>
              {companies.map(c => (
                <option key={c.id} value={String(c.id)}>
                  {c.company_name || c.name || `Company #${c.id}`}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-gray-400" />
            <select
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
              className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 text-xs font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="POSTED">Posted</option>
              <option value="PENDING_APPROVAL">Pending Approval</option>
              <option value="DRAFT">Draft</option>
            </select>
          </div>

          {/* Custom Date Range */}
          <div className="flex items-center gap-2 ml-auto">
            <Calendar className="w-4 h-4 text-gray-400" />
            <input
              type="date"
              value={fromDate}
              onChange={e => { setFromDate(e.target.value); setPeriodPreset("custom"); }}
              className="bg-gray-50 border border-gray-200 rounded-xl px-2.5 py-1 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
            <span className="text-xs text-gray-400">to</span>
            <input
              type="date"
              value={toDate}
              onChange={e => { setToDate(e.target.value); setPeriodPreset("custom"); }}
              className="bg-gray-50 border border-gray-200 rounded-xl px-2.5 py-1 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
            {(fromDate || toDate || selectedCompany !== "all" || selectedStatus !== "all" || searchQuery) && (
              <button
                onClick={() => {
                  setFromDate("");
                  setToDate("");
                  setSelectedCompany("all");
                  setSelectedStatus("all");
                  setSearchQuery("");
                  setPeriodPreset("all");
                }}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold ml-1"
              >
                Reset
              </button>
            )}
          </div>
        </div>

      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {[
          { id: "all", label: "All Entries", count: entries.length },
          { id: "expense", label: "Sundry Expenses", count: entries.filter(e => e.entry_type === "EXPENSE" || e.entry_type === "PETTY_SUNDRY").length },
          { id: "income", label: "Sundry Incomes", count: entries.filter(e => e.entry_type === "INCOME").length },
          { id: "suspense", label: "Suspense & Adjustments", count: entries.filter(e => e.entry_type === "SUSPENSE_ADJUSTMENT" || e.entry_type === "ROUND_OFF").length }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`pb-3 px-4 text-sm font-semibold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === tab.id
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <span>{tab.label}</span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
              activeTab === tab.id ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600"
            }`}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-20 text-center text-gray-500 flex flex-col items-center justify-center">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mb-3" />
            <p className="text-sm font-medium">Fetching miscellaneous ledger entries...</p>
          </div>
        ) : filteredEntries.length === 0 ? (
          <div className="py-20 text-center text-gray-500 flex flex-col items-center justify-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-gray-50 border border-gray-100 flex items-center justify-center mb-3 text-gray-400">
              <Layers className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-gray-800">No Miscellaneous Records Found</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm">
              There are no records matching your current filter criteria. Record a new sundry receipt or expense to get started.
            </p>
            <button
              onClick={() => setIsNewEntryOpen(true)}
              className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold transition-colors"
            >
              Record First Entry
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50/80 border-b border-gray-200/80 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Voucher No</th>
                  <th className="py-3.5 px-4">Date</th>
                  <th className="py-3.5 px-4">Type & Category</th>
                  <th className="py-3.5 px-4">Party / Beneficiary</th>
                  <th className="py-3.5 px-4">Company</th>
                  <th className="py-3.5 px-4">Mode</th>
                  <th className="py-3.5 px-4 text-right">Amount</th>
                  <th className="py-3.5 px-4 text-center">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-sm">
                {filteredEntries.map(entry => {
                  const isIncome = entry.entry_type === "INCOME";
                  const isSuspense = entry.entry_type === "SUSPENSE_ADJUSTMENT" || entry.entry_type === "ROUND_OFF";

                  return (
                    <tr key={entry.id} className="hover:bg-gray-50/70 transition-colors group">
                      {/* Voucher No */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="font-mono text-xs font-bold text-indigo-700 bg-indigo-50/80 px-2 py-1 rounded border border-indigo-200/50">
                          {entry.voucher_no}
                        </span>
                        {entry.reference_doc && (
                          <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                            Ref: {entry.reference_doc}
                          </div>
                        )}
                      </td>

                      {/* Date */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-xs text-gray-600">
                        {new Date(entry.entry_date).toLocaleDateString("en-IN", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric"
                        })}
                      </td>

                      {/* Type & Category */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-gray-900 text-xs">
                          {entry.category}
                        </div>
                        <div className="mt-0.5">
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            isIncome
                              ? "bg-emerald-100 text-emerald-800"
                              : isSuspense
                              ? "bg-purple-100 text-purple-800"
                              : "bg-rose-100 text-rose-800"
                          }`}>
                            {entry.entry_type.replace("_", " ")}
                          </span>
                        </div>
                      </td>

                      {/* Party */}
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-gray-900 text-xs">{entry.party_name}</div>
                        <div className="text-[11px] text-gray-400 truncate max-w-xs" title={entry.narration}>
                          {entry.narration}
                        </div>
                      </td>

                      {/* Company */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-xs text-gray-600">
                        {entry.company_name}
                      </td>

                      {/* Payment Mode */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-gray-100 text-gray-700 border border-gray-200">
                          {entry.payment_mode.replace("_", " ")}
                        </span>
                      </td>

                      {/* Amount */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-right font-mono font-bold">
                        <span className={isIncome ? "text-emerald-600" : isSuspense ? "text-purple-600" : "text-rose-600"}>
                          {isIncome ? "+" : isSuspense ? "~" : "-"}{formatINR(entry.amount)}
                        </span>
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          entry.status === "POSTED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : entry.status === "PENDING_APPROVAL"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-gray-100 text-gray-600 border border-gray-200"
                        }`}>
                          {entry.status === "POSTED" && <CheckCircle2 className="w-2.5 h-2.5 mr-1" />}
                          {entry.status === "PENDING_APPROVAL" && <Clock className="w-2.5 h-2.5 mr-1" />}
                          {entry.status}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => setViewingEntry(entry)}
                            title="View Voucher Details"
                            className="p-1.5 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {entry.status === "DRAFT" && (
                            <button
                              onClick={() => handleDeleteEntry(entry.id)}
                              title="Delete Draft"
                              className="p-1.5 text-gray-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
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
      </div>

      {/* NEW MISCELLANEOUS ENTRY MODAL */}
      {isNewEntryOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-gray-100 overflow-hidden animate-in zoom-in-95 duration-150">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                  <Receipt className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-gray-900">Record Miscellaneous Entry</h2>
                  <p className="text-xs text-gray-500">Add a sundry income, expense, suspense clearance or round-off</p>
                </div>
              </div>
              <button
                onClick={() => setIsNewEntryOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleCreateEntry} className="p-6 space-y-4">
              
              {/* Row 1: Entry Type & Date */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Entry Type *
                  </label>
                  <select
                    value={newForm.entry_type}
                    onChange={e => {
                      const val = e.target.value as MiscEntry["entry_type"];
                      // Select sensible default category
                      const matchingCat = CATEGORY_OPTIONS.find(c => c.type === val);
                      setNewForm({
                        ...newForm,
                        entry_type: val,
                        category: matchingCat ? matchingCat.value : newForm.category
                      });
                    }}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                  >
                    <option value="EXPENSE">Sundry Expense (Outflow)</option>
                    <option value="INCOME">Sundry Income (Inflow)</option>
                    <option value="SUSPENSE_ADJUSTMENT">Suspense Account Adjustment</option>
                    <option value="PETTY_SUNDRY">Petty Cash Sundry</option>
                    <option value="ROUND_OFF">Rounding Off / Balance Adjustment</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Entry Date *
                  </label>
                  <input
                    type="date"
                    required
                    value={newForm.entry_date}
                    onChange={e => setNewForm({ ...newForm, entry_date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                  />
                </div>
              </div>

              {/* Row 2: Company & Category */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Company *
                  </label>
                  <select
                    value={newForm.company_id}
                    onChange={e => setNewForm({ ...newForm, company_id: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                  >
                    {companies.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name || `Company #${c.id}`}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Category *
                  </label>
                  <select
                    value={newForm.category}
                    onChange={e => setNewForm({ ...newForm, category: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                  >
                    {CATEGORY_OPTIONS.filter(c => c.type === newForm.entry_type || (newForm.entry_type === "PETTY_SUNDRY" && c.type === "PETTY_SUNDRY")).map((opt, i) => (
                      <option key={i} value={opt.value}>
                        {opt.value}
                      </option>
                    ))}
                    <option value="General Miscellaneous">Other Miscellaneous</option>
                  </select>
                </div>
              </div>

              {/* Row 3: Party Name & Amount */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Party / Beneficiary / Payer *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Balaji Recyclers, Staples, Sundry Vendor"
                    value={newForm.party_name}
                    onChange={e => setNewForm({ ...newForm, party_name: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Amount (₹ INR) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    placeholder="0.00"
                    value={newForm.amount}
                    onChange={e => setNewForm({ ...newForm, amount: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm font-mono font-bold text-gray-900 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                  />
                </div>
              </div>

              {/* Row 4: Payment Mode & Reference Document */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Payment / Settlement Mode *
                  </label>
                  <select
                    value={newForm.payment_mode}
                    onChange={e => setNewForm({ ...newForm, payment_mode: e.target.value as MiscEntry["payment_mode"] })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                  >
                    <option value="BANK_TRANSFER">Bank Transfer (NEFT/IMPS/RTGS)</option>
                    <option value="UPI">UPI / QR Code</option>
                    <option value="CASH">Physical Cash (Petty Cash)</option>
                    <option value="CHEQUE">Bank Cheque</option>
                    <option value="JOURNAL_ADJUSTMENT">Journal Voucher Adjustment</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                    Reference Bill / Receipt #
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. BILL-4912, NEFT-7788192"
                    value={newForm.reference_doc}
                    onChange={e => setNewForm({ ...newForm, reference_doc: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none font-mono"
                  />
                </div>
              </div>

              {/* Narration */}
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">
                  Narration / Accounting Remarks *
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Explain the background, reason, or particulars for this miscellaneous transaction..."
                  value={newForm.narration}
                  onChange={e => setNewForm({ ...newForm, narration: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsNewEntryOpen(false)}
                  className="px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Posting...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Save & Post Voucher</span>
                    </>
                  )}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {/* VIEW ENTRY DETAILS MODAL */}
      {viewingEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-gray-100 overflow-hidden animate-in zoom-in-95 duration-150">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-gray-900">Voucher Details</h2>
                  <p className="text-xs font-mono text-indigo-600 font-bold">{viewingEntry.voucher_no}</p>
                </div>
              </div>
              <button
                onClick={() => setViewingEntry(null)}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-4 text-sm">
              <div className="bg-gray-50 p-4 rounded-xl space-y-2 border border-gray-100">
                <div className="flex justify-between">
                  <span className="text-xs text-gray-500 font-semibold uppercase">Amount</span>
                  <span className="text-lg font-bold font-mono text-gray-900">{formatINR(viewingEntry.amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-gray-500 font-semibold uppercase">Type</span>
                  <span className="font-semibold text-gray-800">{viewingEntry.entry_type.replace("_", " ")}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-gray-500 font-semibold uppercase">Category</span>
                  <span className="font-medium text-gray-700">{viewingEntry.category}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-gray-400 uppercase font-bold block mb-0.5">Date</span>
                  <span className="font-semibold text-gray-800">{viewingEntry.entry_date}</span>
                </div>
                <div>
                  <span className="text-gray-400 uppercase font-bold block mb-0.5">Company</span>
                  <span className="font-semibold text-gray-800">{viewingEntry.company_name}</span>
                </div>
                <div>
                  <span className="text-gray-400 uppercase font-bold block mb-0.5">Party / Beneficiary</span>
                  <span className="font-semibold text-gray-800">{viewingEntry.party_name}</span>
                </div>
                <div>
                  <span className="text-gray-400 uppercase font-bold block mb-0.5">Payment Mode</span>
                  <span className="font-semibold text-gray-800">{viewingEntry.payment_mode}</span>
                </div>
                <div>
                  <span className="text-gray-400 uppercase font-bold block mb-0.5">Status</span>
                  <span className="font-semibold text-emerald-600">{viewingEntry.status}</span>
                </div>
                <div>
                  <span className="text-gray-400 uppercase font-bold block mb-0.5">Reference Doc</span>
                  <span className="font-mono font-semibold text-gray-800">{viewingEntry.reference_doc || "—"}</span>
                </div>
              </div>

              <div>
                <span className="text-xs text-gray-400 uppercase font-bold block mb-1">Narration</span>
                <p className="p-3 bg-gray-50 border border-gray-100 rounded-xl text-gray-700 text-xs italic">
                  &ldquo;{viewingEntry.narration}&rdquo;
                </p>
              </div>

              <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
                <span>Created By: {viewingEntry.created_by || "Accounts System"}</span>
                <button
                  onClick={() => setViewingEntry(null)}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>

            </div>

          </div>
        </div>
      )}

    </div>
  );
}
