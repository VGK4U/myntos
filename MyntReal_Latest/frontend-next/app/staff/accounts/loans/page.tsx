"use client";

import React, { useState, useEffect, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { 
  Landmark, 
  Building2, 
  ListFilter, 
  Search, 
  Info, 
  AlertTriangle,
  Link as LinkIcon,
  X,
  CreditCard,
  TrendingDown,
  TrendingUp,
  ShieldCheck,
  Building,
  ArrowUpRight,
  ArrowDownLeft,
  FileSpreadsheet,
  PlusCircle,
  RefreshCw,
  PieChart
} from "lucide-react";

// Currency Formatter Utility for Indian Rupees (INR)
const formatCurrency = (amount: number | string | undefined | null) => {
  const val = typeof amount === "string" ? parseFloat(amount) : amount;
  const num = isNaN(val as number) || val === null || val === undefined ? 0 : (val as number);
  const abs = Math.abs(num);
  const formatted = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(abs);
  
  if (num < 0) {
    return <span className="text-red-600 font-semibold">({formatted})</span>;
  }
  return formatted;
};

const formatDate = (date: Date) => date.toISOString().slice(0, 10);

function LoansAccountContent() {
  const { token, isAuthenticated } = useStaffAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  // Context Params (e.g. if drilled down from Consolidated Balance Sheet)
  const ctxCo = searchParams.get("company_id") || "0";
  const ctxAsOn = searchParams.get("as_on") || searchParams.get("date_to") || searchParams.get("to_date") || "";
  const ctxFrom = searchParams.get("from_date") || searchParams.get("date_from") || "";

  // Filter States
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>("0");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");
  const [period, setPeriod] = useState<string>("fy");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Navigation / View Tabs
  const [activeTab, setActiveTab] = useState<"summary" | "txns" | "categories">("summary");

  // Summary Data State
  const [summaryData, setSummaryData] = useState<any[]>([]);
  const [summaryMeta, setSummaryMeta] = useState<{
    total_loans?: string;
    total_secured?: string;
    total_unsecured?: string;
    total_bank_od?: string;
    total_other?: string;
  }>({});
  const [summaryLoading, setSummaryLoading] = useState<boolean>(true);
  const [summaryError, setSummaryError] = useState<string>("");

  // Transactions Data State
  const [txnsData, setTxnsData] = useState<any[]>([]);
  const [txnsLoading, setTxnsLoading] = useState<boolean>(false);
  const [txnsError, setTxnsError] = useState<string>("");
  const [txnsLoaded, setTxnsLoaded] = useState<boolean>(false);

  // Context Notification Banner
  const [showContextBanner, setShowContextBanner] = useState<boolean>(false);
  const [contextMessage, setContextMessage] = useState<string>("");

  // Period setup helper
  const handlePeriodSelect = (p: string) => {
    setPeriod(p);
    const today = new Date();
    const to = formatDate(today);
    
    if (p === "month") {
      setFromDate(formatDate(new Date(today.getFullYear(), today.getMonth(), 1)));
      setToDate(to);
    } else if (p === "quarter") {
      const qm = [0, 0, 0, 3, 3, 3, 6, 6, 6, 9, 9, 9][today.getMonth()];
      setFromDate(formatDate(new Date(today.getFullYear(), qm, 1)));
      setToDate(to);
    } else if (p === "fy") {
      const y = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
      setFromDate(formatDate(new Date(y, 3, 1)));
      setToDate(to);
    } else if (p === "overall") {
      setFromDate("");
      setToDate(to);
    }
  };

  // Initial load & context evaluation
  useEffect(() => {
    fetchCompanies();
    
    let hasContext = false;
    const parts = [];
    if (ctxCo && ctxCo !== "0") {
      parts.push(`Company ID: ${ctxCo}`);
      setSelectedCompany(ctxCo);
      hasContext = true;
    }
    if (ctxAsOn) {
      parts.push(`As on: ${ctxAsOn}`);
      setToDate(ctxAsOn);
      hasContext = true;
    }
    if (ctxFrom) {
      setFromDate(ctxFrom);
      hasContext = true;
    }
    
    if (hasContext) {
      setShowContextBanner(true);
      setContextMessage(`Filtered from Consolidated Balance Sheet — ${parts.join(", ")}`);
    } else {
      handlePeriodSelect("fy");
    }
  }, [ctxCo, ctxAsOn, ctxFrom]);

  // Load summary whenever auth is ready or initial mount settled
  useEffect(() => {
    if (token) {
      loadSummary();
    }
  }, [token]);

  // Load transactions lazily when tab is opened
  useEffect(() => {
    if (activeTab === "txns" && !txnsLoaded && token) {
      loadTxns();
    }
  }, [activeTab, token]);

  const fetchCompanies = async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      if (res.data && res.data.companies) {
        setCompanies(res.data.companies);
      }
    } catch (err) {
      console.error("Failed to load companies", err);
    }
  };

  const clearCtx = () => {
    setShowContextBanner(false);
    setSelectedCompany("0");
    setFromDate("");
    setToDate("");
    handlePeriodSelect("fy");
    router.replace("/staff/accounts/loans");
    setTimeout(loadSummary, 0);
  };

  const buildParams = () => {
    const p = new URLSearchParams();
    if (selectedCompany && selectedCompany !== "0") p.set("company_id", selectedCompany);
    if (fromDate) p.set("from_date", fromDate);
    if (toDate) p.set("to_date", toDate);
    return p.toString();
  };

  const loadSummary = async () => {
    setSummaryLoading(true);
    setSummaryError("");
    setTxnsLoaded(false);
    
    try {
      const qs = buildParams();
      const res = await api.get(`/staff/accounts/loans-summary?${qs}`);
      if (res.data?.success) {
        setSummaryData(res.data.companies || []);
        setSummaryMeta({
          total_loans: res.data.total_loans,
          total_secured: res.data.total_secured,
          total_unsecured: res.data.total_unsecured,
          total_bank_od: res.data.total_bank_od,
          total_other: res.data.total_other,
        });
      } else {
        throw new Error(res.data?.detail || "Failed to load loans summary");
      }
    } catch (err: any) {
      console.warn("Summary fetch returned error, displaying fallback empty state:", err);
      setSummaryError(err.response?.data?.detail || err.message || "An error occurred while loading loans data");
      setSummaryData([]);
    } finally {
      setSummaryLoading(false);
    }
  };

  const loadTxns = async () => {
    setTxnsLoading(true);
    setTxnsError("");
    setTxnsLoaded(true);
    
    try {
      const qs = buildParams();
      const res = await api.get(`/staff/accounts/loans-transactions?${qs}`);
      if (res.data?.success) {
        setTxnsData(res.data.transactions || []);
      } else {
        throw new Error(res.data?.detail || "Failed to load transactions");
      }
    } catch (err: any) {
      setTxnsError(err.response?.data?.detail || err.message || "An error occurred while loading loan transactions");
      setTxnsData([]);
    } finally {
      setTxnsLoading(false);
    }
  };

  const applyFilters = () => {
    loadSummary();
    if (activeTab === "txns") {
      loadTxns();
    }
  };

  const resetFilters = () => {
    setSelectedCompany("0");
    setSearchQuery("");
    handlePeriodSelect("fy");
    setTimeout(applyFilters, 0);
  };

  // Aggregated KPI calculations (derived from data or metadata)
  const computedMetrics = useMemo(() => {
    let grandTotal = 0;
    let secured = 0;
    let unsecured = 0;
    let bankOD = 0;
    let other = 0;
    let totalEntries = 0;

    summaryData.forEach((co) => {
      (co.ledgers || []).forEach((l: any) => {
        const val = parseFloat(l.closing_balance) || 0;
        grandTotal += val;
        totalEntries += l.txn_count || 0;

        const pg = (l.parent_group || "").toLowerCase();
        const nm = (l.ledger_name || "").toLowerCase();

        if (pg.includes("secured") || nm.includes("secured") || nm.includes("term loan") || nm.includes("vehicle")) {
          secured += val;
        } else if (pg.includes("unsecured") || nm.includes("unsecured") || nm.includes("director") || nm.includes("promoter")) {
          unsecured += val;
        } else if (pg.includes("od") || nm.includes("od") || pg.includes("overdraft") || nm.includes("overdraft") || nm.includes("cc") || nm.includes("cash credit")) {
          bankOD += val;
        } else {
          other += val;
        }
      });
    });

    return {
      grandTotal: summaryMeta.total_loans ? parseFloat(summaryMeta.total_loans) : grandTotal,
      secured: summaryMeta.total_secured ? parseFloat(summaryMeta.total_secured) : secured,
      unsecured: summaryMeta.total_unsecured ? parseFloat(summaryMeta.total_unsecured) : unsecured,
      bankOD: summaryMeta.total_bank_od ? parseFloat(summaryMeta.total_bank_od) : bankOD,
      other: summaryMeta.total_other ? parseFloat(summaryMeta.total_other) : other,
      totalEntries,
    };
  }, [summaryData, summaryMeta]);

  // Filtered summary data by search query
  const filteredSummary = useMemo(() => {
    if (!searchQuery.trim()) return summaryData;
    const q = searchQuery.toLowerCase();
    
    return summaryData.map((co) => {
      const matchingLedgers = (co.ledgers || []).filter((l: any) => 
        (l.ledger_name || "").toLowerCase().includes(q) ||
        (l.account_code || "").toLowerCase().includes(q) ||
        (l.parent_group || "").toLowerCase().includes(q)
      );
      return {
        ...co,
        ledgers: matchingLedgers,
      };
    }).filter((co) => (co.ledgers || []).length > 0);
  }, [summaryData, searchQuery]);

  // Filtered transactions by search query
  const filteredTxns = useMemo(() => {
    if (!searchQuery.trim()) return txnsData;
    const q = searchQuery.toLowerCase();
    return txnsData.filter((t: any) =>
      (t.account_name || "").toLowerCase().includes(q) ||
      (t.company_name || "").toLowerCase().includes(q) ||
      (t.reference_number || "").toLowerCase().includes(q) ||
      (t.narration || "").toLowerCase().includes(q) ||
      (t.particulars || "").toLowerCase().includes(q)
    );
  }, [txnsData, searchQuery]);

  // Export summary as CSV
  const exportCSV = () => {
    const rows = [
      ["Company", "Ledger Name", "Account Code", "Parent Group", "Opening Balance", "Period Debit (Repayment)", "Period Credit (Borrowing)", "Closing Balance", "Entries Count"]
    ];

    summaryData.forEach((co) => {
      (co.ledgers || []).forEach((l: any) => {
        rows.push([
          `"${co.company_name || ""}"`,
          `"${l.ledger_name || ""}"`,
          `"${l.account_code || ""}"`,
          `"${l.parent_group || ""}"`,
          l.opening_balance,
          l.period_debit,
          l.period_credit,
          l.closing_balance,
          l.txn_count
        ]);
      });
    });

    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `loans_summary_${formatDate(new Date())}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      
      {/* Enterprise Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white shadow-md shadow-indigo-200">
            <Landmark className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Loans &amp; Borrowings</h1>
              <span className="bg-indigo-50 text-indigo-700 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-indigo-200">
                Liability A/c
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-0.5">
              Secured &amp; Unsecured Loans, Bank OD/CC facilities, and institutional borrowings
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button 
            onClick={exportCSV} 
            disabled={summaryData.length === 0}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-lg text-sm font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FileSpreadsheet className="h-4 w-4 text-emerald-600" /> Export CSV
          </button>
          
          <Link
            href="/staff/accounts/general-ledger?account_type=LOAN"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <ListFilter className="h-4 w-4 text-indigo-600" /> General Ledger
          </Link>

          <Link
            href="/staff/accounts/journal-voucher"
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <PlusCircle className="h-4 w-4" /> Record Loan Entry
          </Link>
        </div>
      </div>

      {/* Context Link Banner */}
      {showContextBanner && (
        <div className="flex items-center justify-between bg-indigo-50 border border-indigo-200 rounded-xl p-3.5 text-sm text-indigo-900 shadow-sm animate-in slide-in-from-top duration-200">
          <div className="flex items-center gap-2.5 font-medium">
            <LinkIcon className="h-4 w-4 text-indigo-600 shrink-0" />
            <span>{contextMessage}</span>
          </div>
          <button 
            onClick={clearCtx}
            className="flex items-center gap-1 text-indigo-700 hover:text-indigo-950 text-xs font-semibold px-2.5 py-1 rounded-md hover:bg-indigo-100/60 transition-colors"
          >
            <X className="h-3.5 w-3.5" /> Clear Filter
          </button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          
          {/* Company Selector */}
          <div className="flex-1 min-w-[200px] flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Company</label>
            <select 
              value={selectedCompany}
              onChange={(e) => setSelectedCompany(e.target.value)}
              className="px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-gray-800"
            >
              <option value="0">All Associated Companies</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.company_name || c.name}</option>
              ))}
            </select>
          </div>

          {/* Quick Period Buttons */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Period</label>
            <div className="flex gap-1 bg-gray-50 p-1 rounded-xl border border-gray-200">
              {[
                { id: "month", label: "This Month" },
                { id: "quarter", label: "This Quarter" },
                { id: "fy", label: "This FY" },
                { id: "overall", label: "Overall" },
                { id: "custom", label: "Custom" }
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => handlePeriodSelect(p.id)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                    period === p.id 
                      ? "bg-white text-indigo-600 shadow-sm font-bold" 
                      : "text-gray-600 hover:text-gray-900 hover:bg-white/50"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* From Date */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">From Date</label>
            <input 
              type="date" 
              value={fromDate}
              onChange={(e) => { setFromDate(e.target.value); setPeriod("custom"); }}
              className="px-3 py-2 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>

          {/* To Date */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">To Date</label>
            <input 
              type="date" 
              value={toDate}
              onChange={(e) => { setToDate(e.target.value); setPeriod("custom"); }}
              className="px-3 py-2 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>

          {/* Search Box */}
          <div className="flex-1 min-w-[200px] flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Search</label>
            <div className="relative">
              <Search className="h-4 w-4 text-gray-400 absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ledger, code, group..."
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button 
              onClick={applyFilters}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors shadow-sm"
            >
              <Search className="h-4 w-4" /> Apply
            </button>
            <button 
              onClick={resetFilters}
              className="px-4 py-2.5 bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 rounded-xl text-sm font-medium transition-colors"
            >
              Reset
            </button>
          </div>

        </div>
      </div>

      {/* Accounting Intelligence Note */}
      <div className="bg-gradient-to-r from-blue-50/70 via-indigo-50/60 to-purple-50/70 border border-indigo-100 rounded-2xl p-4 flex items-start gap-3.5 text-sm text-indigo-950">
        <Info className="h-5 w-5 text-indigo-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold">Double-Entry Standard:</span> Loans &amp; Borrowings are <em>credit-nature liabilities</em>.
          <span className="text-indigo-800"> Closing Balance = Opening Balance + Fresh Borrowings (Credit) − Loan Repayments / EMI Principal (Debit). </span>
          A positive closing balance reflects outstanding loan principal owed by the enterprise.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Total Outstanding */}
        <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Total Loans Liability</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Landmark className="h-4 w-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-indigo-600 tabular-nums">
              {formatCurrency(computedMetrics.grandTotal)}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">All companies &amp; facilities combined</p>
          </div>
          <div className="flex items-center justify-between text-xs pt-2 border-t border-gray-50 text-gray-500">
            <span>Active Ledgers:</span>
            <span className="font-semibold text-gray-700">
              {summaryData.reduce((acc, c) => acc + (c.ledgers?.length || 0), 0)} accounts
            </span>
          </div>
        </div>

        {/* Card 2: Secured Loans */}
        <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Secured / Bank Loans</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-blue-600 tabular-nums">
              {formatCurrency(computedMetrics.secured)}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Term loans, vehicle &amp; hypothecation</p>
          </div>
          <div className="flex items-center justify-between text-xs pt-2 border-t border-gray-50 text-gray-500">
            <span>Portfolio Share:</span>
            <span className="font-semibold text-blue-600">
              {computedMetrics.grandTotal > 0 ? ((computedMetrics.secured / computedMetrics.grandTotal) * 100).toFixed(1) + "%" : "0%"}
            </span>
          </div>
        </div>

        {/* Card 3: Unsecured Loans */}
        <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Unsecured Loans</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <CreditCard className="h-4 w-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-amber-600 tabular-nums">
              {formatCurrency(computedMetrics.unsecured)}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Director, promoter &amp; allied advances</p>
          </div>
          <div className="flex items-center justify-between text-xs pt-2 border-t border-gray-50 text-gray-500">
            <span>Portfolio Share:</span>
            <span className="font-semibold text-amber-600">
              {computedMetrics.grandTotal > 0 ? ((computedMetrics.unsecured / computedMetrics.grandTotal) * 100).toFixed(1) + "%" : "0%"}
            </span>
          </div>
        </div>

        {/* Card 4: Bank OD / CC */}
        <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Bank OD / CC Facilities</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-emerald-600 tabular-nums">
              {formatCurrency(computedMetrics.bankOD)}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Working capital &amp; cash credit limits</p>
          </div>
          <div className="flex items-center justify-between text-xs pt-2 border-t border-gray-50 text-gray-500">
            <span>Portfolio Share:</span>
            <span className="font-semibold text-emerald-600">
              {computedMetrics.grandTotal > 0 ? ((computedMetrics.bankOD / computedMetrics.grandTotal) * 100).toFixed(1) + "%" : "0%"}
            </span>
          </div>
        </div>

      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-gray-200">
        <button
          onClick={() => setActiveTab("summary")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "summary"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <Building2 className="h-4 w-4" /> Company-wise Breakdown
        </button>

        <button
          onClick={() => setActiveTab("txns")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "txns"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <ListFilter className="h-4 w-4" /> Transaction History
        </button>

        <button
          onClick={() => setActiveTab("categories")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "categories"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <PieChart className="h-4 w-4" /> Category Portfolio
        </button>
      </div>

      {/* Tab Panes */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        
        {/* TAB 1: COMPANY-WISE BREAKDOWN */}
        {activeTab === "summary" && (
          <div>
            <div className="flex items-center justify-between p-4 px-6 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2.5 font-bold text-gray-800 text-sm">
                <Landmark className="h-4 w-4 text-indigo-600" />
                Loans Ledger Accounts — Company-wise Breakdown
              </div>
              <div className="text-xs font-semibold text-gray-500">
                Showing {filteredSummary.length} {filteredSummary.length === 1 ? "company" : "companies"}
              </div>
            </div>

            {summaryLoading ? (
              <div className="flex flex-col items-center justify-center p-16 space-y-3">
                <div className="animate-spin rounded-full h-9 w-9 border-3 border-indigo-600 border-t-transparent"></div>
                <p className="text-sm font-medium text-gray-500">Loading loan master balances...</p>
              </div>
            ) : summaryError ? (
              <div className="p-12 text-center text-red-500">
                <AlertTriangle className="h-10 w-10 mx-auto mb-3 opacity-60 text-red-500" />
                <h4 className="font-bold text-base text-gray-800">Unable to load loans summary</h4>
                <p className="text-sm text-gray-500 mt-1">{summaryError}</p>
                <button
                  onClick={loadSummary}
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Try Again
                </button>
              </div>
            ) : filteredSummary.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Landmark className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <h4 className="font-bold text-gray-700 text-base">No Loan Accounts Found</h4>
                <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
                  {searchQuery 
                    ? `No loan accounts match the search "${searchQuery}".` 
                    : "No active loan or borrowing ledger accounts found for the selected company and period."}
                </p>
                <Link
                  href="/staff/accounts/journal-voucher"
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
                >
                  <PlusCircle className="h-3.5 w-3.5" /> Create Loan Voucher
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50/80 border-b border-gray-100 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                      <th className="p-3.5 pl-6">Loan Ledger Account</th>
                      <th className="p-3.5">Code</th>
                      <th className="p-3.5 text-right text-sky-800 bg-sky-50/40">Opening Balance</th>
                      <th className="p-3.5 text-right text-red-700 bg-red-50/40">
                        Period Debit<br/>
                        <span className="font-normal normal-case text-[10px] text-red-500">(Repayments/EMI)</span>
                      </th>
                      <th className="p-3.5 text-right text-emerald-700 bg-emerald-50/40">
                        Period Credit<br/>
                        <span className="font-normal normal-case text-[10px] text-emerald-500">(New Borrowings)</span>
                      </th>
                      <th className="p-3.5 text-right text-indigo-700 bg-indigo-50/40">
                        Closing Balance
                      </th>
                      <th className="p-3.5 text-right pr-6">Activity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredSummary.map((co, idx) => {
                      const ledgers = co.ledgers || [];
                      if (!ledgers.length) return null;

                      let coTotalOpening = 0;
                      let coTotalDebit = 0;
                      let coTotalCredit = 0;
                      let coTotalClosing = 0;

                      return (
                        <React.Fragment key={idx}>
                          {/* Company Header Row */}
                          <tr className="bg-indigo-50/30">
                            <td colSpan={7} className="p-2.5 px-6 font-bold text-indigo-950 text-xs">
                              <div className="flex items-center justify-between">
                                <span className="flex items-center gap-2">
                                  <Building className="h-3.5 w-3.5 text-indigo-600" />
                                  {co.company_name || `Company #${co.company_id}`}
                                </span>
                                <span className="text-[11px] font-medium text-indigo-700 bg-indigo-100/60 px-2 py-0.5 rounded-full">
                                  {ledgers.length} {ledgers.length === 1 ? "account" : "accounts"}
                                </span>
                              </div>
                            </td>
                          </tr>

                          {/* Ledger Detail Rows */}
                          {ledgers.map((l: any, lidx: number) => {
                            const opening = parseFloat(l.opening_balance) || 0;
                            const debit = parseFloat(l.period_debit) || 0;
                            const credit = parseFloat(l.period_credit) || 0;
                            const closing = parseFloat(l.closing_balance) || 0;

                            coTotalOpening += opening;
                            coTotalDebit += debit;
                            coTotalCredit += credit;
                            coTotalClosing += closing;

                            return (
                              <tr key={lidx} className="hover:bg-indigo-50/20 transition-colors group">
                                <td className="p-3 pl-8">
                                  <div className="font-semibold text-gray-800 flex items-center gap-2">
                                    {l.ledger_name}
                                    <Link 
                                      href={`/staff/accounts/general-ledger?account_name=${encodeURIComponent(l.ledger_name)}`}
                                      className="opacity-0 group-hover:opacity-100 text-indigo-600 hover:text-indigo-800 text-[11px] inline-flex items-center transition-opacity"
                                      title="Drill into ledger"
                                    >
                                      <ArrowUpRight className="h-3 w-3" />
                                    </Link>
                                  </div>
                                  {l.parent_group && (
                                    <div className="text-xs text-gray-400 mt-0.5 font-medium">{l.parent_group}</div>
                                  )}
                                </td>
                                <td className="p-3">
                                  <span className="bg-gray-100 text-gray-600 font-mono text-[10px] px-2 py-1 rounded font-semibold border border-gray-200">
                                    {l.account_code || "—"}
                                  </span>
                                </td>
                                <td className="p-3 text-right text-sky-800 font-medium tabular-nums">
                                  {formatCurrency(l.opening_balance)}
                                </td>
                                <td className="p-3 text-right tabular-nums">
                                  {debit > 0 ? (
                                    <span className="text-red-600 font-semibold flex items-center justify-end gap-1">
                                      <ArrowDownLeft className="h-3 w-3 shrink-0" />
                                      {formatCurrency(l.period_debit)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-300 italic">—</span>
                                  )}
                                </td>
                                <td className="p-3 text-right tabular-nums">
                                  {credit > 0 ? (
                                    <span className="text-emerald-600 font-semibold flex items-center justify-end gap-1">
                                      <ArrowUpRight className="h-3 w-3 shrink-0" />
                                      {formatCurrency(l.period_credit)}
                                    </span>
                                  ) : (
                                    <span className="text-gray-300 italic">—</span>
                                  )}
                                </td>
                                <td className="p-3 text-right font-bold text-indigo-700 bg-indigo-50/10 tabular-nums">
                                  {formatCurrency(l.closing_balance)}
                                </td>
                                <td className="p-3 pr-6 text-right text-gray-500 tabular-nums text-xs">
                                  {l.txn_count > 0 ? (
                                    <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full font-medium">
                                      {l.txn_count} txns
                                    </span>
                                  ) : (
                                    <span className="text-gray-300 italic">—</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}

                          {/* Company Subtotal Row */}
                          <tr className="bg-gray-50/90 border-t border-b-2 border-gray-200 font-bold text-xs">
                            <td colSpan={2} className="p-3 pl-8 text-gray-700">
                              Subtotal — {co.company_name}
                            </td>
                            <td className="p-3 text-right text-sky-900 tabular-nums">
                              {formatCurrency(coTotalOpening)}
                            </td>
                            <td className="p-3 text-right text-red-700 tabular-nums">
                              {formatCurrency(coTotalDebit)}
                            </td>
                            <td className="p-3 text-right text-emerald-700 tabular-nums">
                              {formatCurrency(coTotalCredit)}
                            </td>
                            <td className="p-3 text-right text-indigo-700 bg-indigo-50/30 tabular-nums text-sm">
                              {formatCurrency(coTotalClosing)}
                            </td>
                            <td></td>
                          </tr>
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                  {/* Grand Total Footer */}
                  <tfoot>
                    <tr className="bg-indigo-900 text-white font-bold text-sm">
                      <td colSpan={5} className="p-4 pl-6 text-right uppercase tracking-wider text-xs">
                        Grand Total Loans &amp; Borrowings Liability:
                      </td>
                      <td className="p-4 text-right text-indigo-100 text-base font-black tabular-nums">
                        {formatCurrency(computedMetrics.grandTotal)}
                      </td>
                      <td className="p-4 pr-6 text-right text-xs text-indigo-200">
                        {computedMetrics.totalEntries} entries
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: TRANSACTION HISTORY */}
        {activeTab === "txns" && (
          <div>
            <div className="flex items-center justify-between p-4 px-6 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2.5 font-bold text-gray-800 text-sm">
                <ListFilter className="h-4 w-4 text-indigo-600" />
                Loans &amp; Borrowings — Transaction History (account_ledger)
              </div>
              <div className="text-xs font-semibold text-gray-500">
                {filteredTxns.length} transactions recorded
              </div>
            </div>

            {txnsLoading ? (
              <div className="flex flex-col items-center justify-center p-16 space-y-3">
                <div className="animate-spin rounded-full h-9 w-9 border-3 border-indigo-600 border-t-transparent"></div>
                <p className="text-sm font-medium text-gray-500">Fetching transaction logs...</p>
              </div>
            ) : txnsError ? (
              <div className="p-12 text-center text-red-500">
                <AlertTriangle className="h-10 w-10 mx-auto mb-3 opacity-60 text-red-500" />
                <h4 className="font-bold text-base text-gray-800">Unable to load transactions</h4>
                <p className="text-sm text-gray-500 mt-1">{txnsError}</p>
                <button
                  onClick={loadTxns}
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Try Again
                </button>
              </div>
            ) : filteredTxns.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <ListFilter className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <h4 className="font-bold text-gray-700 text-base">No Transactions Found</h4>
                <p className="text-sm text-gray-500 mt-1">
                  No loan account debit or credit entries recorded in the selected period.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50/80 border-b border-gray-100 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                      <th className="p-3.5 pl-6 whitespace-nowrap">Date</th>
                      <th className="p-3.5">Company</th>
                      <th className="p-3.5">Account / Ledger</th>
                      <th className="p-3.5">Type</th>
                      <th className="p-3.5">Voucher / Ref</th>
                      <th className="p-3.5">Narration / Particulars</th>
                      <th className="p-3.5 text-right text-red-700 bg-red-50/30">Debit (Repayment)</th>
                      <th className="p-3.5 pr-6 text-right text-emerald-700 bg-emerald-50/30">Credit (Borrowing)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredTxns.map((t: any, idx: number) => {
                      const isCredit = t.entry_type === "CREDIT";
                      const debit = parseFloat(t.debit) || 0;
                      const credit = parseFloat(t.credit) || 0;
                      const ref = [t.voucher_type, t.reference_number].filter(Boolean).join(" / ") || "—";
                      const narr = t.narration || t.particulars || "—";

                      return (
                        <tr key={idx} className="hover:bg-gray-50 transition-colors">
                          <td className="p-3 pl-6 whitespace-nowrap text-gray-600 font-medium">{t.date}</td>
                          <td className="p-3 text-xs text-gray-500">{t.company_name}</td>
                          <td className="p-3 font-semibold text-gray-800">{t.account_name}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                              isCredit ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                            }`}>
                              {t.entry_type}
                            </span>
                          </td>
                          <td className="p-3 text-xs text-gray-500 font-mono">{ref}</td>
                          <td className="p-3 text-xs text-gray-600 max-w-[220px] truncate" title={narr}>
                            {narr}
                          </td>
                          <td className="p-3 text-right tabular-nums">
                            {debit > 0 ? (
                              <span className="text-red-600 font-semibold">{formatCurrency(t.debit)}</span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                          <td className="p-3 pr-6 text-right tabular-nums">
                            {credit > 0 ? (
                              <span className="text-emerald-600 font-semibold">{formatCurrency(t.credit)}</span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: CATEGORY PORTFOLIO */}
        {activeTab === "categories" && (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-gray-100">
              <div>
                <h3 className="text-base font-bold text-gray-900">Loan Portfolio Distribution</h3>
                <p className="text-xs text-gray-500">Breakdown of borrowings across risk profiles and facility types</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Category Card 1 */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50/40 p-5 rounded-2xl border border-blue-100 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-blue-600" />
                    <h4 className="font-bold text-gray-900 text-sm">Secured Term Loans</h4>
                  </div>
                  <span className="text-xs font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                    {computedMetrics.grandTotal > 0 ? ((computedMetrics.secured / computedMetrics.grandTotal) * 100).toFixed(1) + "%" : "0%"}
                  </span>
                </div>
                <div className="text-2xl font-black text-blue-700 tabular-nums">
                  {formatCurrency(computedMetrics.secured)}
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">
                  Secured by fixed assets, solar installations, inventory, or machinery hypothecation with banking partners.
                </p>
              </div>

              {/* Category Card 2 */}
              <div className="bg-gradient-to-br from-amber-50 to-orange-50/40 p-5 rounded-2xl border border-amber-100 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CreditCard className="h-5 w-5 text-amber-600" />
                    <h4 className="font-bold text-gray-900 text-sm">Unsecured / Director Loans</h4>
                  </div>
                  <span className="text-xs font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                    {computedMetrics.grandTotal > 0 ? ((computedMetrics.unsecured / computedMetrics.grandTotal) * 100).toFixed(1) + "%" : "0%"}
                  </span>
                </div>
                <div className="text-2xl font-black text-amber-700 tabular-nums">
                  {formatCurrency(computedMetrics.unsecured)}
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">
                  Subordinated debt, promoter loans, and unsecured working advances without charge on business collateral.
                </p>
              </div>

              {/* Category Card 3 */}
              <div className="bg-gradient-to-br from-emerald-50 to-teal-50/40 p-5 rounded-2xl border border-emerald-100 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-emerald-600" />
                    <h4 className="font-bold text-gray-900 text-sm">Bank OD &amp; CC Lines</h4>
                  </div>
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                    {computedMetrics.grandTotal > 0 ? ((computedMetrics.bankOD / computedMetrics.grandTotal) * 100).toFixed(1) + "%" : "0%"}
                  </span>
                </div>
                <div className="text-2xl font-black text-emerald-700 tabular-nums">
                  {formatCurrency(computedMetrics.bankOD)}
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">
                  Revolving credit, overdraft limits, and short-term liquidity lines for operational cycle management.
                </p>
              </div>

            </div>

            {/* Quick Link Actions */}
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-600">
              <span>Need to reclassify or create a new loan ledger master account?</span>
              <Link 
                href="/staff/accounts/general-ledger" 
                className="font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
              >
                Go to General Ledger Masters <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        )}

      </div>

    </div>
  );
}

export default function LoansAccountPage() {
  return (
    <Suspense fallback={
      <div className="p-12 flex flex-col items-center justify-center space-y-3 text-gray-400">
        <div className="animate-spin rounded-full h-8 w-8 border-3 border-indigo-600 border-t-transparent"></div>
        <p className="text-sm font-medium">Loading Loans &amp; Borrowings Module...</p>
      </div>
    }>
      <LoansAccountContent />
    </Suspense>
  );
}
