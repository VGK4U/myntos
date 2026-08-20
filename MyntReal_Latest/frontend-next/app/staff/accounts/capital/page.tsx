"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { 
  Coins, 
  Building, 
  List, 
  Search, 
  Info, 
  AlertTriangle,
  Link as LinkIcon,
  X
} from "lucide-react";

// Helper function to format currency
const formatCurrency = (amount: number | string) => {
  const val = typeof amount === 'string' ? parseFloat(amount) : amount;
  const num = isNaN(val) ? 0 : val;
  const abs = Math.abs(num);
  const str = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(abs);
  
  if (num < 0) {
    return <span className="text-red-600">({str})</span>;
  }
  return str;
};

const formatDate = (date: Date) => date.toISOString().slice(0, 10);

function CapitalAccountContent() {
  const { token } = useStaffAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL Params context
  const ctxCo = searchParams.get("company_id") || "0";
  const ctxAsOn = searchParams.get("as_on") || searchParams.get("date_to") || searchParams.get("to_date") || "";
  const ctxFrom = searchParams.get("from_date") || searchParams.get("date_from") || "";

  // State
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState("0");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [period, setPeriod] = useState("fy");
  
  const [activeTab, setActiveTab] = useState("summary");

  const [summaryData, setSummaryData] = useState<any[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [txnsData, setTxnsData] = useState<any[]>([]);
  const [txnsLoading, setTxnsLoading] = useState(false);
  const [txnsError, setTxnsError] = useState("");
  const [txnsLoaded, setTxnsLoaded] = useState(false);

  const [showContextBanner, setShowContextBanner] = useState(false);
  const [contextMessage, setContextMessage] = useState("");

  useEffect(() => {
    // Initial load
    fetchCompanies();
    
    // Set context from URL if available
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
      // Default period setup if no context
      handlePeriodSelect("fy");
    }
  }, [ctxCo, ctxAsOn, ctxFrom]);

  // Load summary whenever filters are applied (after initial load state is settled)
  useEffect(() => {
    if (token) {
      loadSummary();
    }
  }, [token]);

  // Switch tabs
  useEffect(() => {
    if (activeTab === "txns" && !txnsLoaded) {
      loadTxns();
    }
  }, [activeTab]);

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
    router.replace("/staff/accounts/capital");
  };

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
    setTxnsLoaded(false); // require reload of txns next time tab is opened
    
    try {
      const qs = buildParams();
      const res = await api.get(`/staff/accounts/capital-summary?${qs}`);
      if (res.data?.success) {
        setSummaryData(res.data.companies || []);
      } else {
        throw new Error(res.data?.detail || "Failed to load summary");
      }
    } catch (err: any) {
      setSummaryError(err.message || "An error occurred");
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
      const res = await api.get(`/staff/accounts/capital-transactions?${qs}`);
      if (res.data?.success) {
        setTxnsData(res.data.transactions || []);
      } else {
        throw new Error(res.data?.detail || "Failed to load transactions");
      }
    } catch (err: any) {
      setTxnsError(err.message || "An error occurred");
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
    handlePeriodSelect("fy");
    // State updates are async, so use timeout to apply after setting
    setTimeout(applyFilters, 0);
  };

  // Calculate totals
  let totalCapital = 0, totalOwners = 0, totalReserves = 0, totalOther = 0;
  summaryData.forEach(co => {
    (co.ledgers || []).forEach((l: any) => {
      const v = parseFloat(l.closing_balance) || 0;
      totalCapital += v;
      const nm = (l.ledger_name || "").toLowerCase();
      if (nm.includes("owner")) totalOwners += v;
      else if (nm.includes("reserve")) totalReserves += v;
      else totalOther += v;
    });
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 tracking-tight">
          <Coins className="h-7 w-7 text-violet-600" />
          Capital Account
        </h1>
        <p className="text-sm text-gray-500">
          Owner's Capital, Reserves & Surplus — Opening Balance + Period Activity = Closing Balance
        </p>
      </div>

      {/* Context Banner */}
      {showContextBanner && (
        <div className="flex items-center justify-between bg-violet-50 border border-violet-200 rounded-lg p-3 text-sm text-violet-800">
          <div className="flex items-center gap-2 font-medium">
            <LinkIcon className="h-4 w-4" />
            {contextMessage}
          </div>
          <button 
            onClick={clearCtx}
            className="flex items-center gap-1 text-violet-700 hover:text-violet-900 text-xs font-semibold"
          >
            <X className="h-3 w-3" /> Clear filter
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Company</label>
          <select 
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm min-w-[180px] bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
          >
            <option value="0">All Companies</option>
            {companies.map(c => (
              <option key={c.id} value={c.id}>{c.company_name || c.name}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Period</label>
          <div className="flex gap-1">
            {[
              { id: "month", label: "This Month" },
              { id: "quarter", label: "This Quarter" },
              { id: "fy", label: "This FY" },
              { id: "overall", label: "Overall" },
              { id: "custom", label: "Custom" }
            ].map(p => (
              <button
                key={p.id}
                onClick={() => handlePeriodSelect(p.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                  period === p.id 
                    ? "bg-violet-600 text-white border-violet-600 shadow-sm" 
                    : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">From Date</label>
          <input 
            type="date" 
            value={fromDate}
            onChange={(e) => { setFromDate(e.target.value); setPeriod("custom"); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">To Date</label>
          <input 
            type="date" 
            value={toDate}
            onChange={(e) => { setToDate(e.target.value); setPeriod("custom"); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
          />
        </div>

        <div className="flex gap-2">
          <button 
            onClick={applyFilters}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <Search className="h-4 w-4" /> Apply
          </button>
          <button 
            onClick={resetFilters}
            className="px-4 py-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-lg text-sm font-medium transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Accounting Note */}
      <div className="bg-fuchsia-50/50 border border-fuchsia-100 rounded-xl p-4 flex gap-3 text-sm text-fuchsia-800">
        <Info className="h-5 w-5 shrink-0 mt-0.5" />
        <div>
          <strong>Standard Accounting:</strong> Capital is a <em>credit-nature</em> account.
          Closing Balance = Opening Balance + Capital Introduced (Credit) &minus; Drawings / Losses (Debit).
          A positive closing balance means net capital in the business.
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex flex-col gap-1">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Total Capital</span>
          <span className="text-2xl font-bold text-violet-600">{formatCurrency(totalCapital)}</span>
          <span className="text-xs text-gray-400">All companies combined</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex flex-col gap-1">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Owner's Capital</span>
          <span className="text-2xl font-bold text-blue-600">{formatCurrency(totalOwners)}</span>
          <span className="text-xs text-gray-400">Direct capital contributions</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex flex-col gap-1">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Reserves & Surplus</span>
          <span className="text-2xl font-bold text-emerald-600">{formatCurrency(totalReserves)}</span>
          <span className="text-xs text-gray-400">Retained earnings & reserves</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex flex-col gap-1">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Other Capital A/c</span>
          <span className="text-2xl font-bold text-amber-600">{formatCurrency(totalOther)}</span>
          <span className="text-xs text-gray-400">Capital Account entries</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("summary")}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "summary" 
              ? "border-violet-600 text-violet-700" 
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <Building className="h-4 w-4" /> Company-wise Breakdown
        </button>
        <button
          onClick={() => setActiveTab("txns")}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "txns" 
              ? "border-violet-600 text-violet-700" 
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <List className="h-4 w-4" /> Transaction History
        </button>
      </div>

      {/* Tab Contents */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {/* SUMMARY TAB */}
        {activeTab === "summary" && (
          <div>
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <div className="flex items-center gap-2 font-semibold text-gray-800">
                <Coins className="h-4 w-4 text-violet-600" /> Capital Ledger — Company-wise
              </div>
              <div className="text-xs text-gray-500">
                {summaryData.length} {summaryData.length === 1 ? 'company' : 'companies'}
              </div>
            </div>
            
            {summaryLoading ? (
              <div className="flex justify-center items-center p-12 text-gray-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-600"></div>
              </div>
            ) : summaryError ? (
              <div className="p-12 text-center text-red-500">
                <AlertTriangle className="h-10 w-10 mx-auto mb-3 opacity-50" />
                <h4 className="font-semibold text-lg">Error</h4>
                <p className="text-sm">{summaryError}</p>
              </div>
            ) : summaryData.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <Coins className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <h4 className="font-semibold text-gray-600 text-lg">No Capital Account Data</h4>
                <p className="text-sm mt-1">No capital ledgers found for the selected company/period.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100 text-xs font-bold text-gray-500 uppercase tracking-wider">
                      <th className="p-3">Ledger</th>
                      <th className="p-3">Code</th>
                      <th className="p-3 text-right text-sky-700 bg-sky-50/50">Opening Balance</th>
                      <th className="p-3 text-right text-red-700 bg-red-50/50">Period Debit<br/><span className="font-normal normal-case text-[10px] text-red-500">(Drawings/Losses)</span></th>
                      <th className="p-3 text-right text-emerald-700 bg-emerald-50/50">Period Credit<br/><span className="font-normal normal-case text-[10px] text-emerald-500">(Capital Added)</span></th>
                      <th className="p-3 text-right text-violet-700 bg-violet-50/50">Closing Balance</th>
                      <th className="p-3 text-right">Entries</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {summaryData.map((co, idx) => {
                      const ledgers = co.ledgers || [];
                      if (!ledgers.length) return null;
                      
                      let coTotal = 0;
                      return (
                        <React.Fragment key={idx}>
                          <tr className="bg-violet-50/30">
                            <td colSpan={7} className="p-2 px-4 font-bold text-violet-900 text-xs flex items-center gap-1.5">
                              <Building className="h-3.5 w-3.5 text-violet-600" /> {co.company_name}
                            </td>
                          </tr>
                          {ledgers.map((l: any, lidx: number) => {
                            const closing = parseFloat(l.closing_balance) || 0;
                            coTotal += closing;
                            const debit = parseFloat(l.period_debit) || 0;
                            const credit = parseFloat(l.period_credit) || 0;
                            return (
                              <tr key={lidx} className="hover:bg-gray-50/80 transition-colors">
                                <td className="p-3 pl-8">
                                  <div className="font-semibold text-gray-800">{l.ledger_name}</div>
                                  {l.parent_group && <div className="text-xs text-gray-400 mt-0.5">{l.parent_group}</div>}
                                </td>
                                <td className="p-3">
                                  <span className="bg-gray-100 text-gray-600 font-mono text-[10px] px-2 py-1 rounded font-semibold border border-gray-200">{l.account_code || "—"}</span>
                                </td>
                                <td className="p-3 text-right text-sky-700 font-medium tabular-nums">{formatCurrency(l.opening_balance)}</td>
                                <td className="p-3 text-right tabular-nums">
                                  {debit > 0 ? <span className="text-red-600 font-medium">{formatCurrency(l.period_debit)}</span> : <span className="text-gray-300 italic">—</span>}
                                </td>
                                <td className="p-3 text-right tabular-nums">
                                  {credit > 0 ? <span className="text-emerald-600 font-medium">{formatCurrency(l.period_credit)}</span> : <span className="text-gray-300 italic">—</span>}
                                </td>
                                <td className="p-3 text-right text-violet-700 font-bold tabular-nums bg-violet-50/10">{formatCurrency(l.closing_balance)}</td>
                                <td className="p-3 text-right text-gray-500 tabular-nums">
                                  {l.txn_count > 0 ? l.txn_count : <span className="text-gray-300 italic">—</span>}
                                </td>
                              </tr>
                            );
                          })}
                          <tr className="bg-gray-50 border-t-2 border-gray-200 font-bold">
                            <td colSpan={5} className="p-3 text-right text-gray-600">Total Capital — {co.company_name}</td>
                            <td className="p-3 text-right text-violet-700 bg-violet-50/20 tabular-nums">{formatCurrency(coTotal)}</td>
                            <td></td>
                          </tr>
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TRANSACTIONS TAB */}
        {activeTab === "txns" && (
          <div>
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <div className="flex items-center gap-2 font-semibold text-gray-800">
                <List className="h-4 w-4 text-violet-600" /> Capital Account — Transaction History
              </div>
              <div className="text-xs text-gray-500">
                {txnsData.length} entries
              </div>
            </div>
            
            {txnsLoading ? (
              <div className="flex justify-center items-center p-12 text-gray-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-600"></div>
              </div>
            ) : txnsError ? (
              <div className="p-12 text-center text-red-500">
                <AlertTriangle className="h-10 w-10 mx-auto mb-3 opacity-50" />
                <h4 className="font-semibold text-lg">Error</h4>
                <p className="text-sm">{txnsError}</p>
              </div>
            ) : txnsData.length === 0 ? (
              <div className="p-16 text-center text-gray-400">
                <List className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <h4 className="font-semibold text-gray-600 text-lg">No Transactions Found</h4>
                <p className="text-sm mt-1">No capital account entries in the selected period.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100 text-xs font-bold text-gray-500 uppercase tracking-wider">
                      <th className="p-3 whitespace-nowrap">Date</th>
                      <th className="p-3">Company</th>
                      <th className="p-3">Ledger</th>
                      <th className="p-3">Type</th>
                      <th className="p-3">Voucher / Ref</th>
                      <th className="p-3">Narration / Particulars</th>
                      <th className="p-3 text-right text-red-700">Debit</th>
                      <th className="p-3 text-right text-emerald-700">Credit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {txnsData.map((t, idx) => {
                      const isCredit = t.entry_type === "CREDIT";
                      const debit = parseFloat(t.debit) || 0;
                      const credit = parseFloat(t.credit) || 0;
                      const ref = [t.voucher_type, t.reference_number].filter(Boolean).join(" / ") || "—";
                      const narr = t.narration || t.particulars || "—";
                      
                      return (
                        <tr key={idx} className="hover:bg-gray-50 transition-colors">
                          <td className="p-3 whitespace-nowrap text-gray-600">{t.date}</td>
                          <td className="p-3 text-xs text-gray-500">{t.company_name}</td>
                          <td className="p-3 font-medium text-gray-800">{t.account_name}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${isCredit ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                              {t.entry_type}
                            </span>
                          </td>
                          <td className="p-3 text-xs text-gray-500">{ref}</td>
                          <td className="p-3 text-xs text-gray-600 max-w-[200px] truncate" title={narr}>{narr}</td>
                          <td className="p-3 text-right tabular-nums">
                            {debit > 0 ? <span className="text-red-600 font-medium">{formatCurrency(t.debit)}</span> : <span className="text-gray-300">—</span>}
                          </td>
                          <td className="p-3 text-right tabular-nums">
                            {credit > 0 ? <span className="text-emerald-600 font-medium">{formatCurrency(t.credit)}</span> : <span className="text-gray-300">—</span>}
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
    </div>
  );
}

export default function CapitalAccountPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-gray-400">Loading Page...</div>}>
      <CapitalAccountContent />
    </Suspense>
  );
}
