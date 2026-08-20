"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import {
  Wallet,
  Filter,
  RefreshCw,
  Info,
  Building2,
  List,
  ArrowDown,
  ArrowUp,
  User,
  Book,
  AlertTriangle
} from "lucide-react";
import { format } from "date-fns";

import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Company {
  id: string | number;
  company_name?: string;
  name?: string;
}

interface SummaryData {
  company_name: string;
  cash_receipts: number | string;
  cash_payments: number | string;
  fund_float: number | string;
  ledger_net: number | string;
  net_cash_in_hand: number | string;
  cash_receipts_cnt: number;
  cash_payments_cnt: number;
  fund_float_cnt: number;
  fund_allocated: number | string;
}

interface SummaryResponse {
  success: boolean;
  total_cash: number;
  total_receipts: number;
  total_payments: number;
  total_fund_float: number;
  companies: SummaryData[];
}

interface TransactionData {
  date: string;
  company_name: string;
  source: string;
  txn_type: string;
  party: string;
  ref_number: string;
  narration: string;
  receipt: number | string;
  payment: number | string;
  status: string;
}

const SOURCE_LABELS: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
  INCOME: { label: "Cash Income", cls: "bg-emerald-100 text-emerald-700", icon: <ArrowDown className="w-3 h-3 mr-1" /> },
  EXPENSE: { label: "Cash Expense", cls: "bg-red-100 text-red-700", icon: <ArrowUp className="w-3 h-3 mr-1" /> },
  FUND_ALLOC: { label: "Staff Float", cls: "bg-purple-100 text-purple-700", icon: <User className="w-3 h-3 mr-1" /> },
  LEDGER: { label: "Ledger Entry", cls: "bg-gray-100 text-gray-700", icon: <Book className="w-3 h-3 mr-1" /> },
};

const R = (n: number | string) => {
  const v = parseFloat(String(n)) || 0;
  const abs = Math.abs(v);
  const str = '₹' + abs.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (v < 0) {
    return <span className="text-red-600">({str})</span>;
  }
  return str;
};

export default function CashInHandPage() {
  const { isAuthenticated, isLoading: authLoading } = useStaffAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [companies, setCompanies] = useState<Company[]>([]);
  const [filterCompany, setFilterCompany] = useState<string>(searchParams.get("company_id") || "0");
  const [filterFrom, setFilterFrom] = useState<string>(searchParams.get("from_date") || searchParams.get("date_from") || "");
  const [filterTo, setFilterTo] = useState<string>(searchParams.get("as_on") || searchParams.get("date_to") || searchParams.get("to_date") || "");

  const [summaryData, setSummaryData] = useState<SummaryResponse | null>(null);
  const [txnsData, setTxnsData] = useState<TransactionData[]>([]);
  
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [isLoadingTxns, setIsLoadingTxns] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [txnsError, setTxnsError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState("summary");

  const loadCompanies = async () => {
    try {
      const { data } = await api.get("/staff/accounts/companies");
      setCompanies(data?.companies || []);
    } catch (err) {
      console.error("Failed to load companies", err);
    }
  };

  const getFilterParams = useCallback(() => {
    const params: Record<string, string> = {};
    if (filterCompany && filterCompany !== "0") params.company_id = filterCompany;
    if (filterFrom) params.from_date = filterFrom;
    if (filterTo) params.to_date = filterTo;
    return params;
  }, [filterCompany, filterFrom, filterTo]);

  const loadSummary = useCallback(async () => {
    setIsLoadingSummary(true);
    setSummaryError(null);
    try {
      const { data } = await api.get("/staff/accounts/cash-in-hand-summary", { params: getFilterParams() });
      if (!data.success) throw new Error(data.detail || "Failed to load summary");
      setSummaryData(data);
    } catch (err: unknown) {
      setSummaryError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoadingSummary(false);
    }
  }, [getFilterParams]);

  const loadTxns = useCallback(async () => {
    setIsLoadingTxns(true);
    setTxnsError(null);
    try {
      const { data } = await api.get("/staff/accounts/cash-in-hand-transactions", { params: getFilterParams() });
      if (!data.success) throw new Error(data.detail || "Failed to load transactions");
      setTxnsData(data.transactions || []);
    } catch (err: unknown) {
      setTxnsError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoadingTxns(false);
    }
  }, [getFilterParams]);

  const applyFilters = () => {
    loadSummary();
    if (activeTab === "txns") {
      loadTxns();
    }
  };

  const setPeriod = (period: string) => {
    const to = format(new Date(), "yyyy-MM-dd");
    const t = new Date();
    let from = "";
    if (period === "month") {
      from = format(new Date(t.getFullYear(), t.getMonth(), 1), "yyyy-MM-dd");
    } else if (period === "quarter") {
      const qm = [0, 0, 0, 3, 3, 3, 6, 6, 6, 9, 9, 9][t.getMonth()];
      from = format(new Date(t.getFullYear(), qm, 1), "yyyy-MM-dd");
    } else if (period === "fy") {
      const y = t.getMonth() >= 3 ? t.getFullYear() : t.getFullYear() - 1;
      from = format(new Date(y, 3, 1), "yyyy-MM-dd");
    }
    setFilterFrom(from);
    setFilterTo(to);
  };

  const resetFilters = () => {
    setFilterCompany("0");
    setPeriod("fy");
    // We will call applyFilters after state updates via useEffect if we want, or just wait for user to click Apply.
  };

  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadCompanies();
      if (!filterFrom && !filterTo) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setPeriod("fy");
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, authLoading]);

  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      applyFilters();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, authLoading]);

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    if (value === "txns" && txnsData.length === 0 && !txnsError) {
      loadTxns();
    }
  };

  const ctxAsOn = searchParams.get("as_on") || searchParams.get("date_to") || searchParams.get("to_date");
  const ctxCo = searchParams.get("company_id");
  const hasContext = ctxAsOn || (ctxCo && ctxCo !== "0");

  const clearCtx = () => {
    setFilterCompany("0");
    setFilterFrom("");
    setFilterTo("");
    router.replace(pathname);
  };

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      {hasContext && (
        <Alert className="bg-sky-50 border-sky-200 text-sky-900 flex items-center justify-between py-2">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4" />
            <AlertDescription className="text-xs">
              Filtered from Consolidated Balance Sheet — {ctxCo && ctxCo !== "0" ? `Company ID: ${ctxCo}` : ""} {ctxAsOn ? `As on: ${ctxAsOn}` : ""}
            </AlertDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={clearCtx} className="text-sky-900 h-6 text-xs">Clear</Button>
        </Alert>
      )}

      <div className="flex justify-between items-start flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Wallet className="text-sky-700 w-6 h-6" />
            Cash in Hand
          </h1>
          <p className="text-sm text-gray-500 mt-1">Consolidated petty cash & field cash balances across all companies — as per accounting books</p>
        </div>
        <Button onClick={applyFilters} className="bg-sky-700 hover:bg-sky-800">
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-4 flex flex-wrap gap-4 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">Company</label>
            <Select value={filterCompany} onValueChange={setFilterCompany}>
              <SelectTrigger className="w-[180px] bg-white">
                <SelectValue placeholder="All Companies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">All Companies</SelectItem>
                {companies.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.company_name || c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">Period</label>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" onClick={() => setPeriod("month")} className="bg-white">This Month</Button>
              <Button variant="outline" size="sm" onClick={() => setPeriod("quarter")} className="bg-white">This Quarter</Button>
              <Button variant="outline" size="sm" onClick={() => setPeriod("fy")} className="bg-white">This FY</Button>
              <Button variant="outline" size="sm" onClick={() => { setFilterFrom(""); setFilterTo(format(new Date(), "yyyy-MM-dd")); }} className="bg-white">Overall</Button>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">From</label>
            <Input type="date" value={filterFrom} onChange={(e) => setFilterFrom(e.target.value)} className="w-[150px] bg-white" />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">To / As On</label>
            <Input type="date" value={filterTo} onChange={(e) => setFilterTo(e.target.value)} className="w-[150px] bg-white" />
          </div>

          <div className="flex gap-2">
            <Button onClick={applyFilters} className="bg-sky-700 hover:bg-sky-800">Apply</Button>
            <Button variant="outline" onClick={resetFilters} className="bg-white">Reset</Button>
          </div>
        </CardContent>
      </Card>

      <Alert className="bg-sky-50 border-sky-200 text-sky-800 flex gap-2 items-start py-3">
        <Info className="w-4 h-4 mt-0.5 shrink-0" />
        <AlertDescription className="text-xs">
          <strong>Three sources combined:</strong><br />
          <strong>① Cash Received</strong> — income entries collected in cash.<br />
          <strong>② Cash Paid</strong> — expense entries paid in cash.<br />
          <strong>③ Staff Float</strong> — unspent balance from fund allocations currently held by staff.<br />
          Net Cash in Hand = (Cash Received − Cash Paid) + Staff Float + Formal Ledger (if any).
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="shadow-sm">
          <CardContent className="p-5">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Total Cash in Hand</div>
            <div className="text-2xl font-bold text-sky-700">{summaryData ? R(summaryData.total_cash) : "—"}</div>
            <div className="text-xs text-gray-400 mt-1">Net across all sources</div>
          </CardContent>
        </Card>
        <Card className="shadow-sm">
          <CardContent className="p-5">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Cash Received</div>
            <div className="text-2xl font-bold text-emerald-600">{summaryData ? R(summaryData.total_receipts) : "—"}</div>
            <div className="text-xs text-gray-400 mt-1">Income entries (cash mode)</div>
          </CardContent>
        </Card>
        <Card className="shadow-sm">
          <CardContent className="p-5">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Cash Paid Out</div>
            <div className="text-2xl font-bold text-red-600">{summaryData ? R(summaryData.total_payments) : "—"}</div>
            <div className="text-xs text-gray-400 mt-1">Expense entries (cash mode)</div>
          </CardContent>
        </Card>
        <Card className="shadow-sm">
          <CardContent className="p-5">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Staff Float</div>
            <div className="text-2xl font-bold text-purple-600">{summaryData ? R(summaryData.total_fund_float) : "—"}</div>
            <div className="text-xs text-gray-400 mt-1">Unspent fund allocations</div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="bg-transparent border-b border-gray-200 w-full justify-start rounded-none h-auto p-0">
          <TabsTrigger 
            value="summary" 
            className="data-[state=active]:border-b-2 data-[state=active]:border-sky-700 data-[state=active]:text-sky-700 rounded-none bg-transparent px-4 py-2 font-medium text-gray-500"
          >
            <Building2 className="w-4 h-4 mr-2" /> Company Breakdown
          </TabsTrigger>
          <TabsTrigger 
            value="txns" 
            className="data-[state=active]:border-b-2 data-[state=active]:border-sky-700 data-[state=active]:text-sky-700 rounded-none bg-transparent px-4 py-2 font-medium text-gray-500"
          >
            <List className="w-4 h-4 mr-2" /> Transaction History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="mt-4">
          <Card className="shadow-sm border-0">
            <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between py-3 px-4">
              <CardTitle className="text-sm font-semibold flex items-center text-gray-800">
                <Wallet className="w-4 h-4 text-sky-700 mr-2" /> Cash in Hand — Company-wise Breakdown
              </CardTitle>
              <CardDescription className="text-xs">
                {summaryData?.companies?.filter(c => parseFloat(String(c.net_cash_in_hand)) > 0 || parseFloat(String(c.cash_receipts)) > 0 || parseFloat(String(c.fund_float)) > 0).length || 0} companies with activity
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {isLoadingSummary ? (
                <div className="p-10 flex justify-center">
                  <RefreshCw className="w-8 h-8 text-sky-700 animate-spin" />
                </div>
              ) : summaryError ? (
                <div className="p-10 text-center text-gray-500">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-red-500" />
                  <h4 className="font-semibold text-gray-700">Error</h4>
                  <p className="text-sm">{summaryError}</p>
                </div>
              ) : summaryData?.companies?.filter(c => parseFloat(String(c.cash_receipts)) > 0 || parseFloat(String(c.cash_payments)) > 0 || parseFloat(String(c.fund_float)) > 0 || Math.abs(parseFloat(String(c.ledger_net))) > 0).length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <Wallet className="w-10 h-10 mx-auto mb-3" />
                  <h4 className="font-semibold text-gray-500 text-base">No Cash Data Found</h4>
                  <p className="text-sm">No cash income, cash expenses, or fund allocations found for the selected period</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader className="bg-gray-50">
                      <TableRow>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500">Company</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-emerald-600 text-right">Cash Received</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-red-600 text-right">Cash Paid</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-purple-600 text-right">Staff Float</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500 text-right">Ledger</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-sky-700 text-right">Net Cash in Hand</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summaryData?.companies?.filter(co => {
                        const rec = parseFloat(String(co.cash_receipts)) || 0;
                        const pay = parseFloat(String(co.cash_payments)) || 0;
                        const flt = parseFloat(String(co.fund_float)) || 0;
                        const ldg = parseFloat(String(co.ledger_net)) || 0;
                        return rec > 0 || pay > 0 || flt > 0 || Math.abs(ldg) > 0;
                      }).map((co, idx) => {
                        const rec = parseFloat(String(co.cash_receipts)) || 0;
                        const pay = parseFloat(String(co.cash_payments)) || 0;
                        const flt = parseFloat(String(co.fund_float)) || 0;
                        const ldg = parseFloat(String(co.ledger_net)) || 0;
                        const net = parseFloat(String(co.net_cash_in_hand)) || 0;
                        
                        return (
                          <TableRow key={idx}>
                            <TableCell>
                              <strong className="flex items-center text-gray-800">
                                <Building2 className="w-3 h-3 text-sky-700 mr-1" /> {co.company_name}
                              </strong>
                              <div className="text-[11px] text-gray-400 mt-0.5">
                                {co.cash_receipts_cnt} receipts &middot; {co.cash_payments_cnt} payments &middot; {co.fund_float_cnt} allocations
                              </div>
                            </TableCell>
                            <TableCell className="text-right text-emerald-600 tabular-nums">{rec > 0 ? R(rec) : <span className="italic text-gray-400 text-xs">—</span>}</TableCell>
                            <TableCell className="text-right text-red-600 tabular-nums">{pay > 0 ? R(pay) : <span className="italic text-gray-400 text-xs">—</span>}</TableCell>
                            <TableCell className="text-right text-purple-600 tabular-nums">
                              {flt > 0 ? (
                                <>
                                  {R(flt)}<br />
                                  <small className="text-[10px] text-gray-400">of {R(co.fund_allocated)} given</small>
                                </>
                              ) : <span className="italic text-gray-400 text-xs">—</span>}
                            </TableCell>
                            <TableCell className="text-right text-gray-500 tabular-nums">{Math.abs(ldg) > 0.001 ? R(ldg) : <span className="italic text-gray-400 text-xs">—</span>}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              <strong className="text-sky-700 text-[15px]">{R(net)}</strong>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                      {summaryData?.companies && summaryData.companies.length > 1 && (
                        <TableRow className="bg-sky-50 border-t-2 border-sky-700 hover:bg-sky-50">
                          <TableCell><strong className="text-sky-900">CONSOLIDATED TOTAL</strong></TableCell>
                          <TableCell className="text-right font-bold tabular-nums text-sky-900">{R(summaryData.total_receipts)}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums text-sky-900">{R(summaryData.total_payments)}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums text-sky-900">{R(summaryData.total_fund_float)}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums text-sky-900">
                            {(() => {
                              const grandLedger = summaryData.companies.reduce((acc, co) => acc + (parseFloat(String(co.ledger_net)) || 0), 0);
                              return Math.abs(grandLedger) > 0.001 ? R(grandLedger) : "—";
                            })()}
                          </TableCell>
                          <TableCell className="text-right font-bold tabular-nums text-sky-900">{R(summaryData.total_cash)}</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="txns" className="mt-4">
          <Alert className="bg-yellow-50 border-yellow-300 text-yellow-900 mb-4 py-2">
            <AlertDescription className="text-xs">
              <strong>GST Note:</strong> Cash transactions shown here are gross amounts (including GST where applicable). For GST-exclusive figures and tax breakdowns, refer to the <a href="/staff/accounts/duties-taxes" className="text-yellow-700 font-semibold underline">Duties & Taxes</a> page.
            </AlertDescription>
          </Alert>

          <Card className="shadow-sm border-0">
            <CardHeader className="border-b border-gray-200 flex flex-row items-center justify-between py-3 px-4">
              <CardTitle className="text-sm font-semibold flex items-center text-gray-800">
                <List className="w-4 h-4 text-sky-700 mr-2" /> Cash in Hand — Transaction History
              </CardTitle>
              <CardDescription className="text-xs">
                {txnsData.length} entries
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {isLoadingTxns ? (
                <div className="p-10 flex justify-center">
                  <RefreshCw className="w-8 h-8 text-sky-700 animate-spin" />
                </div>
              ) : txnsError ? (
                <div className="p-10 text-center text-gray-500">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-red-500" />
                  <h4 className="font-semibold text-gray-700">Error</h4>
                  <p className="text-sm">{txnsError}</p>
                </div>
              ) : txnsData.length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <List className="w-10 h-10 mx-auto mb-3" />
                  <h4 className="font-semibold text-gray-500 text-base">No Transactions Found</h4>
                  <p className="text-sm">No cash entries in the selected period</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader className="bg-gray-50">
                      <TableRow>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500 whitespace-nowrap">Date</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500">Company</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500">Source</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500">Party / Staff</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500">Ref No.</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500">Narration</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-emerald-600 text-right">Cash In</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-red-600 text-right">Cash Out</TableHead>
                        <TableHead className="font-semibold text-xs uppercase text-gray-500">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {txnsData.map((t, idx) => {
                        const src = SOURCE_LABELS[t.source] || { label: t.txn_type, cls: "bg-gray-100 text-gray-700", icon: <div className="w-3 h-3 mr-1 bg-gray-400 rounded-full" /> };
                        const rec = parseFloat(String(t.receipt)) || 0;
                        const pay = parseFloat(String(t.payment)) || 0;
                        const narr = t.narration || "—";
                        const isFlt = t.source === "FUND_ALLOC";

                        return (
                          <TableRow key={idx}>
                            <TableCell className="whitespace-nowrap text-xs">{t.date}</TableCell>
                            <TableCell className="whitespace-nowrap text-[11px]">{t.company_name}</TableCell>
                            <TableCell>
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${src.cls}`}>
                                {src.icon}
                                {src.label}
                              </span>
                            </TableCell>
                            <TableCell className="text-xs text-gray-700">{t.party || "—"}</TableCell>
                            <TableCell className="text-[11px] text-gray-500">{t.ref_number || "—"}</TableCell>
                            <TableCell className="text-xs max-w-[200px] truncate" title={narr}>{narr}</TableCell>
                            <TableCell className="text-right text-emerald-600 tabular-nums">
                              {rec > 0 ? R(rec) : isFlt ? <small className="text-purple-600">{R(rec + pay)}</small> : "—"}
                            </TableCell>
                            <TableCell className="text-right text-red-600 tabular-nums">
                              {pay > 0 ? R(pay) : "—"}
                            </TableCell>
                            <TableCell className="text-[11px] text-gray-500">{t.status}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
