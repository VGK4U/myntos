"use client";

import React, { useState, useEffect, useCallback, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { toast } from "react-hot-toast";
import {
  HandCoins,
  FileText,
  Users,
  Search,
  RefreshCw,
  AlertTriangle,
  Link as LinkIcon,
  X,
  BookOpen,
  Plus,
  CheckCircle2,
  Calendar,
  Building2,
  Filter,
  Receipt
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";

// ── Types ────────────────────────────────────────────────────────────

interface Company {
  id: number;
  company_name?: string;
  name?: string;
  company_code?: string;
}

interface CustomerSummary {
  customer_name: string;
  company_id: number;
  company_name: string;
  invoice_count: number;
  total_billed: number;
  total_received: number;
  total_outstanding: number;
}

interface ReceivableItem {
  id: number;
  invoice_number: string;
  party_name: string;
  party_type?: string;
  company_id: number;
  company_name: string;
  invoice_date: string;
  due_date: string;
  grand_total: number;
  amount_received: number;
  balance_due: number;
  days_overdue?: number;
  payment_status: "UNPAID" | "PARTIAL" | "OVERDUE" | "PAID" | "FULLY_PAID" | string;
}

// ── Helpers ──────────────────────────────────────────────────────────

function fyStart(): Date {
  const t = new Date();
  const m = t.getMonth();
  const y = m >= 3 ? t.getFullYear() : t.getFullYear() - 1;
  return new Date(y, 3, 1);
}

function formatDateStr(d: Date): string {
  return d.toISOString().split("T")[0];
}

function formatDisplayDate(dateStr?: string | null): string {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr.includes("T") ? dateStr : `${dateStr}T00:00:00`);
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatCurrency(val?: number | string | null): string {
  const num = typeof val === "string" ? parseFloat(val) : val;
  const valid = isNaN(num as number) || num === null || num === undefined ? 0 : (num as number);
  return valid.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// ── Main Page Component ──────────────────────────────────────────────

function AccountsReceivableContent() {
  const { token } = useStaffAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL drill-down parameters
  const ctxCo = searchParams.get("company_id") || "0";
  const ctxAsOn =
    searchParams.get("as_on") ||
    searchParams.get("date_to") ||
    searchParams.get("to_date") ||
    "";
  const ctxFrom =
    searchParams.get("from_date") || searchParams.get("date_from") || "";

  // Filter States
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>("0");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activePeriod, setActivePeriod] = useState<string>("fy");

  // Context banner
  const [showContextBanner, setShowContextBanner] = useState<boolean>(false);
  const [contextMessage, setContextMessage] = useState<string>("");

  // Tab State
  const [activeTab, setActiveTab] = useState<"summary" | "invoices">("summary");

  // Data States
  const [summaryList, setSummaryList] = useState<CustomerSummary[]>([]);
  const [summaryTotalOutstanding, setSummaryTotalOutstanding] = useState<number>(0);
  const [summaryLoading, setSummaryLoading] = useState<boolean>(false);

  const [invoicesList, setInvoicesList] = useState<ReceivableItem[]>([]);
  const [invoicesTotalPending, setInvoicesTotalPending] = useState<number>(0);
  const [invoicesTotalOverdue, setInvoicesTotalOverdue] = useState<number>(0);
  const [invoicesLoading, setInvoicesLoading] = useState<boolean>(false);

  // Receipt Modal State
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState<boolean>(false);
  const [receiptInvoice, setReceiptInvoice] = useState<ReceivableItem | null>(null);
  const [receiptAmount, setReceiptAmount] = useState<string>("");
  const [receiptDate, setReceiptDate] = useState<string>(formatDateStr(new Date()));
  const [paymentMode, setPaymentMode] = useState<string>("BANK");
  const [paymentReference, setPaymentReference] = useState<string>("");
  const [narration, setNarration] = useState<string>("");
  const [submittingReceipt, setSubmittingReceipt] = useState<boolean>(false);

  // ── 1. Fetch Companies ─────────────────────────────────────────────
  const fetchCompanies = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      const list = Array.isArray(res.data)
        ? res.data
        : res.data?.companies || [];
      setCompanies(list);
    } catch (err) {
      console.warn("Failed to load companies:", err);
    }
  }, []);

  // ── 2. Handle Period Selection ─────────────────────────────────────
  const setPeriod = useCallback((p: string) => {
    setActivePeriod(p);
    const today = new Date();
    const todayStr = formatDateStr(today);

    if (p === "month") {
      const ms = new Date(today.getFullYear(), today.getMonth(), 1);
      setFromDate(formatDateStr(ms));
      setToDate(todayStr);
    } else if (p === "quarter") {
      const qm = [0, 0, 0, 3, 3, 3, 6, 6, 6, 9, 9, 9][today.getMonth()];
      const qs = new Date(today.getFullYear(), qm, 1);
      setFromDate(formatDateStr(qs));
      setToDate(todayStr);
    } else if (p === "fy") {
      setFromDate(formatDateStr(fyStart()));
      setToDate(todayStr);
    } else if (p === "overall") {
      setFromDate("");
      setToDate(todayStr);
    } else if (p === "custom") {
      // Keep existing dates for manual editing
    }
  }, []);

  // ── 3. Initialize Filters from URL Context or Defaults ────────────
  useEffect(() => {
    fetchCompanies();

    const initialFrom = ctxFrom || formatDateStr(fyStart());
    const initialTo = ctxAsOn || formatDateStr(new Date());

    setFromDate(initialFrom);
    setToDate(initialTo);

    if (ctxCo && ctxCo !== "0") {
      setSelectedCompany(ctxCo);
    }

    if ((ctxCo && ctxCo !== "0") || ctxAsOn) {
      setShowContextBanner(true);
      const companyPart = ctxCo && ctxCo !== "0" ? `Company ID: ${ctxCo}` : "";
      const datePart = ctxAsOn ? `as on ${formatDisplayDate(ctxAsOn)}` : "";
      const label = [companyPart, datePart].filter(Boolean).join(" ");
      setContextMessage(`Filtered from Consolidated Balance Sheet${label ? ` (${label})` : ""}`);
    }
  }, [fetchCompanies, ctxCo, ctxAsOn, ctxFrom]);

  // ── 4. Fetch Summary Data ──────────────────────────────────────────
  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedCompany && selectedCompany !== "0") {
        params.set("company_id", selectedCompany);
      }
      if (fromDate) params.set("from_date", fromDate);
      if (toDate) params.set("to_date", toDate);

      const res = await api.get(`/staff/accounts/receivables-summary?${params.toString()}`);
      if (res.data?.success) {
        setSummaryList(res.data.customers || []);
        const total = parseFloat(res.data.total_outstanding) || 0;
        setSummaryTotalOutstanding(total);
      } else {
        setSummaryList([]);
        setSummaryTotalOutstanding(0);
      }
    } catch (err) {
      console.error("Failed to load receivables summary:", err);
      setSummaryList([]);
    } finally {
      setSummaryLoading(false);
    }
  }, [selectedCompany, fromDate, toDate]);

  // ── 5. Fetch Invoices Data ─────────────────────────────────────────
  const fetchInvoices = useCallback(async () => {
    setInvoicesLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page_size", "500");
      if (selectedCompany && selectedCompany !== "0") {
        params.set("company_id", selectedCompany);
      }
      if (fromDate) params.set("from_date", fromDate);
      if (toDate) params.set("as_on_date", toDate);
      if (statusFilter) params.set("status", statusFilter);

      const res = await api.get(`/staff/accounts/receivables?${params.toString()}`);
      if (res.data?.success) {
        setInvoicesList(res.data.receivables || []);
        setInvoicesTotalPending(parseFloat(res.data.total_pending) || 0);
        setInvoicesTotalOverdue(parseFloat(res.data.total_overdue) || 0);
      } else {
        setInvoicesList([]);
        setInvoicesTotalPending(0);
        setInvoicesTotalOverdue(0);
      }
    } catch (err) {
      console.error("Failed to load receivables invoices:", err);
      setInvoicesList([]);
    } finally {
      setInvoicesLoading(false);
    }
  }, [selectedCompany, fromDate, toDate, statusFilter]);

  // ── 6. Initial & Triggered Data Load ──────────────────────────────
  const loadAll = useCallback(() => {
    fetchSummary();
    fetchInvoices();
  }, [fetchSummary, fetchInvoices]);

  useEffect(() => {
    if (token) {
      loadAll();
    }
  }, [token, loadAll]);

  // ── 7. Reset Filters ───────────────────────────────────────────────
  const handleResetFilters = () => {
    setSelectedCompany("0");
    setStatusFilter("");
    setSearchQuery("");
    setShowContextBanner(false);
    setPeriod("fy");
    router.replace("/staff/accounts/receivables");
  };

  const handleClearContext = () => {
    setShowContextBanner(false);
    handleResetFilters();
  };

  // ── 8. Navigation to Party Ledger ──────────────────────────────────
  const handleOpenLedger = (partyName: string, companyId: number | string) => {
    const params = new URLSearchParams();
    params.set("party_name", partyName);
    params.set("party_type", "All Types");
    if (companyId && companyId !== 0) params.set("company_id", String(companyId));
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);

    router.push(`/staff/accounts/party-ledger?${params.toString()}`);
  };

  // ── 9. Record Receipt Modal Handlers ───────────────────────────────
  const handleOpenReceiptModal = (inv: ReceivableItem) => {
    setReceiptInvoice(inv);
    setReceiptAmount(String(inv.balance_due || ""));
    setReceiptDate(formatDateStr(new Date()));
    setPaymentMode("BANK");
    setPaymentReference("");
    setNarration("");
    setIsReceiptModalOpen(true);
  };

  const handleCloseReceiptModal = () => {
    setIsReceiptModalOpen(false);
    setReceiptInvoice(null);
  };

  const handleSubmitReceipt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!receiptInvoice) return;

    const amt = parseFloat(receiptAmount);
    if (isNaN(amt) || amt <= 0) {
      toast.error("Please enter a valid receipt amount greater than 0");
      return;
    }
    if (amt > receiptInvoice.balance_due) {
      toast.error(`Receipt amount cannot exceed balance due (₹${formatCurrency(receiptInvoice.balance_due)})`);
      return;
    }
    if (!receiptDate) {
      toast.error("Please select receipt date");
      return;
    }
    if (!paymentMode) {
      toast.error("Please select payment mode");
      return;
    }

    setSubmittingReceipt(true);
    try {
      const payload = {
        invoice_id: receiptInvoice.id,
        amount: amt,
        receipt_date: receiptDate,
        payment_mode: paymentMode,
        payment_reference: paymentReference.trim() || null,
        narration: narration.trim() || null,
      };

      const res = await api.post("/staff/accounts/receivables/record-receipt", payload);
      if (res.data?.success) {
        toast.success(res.data.message || "Receipt recorded successfully!");
        handleCloseReceiptModal();
        loadAll();
      } else {
        toast.error(res.data?.detail || res.data?.message || "Failed to record receipt");
      }
    } catch (err: any) {
      console.error("Receipt submission error:", err);
      toast.error(err.response?.data?.detail || err.message || "Error submitting receipt");
    } finally {
      setSubmittingReceipt(false);
    }
  };

  // ── 10. Filtered Lists via Search Query ────────────────────────────
  const filteredSummary = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return summaryList;
    return summaryList.filter((item) =>
      item.customer_name.toLowerCase().includes(q) ||
      (item.company_name && item.company_name.toLowerCase().includes(q))
    );
  }, [summaryList, searchQuery]);

  const filteredInvoices = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return invoicesList;
    return invoicesList.filter((item) =>
      item.party_name.toLowerCase().includes(q) ||
      item.invoice_number.toLowerCase().includes(q) ||
      (item.company_name && item.company_name.toLowerCase().includes(q))
    );
  }, [invoicesList, searchQuery]);

  // Selected company label
  const selectedCompanyName = useMemo(() => {
    if (selectedCompany === "0") return "All Companies";
    const found = companies.find((c) => String(c.id) === String(selectedCompany));
    return found ? (found.company_name || found.name) : `Company #${selectedCompany}`;
  }, [companies, selectedCompany]);

  return (
    <div className="min-h-screen bg-slate-50/60 pb-16">
      {/* ── Top Header Bar ──────────────────────────────────────────── */}
      <div className="bg-white border-b border-gray-200 px-6 py-5 sticky top-0 z-20 shadow-xs">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-emerald-600/10 border border-emerald-500/20 text-emerald-600 rounded-xl flex items-center justify-center shadow-xs">
              <HandCoins className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-gray-900 tracking-tight">
                  Accounts Receivable
                </h1>
                <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 font-medium text-xs">
                  Sundry Debtors
                </Badge>
              </div>
              <p className="text-xs text-gray-500 font-normal mt-0.5">
                Outstanding receivables from customers — sourced from Sales Invoices (matches Consolidated Balance Sheet)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={loadAll}
              disabled={summaryLoading || invoicesLoading}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-900 transition-colors shadow-xs disabled:opacity-50"
              title="Refresh receivables data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${summaryLoading || invoicesLoading ? "animate-spin text-emerald-600" : ""}`} />
              Refresh
            </button>
            <Link
              href="/staff/accounts/party-ledger"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors shadow-xs"
            >
              <BookOpen className="w-3.5 h-3.5" />
              Party Ledger
            </Link>
            <Link
              href="/staff/accounts/sales-invoices"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Create Sales Invoice
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        {/* ── Context Banner ────────────────────────────────────────── */}
        {showContextBanner && (
          <div className="flex items-center justify-between bg-emerald-50/90 border border-emerald-300/80 rounded-xl px-4 py-3 text-sm text-emerald-900 shadow-xs animate-in fade-in duration-300">
            <div className="flex items-center gap-2.5 font-medium">
              <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                <LinkIcon className="w-3.5 h-3.5" />
              </div>
              <span>
                {contextMessage || `Filtered from Consolidated Balance Sheet — ${selectedCompanyName}`}
              </span>
            </div>
            <button
              onClick={handleClearContext}
              className="inline-flex items-center gap-1 text-xs font-bold text-emerald-800 hover:text-emerald-950 bg-white/70 hover:bg-white px-2.5 py-1 rounded-md border border-emerald-300 transition-all cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              Clear filter
            </button>
          </div>
        )}

        {/* ── Filter Bar ────────────────────────────────────────────── */}
        <div className="bg-white rounded-xl shadow-xs border border-gray-200/80 p-4.5 space-y-4">
          <div className="flex flex-wrap items-end gap-3.5">
            {/* Company Select */}
            <div className="flex flex-col gap-1 min-w-[180px]">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <Building2 className="w-3 h-3 text-gray-400" />
                Company
              </label>
              <select
                value={selectedCompany}
                onChange={(e) => setSelectedCompany(e.target.value)}
                className="px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              >
                <option value="0">All Companies</option>
                {companies.map((co) => (
                  <option key={co.id} value={co.id}>
                    {co.company_name || co.name || `Company #${co.id}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Period Button Group */}
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <Calendar className="w-3 h-3 text-gray-400" />
                Period
              </label>
              <div className="flex gap-1 bg-gray-100/80 p-1 rounded-lg border border-gray-200/60">
                {[
                  { id: "month", label: "This Month" },
                  { id: "quarter", label: "This Quarter" },
                  { id: "fy", label: "This FY" },
                  { id: "overall", label: "Overall" },
                  { id: "custom", label: "Custom" },
                ].map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setPeriod(p.id)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                      activePeriod === p.id
                        ? "bg-white text-emerald-700 shadow-xs border border-gray-200/70"
                        : "text-gray-600 hover:text-gray-900 hover:bg-white/50"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Date Inputs */}
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                From Date
              </label>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => {
                  setFromDate(e.target.value);
                  setActivePeriod("custom");
                }}
                className="px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                To Date (As On)
              </label>
              <input
                type="date"
                value={toDate}
                onChange={(e) => {
                  setToDate(e.target.value);
                  setActivePeriod("custom");
                }}
                className="px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              />
            </div>

            {/* Status Select */}
            <div className="flex flex-col gap-1 min-w-[130px]">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <Filter className="w-3 h-3 text-gray-400" />
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
              >
                <option value="">All Statuses</option>
                <option value="UNPAID">Unpaid</option>
                <option value="PARTIAL">Partial</option>
                <option value="OVERDUE">Overdue</option>
              </select>
            </div>

            {/* Search Input */}
            <div className="flex flex-col gap-1 flex-1 min-w-[200px]">
              <label className="text-[11px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <Search className="w-3 h-3 text-gray-400" />
                Search Party / Invoice
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Filter customer name or invoice number..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                />
                <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={loadAll}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition-colors shadow-xs flex items-center gap-1.5 cursor-pointer"
              >
                <Search className="w-3.5 h-3.5" />
                Apply
              </button>
              <button
                onClick={handleResetFilters}
                className="px-3.5 py-2 bg-white text-gray-600 border border-gray-200 rounded-lg text-xs font-semibold hover:bg-gray-50 hover:text-gray-900 transition-colors shadow-xs cursor-pointer"
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        {/* ── Summary KPI Cards ─────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Total Receivable */}
          <div className="bg-white rounded-xl border border-gray-200/80 p-5 shadow-xs relative overflow-hidden group hover:border-emerald-300 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                Total Receivable
              </span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <HandCoins className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-emerald-600 mt-2 tracking-tight">
              ₹{formatCurrency(summaryTotalOutstanding)}
            </div>
            <div className="flex items-center gap-1 text-[11px] text-gray-500 mt-1.5 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              <span>= Consolidated Balance Sheet</span>
            </div>
          </div>

          {/* Card 2: Total Overdue */}
          <div className="bg-white rounded-xl border border-rose-200/80 p-5 shadow-xs relative overflow-hidden group hover:border-rose-300 bg-rose-50/20 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-rose-700 uppercase tracking-wider">
                Total Overdue
              </span>
              <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-rose-600 mt-2 tracking-tight">
              ₹{formatCurrency(invoicesTotalOverdue)}
            </div>
            <div className="flex items-center gap-1 text-[11px] text-rose-600 mt-1.5 font-medium">
              <span>Past due date & requires collection</span>
            </div>
          </div>

          {/* Card 3: Customers Count */}
          <div className="bg-white rounded-xl border border-gray-200/80 p-5 shadow-xs relative overflow-hidden group hover:border-indigo-300 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                Customers
              </span>
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Users className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900 mt-2 tracking-tight">
              {filteredSummary.length}
            </div>
            <div className="text-[11px] text-gray-500 mt-1.5 font-medium">
              With outstanding receivables
            </div>
          </div>

          {/* Card 4: Invoice Count */}
          <div className="bg-white rounded-xl border border-gray-200/80 p-5 shadow-xs relative overflow-hidden group hover:border-blue-300 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                Invoice Count
              </span>
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <FileText className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900 mt-2 tracking-tight">
              {filteredInvoices.length}
            </div>
            <div className="text-[11px] text-gray-500 mt-1.5 font-medium">
              Active pending invoices
            </div>
          </div>
        </div>

        {/* ── Tabs Navigation ───────────────────────────────────────── */}
        <div className="border-b border-gray-200 flex gap-6">
          <button
            onClick={() => setActiveTab("summary")}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
              activeTab === "summary"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Customer Summary</span>
            <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px] py-0 px-1.5">
              = Consolidated
            </Badge>
          </button>

          <button
            onClick={() => setActiveTab("invoices")}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer ${
              activeTab === "invoices"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Invoice List</span>
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-[10px] py-0 px-1.5">
              Per Invoice
            </Badge>
          </button>
        </div>

        {/* ── TAB 1: Customer Summary Table ─────────────────────────── */}
        {activeTab === "summary" && (
          <div className="bg-white rounded-xl shadow-xs border border-gray-200/80 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200/80 bg-gray-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-600" />
                <h3 className="text-sm font-bold text-gray-900">
                  Customer-wise Outstanding
                </h3>
              </div>
              <span className="text-xs font-semibold text-gray-500">
                {filteredSummary.length} customer{filteredSummary.length === 1 ? "" : "s"} found
              </span>
            </div>

            {summaryLoading ? (
              <div className="py-16 flex flex-col items-center justify-center text-gray-500 space-y-3">
                <RefreshCw className="w-7 h-7 animate-spin text-emerald-600" />
                <p className="text-xs font-medium">Loading customer summary...</p>
              </div>
            ) : filteredSummary.length === 0 ? (
              <div className="py-16 text-center text-gray-500 space-y-3">
                <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-bold text-gray-900">No Outstanding Receivables</h4>
                <p className="text-xs text-gray-500 max-w-sm mx-auto">
                  All customer payments have been settled or no records matched the selected period and company filter.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50/80 text-gray-500 uppercase tracking-wider font-bold border-b border-gray-200">
                      <th className="py-3 px-4 w-12 text-center">#</th>
                      <th className="py-3 px-4">Customer Name</th>
                      <th className="py-3 px-4">Associated Company</th>
                      <th className="py-3 px-4 text-right">Invoices</th>
                      <th className="py-3 px-4 text-right">Total Billed</th>
                      <th className="py-3 px-4 text-right">Total Received</th>
                      <th className="py-3 px-4 text-right text-emerald-700 bg-emerald-50/30">Outstanding</th>
                      <th className="py-3 px-4 text-center w-28">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredSummary.map((item, idx) => (
                      <tr
                        key={`${item.customer_name}-${item.company_id}-${idx}`}
                        className="hover:bg-slate-50/80 transition-colors"
                      >
                        <td className="py-3.5 px-4 text-center text-gray-400 font-mono">
                          {idx + 1}
                        </td>
                        <td className="py-3.5 px-4 font-bold text-gray-900">
                          {item.customer_name}
                        </td>
                        <td className="py-3.5 px-4 text-gray-600 font-medium">
                          {item.company_name || "-"}
                        </td>
                        <td className="py-3.5 px-4 text-right font-medium text-gray-700">
                          {item.invoice_count}
                        </td>
                        <td className="py-3.5 px-4 text-right font-semibold text-gray-900">
                          ₹{formatCurrency(item.total_billed)}
                        </td>
                        <td className="py-3.5 px-4 text-right font-semibold text-emerald-600">
                          ₹{formatCurrency(item.total_received)}
                        </td>
                        <td className="py-3.5 px-4 text-right font-bold text-emerald-700 bg-emerald-50/30">
                          ₹{formatCurrency(item.total_outstanding)}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={() => handleOpenLedger(item.customer_name, item.company_id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/80 rounded-md transition-colors shadow-xs cursor-pointer"
                            title="Open Customer Party Ledger"
                          >
                            <BookOpen className="w-3 h-3" />
                            Ledger
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

        {/* ── TAB 2: Invoices List Table ────────────────────────────── */}
        {activeTab === "invoices" && (
          <div className="bg-white rounded-xl shadow-xs border border-gray-200/80 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200/80 bg-gray-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" />
                <h3 className="text-sm font-bold text-gray-900">
                  Pending Sales Invoices
                </h3>
              </div>
              <span className="text-xs font-semibold text-gray-500">
                {filteredInvoices.length} record{filteredInvoices.length === 1 ? "" : "s"} found
              </span>
            </div>

            {invoicesLoading ? (
              <div className="py-16 flex flex-col items-center justify-center text-gray-500 space-y-3">
                <RefreshCw className="w-7 h-7 animate-spin text-blue-600" />
                <p className="text-xs font-medium">Loading sales invoices...</p>
              </div>
            ) : filteredInvoices.length === 0 ? (
              <div className="py-16 text-center text-gray-500 space-y-3">
                <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-bold text-gray-900">No Pending Invoices</h4>
                <p className="text-xs text-gray-500 max-w-sm mx-auto">
                  All customer invoices are fully settled or no pending invoices match the active filter criteria.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-gray-50/80 text-gray-500 uppercase tracking-wider font-bold border-b border-gray-200">
                      <th className="py-3 px-4">Invoice #</th>
                      <th className="py-3 px-4">Customer Name</th>
                      <th className="py-3 px-4">Company</th>
                      <th className="py-3 px-4">Invoice Date</th>
                      <th className="py-3 px-4 text-right">Total (₹)</th>
                      <th className="py-3 px-4 text-right">Received (₹)</th>
                      <th className="py-3 px-4 text-right text-emerald-700 bg-emerald-50/30">Balance Due (₹)</th>
                      <th className="py-3 px-4">Due Date</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-center w-36">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredInvoices.map((inv) => {
                      return (
                        <tr
                          key={inv.id}
                          className="hover:bg-slate-50/80 transition-colors"
                        >
                          <td className="py-3.5 px-4 font-mono font-bold text-gray-900 whitespace-nowrap">
                            <span className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded border border-gray-200">
                              {inv.invoice_number || `#${inv.id}`}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-bold text-gray-900">
                            {inv.party_name}
                          </td>
                          <td className="py-3.5 px-4 text-gray-600 font-medium">
                            {inv.company_name || "-"}
                          </td>
                          <td className="py-3.5 px-4 text-gray-600 whitespace-nowrap">
                            {formatDisplayDate(inv.invoice_date)}
                          </td>
                          <td className="py-3.5 px-4 text-right font-semibold text-gray-900 whitespace-nowrap">
                            ₹{formatCurrency(inv.grand_total)}
                          </td>
                          <td className="py-3.5 px-4 text-right font-semibold text-emerald-600 whitespace-nowrap">
                            ₹{formatCurrency(inv.amount_received)}
                          </td>
                          <td className="py-3.5 px-4 text-right font-bold text-emerald-700 bg-emerald-50/30 whitespace-nowrap">
                            ₹{formatCurrency(inv.balance_due)}
                          </td>
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <div className="font-medium text-gray-800">
                              {formatDisplayDate(inv.due_date)}
                            </div>
                            {inv.days_overdue && inv.days_overdue > 0 ? (
                              <span className="text-[10px] font-bold text-rose-600 block">
                                {inv.days_overdue}d overdue
                              </span>
                            ) : null}
                          </td>
                          <td className="py-3.5 px-4 text-center whitespace-nowrap">
                            <span
                              className={`inline-flex px-2 py-0.5 text-[10px] font-bold rounded-full uppercase tracking-wider border ${
                                inv.payment_status === "PAID" || inv.payment_status === "FULLY_PAID"
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : inv.payment_status === "OVERDUE"
                                  ? "bg-rose-50 text-rose-700 border-rose-200"
                                  : inv.payment_status === "PARTIAL"
                                  ? "bg-blue-50 text-blue-700 border-blue-200"
                                  : "bg-amber-50 text-amber-700 border-amber-200"
                              }`}
                            >
                              {inv.payment_status}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-center whitespace-nowrap">
                            <div className="flex items-center justify-center gap-1.5">
                              {inv.balance_due > 0 && (
                                <button
                                  onClick={() => handleOpenReceiptModal(inv)}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition-colors shadow-xs cursor-pointer"
                                  title="Record customer payment receipt"
                                >
                                  <Receipt className="w-3 h-3" />
                                  Receive
                                </button>
                              )}
                              <button
                                onClick={() => handleOpenLedger(inv.party_name, inv.company_id)}
                                className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-md transition-colors shadow-xs cursor-pointer"
                                title="Open Party Ledger"
                              >
                                <BookOpen className="w-3 h-3" />
                              </button>
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
        )}
      </div>

      {/* ── Record Customer Receipt Modal ──────────────────────────── */}
      <Dialog open={isReceiptModalOpen} onOpenChange={setIsReceiptModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold text-gray-900">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Receipt className="w-4 h-4" />
              </div>
              Record Customer Receipt
            </DialogTitle>
            <DialogDescription className="text-xs text-gray-500">
              Record incoming payment against sales invoice
            </DialogDescription>
          </DialogHeader>

          {receiptInvoice && (
            <form onSubmit={handleSubmitReceipt} className="space-y-4 pt-1">
              {/* Invoice Summary Box */}
              <div className="bg-slate-50 border border-gray-200 rounded-lg p-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500 font-medium">Invoice:</span>
                  <span className="font-mono font-bold text-gray-900">{receiptInvoice.invoice_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 font-medium">Customer:</span>
                  <span className="font-bold text-gray-900">{receiptInvoice.party_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 font-medium">Company:</span>
                  <span className="font-medium text-gray-700">{receiptInvoice.company_name}</span>
                </div>
                <div className="flex justify-between pt-1 border-t border-gray-200">
                  <span className="text-gray-700 font-bold">Balance Due:</span>
                  <span className="font-bold text-emerald-600">₹{formatCurrency(receiptInvoice.balance_due)}</span>
                </div>
              </div>

              {/* Form Fields */}
              <div className="space-y-3">
                <div>
                  <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
                    Receipt Amount (₹) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={receiptInvoice.balance_due}
                    required
                    value={receiptAmount}
                    onChange={(e) => setReceiptAmount(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-semibold border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                    placeholder="Enter amount received"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
                      Receipt Date <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="date"
                      required
                      value={receiptDate}
                      onChange={(e) => setReceiptDate(e.target.value)}
                      className="w-full px-3 py-2 text-xs font-medium border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
                      Payment Mode <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={paymentMode}
                      onChange={(e) => setPaymentMode(e.target.value)}
                      className="w-full px-3 py-2 text-xs font-medium border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                    >
                      <option value="BANK">Bank Transfer</option>
                      <option value="UPI">UPI</option>
                      <option value="CASH">Cash</option>
                      <option value="CHEQUE">Cheque</option>
                      <option value="NEFT">NEFT</option>
                      <option value="RTGS">RTGS</option>
                      <option value="DD">Demand Draft (DD)</option>
                      <option value="CARD">Debit / Credit Card</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
                    Reference / UTR / Cheque Number
                  </label>
                  <input
                    type="text"
                    value={paymentReference}
                    onChange={(e) => setPaymentReference(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-medium border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                    placeholder="e.g. UTR / Transaction ID / Cheque #"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-1">
                    Narration / Notes
                  </label>
                  <textarea
                    rows={2}
                    value={narration}
                    onChange={(e) => setNarration(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-medium border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 resize-none"
                    placeholder="Optional notes or remarks"
                  />
                </div>
              </div>

              <DialogFooter className="pt-3 border-t border-gray-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={handleCloseReceiptModal}
                  disabled={submittingReceipt}
                  className="px-3.5 py-2 text-xs font-semibold text-gray-600 hover:text-gray-800 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReceipt}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {submittingReceipt ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Saving Receipt...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Record Receipt
                    </>
                  )}
                </button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function AccountsReceivablePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-gray-500">
            <RefreshCw className="w-8 h-8 animate-spin text-emerald-600" />
            <p className="text-sm font-medium">Loading Accounts Receivable...</p>
          </div>
        </div>
      }
    >
      <AccountsReceivableContent />
    </Suspense>
  );
}

