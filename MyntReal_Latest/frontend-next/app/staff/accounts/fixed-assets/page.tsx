"use client";

import React, { useState, useEffect, useCallback, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import api, { getApiUrl } from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
  Building,
  Building2,
  Layers,
  HardHat,
  Laptop,
  Truck,
  Armchair,
  Home,
  Briefcase,
  Search,
  Plus,
  RefreshCw,
  FileSpreadsheet,
  Download,
  AlertCircle,
  Info,
  Link as LinkIcon,
  X,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Coins
} from "lucide-react";

// Helper function to format INR Currency
const formatCurrency = (amount: number | string, includeSign = false) => {
  const val = typeof amount === "string" ? parseFloat(amount) : amount;
  const num = isNaN(val) ? 0 : val;
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

function fyStart() {
  const t = new Date();
  const y = t.getMonth() >= 3 ? t.getFullYear() : t.getFullYear() - 1;
  return new Date(y, 3, 1);
}
function monthStart() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), 1);
}
function quarterStart() {
  const t = new Date();
  const qm = [0, 0, 0, 3, 3, 3, 6, 6, 6, 9, 9, 9][t.getMonth()];
  return new Date(t.getFullYear(), qm, 1);
}

// Category Icons Mapping
const getCategoryIcon = (category: string) => {
  const cat = category.toLowerCase();
  if (cat.includes("machin") || cat.includes("plant") || cat.includes("tool")) {
    return <HardHat className="w-4 h-4 text-amber-600" />;
  }
  if (cat.includes("it") || cat.includes("computer") || cat.includes("electronic") || cat.includes("laptop")) {
    return <Laptop className="w-4 h-4 text-blue-600" />;
  }
  if (cat.includes("vehicle") || cat.includes("car") || cat.includes("truck") || cat.includes("bike")) {
    return <Truck className="w-4 h-4 text-indigo-600" />;
  }
  if (cat.includes("furniture") || cat.includes("fixture") || cat.includes("desk")) {
    return <Armchair className="w-4 h-4 text-emerald-600" />;
  }
  if (cat.includes("land") || cat.includes("building") || cat.includes("premises") || cat.includes("property")) {
    return <Home className="w-4 h-4 text-purple-600" />;
  }
  return <Briefcase className="w-4 h-4 text-slate-600" />;
};

interface FixedAssetLedger {
  id?: number;
  ledger_name: string;
  account_code: string;
  parent_group: string;
  category?: string;
  description?: string;
  opening_balance: string | number;
  period_debit: string | number;
  period_credit: string | number;
  closing_balance: string | number;
  txn_count: number;
}

interface CompanyFixedAssets {
  company_id: number;
  company_name: string;
  ledgers: FixedAssetLedger[];
  total_fixed_assets: string | number;
  total_additions?: string | number;
  total_depreciation?: string | number;
}

interface FixedAssetTransaction {
  id: number;
  company_id: number;
  company_name: string;
  account_name: string;
  date: string;
  entry_type: string;
  debit: string | number;
  credit: string | number;
  reference_type: string;
  reference_number: string;
  narration: string;
  voucher_type: string;
  particulars: string;
}

function FixedAssetsPageContent() {
  const { token, user } = useStaffAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  // Context passed via URL params (from Balance Sheet or DAR)
  const ctxCo = searchParams.get("company_id") || "0";
  const ctxAsOn = searchParams.get("as_on") || searchParams.get("date_to") || searchParams.get("to_date") || "";
  const ctxFrom = searchParams.get("from_date") || searchParams.get("date_from") || "";

  // State
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState("0");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [period, setPeriod] = useState("fy");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");

  const [activeTab, setActiveTab] = useState("summary");

  // Summary State
  const [summaryCompanies, setSummaryCompanies] = useState<CompanyFixedAssets[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");
  const [totalFixedAssets, setTotalFixedAssets] = useState(0);
  const [totalOpening, setTotalOpening] = useState(0);
  const [totalAdditions, setTotalAdditions] = useState(0);
  const [totalDepreciation, setTotalDepreciation] = useState(0);
  const [categoriesSummary, setCategoriesSummary] = useState<Record<string, number>>({});

  // Transactions State
  const [transactions, setTransactions] = useState<FixedAssetTransaction[]>([]);
  const [txnsLoading, setTxnsLoading] = useState(false);
  const [txnsError, setTxnsError] = useState("");
  const [txnsLoaded, setTxnsLoaded] = useState(false);

  // Context banner
  const [showContextBanner, setShowContextBanner] = useState(false);
  const [contextMessage, setContextMessage] = useState("");

  // Add Asset Dialog Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [modalSubmitting, setModalSubmitting] = useState(false);
  const [modalError, setModalError] = useState("");
  const [modalSuccess, setModalSuccess] = useState("");
  const [newAssetForm, setNewAssetForm] = useState({
    company_id: "1",
    account_name: "",
    account_code: "",
    parent_group: "Fixed Assets",
    category: "Plant & Machinery",
    opening_balance: "0",
    opening_balance_date: formatDate(new Date()),
    description: "",
  });

  // Fetch Companies List
  const fetchCompanies = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      if (res.data && res.data.companies) {
        setCompanies(res.data.companies);
        if (res.data.companies.length > 0 && !newAssetForm.company_id) {
          setNewAssetForm(prev => ({ ...prev, company_id: String(res.data.companies[0].id) }));
        }
      }
    } catch (err: any) {
      console.error("Failed to load companies:", err);
    }
  }, []);

  // Handle Quick Period Selection
  const handlePeriodSelect = (p: string) => {
    setPeriod(p);
    const today = new Date();
    const to = formatDate(today);
    if (p === "month") {
      setFromDate(formatDate(monthStart()));
      setToDate(to);
    } else if (p === "quarter") {
      setFromDate(formatDate(quarterStart()));
      setToDate(to);
    } else if (p === "fy") {
      setFromDate(formatDate(fyStart()));
      setToDate(to);
    } else if (p === "overall") {
      setFromDate("");
      setToDate(to);
    }
  };

  // Initialize context & load companies
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
      setContextMessage(`Filtered from Consolidated Balance Sheet / DAR — ${parts.join(", ")}`);
    } else {
      handlePeriodSelect("fy");
    }
  }, [ctxCo, ctxAsOn, ctxFrom, fetchCompanies]);

  // Load Fixed Assets Summary
  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError("");
    try {
      const params = new URLSearchParams();
      if (selectedCompany && selectedCompany !== "0") params.set("company_id", selectedCompany);
      if (fromDate) params.set("from_date", fromDate);
      if (toDate) params.set("to_date", toDate);

      const res = await api.get(`/staff/accounts/fixed-assets-summary?${params.toString()}`);
      if (res.data && res.data.success) {
        const cos: CompanyFixedAssets[] = res.data.companies || [];
        setSummaryCompanies(cos);
        setTotalFixedAssets(parseFloat(res.data.total_fixed_assets) || 0);
        setTotalOpening(parseFloat(res.data.total_opening) || 0);
        setTotalAdditions(parseFloat(res.data.total_additions) || 0);
        setTotalDepreciation(parseFloat(res.data.total_depreciation) || 0);

        if (res.data.categories) {
          const catsObj: Record<string, number> = {};
          Object.entries(res.data.categories).forEach(([k, v]) => {
            catsObj[k] = parseFloat(v as string) || 0;
          });
          setCategoriesSummary(catsObj);
        }
      } else {
        throw new Error(res.data?.detail || "Failed to load summary");
      }
    } catch (err: any) {
      console.error("Summary load error:", err);
      setSummaryError(err.response?.data?.detail || err.message || "Failed to load fixed assets summary data.");
    } finally {
      setSummaryLoading(false);
    }
  }, [selectedCompany, fromDate, toDate]);

  // Load Fixed Assets Transactions
  const loadTransactions = useCallback(async () => {
    setTxnsLoading(true);
    setTxnsError("");
    try {
      const params = new URLSearchParams();
      if (selectedCompany && selectedCompany !== "0") params.set("company_id", selectedCompany);
      if (fromDate) params.set("from_date", fromDate);
      if (toDate) params.set("to_date", toDate);

      const res = await api.get(`/staff/accounts/fixed-assets-transactions?${params.toString()}`);
      if (res.data && res.data.success) {
        setTransactions(res.data.transactions || []);
        setTxnsLoaded(true);
      } else {
        throw new Error(res.data?.detail || "Failed to load transactions");
      }
    } catch (err: any) {
      console.error("Transactions load error:", err);
      setTxnsError(err.response?.data?.detail || err.message || "Failed to load fixed asset transaction entries.");
    } finally {
      setTxnsLoading(false);
    }
  }, [selectedCompany, fromDate, toDate]);

  // Trigger loads when filters or tabs change
  useEffect(() => {
    loadSummary();
    if (activeTab === "txns" || activeTab === "all") {
      loadTransactions();
    }
  }, [loadSummary, activeTab]);

  const handleTabChange = (t: string) => {
    setActiveTab(t);
    if (t === "txns" && !txnsLoaded) {
      loadTransactions();
    }
  };

  const handleApplyFilters = () => {
    setTxnsLoaded(false);
    loadSummary();
    if (activeTab === "txns") {
      loadTransactions();
    }
  };

  const handleResetFilters = () => {
    setSelectedCompany("0");
    setCategoryFilter("ALL");
    setSearchQuery("");
    setShowContextBanner(false);
    handlePeriodSelect("fy");
    router.replace(window.location.pathname);
  };

  const clearCtx = () => {
    setShowContextBanner(false);
    setSelectedCompany("0");
    handlePeriodSelect("fy");
    router.replace(window.location.pathname);
  };

  // Submit Create New Asset Ledger Master
  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError("");
    setModalSuccess("");

    if (!newAssetForm.account_name.trim()) {
      setModalError("Please enter an Asset Name.");
      return;
    }

    setModalSubmitting(true);
    try {
      const payload = {
        company_id: parseInt(newAssetForm.company_id, 10),
        account_type: "ASSET",
        account_name: newAssetForm.account_name.trim(),
        account_code: newAssetForm.account_code.trim() || undefined,
        parent_group: newAssetForm.parent_group || "Fixed Assets",
        description: newAssetForm.description.trim() || `${newAssetForm.category} asset record`,
        opening_balance: parseFloat(newAssetForm.opening_balance) || 0,
        opening_balance_type: "DEBIT",
        opening_balance_date: newAssetForm.opening_balance_date || undefined,
      };

      const res = await api.post("/staff/accounts/ledger-masters", payload);
      if (res.data && res.data.success) {
        setModalSuccess(`Asset "${newAssetForm.account_name}" successfully registered!`);
        setTimeout(() => {
          setIsAddModalOpen(false);
          setModalSuccess("");
          setNewAssetForm({
            company_id: companies[0]?.id ? String(companies[0].id) : "1",
            account_name: "",
            account_code: "",
            parent_group: "Fixed Assets",
            category: "Plant & Machinery",
            opening_balance: "0",
            opening_balance_date: formatDate(new Date()),
            description: "",
          });
          loadSummary();
        }, 1200);
      } else {
        throw new Error(res.data?.detail || "Failed to create fixed asset ledger");
      }
    } catch (err: any) {
      console.error("Create asset error:", err);
      setModalError(err.response?.data?.detail || err.message || "Failed to create fixed asset.");
    } finally {
      setModalSubmitting(false);
    }
  };

  // Filtered Summary Ledgers (Search + Category Filter)
  const filteredCompanies = useMemo(() => {
    return summaryCompanies.map(co => {
      const filteredLedgers = (co.ledgers || []).filter(l => {
        const matchesSearch =
          searchQuery.trim() === "" ||
          l.ledger_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          l.account_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (l.parent_group && l.parent_group.toLowerCase().includes(searchQuery.toLowerCase()));

        const matchesCat =
          categoryFilter === "ALL" ||
          (l.category && l.category.toLowerCase() === categoryFilter.toLowerCase());

        return matchesSearch && matchesCat;
      });

      const coTotal = filteredLedgers.reduce((acc, curr) => acc + (parseFloat(String(curr.closing_balance)) || 0), 0);

      return {
        ...co,
        ledgers: filteredLedgers,
        filteredTotal: coTotal,
      };
    }).filter(co => co.ledgers.length > 0 || searchQuery === "");
  }, [summaryCompanies, searchQuery, categoryFilter]);

  // Filtered Transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter(t => {
      const matchesSearch =
        searchQuery.trim() === "" ||
        t.account_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.reference_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.narration && t.narration.toLowerCase().includes(searchQuery.toLowerCase()));

      return matchesSearch;
    });
  }, [transactions, searchQuery]);

  // Export CSV functionality
  const handleExportCSV = () => {
    const rows = [
      ["Company", "Asset Name", "Code", "Parent Group", "Category", "Opening Balance", "Additions (Dr)", "Depreciation/Disposal (Cr)", "Closing Book Value", "Entries Count"]
    ];

    summaryCompanies.forEach(co => {
      (co.ledgers || []).forEach(l => {
        rows.push([
          `"${co.company_name}"`,
          `"${l.ledger_name}"`,
          `"${l.account_code || ''}"`,
          `"${l.parent_group || ''}"`,
          `"${l.category || ''}"`,
          String(l.opening_balance),
          String(l.period_debit),
          String(l.period_credit),
          String(l.closing_balance),
          String(l.txn_count)
        ]);
      });
    });

    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Fixed_Assets_Register_${formatDate(new Date())}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-slate-50/60 pb-16">
      {/* Enterprise Top Navbar / Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-xl flex items-center justify-center shadow-sm ring-4 ring-indigo-50">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Fixed Assets</h1>
                  <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 font-semibold text-xs">
                    Asset Register (Debit)
                  </Badge>
                </div>
                <p className="text-xs sm:text-sm text-slate-500 font-normal mt-0.5">
                  Plant &amp; Machinery, IT Equipment, Furniture, Vehicles &amp; Accumulated Depreciation
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={handleApplyFilters}
                disabled={summaryLoading}
                className="text-slate-700 hover:bg-slate-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${summaryLoading ? "animate-spin" : ""}`} />
                Refresh
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleExportCSV}
                className="text-slate-700 hover:bg-slate-50"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                Export Register
              </Button>

              <Link href="/staff/accounts/journal-voucher">
                <Button variant="outline" size="sm" className="text-indigo-700 border-indigo-200 hover:bg-indigo-50">
                  <Coins className="w-3.5 h-3.5 mr-1.5" />
                  Record Journal
                </Button>
              </Link>

              <Button
                size="sm"
                onClick={() => setIsAddModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs font-medium"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Add Fixed Asset
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Context Drill-Through Banner */}
        {showContextBanner && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3.5 px-4.5 flex items-center justify-between gap-3 text-indigo-900 shadow-xs animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="flex items-center gap-2.5 text-xs sm:text-sm font-medium">
              <LinkIcon className="w-4 h-4 text-indigo-600 shrink-0" />
              <span>{contextMessage}</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearCtx}
              className="text-indigo-700 hover:text-indigo-900 hover:bg-indigo-100/60 h-7 px-2 text-xs font-semibold"
            >
              <X className="w-3.5 h-3.5 mr-1" />
              Clear Filter
            </Button>
          </div>
        )}

        {/* Filter Card */}
        <Card className="shadow-xs border-slate-200 bg-white">
          <CardContent className="p-4 sm:p-5">
            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3.5 flex-1">
                {/* Company Selector */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                    Company
                  </label>
                  <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                    <SelectTrigger className="w-full h-9 text-xs sm:text-sm bg-white border-slate-200">
                      <SelectValue placeholder="All Companies" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">All Associated Companies</SelectItem>
                      {companies.map(c => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.company_name || c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Period Presets */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                    Preset Period
                  </label>
                  <div className="flex gap-1 p-0.5 bg-slate-100 rounded-lg border border-slate-200">
                    <button
                      type="button"
                      onClick={() => handlePeriodSelect("month")}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                        period === "month" ? "bg-white text-indigo-700 font-semibold shadow-xs" : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      Month
                    </button>
                    <button
                      type="button"
                      onClick={() => handlePeriodSelect("quarter")}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                        period === "quarter" ? "bg-white text-indigo-700 font-semibold shadow-xs" : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      Quarter
                    </button>
                    <button
                      type="button"
                      onClick={() => handlePeriodSelect("fy")}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                        period === "fy" ? "bg-white text-indigo-700 font-semibold shadow-xs" : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      This FY
                    </button>
                    <button
                      type="button"
                      onClick={() => handlePeriodSelect("overall")}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                        period === "overall" ? "bg-white text-indigo-700 font-semibold shadow-xs" : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      All
                    </button>
                  </div>
                </div>

                {/* From Date */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                    From Date
                  </label>
                  <Input
                    type="date"
                    value={fromDate}
                    onChange={e => {
                      setFromDate(e.target.value);
                      setPeriod("custom");
                    }}
                    className="h-9 text-xs sm:text-sm bg-white"
                  />
                </div>

                {/* To Date */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                    To / As On Date
                  </label>
                  <Input
                    type="date"
                    value={toDate}
                    onChange={e => {
                      setToDate(e.target.value);
                      setPeriod("custom");
                    }}
                    className="h-9 text-xs sm:text-sm bg-white"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 self-end">
                <Button
                  onClick={handleApplyFilters}
                  disabled={summaryLoading}
                  className="h-9 bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold px-4 shadow-xs"
                >
                  <Search className="w-3.5 h-3.5 mr-1.5" />
                  Apply Filter
                </Button>
                <Button
                  variant="outline"
                  onClick={handleResetFilters}
                  className="h-9 text-slate-600 hover:bg-slate-100 text-xs sm:text-sm"
                >
                  Reset
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Standard Accounting Rule Banner */}
        <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white rounded-xl p-4.5 shadow-xs border border-indigo-700/50 flex items-start gap-3.5">
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0 mt-0.5">
            <Info className="w-4 h-4 text-indigo-300" />
          </div>
          <div className="text-xs sm:text-sm leading-relaxed space-y-1">
            <p className="font-semibold text-indigo-100">
              Standard Double-Entry Accounting — Fixed Assets (Asset / Debit Nature)
            </p>
            <p className="text-indigo-200/90 text-xs">
              <strong>Net Book Value</strong> = Opening Balance (Debit) + Period Additions / Capital Purchases (Debit) &minus; Period Depreciation / Disposals (Credit).
              Reflects the verified carrying cost of all tangible assets on the Consolidated Balance Sheet.
            </p>
          </div>
        </div>

        {/* Top Executive KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Fixed Assets */}
          <Card className="border-indigo-100 bg-white shadow-xs hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-50 rounded-full -mr-8 -mt-8 opacity-60 pointer-events-none" />
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Net Book Value</span>
                <span className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg">
                  <Building className="w-4 h-4" />
                </span>
              </div>
              <div className="mt-2.5">
                <div className="text-2xl sm:text-3xl font-extrabold text-indigo-600 tracking-tight">
                  {formatCurrency(totalFixedAssets)}
                </div>
                <div className="text-xs text-slate-400 mt-1 font-medium flex items-center gap-1.5">
                  <span className="text-indigo-600 font-semibold">{summaryCompanies.length}</span> companies combined
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Period Additions (Debits) */}
          <Card className="border-emerald-100 bg-white shadow-xs hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-50 rounded-full -mr-8 -mt-8 opacity-60 pointer-events-none" />
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Period Additions (Dr)</span>
                <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg">
                  <ArrowUpRight className="w-4 h-4" />
                </span>
              </div>
              <div className="mt-2.5">
                <div className="text-2xl sm:text-3xl font-extrabold text-emerald-600 tracking-tight">
                  {formatCurrency(totalAdditions)}
                </div>
                <div className="text-xs text-emerald-700 mt-1 font-medium">
                  Capital equipment &amp; purchases added
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Period Depreciation / Disposals (Credits) */}
          <Card className="border-rose-100 bg-white shadow-xs hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-rose-50 rounded-full -mr-8 -mt-8 opacity-60 pointer-events-none" />
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Depreciation / Write-offs (Cr)</span>
                <span className="p-1.5 bg-rose-50 text-rose-600 rounded-lg">
                  <ArrowDownRight className="w-4 h-4" />
                </span>
              </div>
              <div className="mt-2.5">
                <div className="text-2xl sm:text-3xl font-extrabold text-rose-600 tracking-tight">
                  {formatCurrency(totalDepreciation)}
                </div>
                <div className="text-xs text-rose-700 mt-1 font-medium">
                  Period depreciation / disposal credits
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Opening Carrying Value */}
          <Card className="border-slate-200 bg-white shadow-xs hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-slate-100 rounded-full -mr-8 -mt-8 opacity-60 pointer-events-none" />
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Opening Balance (OB)</span>
                <span className="p-1.5 bg-slate-100 text-slate-600 rounded-lg">
                  <Calendar className="w-4 h-4" />
                </span>
              </div>
              <div className="mt-2.5">
                <div className="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">
                  {formatCurrency(totalOpening)}
                </div>
                <div className="text-xs text-slate-500 mt-1 font-medium">
                  Carrying value at period start
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Category Pills Breakdown */}
        {Object.keys(categoriesSummary).length > 0 && (
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5 flex items-center justify-between">
              <span>Asset Category Distribution</span>
              <span className="text-slate-400 font-normal">Click category to filter register</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setCategoryFilter("ALL")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                  categoryFilter === "ALL"
                    ? "bg-slate-900 text-white border-slate-900 shadow-xs"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                All Categories ({summaryCompanies.reduce((acc, c) => acc + (c.ledgers?.length || 0), 0)})
              </button>
              {Object.entries(categoriesSummary).map(([catName, val]) => (
                <button
                  key={catName}
                  type="button"
                  onClick={() => setCategoryFilter(catName)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                    categoryFilter.toLowerCase() === catName.toLowerCase()
                      ? "bg-indigo-600 text-white border-indigo-600 shadow-xs font-semibold"
                      : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {getCategoryIcon(catName)}
                  <span>{catName}:</span>
                  <span className="font-bold">{formatCurrency(val)}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Search & Tabs Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full sm:w-auto">
            <TabsList className="bg-slate-100 p-1 rounded-lg">
              <TabsTrigger value="summary" className="data-[state=active]:bg-white data-[state=active]:text-indigo-700 text-xs sm:text-sm font-semibold">
                <Building className="w-4 h-4 mr-1.5" />
                Asset Register &amp; Ledger Summary
              </TabsTrigger>
              <TabsTrigger value="txns" className="data-[state=active]:bg-white data-[state=active]:text-indigo-700 text-xs sm:text-sm font-semibold">
                <Coins className="w-4 h-4 mr-1.5" />
                Transaction History ({transactions.length})
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <Input
              placeholder="Search asset, code, group..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-9 h-9 text-xs sm:text-sm bg-white border-slate-200"
            />
          </div>
        </div>

        {/* TAB 1: ASSET REGISTER / COMPANY SUMMARY */}
        {activeTab === "summary" && (
          <div className="space-y-4">
            {summaryLoading ? (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center space-y-3">
                <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
                <p className="text-slate-600 text-sm font-medium">Loading Fixed Asset register data...</p>
              </div>
            ) : summaryError ? (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-6 text-center space-y-2">
                <AlertCircle className="w-8 h-8 text-rose-600 mx-auto" />
                <h3 className="font-bold text-base">Error Loading Fixed Assets</h3>
                <p className="text-sm text-rose-700 max-w-md mx-auto">{summaryError}</p>
                <Button variant="outline" size="sm" onClick={loadSummary} className="mt-2">
                  Retry Loading
                </Button>
              </div>
            ) : filteredCompanies.length === 0 ? (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center space-y-4">
                <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto">
                  <HardHat className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">No Fixed Assets Found</h3>
                  <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
                    No active fixed asset accounts matched the selected company and filter criteria.
                  </p>
                </div>
                <Button onClick={() => setIsAddModalOpen(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                  <Plus className="w-4 h-4 mr-1.5" />
                  Add First Fixed Asset
                </Button>
              </div>
            ) : (
              <div className="space-y-5">
                {filteredCompanies.map(co => (
                  <Card key={co.company_id} className="border-slate-200 shadow-xs bg-white overflow-hidden">
                    <CardHeader className="bg-slate-50/80 border-b border-slate-200 py-3.5 px-5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <Building className="w-4 h-4 text-indigo-600 shrink-0" />
                          <CardTitle className="text-sm sm:text-base font-bold text-slate-900">
                            {co.company_name}
                          </CardTitle>
                          <Badge variant="secondary" className="text-xs bg-indigo-50 text-indigo-700 border-indigo-100">
                            {co.ledgers.length} {co.ledgers.length === 1 ? "Asset Ledger" : "Asset Ledgers"}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-xs font-semibold">
                          <span className="text-slate-500">
                            Company Total: <strong className="text-indigo-700 text-sm font-bold ml-1">{formatCurrency(co.total_fixed_assets)}</strong>
                          </span>
                        </div>
                      </div>
                    </CardHeader>

                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-slate-50/40 text-xs uppercase font-bold text-slate-600 border-b border-slate-200">
                            <TableHead className="font-bold py-3">Asset Ledger</TableHead>
                            <TableHead className="font-bold py-3">Code / Group</TableHead>
                            <TableHead className="font-bold py-3">Category</TableHead>
                            <TableHead className="font-bold py-3 text-right text-sky-800 bg-sky-50/50">
                              Opening Balance (Dr)
                            </TableHead>
                            <TableHead className="font-bold py-3 text-right text-emerald-800 bg-emerald-50/50">
                              Additions / Purchases (Dr)
                            </TableHead>
                            <TableHead className="font-bold py-3 text-right text-rose-800 bg-rose-50/50">
                              Depreciation / Write-off (Cr)
                            </TableHead>
                            <TableHead className="font-bold py-3 text-right text-indigo-900 bg-indigo-50/60">
                              Closing Book Value
                            </TableHead>
                            <TableHead className="font-bold py-3 text-center">Entries</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-slate-100 text-xs sm:text-sm">
                          {co.ledgers.map((l, idx) => {
                            const hasActivity = parseFloat(String(l.period_debit)) > 0 || parseFloat(String(l.period_credit)) > 0;
                            return (
                              <TableRow key={l.id || idx} className="hover:bg-slate-50/80 transition-colors">
                                <TableCell className="font-medium text-slate-900">
                                  <div className="flex items-center gap-2">
                                    <span className="p-1 rounded bg-slate-100 text-slate-600">
                                      {getCategoryIcon(l.category || l.parent_group)}
                                    </span>
                                    <div>
                                      <div className="font-semibold text-slate-900">{l.ledger_name}</div>
                                      {l.description && (
                                        <div className="text-xs text-slate-400 line-clamp-1">{l.description}</div>
                                      )}
                                    </div>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="space-y-0.5">
                                    <Badge variant="outline" className="font-mono text-[11px] bg-slate-50 text-slate-700 border-slate-200">
                                      {l.account_code || "FA-3001"}
                                    </Badge>
                                    <div className="text-[11px] text-slate-400">{l.parent_group || "Fixed Assets"}</div>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Badge variant="secondary" className="text-[11px] bg-slate-100 text-slate-700 font-medium">
                                    {l.category || "Fixed Asset"}
                                  </Badge>
                                </TableCell>
                                <TableCell className="text-right font-medium text-sky-700">
                                  {formatCurrency(l.opening_balance)}
                                </TableCell>
                                <TableCell className="text-right font-medium text-emerald-600">
                                  {parseFloat(String(l.period_debit)) > 0 ? (
                                    formatCurrency(l.period_debit)
                                  ) : (
                                    <span className="text-slate-300">—</span>
                                  )}
                                </TableCell>
                                <TableCell className="text-right font-medium text-rose-600">
                                  {parseFloat(String(l.period_credit)) > 0 ? (
                                    formatCurrency(l.period_credit)
                                  ) : (
                                    <span className="text-slate-300">—</span>
                                  )}
                                </TableCell>
                                <TableCell className="text-right font-bold text-indigo-700 bg-indigo-50/20">
                                  {formatCurrency(l.closing_balance)}
                                </TableCell>
                                <TableCell className="text-center">
                                  {l.txn_count > 0 ? (
                                    <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 text-xs font-semibold">
                                      {l.txn_count}
                                    </Badge>
                                  ) : (
                                    <span className="text-slate-300 text-xs">0</span>
                                  )}
                                </TableCell>
                              </TableRow>
                            );
                          })}
                          {/* Company Subtotal Footer Row */}
                          <TableRow className="bg-slate-50 font-bold border-t-2 border-slate-200 text-xs sm:text-sm">
                            <TableCell colSpan={3} className="text-right py-3 pr-4 text-slate-700">
                              Subtotal — {co.company_name}
                            </TableCell>
                            <TableCell className="text-right text-sky-800 py-3">
                              {formatCurrency(co.ledgers.reduce((sum, item) => sum + (parseFloat(String(item.opening_balance)) || 0), 0))}
                            </TableCell>
                            <TableCell className="text-right text-emerald-700 py-3">
                              {formatCurrency(co.ledgers.reduce((sum, item) => sum + (parseFloat(String(item.period_debit)) || 0), 0))}
                            </TableCell>
                            <TableCell className="text-right text-rose-700 py-3">
                              {formatCurrency(co.ledgers.reduce((sum, item) => sum + (parseFloat(String(item.period_credit)) || 0), 0))}
                            </TableCell>
                            <TableCell className="text-right text-indigo-700 font-extrabold py-3 bg-indigo-50/40">
                              {formatCurrency(co.total_fixed_assets)}
                            </TableCell>
                            <TableCell className="text-center py-3 text-slate-500">
                              {co.ledgers.reduce((sum, item) => sum + (item.txn_count || 0), 0)} txns
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </div>
                  </Card>
                ))}

                {/* Grand Consolidated Summary Footer Card */}
                <Card className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white border-0 shadow-md">
                  <CardContent className="p-5">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <div className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                          Consolidated Balance Sheet Position
                        </div>
                        <div className="text-xl sm:text-2xl font-black text-white mt-1">
                          Total Fixed Assets: {formatCurrency(totalFixedAssets)}
                        </div>
                      </div>
                      <div className="flex items-center gap-6 text-xs sm:text-sm">
                        <div>
                          <div className="text-slate-400">Total Additions</div>
                          <div className="font-bold text-emerald-400 text-base">{formatCurrency(totalAdditions)}</div>
                        </div>
                        <div>
                          <div className="text-slate-400">Total Depreciation</div>
                          <div className="font-bold text-rose-400 text-base">{formatCurrency(totalDepreciation)}</div>
                        </div>
                        <div>
                          <div className="text-slate-400">Net Carrying Value</div>
                          <div className="font-bold text-indigo-300 text-base">{formatCurrency(totalFixedAssets)}</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: TRANSACTION HISTORY */}
        {activeTab === "txns" && (
          <Card className="border-slate-200 shadow-xs bg-white">
            <CardHeader className="py-4 px-5 border-b border-slate-200 bg-slate-50/60">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-base font-bold text-slate-900">
                    Fixed Asset Transactions Audit Trail
                  </CardTitle>
                  <CardDescription className="text-xs text-slate-500">
                    Chronological journal entries, capital asset purchases, and depreciation postings
                  </CardDescription>
                </div>
                <Badge variant="outline" className="text-xs bg-indigo-50 text-indigo-700 border-indigo-200">
                  {filteredTransactions.length} {filteredTransactions.length === 1 ? "entry" : "entries"}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              {txnsLoading ? (
                <div className="p-12 text-center space-y-3">
                  <RefreshCw className="w-7 h-7 text-indigo-600 animate-spin mx-auto" />
                  <p className="text-slate-600 text-sm">Fetching fixed asset transaction journal entries...</p>
                </div>
              ) : txnsError ? (
                <div className="p-8 text-center text-rose-600 space-y-2">
                  <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
                  <p className="text-sm font-semibold">{txnsError}</p>
                </div>
              ) : filteredTransactions.length === 0 ? (
                <div className="p-12 text-center space-y-3 text-slate-500">
                  <Coins className="w-10 h-10 text-slate-300 mx-auto" />
                  <h4 className="font-bold text-slate-700">No Fixed Asset Transactions Found</h4>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    No debit/credit postings found in account_ledger for the selected period.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50/70 text-xs uppercase font-bold text-slate-600">
                        <TableHead className="py-3">Date</TableHead>
                        <TableHead className="py-3">Company</TableHead>
                        <TableHead className="py-3">Asset Ledger</TableHead>
                        <TableHead className="py-3">Type</TableHead>
                        <TableHead className="py-3">Voucher / Ref</TableHead>
                        <TableHead className="py-3">Particulars &amp; Narration</TableHead>
                        <TableHead className="py-3 text-right text-emerald-700">Debit (Addition)</TableHead>
                        <TableHead className="py-3 text-right text-rose-700">Credit (Deprec/Disposal)</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="divide-y divide-slate-100 text-xs sm:text-sm">
                      {filteredTransactions.map(txn => {
                        const isDebit = txn.entry_type === "DEBIT" || parseFloat(String(txn.debit)) > 0;
                        const ref = [txn.voucher_type, txn.reference_number].filter(Boolean).join(" / ") || "—";
                        const narr = txn.narration || txn.particulars || "—";

                        return (
                          <TableRow key={txn.id} className="hover:bg-slate-50/70 transition-colors">
                            <TableCell className="font-medium whitespace-nowrap text-slate-800">
                              {txn.date}
                            </TableCell>
                            <TableCell className="whitespace-nowrap text-xs text-slate-600">
                              {txn.company_name}
                            </TableCell>
                            <TableCell className="font-semibold text-slate-900">
                              {txn.account_name}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant="outline"
                                className={`text-[11px] font-bold ${
                                  isDebit
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : "bg-rose-50 text-rose-700 border-rose-200"
                                }`}
                              >
                                {txn.entry_type || (isDebit ? "DEBIT" : "CREDIT")}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs text-slate-500 font-mono">
                              {ref}
                            </TableCell>
                            <TableCell className="text-xs text-slate-600 max-w-xs truncate" title={narr}>
                              {narr}
                            </TableCell>
                            <TableCell className="text-right font-semibold text-emerald-600">
                              {parseFloat(String(txn.debit)) > 0 ? formatCurrency(txn.debit) : <span className="text-slate-300">—</span>}
                            </TableCell>
                            <TableCell className="text-right font-semibold text-rose-600">
                              {parseFloat(String(txn.credit)) > 0 ? formatCurrency(txn.credit) : <span className="text-slate-300">—</span>}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* MODAL DIALOG: ADD FIXED ASSET */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="sm:max-w-lg bg-white">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-indigo-600" />
              Register New Fixed Asset
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Create a new Fixed Asset ledger master in the Chart of Accounts (Debit-nature asset).
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateAsset} className="space-y-4 pt-2">
            {modalError && (
              <div className="bg-rose-50 border border-rose-200 text-rose-700 text-xs p-3 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}
            {modalSuccess && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs p-3 rounded-lg flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{modalSuccess}</span>
              </div>
            )}

            {/* Company Selection */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Company <span className="text-rose-500">*</span>
              </label>
              <Select
                value={newAssetForm.company_id}
                onValueChange={v => setNewAssetForm(prev => ({ ...prev, company_id: v }))}
              >
                <SelectTrigger className="w-full h-9 text-xs sm:text-sm bg-white">
                  <SelectValue placeholder="Select Company" />
                </SelectTrigger>
                <SelectContent>
                  {companies.map(c => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.company_name || c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Asset Name */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Asset / Ledger Name <span className="text-rose-500">*</span>
              </label>
              <Input
                placeholder="e.g. Solar Testing Equipment / Office MacBook Pro M3"
                value={newAssetForm.account_name}
                onChange={e => setNewAssetForm(prev => ({ ...prev, account_name: e.target.value }))}
                className="h-9 text-xs sm:text-sm"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* Category */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Asset Category
                </label>
                <Select
                  value={newAssetForm.category}
                  onValueChange={v => setNewAssetForm(prev => ({ ...prev, category: v, parent_group: v }))}
                >
                  <SelectTrigger className="w-full h-9 text-xs sm:text-sm bg-white">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Plant & Machinery">Plant &amp; Machinery</SelectItem>
                    <SelectItem value="IT & Electronics">IT &amp; Electronics</SelectItem>
                    <SelectItem value="Vehicles">Vehicles</SelectItem>
                    <SelectItem value="Furniture & Fixtures">Furniture &amp; Fixtures</SelectItem>
                    <SelectItem value="Office Equipment">Office Equipment</SelectItem>
                    <SelectItem value="Land & Buildings">Land &amp; Buildings</SelectItem>
                    <SelectItem value="Fixed Assets">Other Fixed Asset</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Asset Code */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Account / Asset Code
                </label>
                <Input
                  placeholder="e.g. 3001 or FA-104"
                  value={newAssetForm.account_code}
                  onChange={e => setNewAssetForm(prev => ({ ...prev, account_code: e.target.value }))}
                  className="h-9 text-xs sm:text-sm font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* Opening Balance */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Opening Balance (₹)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={newAssetForm.opening_balance}
                  onChange={e => setNewAssetForm(prev => ({ ...prev, opening_balance: e.target.value }))}
                  className="h-9 text-xs sm:text-sm"
                />
              </div>

              {/* Opening Balance Date */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Opening Date
                </label>
                <Input
                  type="date"
                  value={newAssetForm.opening_balance_date}
                  onChange={e => setNewAssetForm(prev => ({ ...prev, opening_balance_date: e.target.value }))}
                  className="h-9 text-xs sm:text-sm"
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Description / Specifications
              </label>
              <Input
                placeholder="Serial number, make/model, warranty, location..."
                value={newAssetForm.description}
                onChange={e => setNewAssetForm(prev => ({ ...prev, description: e.target.value }))}
                className="h-9 text-xs sm:text-sm"
              />
            </div>

            <DialogFooter className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsAddModalOpen(false)}
                disabled={modalSubmitting}
                className="h-9 text-xs sm:text-sm"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={modalSubmitting}
                className="h-9 bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold shadow-xs"
              >
                {modalSubmitting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    Registering...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-1.5" />
                    Create Asset Ledger
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function FixedAssetsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-12">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
            <p className="text-slate-600 text-sm font-medium">Loading Fixed Assets Module...</p>
          </div>
        </div>
      }
    >
      <FixedAssetsPageContent />
    </Suspense>
  );
}
