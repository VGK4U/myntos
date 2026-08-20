"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import api from "@/lib/api";
import { useStaffAuth, Employee } from "@/contexts/StaffAuthContext";
import toast, { Toaster } from "react-hot-toast";
import {
  FileSpreadsheet,
  Receipt,
  Trophy,
  Route,
  HardHat,
  Calendar,
  CalendarCheck,
  Building2,
  User,
  Users,
  Filter,
  RefreshCw,
  RotateCcw,
  CheckCircle2,
  Clock,
  Hourglass,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Info,
  Check,
  Search,
  IndianRupee,
  Layers,
  FileText,
  AlertCircle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableFooter } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

// ==========================================
// Constants & Lookups
// ==========================================
const MONTH_NAMES = [
  "",
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const MONTH_ABBR = [
  "",
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const SLUGS = [
  "solar",
  "ev_b2c",
  "ev_b2b",
  "training",
  "insurance",
  "real_estate",
] as const;

const SLUG_LBL: Record<string, string> = {
  solar: "Solar",
  ev_b2c: "EV B2C",
  ev_b2b: "EV B2B",
  training: "Training",
  insurance: "Insurance",
  real_estate: "Real Estate",
};

// ==========================================
// Types & Interfaces
// ==========================================
interface Company {
  id: number | string;
  company_name?: string;
  name?: string;
  company_code?: string;
}

interface EmployeeOption {
  id: number;
  emp_code: string;
  full_name?: string;
}

interface AchievementCategory {
  slug: string;
  incentive_earned: number;
}

interface IncentiveAchievement {
  employee_id: number;
  name?: string;
  emp_code?: string;
  categories?: AchievementCategory[];
}

interface PayoutRecord {
  id: number;
  employee_id: number;
  company_id?: number;
  month: number;
  year: number;
  total_incentive: number;
  payout_status: "in_progress" | "pending" | "cleared" | string;
  cleared_by?: string | null;
  cleared_at?: string | null;
  due_date?: string | null;
  due_date_label?: string | null;
  notes?: string | null;
  employee_name?: string;
  emp_code?: string;
  breakdown?: string;
  solar?: number;
  ev_b2c?: number;
  ev_b2b?: number;
  training?: number;
  insurance?: number;
  real_estate?: number;
  [key: string]: any;
}

interface ExpenseRecord {
  source_type: "expense" | "journey" | "field_work" | string;
  source_id: number;
  entry_date?: string | null;
  employee_name?: string | null;
  emp_code?: string | null;
  category?: string | null;
  description?: string | null;
  amount: number;
  status?: string | null;
  payment_mode?: string | null;
  reference_no?: string | null;
  [key: string]: any;
}

interface UnifiedRecord {
  id: string | number;
  row_type: "incentive" | "expense" | "journey" | "field_work";
  entry_date: string;
  employee_name: string;
  emp_code: string;
  category: string;
  description: string;
  amount: number;
  status: string;
  ref_due: string;
  raw_payout?: PayoutRecord;
  raw_expense?: ExpenseRecord;
  breakdown?: string;
}

type SortColumn =
  | "row_type"
  | "entry_date"
  | "employee_name"
  | "emp_code"
  | "category"
  | "amount"
  | "status";

// ==========================================
// Helper Functions
// ==========================================
function canUserClear(emp: Employee | null): boolean {
  if (!emp) return false;
  const ec = (emp.emp_code || "").toUpperCase();
  const rn = (emp.role_name || emp.role || "").toLowerCase();
  const rc = (emp.role_code || "").toLowerCase();
  return (
    ec === "MR10001" ||
    rn.includes("account") ||
    rc.includes("account") ||
    rn.includes(" hr") ||
    rn === "hr" ||
    rc.includes("hr") ||
    rn.includes("vgk mentor") ||
    rc.includes("vgk_mentor") ||
    (ec.startsWith("MR") && (rn.includes("admin") || rc.includes("admin")))
  );
}

function formatINR(val: number | string | null | undefined): string {
  const num = typeof val === "string" ? parseFloat(val) : (val ?? 0);
  if (isNaN(num) || !num) return "₹0";
  return (
    "₹" +
    num.toLocaleString("en-IN", {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    })
  );
}

export default function AccountsPendingClearPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useStaffAuth();

  // Filters State
  const now = new Date();
  const [filterMonth, setFilterMonth] = useState<number>(now.getMonth() + 1);
  const [filterYear, setFilterYear] = useState<number>(now.getFullYear());
  const [filterCompany, setFilterCompany] = useState<string>("");
  const [filterEmployee, setFilterEmployee] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Options State
  const [companies, setCompanies] = useState<Company[]>([]);
  const [employees, setEmployees] = useState<EmployeeOption[]>([]);

  // Raw Data State
  const [payoutsData, setPayoutsData] = useState<PayoutRecord[]>([]);
  const [expensesData, setExpensesData] = useState<ExpenseRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // Sorting State
  const [sortCol, setSortCol] = useState<SortColumn>("entry_date");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);

  // Mark Cleared Modal State
  const [clearModalOpen, setClearModalOpen] = useState<boolean>(false);
  const [targetPayout, setTargetPayout] = useState<PayoutRecord | null>(null);
  const [clearNotes, setClearNotes] = useState<string>("");
  const [clearSubmitting, setClearSubmitting] = useState<boolean>(false);
  const [clearError, setClearError] = useState<string | null>(null);

  // Category Breakdown Modal State
  const [breakdownModalOpen, setBreakdownModalOpen] = useState<boolean>(false);
  const [breakdownTarget, setBreakdownTarget] = useState<PayoutRecord | null>(null);

  const userCanClear = useMemo(() => canUserClear(user), [user]);

  // Available Years list (2024 to current + 1)
  const availableYears = useMemo(() => {
    const currentYr = new Date().getFullYear();
    const list: number[] = [];
    for (let y = currentYr + 1; y >= 2024; y--) {
      list.push(y);
    }
    return list;
  }, []);

  // Compute Due Notice Text
  const dueNoticeInfo = useMemo(() => {
    const mo = filterMonth || now.getMonth() + 1;
    const yr = filterYear || now.getFullYear();
    const nextMo = mo === 12 ? 1 : mo + 1;
    const nextYr = mo === 12 ? yr + 1 : yr;
    return {
      dueLabel: `15 ${MONTH_ABBR[nextMo]} ${nextYr}`,
      periodLabel: `${MONTH_NAMES[mo]} ${yr}`,
    };
  }, [filterMonth, filterYear, now]);

  // Load Companies & Employees Dropdowns
  const loadFilterOptions = useCallback(async () => {
    try {
      const [compRes, empRes] = await Promise.all([
        api.get("/staff/accounts/companies"),
        api.get("/staff/employees/list?page_size=500"),
      ]);

      if (compRes.data) {
        const cList = compRes.data.companies || compRes.data.data?.companies || compRes.data.data || [];
        setCompanies(Array.isArray(cList) ? cList : []);
      }

      if (empRes.data) {
        const eList = empRes.data.employees || empRes.data.data || [];
        setEmployees(Array.isArray(eList) ? eList : []);
      }
    } catch (err) {
      console.error("Error loading filter dropdown options:", err);
    }
  }, []);

  // Load Payouts & Expenses
  const loadAllData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {
        month: filterMonth,
        year: filterYear,
      };
      if (filterCompany) params.company_id = filterCompany;
      if (filterEmployee) params.employee_id = filterEmployee;
      if (filterStatus) params.status = filterStatus;

      // 1. Fetch Incentive Payouts
      let loadedPayouts: PayoutRecord[] = [];
      try {
        const payoutRes = await api.get("/staff/incentive-payouts/list", { params });
        if (payoutRes.data?.success) {
          loadedPayouts = payoutRes.data.data || [];
        }
      } catch (e) {
        console.error("Failed to load incentive payouts:", e);
      }

      // 2. Fetch Achievements for Breakdown Tooltips
      let achMap: Record<number, { slugMap: Record<string, number>; name?: string; emp_code?: string }> = {};
      try {
        const achParams: Record<string, any> = { month: filterMonth, year: filterYear };
        if (filterCompany) achParams.company_id = filterCompany;
        const achRes = await api.get("/staff/incentive-achievements", { params: achParams });
        if (achRes.data?.success && Array.isArray(achRes.data.data)) {
          achRes.data.data.forEach((r: IncentiveAchievement) => {
            const slugMap: Record<string, number> = {};
            (r.categories || []).forEach((c) => {
              slugMap[c.slug] = c.incentive_earned;
            });
            achMap[r.employee_id] = { slugMap, name: r.name, emp_code: r.emp_code };
          });
        }
      } catch (e) {
        console.error("Failed to load incentive achievements:", e);
      }

      // Map breakdown into payouts
      const enrichedPayouts = loadedPayouts.map((row) => {
        const ach = achMap[row.employee_id] || { slugMap: {} };
        const slugMap = ach.slugMap || {};
        const breakdownParts = SLUGS.map((s) => {
          const v = parseFloat(String(slugMap[s] || 0));
          return v > 0 ? `${SLUG_LBL[s]}: ₹${v.toLocaleString("en-IN")}` : null;
        }).filter(Boolean);
        const breakdown = breakdownParts.join(" | ");
        return {
          ...row,
          ...slugMap,
          breakdown,
        };
      });
      setPayoutsData(enrichedPayouts);

      // 3. Fetch Outgoing Expenses
      let loadedExpenses: ExpenseRecord[] = [];
      try {
        const expParams: Record<string, any> = {
          month: filterMonth,
          year: filterYear,
        };
        if (filterCompany) expParams.company_id = filterCompany;
        if (filterEmployee) expParams.employee_id = filterEmployee;
        if (filterStatus) expParams.status = filterStatus;

        const expRes = await api.get("/staff/outgoing-expenses", { params: expParams });
        if (expRes.data?.success) {
          loadedExpenses = expRes.data.data || [];
        }
      } catch (e) {
        console.error("Failed to load outgoing expenses:", e);
      }
      setExpensesData(loadedExpenses);
    } catch (err) {
      console.error("Error loading pending clear data:", err);
      toast.error("Failed to load clearance records.");
    } finally {
      setLoading(false);
    }
  }, [filterMonth, filterYear, filterCompany, filterEmployee, filterStatus]);

  // Initial Load
  useEffect(() => {
    if (isAuthenticated) {
      loadFilterOptions();
      loadAllData();
    }
  }, [isAuthenticated, loadFilterOptions, loadAllData]);

  // Reset Filters
  const handleResetFilters = () => {
    const current = new Date();
    setFilterMonth(current.getMonth() + 1);
    setFilterYear(current.getFullYear());
    setFilterCompany("");
    setFilterEmployee("");
    setFilterType("");
    setFilterStatus("");
    setSearchQuery("");
  };

  // Convert raw payouts + expenses into unified list
  const unifiedList = useMemo<UnifiedRecord[]>(() => {
    const list: UnifiedRecord[] = [];

    // 1. Add Payouts
    payoutsData.forEach((p) => {
      const periodStr = `${MONTH_NAMES[p.month] || filterMonth} ${p.year || filterYear}`;
      list.push({
        id: `payout-${p.id}`,
        row_type: "incentive",
        entry_date: periodStr,
        employee_name: p.employee_name || "—",
        emp_code: p.emp_code || "—",
        category: "Incentive Payout",
        description: p.breakdown ? "Incentive Breakdown" : "Performance Incentive",
        amount: parseFloat(String(p.total_incentive || 0)),
        status: p.payout_status,
        ref_due: p.due_date_label || `Due 15th of next month`,
        raw_payout: p,
        breakdown: p.breakdown,
      });
    });

    // 2. Add Expenses
    expensesData.forEach((e) => {
      const rowType = (e.source_type || "expense") as "expense" | "journey" | "field_work";
      const ref = [e.payment_mode, e.reference_no].filter(Boolean).join(" · ") || "—";
      list.push({
        id: `expense-${e.source_type}-${e.source_id}`,
        row_type: rowType,
        entry_date: e.entry_date || "—",
        employee_name: e.employee_name || "—",
        emp_code: e.emp_code || "—",
        category: e.category || "General Expense",
        description: e.description || "—",
        amount: parseFloat(String(e.amount || 0)),
        status: e.status || "pending",
        ref_due: ref,
        raw_expense: e,
      });
    });

    return list;
  }, [payoutsData, expensesData, filterMonth, filterYear]);

  // Filter & Sort unified records
  const filteredAndSortedRecords = useMemo(() => {
    let result = [...unifiedList];

    // Filter by Type
    if (filterType) {
      result = result.filter((r) => r.row_type === filterType);
    }

    // Filter by Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (r) =>
          r.employee_name.toLowerCase().includes(q) ||
          r.emp_code.toLowerCase().includes(q) ||
          r.category.toLowerCase().includes(q) ||
          r.description.toLowerCase().includes(q) ||
          r.ref_due.toLowerCase().includes(q)
      );
    }

    // Sort Records
    result.sort((a, b) => {
      let va: any = a[sortCol] ?? "";
      let vb: any = b[sortCol] ?? "";

      if (sortCol === "amount") {
        return (Number(va) - Number(vb)) * sortDir;
      }
      return String(va).localeCompare(String(vb)) * sortDir;
    });

    return result;
  }, [unifiedList, filterType, searchQuery, sortCol, sortDir]);

  // Summary Metrics Calculation
  const summaryMetrics = useMemo(() => {
    let inProgressCount = 0;
    let pendingCount = 0;
    let clearedCount = 0;
    let totalPendingAmount = 0;

    payoutsData.forEach((r) => {
      const amt = parseFloat(String(r.total_incentive || 0));
      if (r.payout_status === "in_progress") {
        inProgressCount++;
        totalPendingAmount += amt;
      } else if (r.payout_status === "pending") {
        pendingCount++;
        totalPendingAmount += amt;
      } else if (r.payout_status === "cleared") {
        clearedCount++;
      }
    });

    expensesData.forEach((r) => {
      const st = (r.status || "").toLowerCase();
      const amt = parseFloat(String(r.amount || 0));
      if (!st.includes("clear") && !st.includes("approv") && st !== "completed") {
        totalPendingAmount += amt;
      }
    });

    return {
      inProgressCount,
      pendingCount,
      clearedCount,
      totalPendingAmount,
    };
  }, [payoutsData, expensesData]);

  // Handle Sort Change
  const handleSort = (col: SortColumn) => {
    if (sortCol === col) {
      setSortDir((prev) => (prev === 1 ? -1 : 1));
    } else {
      setSortCol(col);
      setSortDir(1);
    }
  };

  // Open Mark Cleared Modal
  const handleOpenClearModal = (payout: PayoutRecord) => {
    setTargetPayout(payout);
    setClearNotes("");
    setClearError(null);
    setClearModalOpen(true);
  };

  // Confirm Mark Cleared
  const handleConfirmClear = async () => {
    if (!targetPayout) return;
    setClearSubmitting(true);
    setClearError(null);
    try {
      const res = await api.put(
        `/staff/incentive-payouts/${targetPayout.id}/mark-cleared`,
        { notes: clearNotes.trim() }
      );
      if (res.data?.success) {
        toast.success(
          `Payout for ${targetPayout.employee_name || "Employee"} marked as cleared!`
        );
        setClearModalOpen(false);
        setTargetPayout(null);
        loadAllData();
      } else {
        setClearError(res.data?.detail || res.data?.message || "Failed to mark payout as cleared.");
      }
    } catch (err: any) {
      console.error("Error clearing payout:", err);
      setClearError(
        err?.response?.data?.detail || err?.message || "Failed to clear payout."
      );
    } finally {
      setClearSubmitting(false);
    }
  };

  // Open Breakdown Modal
  const handleOpenBreakdownModal = (payout: PayoutRecord) => {
    setBreakdownTarget(payout);
    setBreakdownModalOpen(true);
  };

  // Render Type Badge
  const renderTypeBadge = (type: string) => {
    switch (type) {
      case "incentive":
        return (
          <Badge
            variant="outline"
            className="bg-amber-50 text-amber-800 border-amber-300 font-semibold px-2 py-0.5 text-[11px] gap-1 shadow-xs"
          >
            <Trophy className="w-3 h-3 text-amber-600" />
            Incentive
          </Badge>
        );
      case "expense":
        return (
          <Badge
            variant="outline"
            className="bg-blue-50 text-blue-800 border-blue-300 font-semibold px-2 py-0.5 text-[11px] gap-1 shadow-xs"
          >
            <Receipt className="w-3 h-3 text-blue-600" />
            Expense
          </Badge>
        );
      case "journey":
        return (
          <Badge
            variant="outline"
            className="bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold px-2 py-0.5 text-[11px] gap-1 shadow-xs"
          >
            <Route className="w-3 h-3 text-emerald-600" />
            Journey
          </Badge>
        );
      case "field_work":
        return (
          <Badge
            variant="outline"
            className="bg-purple-50 text-purple-800 border-purple-300 font-semibold px-2 py-0.5 text-[11px] gap-1 shadow-xs"
          >
            <HardHat className="w-3 h-3 text-purple-600" />
            Field Work
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-300 text-[11px]">
            {type}
          </Badge>
        );
    }
  };

  // Render Status Badge
  const renderStatusBadge = (status: string, rowType: string) => {
    const s = (status || "").toLowerCase();
    if (rowType === "incentive") {
      if (s === "cleared") {
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Cleared
          </span>
        );
      }
      if (s === "pending") {
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <Hourglass className="w-3.5 h-3.5 text-rose-600 animate-pulse" />
            Pending
          </span>
        );
      }
      if (s === "in_progress") {
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            In Progress
          </span>
        );
      }
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
          {status}
        </span>
      );
    }

    // Expense / Journey / Field Work status badges
    if (s.includes("approv") || s.includes("clear") || s === "completed") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          {status}
        </span>
      );
    }
    if (s.includes("pending") || s === "in_progress") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
          <Hourglass className="w-3.5 h-3.5 text-rose-600" />
          {status}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
        {status || "—"}
      </span>
    );
  };

  // Grand Total Calculation
  const grandTotalFilteredAmount = useMemo(() => {
    return filteredAndSortedRecords.reduce((sum, r) => sum + r.amount, 0);
  }, [filteredAndSortedRecords]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <Toaster position="top-right" />

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl border border-indigo-100 shadow-xs">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                Pending to Clear
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                All outgoing obligations — incentive payouts &amp; staff expenses requiring accounts clearance
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={loadAllData}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </div>

      {/* Due Notice Banner */}
      <div className="bg-amber-50/90 border border-amber-200/80 rounded-xl p-4 flex items-center gap-3 text-amber-900 shadow-xs">
        <div className="p-2 bg-amber-100 text-amber-700 rounded-lg shrink-0">
          <CalendarCheck className="w-5 h-5" />
        </div>
        <div className="text-sm font-medium flex-1">
          <span className="font-bold text-amber-950">Incentive &amp; expense clearance due: </span>
          <span className="underline decoration-amber-400 font-semibold">{dueNoticeInfo.dueLabel}</span>
          <span className="text-amber-800/80 ml-2">
            (For period: <strong className="text-amber-950">{dueNoticeInfo.periodLabel}</strong>)
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="shadow-xs border-gray-200 bg-white">
        <CardContent className="p-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5 items-end">
            {/* Month Filter */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider flex items-center gap-1">
                <Calendar className="w-3 h-3 text-gray-400" />
                Month
              </label>
              <select
                value={filterMonth}
                onChange={(e) => setFilterMonth(parseInt(e.target.value))}
                className="w-full px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-2xs"
              >
                {MONTH_NAMES.map((name, idx) => {
                  if (!idx) return null;
                  return (
                    <option key={idx} value={idx}>
                      {name}
                    </option>
                  );
                })}
              </select>
            </div>

            {/* Year Filter */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">
                Year
              </label>
              <select
                value={filterYear}
                onChange={(e) => setFilterYear(parseInt(e.target.value))}
                className="w-full px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-2xs"
              >
                {availableYears.map((yr) => (
                  <option key={yr} value={yr}>
                    {yr}
                  </option>
                ))}
              </select>
            </div>

            {/* Company Filter */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider flex items-center gap-1">
                <Building2 className="w-3 h-3 text-gray-400" />
                Company
              </label>
              <select
                value={filterCompany}
                onChange={(e) => setFilterCompany(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-2xs"
              >
                <option value="">All Companies</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name || c.name || `Company #${c.id}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Employee Filter */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider flex items-center gap-1">
                <User className="w-3 h-3 text-gray-400" />
                Employee
              </label>
              <select
                value={filterEmployee}
                onChange={(e) => setFilterEmployee(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-2xs"
              >
                <option value="">All Employees</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.full_name || e.emp_code} ({e.emp_code})
                  </option>
                ))}
              </select>
            </div>

            {/* Type Filter */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider flex items-center gap-1">
                <Filter className="w-3 h-3 text-gray-400" />
                Type
              </label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-2xs"
              >
                <option value="">All Types</option>
                <option value="incentive">Incentive</option>
                <option value="expense">Expense</option>
                <option value="journey">Journey</option>
                <option value="field_work">Field Work</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider">
                Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-2xs"
              >
                <option value="">All Statuses</option>
                <option value="in_progress">In Progress</option>
                <option value="pending">Pending</option>
                <option value="cleared">Cleared</option>
              </select>
            </div>
          </div>

          {/* Action Buttons & Search */}
          <div className="mt-4 pt-3.5 border-t border-gray-100 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search employee, category, description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs font-medium border border-gray-200 rounded-lg bg-gray-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="text-xs text-gray-600 hover:text-gray-900 border-gray-200 shadow-2xs gap-1"
              >
                <RotateCcw className="w-3.5 h-3.5 text-gray-400" />
                Reset
              </Button>
              <Button
                size="sm"
                onClick={loadAllData}
                disabled={loading}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs gap-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                Load
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* In Progress Card */}
        <Card className="shadow-xs border-amber-100 bg-gradient-to-br from-amber-50/40 via-white to-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-amber-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-amber-600" />
                  In Progress
                </p>
                <h3 className="text-2xl font-extrabold text-amber-600 mt-1">
                  {summaryMetrics.inProgressCount}
                </h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-amber-100/70 border border-amber-200/60 flex items-center justify-center text-amber-700">
                <Clock className="w-5 h-5" />
              </div>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">Active month incentive calculations</p>
          </CardContent>
        </Card>

        {/* Pending Clearance Card */}
        <Card className="shadow-xs border-rose-100 bg-gradient-to-br from-rose-50/40 via-white to-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-rose-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Hourglass className="w-3.5 h-3.5 text-rose-600" />
                  Pending Clearance
                </p>
                <h3 className="text-2xl font-extrabold text-rose-600 mt-1">
                  {summaryMetrics.pendingCount}
                </h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-rose-100/70 border border-rose-200/60 flex items-center justify-center text-rose-700">
                <Hourglass className="w-5 h-5" />
              </div>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">Payouts awaiting accounts clearance</p>
          </CardContent>
        </Card>

        {/* Cleared Card */}
        <Card className="shadow-xs border-emerald-100 bg-gradient-to-br from-emerald-50/40 via-white to-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-emerald-700 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Cleared
                </p>
                <h3 className="text-2xl font-extrabold text-emerald-600 mt-1">
                  {summaryMetrics.clearedCount}
                </h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-100/70 border border-emerald-200/60 flex items-center justify-center text-emerald-700">
                <CheckCircle2 className="w-5 h-5" />
              </div>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">Cleared &amp; disbursed payouts</p>
          </CardContent>
        </Card>

        {/* Total Pending Amount Card */}
        <Card className="shadow-xs border-indigo-100 bg-gradient-to-br from-indigo-50/40 via-white to-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-indigo-700 uppercase tracking-wider flex items-center gap-1.5">
                  <IndianRupee className="w-3.5 h-3.5 text-indigo-600" />
                  Total Pending Amount
                </p>
                <h3 className="text-2xl font-extrabold text-indigo-700 mt-1">
                  {formatINR(summaryMetrics.totalPendingAmount)}
                </h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-indigo-100/70 border border-indigo-200/60 flex items-center justify-center text-indigo-700">
                <IndianRupee className="w-5 h-5" />
              </div>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">Combined pending incentives &amp; expenses</p>
          </CardContent>
        </Card>
      </div>

      {/* Unified Clearance Table */}
      <Card className="shadow-xs border-gray-200 overflow-hidden bg-white">
        <CardHeader className="p-4 sm:px-6 border-b border-gray-100 bg-gray-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-600" />
            <CardTitle className="text-base font-bold text-gray-900">
              All Pending Obligations
            </CardTitle>
            <Badge variant="secondary" className="text-xs font-semibold ml-1">
              {filteredAndSortedRecords.length} record
              {filteredAndSortedRecords.length !== 1 ? "s" : ""}
            </Badge>
          </div>
          <div className="text-xs text-gray-500 font-medium">
            Click column headers to sort &bull; Showing live combined ledger records
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50/80 hover:bg-gray-50/80">
                  <TableHead
                    onClick={() => handleSort("row_type")}
                    className="cursor-pointer select-none font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3"
                  >
                    <div className="flex items-center gap-1">
                      Type
                      <ArrowUpDown className="w-3 h-3 text-gray-400" />
                    </div>
                  </TableHead>

                  <TableHead
                    onClick={() => handleSort("entry_date")}
                    className="cursor-pointer select-none font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3"
                  >
                    <div className="flex items-center gap-1">
                      Date / Period
                      <ArrowUpDown className="w-3 h-3 text-gray-400" />
                    </div>
                  </TableHead>

                  <TableHead
                    onClick={() => handleSort("employee_name")}
                    className="cursor-pointer select-none font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3"
                  >
                    <div className="flex items-center gap-1">
                      Employee
                      <ArrowUpDown className="w-3 h-3 text-gray-400" />
                    </div>
                  </TableHead>

                  <TableHead
                    onClick={() => handleSort("emp_code")}
                    className="cursor-pointer select-none font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3"
                  >
                    <div className="flex items-center gap-1">
                      Emp Code
                      <ArrowUpDown className="w-3 h-3 text-gray-400" />
                    </div>
                  </TableHead>

                  <TableHead
                    onClick={() => handleSort("category")}
                    className="cursor-pointer select-none font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3"
                  >
                    <div className="flex items-center gap-1">
                      Category
                      <ArrowUpDown className="w-3 h-3 text-gray-400" />
                    </div>
                  </TableHead>

                  <TableHead className="font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3">
                    Description
                  </TableHead>

                  <TableHead
                    onClick={() => handleSort("amount")}
                    className="cursor-pointer select-none font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3 text-right"
                  >
                    <div className="flex items-center justify-end gap-1">
                      Amount
                      <ArrowUpDown className="w-3 h-3 text-gray-400" />
                    </div>
                  </TableHead>

                  <TableHead
                    onClick={() => handleSort("status")}
                    className="cursor-pointer select-none font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3"
                  >
                    <div className="flex items-center gap-1">
                      Status
                      <ArrowUpDown className="w-3 h-3 text-gray-400" />
                    </div>
                  </TableHead>

                  <TableHead className="font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3">
                    Ref / Due Date
                  </TableHead>

                  {userCanClear && (
                    <TableHead className="font-bold text-gray-600 uppercase text-[11px] whitespace-nowrap py-3 text-center">
                      Action
                    </TableHead>
                  )}
                </TableRow>
              </TableHeader>

              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell
                      colSpan={userCanClear ? 10 : 9}
                      className="h-44 text-center text-gray-500"
                    >
                      <div className="flex flex-col items-center justify-center gap-2">
                        <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
                        <span className="text-sm font-medium">
                          Loading pending clearance records...
                        </span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : filteredAndSortedRecords.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={userCanClear ? 10 : 9}
                      className="h-48 text-center text-gray-500"
                    >
                      <div className="flex flex-col items-center justify-center gap-2 py-6">
                        <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-gray-400">
                          <Layers className="w-6 h-6" />
                        </div>
                        <p className="font-semibold text-gray-800 text-sm">
                          No pending clearance records found
                        </p>
                        <p className="text-xs text-gray-500 max-w-sm">
                          Try adjusting the month, year, type, or company filters, or click Reset.
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleResetFilters}
                          className="mt-2 text-xs"
                        >
                          Reset Filters
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredAndSortedRecords.map((row) => {
                    const isIncentive = row.row_type === "incentive";
                    const isCleared = row.status === "cleared";

                    return (
                      <TableRow key={row.id} className="hover:bg-gray-50/80 transition-colors">
                        <TableCell className="py-3">
                          {renderTypeBadge(row.row_type)}
                        </TableCell>

                        <TableCell className="py-3 text-xs font-medium text-gray-700 whitespace-nowrap">
                          {row.entry_date}
                        </TableCell>

                        <TableCell className="py-3 font-semibold text-xs text-gray-900">
                          {row.employee_name}
                        </TableCell>

                        <TableCell className="py-3 text-xs text-gray-500 font-mono">
                          {row.emp_code}
                        </TableCell>

                        <TableCell className="py-3 text-xs text-gray-800 font-medium">
                          {row.category}
                        </TableCell>

                        <TableCell className="py-3 text-xs text-gray-600 max-w-xs truncate">
                          {isIncentive && row.breakdown ? (
                            <button
                              onClick={() =>
                                row.raw_payout && handleOpenBreakdownModal(row.raw_payout)
                              }
                              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 hover:underline font-medium"
                              title="Click to view detailed incentive breakdown"
                            >
                              <Info className="w-3.5 h-3.5 text-indigo-500" />
                              Breakdown Details
                            </button>
                          ) : (
                            <span title={row.description}>{row.description}</span>
                          )}
                        </TableCell>

                        <TableCell className="py-3 text-xs font-bold text-right text-indigo-700 font-mono">
                          {formatINR(row.amount)}
                        </TableCell>

                        <TableCell className="py-3">
                          {renderStatusBadge(row.status, row.row_type)}
                        </TableCell>

                        <TableCell className="py-3 text-xs text-emerald-800 font-medium">
                          {row.ref_due}
                        </TableCell>

                        {userCanClear && (
                          <TableCell className="py-3 text-center whitespace-nowrap">
                            {isIncentive ? (
                              isCleared ? (
                                <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600">
                                  <Check className="w-4 h-4 text-emerald-600" /> Done
                                </span>
                              ) : (
                                <Button
                                  size="sm"
                                  onClick={() =>
                                    row.raw_payout && handleOpenClearModal(row.raw_payout)
                                  }
                                  className="h-7 px-3 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs gap-1"
                                >
                                  <Check className="w-3 h-3" />
                                  Clear
                                </Button>
                              )
                            ) : (
                              <span className="text-gray-400 text-xs">—</span>
                            )}
                          </TableCell>
                        )}
                      </TableRow>
                    );
                  })
                )}
              </TableBody>

              {filteredAndSortedRecords.length > 0 && (
                <TableFooter className="bg-gray-100/90 font-semibold border-t-2 border-gray-200">
                  <TableRow>
                    <TableCell colSpan={6} className="text-xs text-gray-900 uppercase font-bold py-3.5 px-4">
                      Total ({filteredAndSortedRecords.length} records)
                    </TableCell>
                    <TableCell className="text-right text-sm font-extrabold text-indigo-700 font-mono py-3.5">
                      {formatINR(grandTotalFilteredAmount)}
                    </TableCell>
                    <TableCell colSpan={userCanClear ? 3 : 2} className="py-3.5"></TableCell>
                  </TableRow>
                </TableFooter>
              )}
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Footer Info */}
      <div className="text-center text-xs text-gray-400 py-3">
        Pending to Clear &bull; SFMS Accounts Clearance Portal &bull; Standard clearance cycle due 15th of following month
      </div>

      {/* Mark Cleared Confirmation Modal */}
      <Dialog open={clearModalOpen} onOpenChange={setClearModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-gray-900">
              <div className="p-1.5 rounded-lg bg-emerald-100 text-emerald-700">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              Mark Payout as Cleared
            </DialogTitle>
            <DialogDescription className="text-xs text-gray-500 pt-1">
              Confirm payout clearance for{" "}
              <strong className="text-gray-900">{targetPayout?.employee_name || "Employee"}</strong> (
              {targetPayout?.emp_code}) for{" "}
              <strong className="text-gray-900">
                {MONTH_NAMES[targetPayout?.month || filterMonth]} {targetPayout?.year || filterYear}
              </strong>
              .
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="bg-emerald-50/70 border border-emerald-200 rounded-lg p-3 flex justify-between items-center">
              <span className="text-xs font-semibold text-emerald-900">Total Incentive Amount</span>
              <span className="text-lg font-bold text-emerald-700 font-mono">
                {formatINR(targetPayout?.total_incentive)}
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-700 flex items-center justify-between">
                <span>Clearance Notes / Reference (Optional)</span>
                <span className="text-[10px] text-gray-400">e.g. Bank Ref, Cheque No, UTR</span>
              </label>
              <Textarea
                rows={3}
                placeholder="Enter transaction reference, payment mode, or bank notes..."
                value={clearNotes}
                onChange={(e) => setClearNotes(e.target.value)}
                className="text-xs"
              />
            </div>

            {clearError && (
              <Alert variant="destructive" className="py-2 text-xs">
                <AlertCircle className="w-4 h-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{clearError}</AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setClearModalOpen(false)}
              disabled={clearSubmitting}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleConfirmClear}
              disabled={clearSubmitting}
              className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1.5"
            >
              <Check className="w-3.5 h-3.5" />
              {clearSubmitting ? "Confirming..." : "Confirm Clear"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Category Breakdown Modal */}
      <Dialog open={breakdownModalOpen} onOpenChange={setBreakdownModalOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-gray-900">
              <div className="p-1.5 rounded-lg bg-indigo-100 text-indigo-700">
                <Trophy className="w-5 h-5" />
              </div>
              Incentive Category Breakdown
            </DialogTitle>
            <DialogDescription className="text-xs text-gray-500 pt-1">
              Achievement earnings for{" "}
              <strong className="text-gray-900">{breakdownTarget?.employee_name}</strong> (
              {breakdownTarget?.emp_code}) —{" "}
              <strong>
                {MONTH_NAMES[breakdownTarget?.month || filterMonth]} {breakdownTarget?.year || filterYear}
              </strong>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="grid grid-cols-2 gap-2.5">
              {SLUGS.map((slug) => {
                const amt = parseFloat(String(breakdownTarget?.[slug] || 0));
                return (
                  <div
                    key={slug}
                    className={`p-3 rounded-lg border flex flex-col justify-between ${
                      amt > 0
                        ? "bg-indigo-50/50 border-indigo-200"
                        : "bg-gray-50/50 border-gray-200 opacity-60"
                    }`}
                  >
                    <span className="text-[11px] font-semibold text-gray-600">
                      {SLUG_LBL[slug]}
                    </span>
                    <span
                      className={`text-sm font-bold mt-1 font-mono ${
                        amt > 0 ? "text-indigo-700" : "text-gray-400"
                      }`}
                    >
                      {formatINR(amt)}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3.5 flex justify-between items-center mt-3">
              <span className="text-xs font-bold text-indigo-900 uppercase">
                Total Incentive Earned
              </span>
              <span className="text-base font-extrabold text-indigo-700 font-mono">
                {formatINR(breakdownTarget?.total_incentive)}
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setBreakdownModalOpen(false)}
              className="text-xs"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
