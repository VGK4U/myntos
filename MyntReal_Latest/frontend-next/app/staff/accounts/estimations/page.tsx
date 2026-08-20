"use client";

import React, { useState, useEffect, useCallback, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { toast } from "react-hot-toast";
import {
  Calculator,
  ArrowDownLeft,
  ArrowUpRight,
  CreditCard,
  Boxes,
  PieChart,
  Building2,
  RefreshCw,
  Search,
  Plus,
  Trash2,
  Edit3,
  CheckCircle2,
  RotateCcw,
  FileText,
  AlertCircle,
  ArrowLeft,
  ExternalLink,
  Check,
  X,
  Info,
  Calendar,
  User,
  Wallet,
  Tag,
  DollarSign,
  Landmark,
  Layers,
  TrendingUp,
  TrendingDown,
  ChevronRight,
  ShieldCheck,
  Clock
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// ── Types ────────────────────────────────────────────────────────────

interface Company {
  id: number;
  company_name?: string;
  name?: string;
  company_code?: string;
  code?: string;
}

interface BankAccount {
  id: number;
  account_name: string;
  bank_name?: string;
  account_type: string;
  account_number?: string;
}

interface EstimatedIncomeEntry {
  id: number;
  entry_number?: string;
  income_date: string;
  company_id: number;
  company_name?: string;
  payer_name?: string;
  amount: number | string;
  payment_mode?: string;
  income_source_name?: string;
  status: string;
  notes?: string;
}

interface OutPlanningRecord {
  id: number;
  company_id: number;
  entry_date: string;
  description: string;
  estimated_amount: number | string;
  party_name?: string;
  account_name?: string;
  notes?: string;
  status?: string;
  created_at?: string;
}

interface EstimatePayment {
  id: number;
  income_entry_id: number;
  _entry_number?: string;
  payment_date: string;
  amount: number | string;
  payment_mode?: string;
  party_name?: string;
  account_received?: string;
  notes?: string;
  created_at?: string;
}

interface EstimateStockMovement {
  id: number;
  transaction_date: string;
  item_name?: string;
  item_code?: string;
  quantity_out: number | string;
  reference_number?: string;
  is_estimate?: boolean;
}

interface ExecutiveSummaryData {
  in_estimates: { count: number; total: number };
  out_estimates: { count: number; total: number };
  payments: { count: number; total: number };
  net_estimated: number;
}

// ── Formatting Helpers ───────────────────────────────────────────────

function formatCurrency(val?: number | string | null): string {
  const num = typeof val === "string" ? parseFloat(val) : val;
  const valid = isNaN(num as number) || num === null || num === undefined ? 0 : (num as number);
  return "₹" + valid.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function formatDate(dateStr?: string | null): string {
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

// ── Main Page Component ──────────────────────────────────────────────

function EstimationsContent() {
  const { token, user } = useStaffAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL drill-down param
  const urlCompanyId = searchParams.get("company_id") || "";

  // State
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(urlCompanyId);
  const [activeTab, setActiveTab] = useState<"in" | "out" | "payments" | "stock" | "executive">("in");
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Data
  const [inEntries, setInEntries] = useState<EstimatedIncomeEntry[]>([]);
  const [outRecords, setOutRecords] = useState<OutPlanningRecord[]>([]);
  const [payments, setPayments] = useState<EstimatePayment[]>([]);
  const [stockMovements, setStockMovements] = useState<EstimateStockMovement[]>([]);
  const [summary, setSummary] = useState<ExecutiveSummaryData | null>(null);

  // Bank accounts cache for modals
  const [bankAccountsCache, setBankAccountsCache] = useState<Record<number, BankAccount[]>>({});
  const [loadingBanks, setLoadingBanks] = useState<boolean>(false);

  // ── Modals State ──
  // 1. Confirm Income Entry Modal
  const [isConfirmOpen, setIsConfirmOpen] = useState<boolean>(false);
  const [confirmingEntry, setConfirmingEntry] = useState<EstimatedIncomeEntry | null>(null);
  const [confType, setConfType] = useState<"TAXED" | "ESTIMATED">("TAXED");
  const [confCompanyId, setConfCompanyId] = useState<string>("");
  const [confBankAccountId, setConfBankAccountId] = useState<string>("");
  const [confPayerName, setConfPayerName] = useState<string>("");
  const [submittingConfirm, setSubmittingConfirm] = useState<boolean>(false);

  // 2. OUT Record Modal (Add / Edit)
  const [isOutModalOpen, setIsOutModalOpen] = useState<boolean>(false);
  const [editingOutId, setEditingOutId] = useState<number | null>(null);
  const [outFormDate, setOutFormDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [outFormAmt, setOutFormAmt] = useState<string>("");
  const [outFormDesc, setOutFormDesc] = useState<string>("");
  const [outFormParty, setOutFormParty] = useState<string>("");
  const [outFormAcct, setOutFormAcct] = useState<string>("");
  const [outFormNotes, setOutFormNotes] = useState<string>("");
  const [outFormCompanyId, setOutFormCompanyId] = useState<string>("");
  const [submittingOut, setSubmittingOut] = useState<boolean>(false);

  // 3. Add Payment Modal
  const [isAddPaymentOpen, setIsAddPaymentOpen] = useState<boolean>(false);
  const [paymentEntryId, setPaymentEntryId] = useState<string>("");
  const [paymentDate, setPaymentDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [paymentAmount, setPaymentAmount] = useState<string>("");
  const [paymentMode, setPaymentMode] = useState<string>("UPI");
  const [paymentParty, setPaymentParty] = useState<string>("");
  const [paymentAccount, setPaymentAccount] = useState<string>("");
  const [paymentNotes, setPaymentNotes] = useState<string>("");
  const [submittingPayment, setSubmittingPayment] = useState<boolean>(false);

  // ── Fetch Companies ──────────────────────────────────────────────────
  const loadCompanies = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      if (res.data && res.data.companies) {
        setCompanies(res.data.companies);
      }
    } catch (err: any) {
      console.error("Error loading companies:", err);
    }
  }, []);

  // ── Fetch All Estimations Data ───────────────────────────────────────
  const refreshData = useCallback(async () => {
    setLoading(true);
    const cq = selectedCompanyId ? `?company_id=${selectedCompanyId}` : "";
    try {
      const [rIn, rOut, rStock, rSummary] = await Promise.all([
        api.get(`/staff/accounts/income-entries/estimations${cq}`).catch(() => ({ data: { entries: [] } })),
        api.get(`/staff/accounts/income-entries/estimations/out${cq}`).catch(() => ({ data: { records: [] } })),
        api.get(`/staff/accounts/income-entries/estimations/stock${cq}`).catch(() => ({ data: { stock_movements: [] } })),
        api.get(`/staff/accounts/income-entries/estimations/executive-summary${cq}`).catch(() => ({ data: { summary: null } }))
      ]);

      const fetchedInEntries: EstimatedIncomeEntry[] = rIn.data?.entries || [];
      const fetchedOutRecords: OutPlanningRecord[] = rOut.data?.records || [];
      const fetchedStock: EstimateStockMovement[] = rStock.data?.stock_movements || [];
      const fetchedSummary: ExecutiveSummaryData | null = rSummary.data?.summary || null;

      setInEntries(fetchedInEntries);
      setOutRecords(fetchedOutRecords);
      setStockMovements(fetchedStock);
      setSummary(fetchedSummary);

      // Fetch payment records for estimated entries (first 30)
      const allPayments: EstimatePayment[] = [];
      const paymentPromises = fetchedInEntries.slice(0, 30).map(async (e) => {
        try {
          const rp = await api.get(`/staff/accounts/income-entries/${e.id}/estimation-payments`);
          if (rp.data && rp.data.payments) {
            rp.data.payments.forEach((p: EstimatePayment) => {
              allPayments.push({
                ...p,
                _entry_number: e.entry_number || `IE-${e.id}`,
              });
            });
          }
        } catch {
          // ignore single entry failure
        }
      });

      await Promise.all(paymentPromises);
      setPayments(allPayments);
    } catch (err: any) {
      console.error("Failed to load estimations data:", err);
      toast.error("Failed to load estimations data");
    } finally {
      setLoading(false);
    }
  }, [selectedCompanyId]);

  useEffect(() => {
    if (token) {
      loadCompanies();
    }
  }, [token, loadCompanies]);

  useEffect(() => {
    if (token) {
      refreshData();
    }
  }, [token, refreshData]);

  // ── Load Bank Accounts For Company ──────────────────────────────────
  const fetchBankAccounts = async (compId: number) => {
    if (!compId) return [];
    if (bankAccountsCache[compId]) return bankAccountsCache[compId];
    setLoadingBanks(true);
    try {
      const res = await api.get(`/staff/accounts/ledger-masters/bank-accounts?company_id=${compId}`);
      const accs: BankAccount[] = res.data?.accounts || [];
      setBankAccountsCache((prev) => ({ ...prev, [compId]: accs }));
      return accs;
    } catch {
      return [];
    } finally {
      setLoadingBanks(false);
    }
  };

  // ── Confirm Income Entry Handlers ────────────────────────────────────
  const openConfirmModal = async (entry: EstimatedIncomeEntry) => {
    setConfirmingEntry(entry);
    setConfType("TAXED");
    const initCompId = entry.company_id ? String(entry.company_id) : (selectedCompanyId || "");
    setConfCompanyId(initCompId);
    setConfPayerName(entry.payer_name || "");
    setConfBankAccountId("");
    setIsConfirmOpen(true);

    if (initCompId) {
      await fetchBankAccounts(parseInt(initCompId));
    }
  };

  const handleConfCompanyChange = async (newCompId: string) => {
    setConfCompanyId(newCompId);
    setConfBankAccountId("");
    if (newCompId) {
      await fetchBankAccounts(parseInt(newCompId));
    }
  };

  const submitConfirmModal = async () => {
    if (!confirmingEntry) return;
    if (!confType) {
      toast.error("Please choose Taxed or Estimated");
      return;
    }

    setSubmittingConfirm(true);
    const payload: any = {
      status: confType === "ESTIMATED" ? "ESTIMATED" : "CONFIRMED",
      confirmation_type: confType,
      company_id: confCompanyId ? parseInt(confCompanyId) : null,
    };

    if (confType === "TAXED") {
      if (confBankAccountId) {
        payload.bank_account_id = parseInt(confBankAccountId);
        const compAccs = bankAccountsCache[parseInt(confCompanyId)] || [];
        const matched = compAccs.find((a) => a.id === parseInt(confBankAccountId));
        if (matched) payload.bank_account_name = matched.account_name;
      }
      if (confPayerName.trim()) {
        payload.payer_name = confPayerName.trim();
      }
    }

    try {
      const res = await api.patch(`/staff/accounts/income-entries/${confirmingEntry.id}/status`, payload);
      if (res.status === 200 || res.data?.success) {
        toast.success(`Entry ${confirmingEntry.entry_number || confirmingEntry.id} confirmed successfully!`);
        setIsConfirmOpen(false);
        setConfirmingEntry(null);
        refreshData();
      } else {
        toast.error(res.data?.detail || res.data?.message || "Failed to confirm entry");
      }
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to confirm entry");
    } finally {
      setSubmittingConfirm(false);
    }
  };

  // ── Revert Status Handler ────────────────────────────────────────────
  const handleRevertStatus = async (entry: EstimatedIncomeEntry) => {
    if (!confirm(`Are you sure you want to revert entry ${entry.entry_number || entry.id} to PENDING?`)) {
      return;
    }
    try {
      const res = await api.patch(`/staff/accounts/income-entries/${entry.id}/status`, {
        status: "PENDING",
      });
      if (res.status === 200 || res.data?.success) {
        toast.success("Entry reverted to Pending status");
        refreshData();
      } else {
        toast.error(res.data?.detail || "Failed to revert entry");
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to revert entry");
    }
  };

  // ── OUT Record Handlers ──────────────────────────────────────────────
  const openAddOutModal = () => {
    setEditingOutId(null);
    setOutFormDate(new Date().toISOString().split("T")[0]);
    setOutFormAmt("");
    setOutFormDesc("");
    setOutFormParty("");
    setOutFormAcct("");
    setOutFormNotes("");
    setOutFormCompanyId(selectedCompanyId || (companies[0]?.id ? String(companies[0].id) : ""));
    setIsOutModalOpen(true);
  };

  const openEditOutModal = (rec: OutPlanningRecord) => {
    setEditingOutId(rec.id);
    setOutFormDate(rec.entry_date ? rec.entry_date.split("T")[0] : new Date().toISOString().split("T")[0]);
    setOutFormAmt(String(rec.estimated_amount || ""));
    setOutFormDesc(rec.description || "");
    setOutFormParty(rec.party_name || "");
    setOutFormAcct(rec.account_name || "");
    setOutFormNotes(rec.notes || "");
    setOutFormCompanyId(rec.company_id ? String(rec.company_id) : selectedCompanyId || "");
    setIsOutModalOpen(true);
  };

  const saveOutRecord = async () => {
    const compId = outFormCompanyId || selectedCompanyId || (companies.length === 1 ? String(companies[0].id) : "");
    if (!compId) {
      toast.error("Please select a company for this record");
      return;
    }
    if (!outFormDesc.trim()) {
      toast.error("Description is required");
      return;
    }
    if (!outFormDate) {
      toast.error("Date is required");
      return;
    }
    const amtNum = parseFloat(outFormAmt);
    if (isNaN(amtNum) || amtNum < 0) {
      toast.error("Please enter a valid amount");
      return;
    }

    setSubmittingOut(true);
    const payload = {
      company_id: parseInt(compId),
      entry_date: outFormDate,
      description: outFormDesc.trim(),
      estimated_amount: amtNum,
      party_name: outFormParty.trim() || null,
      account_name: outFormAcct.trim() || null,
      notes: outFormNotes.trim() || null,
    };

    try {
      if (editingOutId) {
        await api.put(`/staff/accounts/income-entries/estimations/out/${editingOutId}`, payload);
        toast.success("OUT Planning record updated");
      } else {
        await api.post(`/staff/accounts/income-entries/estimations/out`, payload);
        toast.success("OUT Planning record added");
      }
      setIsOutModalOpen(false);
      refreshData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to save OUT record");
    } finally {
      setSubmittingOut(false);
    }
  };

  const deleteOutRecord = async (id: number) => {
    if (!confirm("Are you sure you want to delete this OUT planning record?")) return;
    try {
      await api.delete(`/staff/accounts/income-entries/estimations/out/${id}`);
      toast.success("OUT planning record deleted");
      refreshData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete record");
    }
  };

  // ── Payment Handlers ─────────────────────────────────────────────────
  const openAddPaymentForEntry = (entry?: EstimatedIncomeEntry) => {
    if (entry) {
      setPaymentEntryId(String(entry.id));
      setPaymentParty(entry.payer_name || "");
      setPaymentAmount(String(entry.amount || ""));
    } else if (inEntries.length > 0) {
      setPaymentEntryId(String(inEntries[0].id));
      setPaymentParty(inEntries[0].payer_name || "");
      setPaymentAmount(String(inEntries[0].amount || ""));
    } else {
      setPaymentEntryId("");
      setPaymentParty("");
      setPaymentAmount("");
    }
    setPaymentDate(new Date().toISOString().split("T")[0]);
    setPaymentMode("UPI");
    setPaymentAccount("");
    setPaymentNotes("");
    setIsAddPaymentOpen(true);
  };

  const saveEstimatePayment = async () => {
    if (!paymentEntryId) {
      toast.error("Please select an estimated income entry");
      return;
    }
    const amtNum = parseFloat(paymentAmount);
    if (isNaN(amtNum) || amtNum <= 0) {
      toast.error("Please enter a valid payment amount");
      return;
    }
    setSubmittingPayment(true);
    const payload = {
      payment_date: paymentDate,
      amount: amtNum,
      payment_mode: paymentMode,
      party_name: paymentParty.trim() || null,
      account_received: paymentAccount.trim() || null,
      notes: paymentNotes.trim() || null,
    };

    try {
      await api.post(`/staff/accounts/income-entries/${paymentEntryId}/estimation-payments`, payload);
      toast.success("Payment recorded successfully!");
      setIsAddPaymentOpen(false);
      refreshData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to record payment");
    } finally {
      setSubmittingPayment(false);
    }
  };

  const deletePayment = async (entryId: number, paymentId: number) => {
    if (!confirm("Are you sure you want to delete this payment record?")) return;
    try {
      await api.delete(`/staff/accounts/income-entries/${entryId}/estimation-payments/${paymentId}`);
      toast.success("Payment deleted");
      refreshData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete payment");
    }
  };

  // ── Filtered Datasets ────────────────────────────────────────────────
  const filteredInEntries = useMemo(() => {
    if (!searchQuery.trim()) return inEntries;
    const q = searchQuery.toLowerCase();
    return inEntries.filter(
      (e) =>
        e.entry_number?.toLowerCase().includes(q) ||
        e.payer_name?.toLowerCase().includes(q) ||
        e.company_name?.toLowerCase().includes(q) ||
        e.payment_mode?.toLowerCase().includes(q)
    );
  }, [inEntries, searchQuery]);

  const filteredOutRecords = useMemo(() => {
    if (!searchQuery.trim()) return outRecords;
    const q = searchQuery.toLowerCase();
    return outRecords.filter(
      (r) =>
        r.description?.toLowerCase().includes(q) ||
        r.party_name?.toLowerCase().includes(q) ||
        r.account_name?.toLowerCase().includes(q) ||
        r.notes?.toLowerCase().includes(q)
    );
  }, [outRecords, searchQuery]);

  const filteredPayments = useMemo(() => {
    if (!searchQuery.trim()) return payments;
    const q = searchQuery.toLowerCase();
    return payments.filter(
      (p) =>
        p._entry_number?.toLowerCase().includes(q) ||
        p.party_name?.toLowerCase().includes(q) ||
        p.account_received?.toLowerCase().includes(q) ||
        p.payment_mode?.toLowerCase().includes(q) ||
        p.notes?.toLowerCase().includes(q)
    );
  }, [payments, searchQuery]);

  const filteredStock = useMemo(() => {
    if (!searchQuery.trim()) return stockMovements;
    const q = searchQuery.toLowerCase();
    return stockMovements.filter(
      (s) =>
        s.item_name?.toLowerCase().includes(q) ||
        s.item_code?.toLowerCase().includes(q) ||
        s.reference_number?.toLowerCase().includes(q)
    );
  }, [stockMovements, searchQuery]);

  // Totals calculations
  const totalIn = useMemo(() => inEntries.reduce((s, e) => s + (parseFloat(String(e.amount)) || 0), 0), [inEntries]);
  const totalOut = useMemo(() => outRecords.reduce((s, r) => s + (parseFloat(String(r.estimated_amount)) || 0), 0), [outRecords]);
  const totalPayments = useMemo(() => payments.reduce((s, p) => s + (parseFloat(String(p.amount)) || 0), 0), [payments]);
  const netEstimatedCash = summary ? summary.net_estimated : (totalIn - totalOut);

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* ── Top Header ────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white dark:bg-zinc-900 p-6 rounded-2xl border border-zinc-200/80 dark:border-zinc-800 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center border border-amber-500/20 shadow-xs">
              <Calculator className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 tracking-tight">
                Estimations
              </h1>
              <p className="text-xs md:text-sm text-zinc-500 dark:text-zinc-400">
                SFMS estimation tracking — IN estimates, OUT planning, payments and stock movement
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={refreshData}
            disabled={loading}
            className="h-9 px-3.5 gap-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 border-zinc-200 dark:border-zinc-700"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-amber-600" : ""}`} />
            <span>Refresh</span>
          </Button>

          <Link href="/staff/accounts/income-entries">
            <Button
              variant="outline"
              size="sm"
              className="h-9 px-3.5 gap-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 border-zinc-200 dark:border-zinc-700"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Income Entries</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Filter Bar & Metrics ──────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center bg-white dark:bg-zinc-900 p-4 rounded-xl border border-zinc-200/80 dark:border-zinc-800 shadow-xs">
        {/* Company filter */}
        <div className="space-y-1.5 md:col-span-1">
          <Label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
            <Building2 className="h-3.5 w-3.5 text-zinc-400" />
            Company Filter
          </Label>
          <select
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId(e.target.value)}
            className="w-full h-9 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-800/60 px-3 text-sm font-medium text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all"
          >
            <option value="">All Companies</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.company_name || c.name || `Company #${c.id}`}
              </option>
            ))}
          </select>
        </div>

        {/* Real-time search */}
        <div className="space-y-1.5 md:col-span-2">
          <Label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
            <Search className="h-3.5 w-3.5 text-zinc-400" />
            Search Active View
          </Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <input
              type="text"
              placeholder="Filter by entry #, party, description, item..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-9 pl-9 pr-8 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-800/60 text-sm text-zinc-800 dark:text-zinc-200 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Quick Summary Pill */}
        <div className="flex md:justify-end items-center gap-2 pt-4 md:pt-0">
          <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200/70 dark:border-amber-900/50 rounded-lg p-2.5 text-right w-full md:w-auto min-w-[140px]">
            <div className="text-[10px] uppercase font-bold text-amber-700 dark:text-amber-400">Net Estimated</div>
            <div className={`text-base font-bold font-mono ${netEstimatedCash >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
              {formatCurrency(netEstimatedCash)}
            </div>
          </div>
        </div>
      </div>

      {/* ── Sub Navigation Tabs ───────────────────────────────────── */}
      <div className="flex items-center gap-1.5 border-b border-zinc-200 dark:border-zinc-800 overflow-x-auto pb-px">
        <button
          onClick={() => setActiveTab("in")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === "in"
              ? "border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/20 rounded-t-lg"
              : "border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 rounded-t-lg"
          }`}
        >
          <ArrowDownLeft className="h-4 w-4 text-emerald-600" />
          <span>IN Estimates</span>
          <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            {inEntries.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("out")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === "out"
              ? "border-rose-500 text-rose-600 dark:text-rose-400 bg-rose-50/50 dark:bg-rose-950/20 rounded-t-lg"
              : "border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 rounded-t-lg"
          }`}
        >
          <ArrowUpRight className="h-4 w-4 text-rose-600" />
          <span>OUT Planning</span>
          <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">
            {outRecords.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("payments")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === "payments"
              ? "border-purple-500 text-purple-600 dark:text-purple-400 bg-purple-50/50 dark:bg-purple-950/20 rounded-t-lg"
              : "border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 rounded-t-lg"
          }`}
        >
          <CreditCard className="h-4 w-4 text-purple-600" />
          <span>Payments</span>
          <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
            {payments.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("stock")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === "stock"
              ? "border-sky-500 text-sky-600 dark:text-sky-400 bg-sky-50/50 dark:bg-sky-950/20 rounded-t-lg"
              : "border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 rounded-t-lg"
          }`}
        >
          <Boxes className="h-4 w-4 text-sky-600" />
          <span>Stock Movement</span>
          <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300">
            {stockMovements.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("executive")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
            activeTab === "executive"
              ? "border-amber-500 text-amber-600 dark:text-amber-400 bg-amber-50/50 dark:bg-amber-950/20 rounded-t-lg"
              : "border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 rounded-t-lg"
          }`}
        >
          <PieChart className="h-4 w-4 text-amber-600" />
          <span>Executive Summary</span>
        </button>
      </div>

      {/* ── Main Tab Content ──────────────────────────────────────── */}
      {loading ? (
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-16 flex flex-col items-center justify-center gap-3 text-zinc-500">
          <RefreshCw className="h-8 w-8 animate-spin text-amber-500" />
          <p className="text-sm font-medium">Loading estimations data...</p>
        </div>
      ) : (
        <>
          {/* TAB 1: IN ESTIMATES */}
          {activeTab === "in" && (
            <div className="space-y-4">
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-xs">
                {/* Header Banner */}
                <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-zinc-50/50 dark:bg-zinc-800/40">
                  <div className="flex items-center gap-2.5">
                    <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
                      <ArrowDownLeft className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                        IN Estimated Entries ({filteredInEntries.length})
                      </h3>
                      <p className="text-xs text-zinc-500">Income entries in estimation phase — excluded from formal revenue</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-xs text-zinc-500 block">Total Estimated</span>
                      <span className="text-sm md:text-base font-bold font-mono text-emerald-600 dark:text-emerald-400">
                        {formatCurrency(totalIn)}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => openAddPaymentForEntry()}
                      className="bg-purple-600 hover:bg-purple-700 text-white text-xs h-8 gap-1.5"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>Record Payment</span>
                    </Button>
                  </div>
                </div>

                {/* Table */}
                {filteredInEntries.length === 0 ? (
                  <div className="py-16 px-4 text-center space-y-3">
                    <div className="mx-auto h-12 w-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
                      <FileText className="h-6 w-6" />
                    </div>
                    <h4 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">No Estimated Entries</h4>
                    <p className="text-xs md:text-sm text-zinc-500 max-w-md mx-auto">
                      {selectedCompanyId
                        ? "No estimated income entries found for the selected company."
                        : "Create an income entry on the Income Entries page and set its status to Estimated."}
                    </p>
                    <div className="pt-2">
                      <Link href="/staff/accounts/income-entries">
                        <Button variant="outline" size="sm" className="gap-2">
                          <ExternalLink className="h-3.5 w-3.5" />
                          <span>Go to Income Entries</span>
                        </Button>
                      </Link>
                    </div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm border-collapse">
                      <thead>
                        <tr className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">
                          <th className="py-3 px-4">Entry #</th>
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Company</th>
                          <th className="py-3 px-4">Payer</th>
                          <th className="py-3 px-4">Amount</th>
                          <th className="py-3 px-4">Payment Mode</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {filteredInEntries.map((e) => (
                          <tr key={e.id} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors">
                            <td className="py-3 px-4 font-mono text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                              <Link
                                href={`/staff/accounts/income-entries?search=${e.entry_number || e.id}`}
                                className="hover:underline flex items-center gap-1"
                              >
                                {e.entry_number || `IE-${e.id}`}
                              </Link>
                            </td>
                            <td className="py-3 px-4 text-xs text-zinc-600 dark:text-zinc-400">
                              {formatDate(e.income_date)}
                            </td>
                            <td className="py-3 px-4">
                              <Badge variant="outline" className="text-[10px] font-medium border-zinc-200 dark:border-zinc-700">
                                {e.company_name || `Company #${e.company_id}`}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-xs font-medium text-zinc-900 dark:text-zinc-100">
                              {e.payer_name || "-"}
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                              {formatCurrency(e.amount)}
                            </td>
                            <td className="py-3 px-4">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300">
                                {e.payment_mode || "OTHER"}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <Button
                                  variant="outline"
                                  size="xs"
                                  onClick={() => openConfirmModal(e)}
                                  className="h-7 px-2.5 text-xs text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800 gap-1 font-medium"
                                >
                                  <Check className="h-3 w-3" />
                                  <span>Confirm (Taxed)</span>
                                </Button>
                                <Button
                                  variant="outline"
                                  size="xs"
                                  onClick={() => openAddPaymentForEntry(e)}
                                  className="h-7 px-2 text-xs text-purple-700 bg-purple-50 hover:bg-purple-100 border-purple-300 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800 gap-1 font-medium"
                                >
                                  <CreditCard className="h-3 w-3" />
                                  <span>Pay</span>
                                </Button>
                                <Button
                                  variant="outline"
                                  size="xs"
                                  onClick={() => handleRevertStatus(e)}
                                  className="h-7 px-2 text-xs text-amber-700 bg-amber-50 hover:bg-amber-100 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800 gap-1 font-medium"
                                >
                                  <RotateCcw className="h-3 w-3" />
                                  <span>Revert</span>
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: OUT PLANNING */}
          {activeTab === "out" && (
            <div className="space-y-4">
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-xs">
                {/* Header Banner */}
                <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-zinc-50/50 dark:bg-zinc-800/40">
                  <div className="flex items-center gap-2.5">
                    <div className="h-8 w-8 rounded-lg bg-rose-500/10 text-rose-600 flex items-center justify-center">
                      <ArrowUpRight className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                        OUT Planning Records ({filteredOutRecords.length})
                      </h3>
                      <p className="text-xs text-zinc-500">Informational outgoing estimates — zero ledger impact</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-xs text-zinc-500 block">Total Planned</span>
                      <span className="text-sm md:text-base font-bold font-mono text-rose-600 dark:text-rose-400">
                        {formatCurrency(totalOut)}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      onClick={openAddOutModal}
                      className="bg-rose-600 hover:bg-rose-700 text-white text-xs h-8 gap-1.5 shadow-xs"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>Add OUT Record</span>
                    </Button>
                  </div>
                </div>

                {/* Table */}
                {filteredOutRecords.length === 0 ? (
                  <div className="py-16 px-4 text-center space-y-3">
                    <div className="mx-auto h-12 w-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
                      <ArrowUpRight className="h-6 w-6" />
                    </div>
                    <h4 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">No OUT Planning Records</h4>
                    <p className="text-xs md:text-sm text-zinc-500 max-w-md mx-auto">
                      Record anticipated outgoing expenses (vendor procurement, repairs, logistics) for cash planning.
                    </p>
                    <div className="pt-2">
                      <Button size="sm" onClick={openAddOutModal} className="bg-rose-600 hover:bg-rose-700 text-white gap-2">
                        <Plus className="h-3.5 w-3.5" />
                        <span>Add First OUT Record</span>
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm border-collapse">
                      <thead>
                        <tr className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Description</th>
                          <th className="py-3 px-4">Party / Payee</th>
                          <th className="py-3 px-4">Account</th>
                          <th className="py-3 px-4">Amount</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {filteredOutRecords.map((r) => (
                          <tr key={r.id} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors">
                            <td className="py-3 px-4 text-xs text-zinc-600 dark:text-zinc-400">
                              {formatDate(r.entry_date)}
                            </td>
                            <td className="py-3 px-4">
                              <div className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">{r.description}</div>
                              {r.notes && <div className="text-[11px] text-zinc-400 truncate max-w-xs">{r.notes}</div>}
                            </td>
                            <td className="py-3 px-4 text-xs text-zinc-700 dark:text-zinc-300">
                              {r.party_name || "-"}
                            </td>
                            <td className="py-3 px-4 text-xs text-zinc-600 dark:text-zinc-400">
                              {r.account_name || "-"}
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-rose-600 dark:text-rose-400 text-sm">
                              {formatCurrency(r.estimated_amount)}
                            </td>
                            <td className="py-3 px-4">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                                {r.status || "PENDING"}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <Button
                                  variant="ghost"
                                  size="icon-xs"
                                  onClick={() => openEditOutModal(r)}
                                  className="h-7 w-7 text-sky-600 hover:bg-sky-50 dark:hover:bg-sky-950/40"
                                >
                                  <Edit3 className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon-xs"
                                  onClick={() => deleteOutRecord(r.id)}
                                  className="h-7 w-7 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: PAYMENTS */}
          {activeTab === "payments" && (
            <div className="space-y-4">
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-xs">
                {/* Header Banner */}
                <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-zinc-50/50 dark:bg-zinc-800/40">
                  <div className="flex items-center gap-2.5">
                    <div className="h-8 w-8 rounded-lg bg-purple-500/10 text-purple-600 flex items-center justify-center">
                      <CreditCard className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                        Estimate Payments Collected ({filteredPayments.length})
                      </h3>
                      <p className="text-xs text-zinc-500">Payments tracked against estimated income entries</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-xs text-zinc-500 block">Total Payments</span>
                      <span className="text-sm md:text-base font-bold font-mono text-purple-600 dark:text-purple-400">
                        {formatCurrency(totalPayments)}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => openAddPaymentForEntry()}
                      className="bg-purple-600 hover:bg-purple-700 text-white text-xs h-8 gap-1.5 shadow-xs"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>Add Payment</span>
                    </Button>
                  </div>
                </div>

                {/* Table */}
                {filteredPayments.length === 0 ? (
                  <div className="py-16 px-4 text-center space-y-3">
                    <div className="mx-auto h-12 w-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
                      <CreditCard className="h-6 w-6" />
                    </div>
                    <h4 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">No Payments Recorded</h4>
                    <p className="text-xs md:text-sm text-zinc-500 max-w-md mx-auto">
                      Payments collected against estimated entries can be recorded directly here or via the Income Entries module.
                    </p>
                    <div className="pt-2">
                      <Button
                        size="sm"
                        onClick={() => openAddPaymentForEntry()}
                        className="bg-purple-600 hover:bg-purple-700 text-white gap-2"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        <span>Record A Payment</span>
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm border-collapse">
                      <thead>
                        <tr className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">
                          <th className="py-3 px-4">Entry #</th>
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Amount</th>
                          <th className="py-3 px-4">Mode</th>
                          <th className="py-3 px-4">Party</th>
                          <th className="py-3 px-4">Account Received</th>
                          <th className="py-3 px-4">Notes</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {filteredPayments.map((p) => (
                          <tr key={p.id} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors">
                            <td className="py-3 px-4 font-mono text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                              {p._entry_number || `#${p.income_entry_id}`}
                            </td>
                            <td className="py-3 px-4 text-xs text-zinc-600 dark:text-zinc-400">
                              {formatDate(p.payment_date)}
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                              {formatCurrency(p.amount)}
                            </td>
                            <td className="py-3 px-4">
                              <Badge variant="outline" className="text-[10px] font-semibold">
                                {p.payment_mode || "OTHER"}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-xs text-zinc-800 dark:text-zinc-200">
                              {p.party_name || "-"}
                            </td>
                            <td className="py-3 px-4 text-xs text-zinc-600 dark:text-zinc-400">
                              {p.account_received || "-"}
                            </td>
                            <td className="py-3 px-4 text-xs text-zinc-500 truncate max-w-xs">
                              {p.notes || "-"}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <Button
                                variant="ghost"
                                size="icon-xs"
                                onClick={() => deletePayment(p.income_entry_id, p.id)}
                                className="h-7 w-7 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: STOCK MOVEMENT */}
          {activeTab === "stock" && (
            <div className="space-y-4">
              <div className="bg-sky-50 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-900/60 rounded-xl p-4 flex items-start gap-3">
                <Info className="h-5 w-5 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="text-xs font-bold text-sky-900 dark:text-sky-200 uppercase tracking-wider">
                    Soft Inventory Deductions
                  </h4>
                  <p className="text-xs text-sky-800 dark:text-sky-300 leading-relaxed">
                    These stock movements represent spare parts and items allocated to service tickets in the estimation phase.
                    They are <strong>soft deductions</strong> and are excluded from formal balance-sheet inventory deductions until tickets are finalized.
                  </p>
                </div>
              </div>

              <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-xs">
                {/* Header Banner */}
                <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/40">
                  <div className="flex items-center gap-2.5">
                    <div className="h-8 w-8 rounded-lg bg-sky-500/10 text-sky-600 flex items-center justify-center">
                      <Boxes className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                        Estimate Stock Movements ({filteredStock.length})
                      </h3>
                      <p className="text-xs text-zinc-500">Soft parts movement linked to estimates</p>
                    </div>
                  </div>
                </div>

                {/* Table */}
                {filteredStock.length === 0 ? (
                  <div className="py-16 px-4 text-center space-y-3">
                    <div className="mx-auto h-12 w-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
                      <Boxes className="h-6 w-6" />
                    </div>
                    <h4 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">No Estimate Stock Movements</h4>
                    <p className="text-xs md:text-sm text-zinc-500 max-w-md mx-auto">
                      Stock items will show here when estimated service tickets allocate spare parts without finalizing invoices.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm border-collapse">
                      <thead>
                        <tr className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Item Name</th>
                          <th className="py-3 px-4">Item Code</th>
                          <th className="py-3 px-4">Quantity Out</th>
                          <th className="py-3 px-4">Reference</th>
                          <th className="py-3 px-4">Type</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {filteredStock.map((s, idx) => (
                          <tr key={s.id || idx} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors">
                            <td className="py-3 px-4 text-xs text-zinc-600 dark:text-zinc-400">
                              {formatDate(s.transaction_date)}
                            </td>
                            <td className="py-3 px-4 text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                              {s.item_name || "-"}
                            </td>
                            <td className="py-3 px-4 font-mono text-xs text-zinc-600 dark:text-zinc-400">
                              <code>{s.item_code || "-"}</code>
                            </td>
                            <td className="py-3 px-4 font-mono font-bold text-rose-600 dark:text-rose-400 text-sm">
                              {s.quantity_out || 0}
                            </td>
                            <td className="py-3 px-4 font-mono text-xs text-zinc-600 dark:text-zinc-400">
                              <code>{s.reference_number || "-"}</code>
                            </td>
                            <td className="py-3 px-4">
                              <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 text-[10px] font-semibold border-amber-300">
                                Estimate Soft Hold
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: EXECUTIVE SUMMARY */}
          {activeTab === "executive" && (
            <div className="space-y-6">
              {/* Top 4 KPI Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* 1. IN Estimates */}
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl p-5 shadow-xs relative overflow-hidden">
                  <div className="absolute top-0 right-0 h-16 w-16 bg-emerald-500/10 rounded-bl-full pointer-events-none" />
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">IN Estimated Income</span>
                    <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
                      <ArrowDownLeft className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                    {formatCurrency(summary?.in_estimates.total ?? totalIn)}
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {summary?.in_estimates.count ?? inEntries.length} estimation entries
                  </div>
                </div>

                {/* 2. OUT Planned Spend */}
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl p-5 shadow-xs relative overflow-hidden">
                  <div className="absolute top-0 right-0 h-16 w-16 bg-rose-500/10 rounded-bl-full pointer-events-none" />
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">OUT Planned Spend</span>
                    <div className="h-8 w-8 rounded-lg bg-rose-500/10 text-rose-600 flex items-center justify-center">
                      <ArrowUpRight className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="text-2xl font-bold font-mono text-rose-600 dark:text-rose-400">
                    {formatCurrency(summary?.out_estimates.total ?? totalOut)}
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {summary?.out_estimates.count ?? outRecords.length} planned records
                  </div>
                </div>

                {/* 3. Payments Collected */}
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl p-5 shadow-xs relative overflow-hidden">
                  <div className="absolute top-0 right-0 h-16 w-16 bg-purple-500/10 rounded-bl-full pointer-events-none" />
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Payments Collected</span>
                    <div className="h-8 w-8 rounded-lg bg-purple-500/10 text-purple-600 flex items-center justify-center">
                      <CreditCard className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="text-2xl font-bold font-mono text-purple-600 dark:text-purple-400">
                    {formatCurrency(summary?.payments.total ?? totalPayments)}
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {summary?.payments.count ?? payments.length} payment receipts
                  </div>
                </div>

                {/* 4. Net Estimated Cash */}
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl p-5 shadow-xs relative overflow-hidden">
                  <div className={`absolute top-0 right-0 h-16 w-16 ${netEstimatedCash >= 0 ? "bg-emerald-500/10" : "bg-rose-500/10"} rounded-bl-full pointer-events-none`} />
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Net Estimated Cash</span>
                    <div className={`h-8 w-8 rounded-lg ${netEstimatedCash >= 0 ? "bg-emerald-500/10 text-emerald-600" : "bg-rose-500/10 text-rose-600"} flex items-center justify-center`}>
                      {netEstimatedCash >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                    </div>
                  </div>
                  <div className={`text-2xl font-bold font-mono ${netEstimatedCash >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                    {formatCurrency(Math.abs(netEstimatedCash))}
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {netEstimatedCash >= 0 ? "Surplus Anticipated" : "Deficit Anticipated"}
                  </div>
                </div>
              </div>

              {/* Explanatory Guide Card */}
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded-2xl p-6 shadow-xs space-y-4">
                <div className="flex items-center gap-2.5 border-b border-zinc-100 dark:border-zinc-800 pb-3">
                  <ShieldCheck className="h-5 w-5 text-amber-600" />
                  <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                    About Estimations Architecture
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 space-y-1.5">
                    <div className="font-bold text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5">
                      <ArrowDownLeft className="h-4 w-4" />
                      IN Estimates
                    </div>
                    <p>
                      Income entries in the estimation phase. These are completely excluded from confirmed statutory revenue totals
                      until officially verified and transitioned to <strong>CONFIRMED (Taxed)</strong>.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 space-y-1.5">
                    <div className="font-bold text-rose-700 dark:text-rose-400 flex items-center gap-1.5">
                      <ArrowUpRight className="h-4 w-4" />
                      OUT Planning
                    </div>
                    <p>
                      Informational outgoing expense estimates (procurement, supplier requisitions). They have <strong>zero ledger impact</strong>
                      and are utilized exclusively for forecast &amp; liquidity visibility.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 space-y-1.5">
                    <div className="font-bold text-purple-700 dark:text-purple-400 flex items-center gap-1.5">
                      <CreditCard className="h-4 w-4" />
                      Estimate Payments
                    </div>
                    <p>
                      Advance payments or cash collected against estimated tickets. Tracked in estimation records without affecting the formal
                      statutory general ledger until the entry is fully confirmed.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 space-y-1.5">
                    <div className="font-bold text-sky-700 dark:text-sky-400 flex items-center gap-1.5">
                      <Boxes className="h-4 w-4" />
                      Stock Movement
                    </div>
                    <p>
                      Soft inventory deductions for spare parts linked to estimated service tickets. Soft-held parts are preserved from double allocation
                      without altering audited physical inventory counts.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── MODAL 1: Confirm Income Entry Modal ───────────────────── */}
      {isConfirmOpen && confirmingEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden max-h-[90vh] flex flex-col">
            <div className="p-5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  Confirm Income Entry
                </h3>
              </div>
              <button
                onClick={() => setIsConfirmOpen(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 overflow-y-auto">
              {/* Summary Card */}
              <div className="grid grid-cols-2 gap-3 p-3.5 bg-zinc-50 dark:bg-zinc-800/60 rounded-xl border border-zinc-200/60 dark:border-zinc-700 text-xs">
                <div>
                  <span className="text-[10px] font-bold text-zinc-400 uppercase">Entry #</span>
                  <div className="font-mono font-bold text-zinc-900 dark:text-zinc-100">
                    {confirmingEntry.entry_number || `IE-${confirmingEntry.id}`}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-zinc-400 uppercase">Amount</span>
                  <div className="font-mono font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                    {formatCurrency(confirmingEntry.amount)}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-zinc-400 uppercase">Date</span>
                  <div className="text-zinc-700 dark:text-zinc-300">
                    {formatDate(confirmingEntry.income_date)}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-zinc-400 uppercase">Payment Mode</span>
                  <div className="text-zinc-700 dark:text-zinc-300">
                    {confirmingEntry.payment_mode || "-"}
                  </div>
                </div>
              </div>

              {/* Company selector */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Assigned Company
                </Label>
                <select
                  value={confCompanyId}
                  onChange={(e) => handleConfCompanyChange(e.target.value)}
                  className="w-full h-9 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-3 text-sm text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                >
                  <option value="">Select Company</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name || `Company #${c.id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* Confirmation Type Choice */}
              <div className="space-y-2">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Select Confirmation Type
                </Label>
                <div className="grid grid-cols-2 gap-3">
                  <div
                    onClick={() => setConfType("TAXED")}
                    className={`cursor-pointer p-4 rounded-xl border-2 flex flex-col items-center text-center gap-2 transition-all ${
                      confType === "TAXED"
                        ? "border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/30 text-emerald-900 dark:text-emerald-200"
                        : "border-zinc-200 dark:border-zinc-700 hover:border-zinc-300"
                    }`}
                  >
                    <Landmark className={`h-6 w-6 ${confType === "TAXED" ? "text-emerald-600" : "text-zinc-400"}`} />
                    <span className="text-xs font-bold">Taxed (Confirmed)</span>
                    <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                      Posts to ledger accounts &amp; customer party ledger
                    </span>
                  </div>

                  <div
                    onClick={() => setConfType("ESTIMATED")}
                    className={`cursor-pointer p-4 rounded-xl border-2 flex flex-col items-center text-center gap-2 transition-all ${
                      confType === "ESTIMATED"
                        ? "border-amber-500 bg-amber-50/50 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200"
                        : "border-zinc-200 dark:border-zinc-700 hover:border-zinc-300"
                    }`}
                  >
                    <Calculator className={`h-6 w-6 ${confType === "ESTIMATED" ? "text-amber-600" : "text-zinc-400"}`} />
                    <span className="text-xs font-bold">Estimated</span>
                    <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                      Keeps in estimation phase, no ledger posting
                    </span>
                  </div>
                </div>
              </div>

              {/* Form fields for TAXED confirmation */}
              {confType === "TAXED" && (
                <div className="space-y-3 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Deposit Bank / Cash Account <span className="text-zinc-400 text-[10px] font-normal">(Optional)</span>
                    </Label>
                    <select
                      value={confBankAccountId}
                      onChange={(e) => setConfBankAccountId(e.target.value)}
                      disabled={loadingBanks}
                      className="w-full h-9 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-3 text-sm text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                    >
                      <option value="">Auto-resolve from payment mode</option>
                      {(bankAccountsCache[parseInt(confCompanyId)] || []).map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.account_name} ({acc.account_type})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Payer / Customer Name <span className="text-zinc-400 text-[10px] font-normal">(Optional)</span>
                    </Label>
                    <Input
                      placeholder="Payer / customer name"
                      value={confPayerName}
                      onChange={(e) => setConfPayerName(e.target.value)}
                      className="h-9 text-sm"
                    />
                  </div>
                </div>
              )}

              {/* Notice for ESTIMATED confirmation */}
              {confType === "ESTIMATED" && (
                <div className="p-3.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 rounded-xl text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
                  <Info className="h-4 w-4 shrink-0 mt-0.5 text-amber-600" />
                  <p>
                    This entry will remain in <strong>Estimated</strong> status. No ledger transactions or party entries will be generated.
                  </p>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/40 flex items-center justify-end gap-2.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsConfirmOpen(false)}
                disabled={submittingConfirm}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={submitConfirmModal}
                disabled={submittingConfirm}
                className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
              >
                {submittingConfirm ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                <span>Confirm Entry</span>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 2: OUT Planning Record Modal (Add / Edit) ─────────── */}
      {isOutModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden max-h-[90vh] flex flex-col">
            <div className="p-5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ArrowUpRight className="h-5 w-5 text-rose-600" />
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  {editingOutId ? "Edit OUT Planning Record" : "Add OUT Planning Record"}
                </h3>
              </div>
              <button
                onClick={() => setIsOutModalOpen(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Date *
                  </Label>
                  <Input
                    type="date"
                    value={outFormDate}
                    onChange={(e) => setOutFormDate(e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Estimated Amount (₹) *
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={outFormAmt}
                    onChange={(e) => setOutFormAmt(e.target.value)}
                    className="h-9 text-sm font-mono font-semibold"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Description *
                </Label>
                <Input
                  placeholder="e.g. Spare parts procurement, emergency repairs, travel..."
                  value={outFormDesc}
                  onChange={(e) => setOutFormDesc(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Party / Payee <span className="text-zinc-400 text-[10px] font-normal">(Optional)</span>
                  </Label>
                  <Input
                    placeholder="Vendor / payee name"
                    value={outFormParty}
                    onChange={(e) => setOutFormParty(e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Account <span className="text-zinc-400 text-[10px] font-normal">(Optional)</span>
                  </Label>
                  <Input
                    placeholder="Account name"
                    value={outFormAcct}
                    onChange={(e) => setOutFormAcct(e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Company
                </Label>
                <select
                  value={outFormCompanyId}
                  onChange={(e) => setOutFormCompanyId(e.target.value)}
                  className="w-full h-9 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-3 text-sm text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                >
                  <option value="">Select Company</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name || `Company #${c.id}`}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Notes
                </Label>
                <Textarea
                  rows={2}
                  placeholder="Additional context or notes..."
                  value={outFormNotes}
                  onChange={(e) => setOutFormNotes(e.target.value)}
                  className="text-sm"
                />
              </div>

              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2">
                <Info className="h-4 w-4 shrink-0 mt-0.5 text-rose-600" />
                <p>
                  OUT records are <strong>informational only</strong>. They have zero general ledger impact.
                </p>
              </div>
            </div>

            <div className="p-4 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/40 flex items-center justify-end gap-2.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsOutModalOpen(false)}
                disabled={submittingOut}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={saveOutRecord}
                disabled={submittingOut}
                className="bg-rose-600 hover:bg-rose-700 text-white gap-1.5"
              >
                {submittingOut ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                <span>{editingOutId ? "Save Changes" : "Save OUT Record"}</span>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 3: Add Estimate Payment Modal ────────────────────── */}
      {isAddPaymentOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden max-h-[90vh] flex flex-col">
            <div className="p-5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-purple-600" />
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  Record Estimate Payment
                </h3>
              </div>
              <button
                onClick={() => setIsAddPaymentOpen(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Estimated Income Entry *
                </Label>
                <select
                  value={paymentEntryId}
                  onChange={(e) => {
                    setPaymentEntryId(e.target.value);
                    const matched = inEntries.find((ent) => String(ent.id) === e.target.value);
                    if (matched) {
                      setPaymentParty(matched.payer_name || "");
                      setPaymentAmount(String(matched.amount || ""));
                    }
                  }}
                  className="w-full h-9 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-3 text-sm text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all"
                >
                  <option value="">Select an entry</option>
                  {inEntries.map((ent) => (
                    <option key={ent.id} value={ent.id}>
                      {ent.entry_number || `IE-${ent.id}`} - {ent.payer_name || "Unknown"} ({formatCurrency(ent.amount)})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Payment Date *
                  </Label>
                  <Input
                    type="date"
                    value={paymentDate}
                    onChange={(e) => setPaymentDate(e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Payment Amount (₹) *
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    className="h-9 text-sm font-mono font-semibold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Payment Mode
                  </Label>
                  <select
                    value={paymentMode}
                    onChange={(e) => setPaymentMode(e.target.value)}
                    className="w-full h-9 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-3 text-sm text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all"
                  >
                    <option value="UPI">UPI</option>
                    <option value="CASH">Cash</option>
                    <option value="BANK_TRANSFER">Bank Transfer / NEFT</option>
                    <option value="CHEQUE">Cheque</option>
                    <option value="CARD">Debit / Credit Card</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Party Name
                  </Label>
                  <Input
                    placeholder="Customer / payer"
                    value={paymentParty}
                    onChange={(e) => setPaymentParty(e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Account Received <span className="text-zinc-400 text-[10px] font-normal">(Optional)</span>
                </Label>
                <Input
                  placeholder="e.g. Petty Cash, HDFC Current..."
                  value={paymentAccount}
                  onChange={(e) => setPaymentAccount(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Notes
                </Label>
                <Textarea
                  rows={2}
                  placeholder="Reference number or transaction notes..."
                  value={paymentNotes}
                  onChange={(e) => setPaymentNotes(e.target.value)}
                  className="text-sm"
                />
              </div>
            </div>

            <div className="p-4 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/40 flex items-center justify-end gap-2.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddPaymentOpen(false)}
                disabled={submittingPayment}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={saveEstimatePayment}
                disabled={submittingPayment}
                className="bg-purple-600 hover:bg-purple-700 text-white gap-1.5"
              >
                {submittingPayment ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                <span>Save Payment</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EstimationsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
          <div className="flex items-center gap-3 text-zinc-500">
            <RefreshCw className="h-6 w-6 animate-spin text-amber-500" />
            <span className="text-sm font-medium">Loading Estimations Module...</span>
          </div>
        </div>
      }
    >
      <EstimationsContent />
    </Suspense>
  );
}

