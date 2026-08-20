"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import toast, { Toaster } from "react-hot-toast";
import {
  Wallet,
  Plus,
  Search,
  Filter,
  RefreshCw,
  Eye,
  Check,
  CheckCheck,
  X,
  XCircle,
  Clock,
  Building2,
  User,
  ArrowRight,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Calendar,
  CreditCard,
  Banknote,
  DollarSign,
  AlertCircle,
  FileText,
  Copy,
  Download,
  Tag,
  Loader2,
  FolderOpen,
  ArrowUpDown,
  FileCheck2,
  TrendingUp,
  Landmark,
  Layers,
  Sparkles,
} from "lucide-react";

import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

// ==========================================
// Interfaces
// ==========================================

interface Company {
  id: number;
  company_name?: string;
  name?: string;
  code?: string;
}

interface StaffParty {
  id: number;
  emp_code: string;
  full_name: string;
  department?: string;
  role?: string;
  is_active: boolean;
}

interface BankAccount {
  id: number;
  bank_name: string;
  account_name?: string;
  account_number: string;
  account_type: string;
  is_primary?: boolean;
}

interface MainCategory {
  id: number;
  name: string;
}

interface SubCategory {
  id: number;
  name: string;
  parent_id: number;
}

interface FundAllocation {
  id: number;
  allocation_number?: string;
  company_id: number;
  company_name?: string;
  segment_id?: number | null;
  from_employee_id: number;
  from_employee_name?: string;
  to_employee_id: number;
  to_employee_name?: string;
  recipient_name?: string;
  recipient_id?: number;
  allocation_date: string;
  amount: number;
  purpose?: string | null;
  category_id?: number | null;
  category_name?: string | null;
  payment_mode?: string | null;
  payment_reference?: string | null;
  bank_account_id?: number | null;
  bank_account_name?: string | null;
  status: "PENDING" | "CONFIRMED" | "SETTLED" | "PARTIALLY_SETTLED" | "CANCELLED" | string;
  balance_remaining: number;
  balance_used: number;
  total_expensed?: number;
  settlement_date?: string | null;
  settlement_remarks?: string | null;
  confirmed_by_id?: number | null;
  confirmed_at?: string | null;
  ledger_entry_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  created_by?: number | null;
}

interface AllocationSummary {
  pending_count: number;
  pending_amount: number;
  confirmed_count: number;
  confirmed_amount: number;
  settled_count: number;
  settled_amount: number;
  total_count: number;
  total_amount: number;
}

export default function FundAllocationsPage() {
  const { user, token } = useStaffAuth();

  // Data states
  const [allocations, setAllocations] = useState<FundAllocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Reference master states
  const [companies, setCompanies] = useState<Company[]>([]);
  const [staffParties, setStaffParties] = useState<StaffParty[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [loadingBanks, setLoadingBanks] = useState(false);
  const [mainCategories, setMainCategories] = useState<MainCategory[]>([]);
  const [subCategories, setSubCategories] = useState<SubCategory[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);

  // Filter states
  const [filterSearch, setFilterSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterCompany, setFilterCompany] = useState("");
  const [filterRecipient, setFilterRecipient] = useState("");
  const [filterPaymentMode, setFilterPaymentMode] = useState("");
  const [filterFromDate, setFilterFromDate] = useState("");
  const [filterToDate, setFilterToDate] = useState("");

  // Modal / Dialog states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isSettleOpen, setIsSettleOpen] = useState(false);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isQuickCatOpen, setIsQuickCatOpen] = useState(false);

  // Selected item for actions
  const [selectedAllocation, setSelectedAllocation] = useState<FundAllocation | null>(null);

  // Form submission states
  const [actionLoading, setActionLoading] = useState(false);

  // Create Form State
  const [createForm, setCreateForm] = useState({
    company_id: "",
    to_employee_id: "",
    payment_source: "CASH", // 'CASH' | 'ACCOUNT'
    bank_account_id: "",
    allocation_date: new Date().toISOString().split("T")[0],
    amount: "",
    main_category_id: "",
    sub_category_id: "",
    purpose: "",
    payment_reference: "",
  });

  // Action remarks / forms
  const [confirmRemarks, setConfirmRemarks] = useState("");
  const [settleAmount, setSettleAmount] = useState("");
  const [settleRemarks, setSettleRemarks] = useState("");
  const [cancelReason, setCancelReason] = useState("");

  // Quick Category Form State
  const [quickCatMode, setQuickCatMode] = useState<"sub" | "main">("sub");
  const [quickCatMainName, setQuickCatMainName] = useState("");
  const [quickCatParentId, setQuickCatParentId] = useState("");
  const [quickCatSubName, setQuickCatSubName] = useState("");
  const [savingQuickCat, setSavingQuickCat] = useState(false);

  // ----------------------------------------------------------------------
  // Role & Permission Checks
  // ----------------------------------------------------------------------
  const hasElevatedAccess = useMemo(() => {
    if (!user?.role_name) return false;
    const r = user.role_name.toLowerCase();
    return (
      r.includes("supreme") ||
      r.includes("vgk") ||
      r.includes("mentor") ||
      r.includes("ea") ||
      r.includes("executive") ||
      r.includes("account") ||
      r.includes("admin") ||
      r.includes("director")
    );
  }, [user]);

  const canConfirm = useCallback(
    (alloc: FundAllocation) => {
      if (alloc.status !== "PENDING") return false;
      const isRecipient = alloc.to_employee_id === user?.id || alloc.recipient_id === user?.id;
      const isAllocator = alloc.from_employee_id === user?.id || alloc.created_by === user?.id;
      return isRecipient || isAllocator || hasElevatedAccess;
    },
    [user, hasElevatedAccess]
  );

  const canSettle = useCallback(
    (alloc: FundAllocation) => {
      if (alloc.status !== "CONFIRMED" && alloc.status !== "PARTIALLY_SETTLED") return false;
      const isRecipient = alloc.to_employee_id === user?.id || alloc.recipient_id === user?.id;
      const isAllocator = alloc.from_employee_id === user?.id || alloc.created_by === user?.id;
      return isRecipient || isAllocator || hasElevatedAccess;
    },
    [user, hasElevatedAccess]
  );

  const canCancel = useCallback(
    (alloc: FundAllocation) => {
      if (alloc.status === "SETTLED" || alloc.status === "CANCELLED") return false;
      const isAllocator = alloc.from_employee_id === user?.id || alloc.created_by === user?.id;
      return isAllocator || hasElevatedAccess;
    },
    [user, hasElevatedAccess]
  );

  // ----------------------------------------------------------------------
  // Data Fetching
  // ----------------------------------------------------------------------

  // Load Companies
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

  // Load Staff Parties (Recipients)
  const loadStaffList = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/fund-allocation-parties");
      if (res.data && res.data.employees) {
        setStaffParties(res.data.employees);
      }
    } catch (err: any) {
      console.error("Error loading staff parties:", err);
    }
  }, []);

  // Load Expense Categories
  const loadCategories = useCallback(async () => {
    setLoadingCategories(true);
    try {
      const res = await api.get("/expense-categories/list");
      if (res.data) {
        setMainCategories(res.data.main_categories || []);
        setSubCategories(res.data.sub_categories || []);
      }
    } catch (err: any) {
      console.error("Error loading categories:", err);
    } finally {
      setLoadingCategories(false);
    }
  }, []);

  // Load Bank Accounts for selected company
  const loadBankAccounts = useCallback(async (companyId: number | string) => {
    if (!companyId) {
      setBankAccounts([]);
      return;
    }
    setLoadingBanks(true);
    try {
      const res = await api.get(`/staff/accounts/ledger-masters/bank-accounts?company_id=${companyId}`);
      if (res.data && res.data.accounts) {
        setBankAccounts(res.data.accounts);
      } else {
        setBankAccounts([]);
      }
    } catch (err: any) {
      console.error("Error loading bank accounts:", err);
      setBankAccounts([]);
    } finally {
      setLoadingBanks(false);
    }
  }, []);

  // Load Allocations List
  const loadAllocations = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString(),
      });

      if (filterStatus) params.append("status", filterStatus);
      if (filterCompany) params.append("company_id", filterCompany);
      if (filterRecipient) params.append("to_employee_id", filterRecipient);
      if (filterFromDate) params.append("from_date", filterFromDate);
      if (filterToDate) params.append("to_date", filterToDate);

      const res = await api.get(`/staff/accounts/fund-allocations?${params.toString()}`);
      if (res.data && res.data.allocations) {
        setAllocations(res.data.allocations);
        setTotalRecords(res.data.total || res.data.allocations.length);
        setTotalPages(res.data.total_pages || Math.ceil((res.data.total || 1) / pageSize));
      } else {
        setAllocations([]);
        setTotalRecords(0);
        setTotalPages(1);
      }
    } catch (err: any) {
      console.error("Error loading fund allocations:", err);
      toast.error(err?.response?.data?.detail || "Failed to load fund allocations");
      setAllocations([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, filterStatus, filterCompany, filterRecipient, filterFromDate, filterToDate]);

  // Initial load
  useEffect(() => {
    if (token) {
      Promise.all([loadCompanies(), loadStaffList(), loadCategories()]);
    }
  }, [token, loadCompanies, loadStaffList, loadCategories]);

  useEffect(() => {
    if (token) {
      loadAllocations();
    }
  }, [token, loadAllocations]);

  // Watch company selection in create form to load bank accounts
  useEffect(() => {
    if (createForm.company_id && createForm.payment_source === "ACCOUNT") {
      loadBankAccounts(createForm.company_id);
    }
  }, [createForm.company_id, createForm.payment_source, loadBankAccounts]);

  // ----------------------------------------------------------------------
  // Calculated Summaries
  // ----------------------------------------------------------------------
  const summary: AllocationSummary = useMemo(() => {
    let pendingCount = 0;
    let pendingAmount = 0;
    let confirmedCount = 0;
    let confirmedAmount = 0;
    let settledCount = 0;
    let settledAmount = 0;
    let totalAmount = 0;

    allocations.forEach((a) => {
      const amt = Number(a.amount) || 0;
      totalAmount += amt;
      if (a.status === "PENDING") {
        pendingCount += 1;
        pendingAmount += amt;
      } else if (a.status === "CONFIRMED" || a.status === "PARTIALLY_SETTLED") {
        confirmedCount += 1;
        confirmedAmount += amt;
      } else if (a.status === "SETTLED") {
        settledCount += 1;
        settledAmount += amt;
      }
    });

    return {
      pending_count: pendingCount,
      pending_amount: pendingAmount,
      confirmed_count: confirmedCount,
      confirmed_amount: confirmedAmount,
      settled_count: settledCount,
      settled_amount: settledAmount,
      total_count: allocations.length,
      total_amount: totalAmount,
    };
  }, [allocations]);

  // Client search filtering
  const filteredAllocations = useMemo(() => {
    if (!filterSearch.trim() && !filterPaymentMode) return allocations;
    return allocations.filter((a) => {
      const matchSearch =
        !filterSearch.trim() ||
        (a.allocation_number && a.allocation_number.toLowerCase().includes(filterSearch.toLowerCase())) ||
        (a.id && a.id.toString().includes(filterSearch)) ||
        (a.to_employee_name && a.to_employee_name.toLowerCase().includes(filterSearch.toLowerCase())) ||
        (a.recipient_name && a.recipient_name.toLowerCase().includes(filterSearch.toLowerCase())) ||
        (a.from_employee_name && a.from_employee_name.toLowerCase().includes(filterSearch.toLowerCase())) ||
        (a.company_name && a.company_name.toLowerCase().includes(filterSearch.toLowerCase())) ||
        (a.purpose && a.purpose.toLowerCase().includes(filterSearch.toLowerCase())) ||
        (a.payment_reference && a.payment_reference.toLowerCase().includes(filterSearch.toLowerCase()));

      const matchPaymentMode =
        !filterPaymentMode ||
        (filterPaymentMode === "CASH" && a.payment_mode === "CASH") ||
        (filterPaymentMode === "ACCOUNT" && a.payment_mode !== "CASH");

      return matchSearch && matchPaymentMode;
    });
  }, [allocations, filterSearch, filterPaymentMode]);

  // Filtered sub-categories based on selected main category
  const availableSubCategories = useMemo(() => {
    if (!createForm.main_category_id) return [];
    return subCategories.filter((s) => s.parent_id === Number(createForm.main_category_id));
  }, [createForm.main_category_id, subCategories]);

  // ----------------------------------------------------------------------
  // Formatters & Helpers
  // ----------------------------------------------------------------------
  const formatCurrency = (val?: number | string | null) => {
    const num = Number(val) || 0;
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const formatDate = (val?: string | null) => {
    if (!val) return "—";
    try {
      const d = new Date(val);
      if (isNaN(d.getTime())) return val;
      return d.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    } catch {
      return val;
    }
  };

  const formatDateTime = (val?: string | null) => {
    if (!val) return "—";
    try {
      const d = new Date(val);
      if (isNaN(d.getTime())) return val;
      return d.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return val;
    }
  };

  const copyToClipboard = (text: string, label = "Copied to clipboard") => {
    navigator.clipboard.writeText(text);
    toast.success(label);
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case "PENDING":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            Pending
          </span>
        );
      case "CONFIRMED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Check className="w-3.5 h-3.5 text-blue-600" />
            Confirmed
          </span>
        );
      case "SETTLED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
            Settled
          </span>
        );
      case "PARTIALLY_SETTLED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
            Partially Settled
          </span>
        );
      case "CANCELLED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3.5 h-3.5 text-rose-600" />
            Cancelled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
            {status || "Unknown"}
          </span>
        );
    }
  };

  // ----------------------------------------------------------------------
  // Handlers & Actions
  // ----------------------------------------------------------------------

  const handleResetFilters = () => {
    setFilterSearch("");
    setFilterStatus("");
    setFilterCompany("");
    setFilterRecipient("");
    setFilterPaymentMode("");
    setFilterFromDate("");
    setFilterToDate("");
    setCurrentPage(1);
  };

  // Create Fund Allocation
  const handleCreateAllocation = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!createForm.company_id) {
      toast.error("Please select an Associated Company");
      return;
    }
    if (!createForm.to_employee_id) {
      toast.error("Please select a Recipient Staff");
      return;
    }
    if (!createForm.allocation_date) {
      toast.error("Please select Allocation Date");
      return;
    }
    const amt = parseFloat(createForm.amount);
    if (isNaN(amt) || amt <= 0) {
      toast.error("Please enter a valid positive amount");
      return;
    }
    if (createForm.payment_source === "ACCOUNT" && !createForm.bank_account_id) {
      toast.error("Please select a Bank / Ledger Account");
      return;
    }

    const selectedBank = bankAccounts.find((b) => b.id === Number(createForm.bank_account_id));
    const payload: any = {
      company_id: parseInt(createForm.company_id),
      to_employee_id: parseInt(createForm.to_employee_id),
      allocation_date: createForm.allocation_date,
      amount: amt,
      purpose: createForm.purpose.trim() || null,
      payment_reference: createForm.payment_reference.trim() || null,
      payment_mode: createForm.payment_source === "ACCOUNT" ? selectedBank?.account_type || "BANK" : "CASH",
      bank_account_id: createForm.payment_source === "ACCOUNT" ? parseInt(createForm.bank_account_id) : null,
    };

    if (createForm.sub_category_id) {
      payload.category_id = parseInt(createForm.sub_category_id);
    } else if (createForm.main_category_id) {
      payload.category_id = parseInt(createForm.main_category_id);
    }

    setActionLoading(true);
    try {
      const res = await api.post("/staff/accounts/fund-allocations", payload);
      if (res.status === 201 || res.data?.success || res.data?.id) {
        toast.success("Fund allocation created successfully!");
        setIsCreateOpen(false);
        setCreateForm({
          company_id: "",
          to_employee_id: "",
          payment_source: "CASH",
          bank_account_id: "",
          allocation_date: new Date().toISOString().split("T")[0],
          amount: "",
          main_category_id: "",
          sub_category_id: "",
          purpose: "",
          payment_reference: "",
        });
        loadAllocations();
      } else {
        toast.error(res.data?.detail || "Failed to create allocation");
      }
    } catch (err: any) {
      console.error("Create allocation error:", err);
      toast.error(err?.response?.data?.detail || err?.message || "Failed to create fund allocation");
    } finally {
      setActionLoading(false);
    }
  };

  // Confirm Fund Allocation
  const handleConfirmAllocation = async () => {
    if (!selectedAllocation) return;
    setActionLoading(true);
    try {
      const res = await api.post(`/staff/accounts/fund-allocations/${selectedAllocation.id}/confirm`, {
        confirmation_remarks: confirmRemarks.trim() || null,
      });
      if (res.data) {
        toast.success("Fund allocation confirmed successfully!");
        setIsConfirmOpen(false);
        setSelectedAllocation(null);
        setConfirmRemarks("");
        loadAllocations();
      }
    } catch (err: any) {
      console.error("Confirm allocation error:", err);
      toast.error(err?.response?.data?.detail || "Failed to confirm allocation");
    } finally {
      setActionLoading(false);
    }
  };

  // Settle Fund Allocation
  const handleSettleAllocation = async () => {
    if (!selectedAllocation) return;
    setActionLoading(true);
    try {
      const amt = settleAmount ? parseFloat(settleAmount) : undefined;
      const res = await api.post(`/staff/accounts/fund-allocations/${selectedAllocation.id}/settle`, {
        settlement_remarks: settleRemarks.trim() || null,
        settlement_amount: amt,
      });
      if (res.data) {
        toast.success("Fund allocation marked as settled!");
        setIsSettleOpen(false);
        setSelectedAllocation(null);
        setSettleAmount("");
        setSettleRemarks("");
        loadAllocations();
      }
    } catch (err: any) {
      console.error("Settle allocation error:", err);
      toast.error(err?.response?.data?.detail || "Failed to settle allocation");
    } finally {
      setActionLoading(false);
    }
  };

  // Cancel Fund Allocation
  const handleCancelAllocation = async () => {
    if (!selectedAllocation) return;
    if (!cancelReason.trim()) {
      toast.error("Please provide a cancellation reason");
      return;
    }
    setActionLoading(true);
    try {
      const res = await api.post(`/staff/accounts/fund-allocations/${selectedAllocation.id}/cancel`, {
        cancellation_reason: cancelReason.trim(),
      });
      if (res.data) {
        toast.success("Fund allocation cancelled successfully!");
        setIsCancelOpen(false);
        setSelectedAllocation(null);
        setCancelReason("");
        loadAllocations();
      }
    } catch (err: any) {
      console.error("Cancel allocation error:", err);
      toast.error(err?.response?.data?.detail || "Failed to cancel allocation");
    } finally {
      setActionLoading(false);
    }
  };

  // Quick Add Category
  const handleSaveQuickCat = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingQuickCat(true);
    try {
      if (quickCatMode === "main") {
        if (!quickCatMainName.trim()) {
          toast.error("Main Category Name is required");
          return;
        }
        const res = await api.post("/expense-categories/main/create", {
          name: quickCatMainName.trim(),
        });
        if (res.data?.success || res.status === 200) {
          toast.success("Main category created!");
          await loadCategories();
          if (res.data?.category_id) {
            setCreateForm((prev) => ({
              ...prev,
              main_category_id: res.data.category_id.toString(),
            }));
          }
          setIsQuickCatOpen(false);
          setQuickCatMainName("");
        }
      } else {
        if (!quickCatParentId) {
          toast.error("Please select a parent main category");
          return;
        }
        if (!quickCatSubName.trim()) {
          toast.error("Sub Category Name is required");
          return;
        }
        const res = await api.post("/expense-categories/sub/create", {
          parent_id: parseInt(quickCatParentId),
          name: quickCatSubName.trim(),
        });
        if (res.data?.success || res.status === 200) {
          toast.success("Sub category created!");
          await loadCategories();
          setCreateForm((prev) => ({
            ...prev,
            main_category_id: quickCatParentId,
            sub_category_id: res.data?.category_id ? res.data.category_id.toString() : prev.sub_category_id,
          }));
          setIsQuickCatOpen(false);
          setQuickCatSubName("");
        }
      }
    } catch (err: any) {
      console.error("Quick category create error:", err);
      toast.error(err?.response?.data?.message || err?.response?.data?.detail || "Failed to create category");
    } finally {
      setSavingQuickCat(false);
    }
  };

  // Export CSV
  const handleExportCSV = () => {
    if (!filteredAllocations.length) {
      toast.error("No records to export");
      return;
    }
    const headers = [
      "ID",
      "Allocation Number",
      "Date",
      "Company",
      "From Employee",
      "To Employee",
      "Payment Mode",
      "Amount",
      "Balance Remaining",
      "Balance Used",
      "Status",
      "Purpose",
      "Reference",
    ];

    const rows = filteredAllocations.map((a) => [
      a.id,
      a.allocation_number || `FA-${a.id}`,
      a.allocation_date || "",
      `"${(a.company_name || "").replace(/"/g, '""')}"`,
      `"${(a.from_employee_name || "").replace(/"/g, '""')}"`,
      `"${(a.to_employee_name || a.recipient_name || "").replace(/"/g, '""')}"`,
      a.payment_mode || "CASH",
      a.amount || 0,
      a.balance_remaining || 0,
      a.balance_used || 0,
      a.status || "",
      `"${(a.purpose || "").replace(/"/g, '""')}"`,
      `"${(a.payment_reference || "").replace(/"/g, '""')}"`,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `fund_allocations_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("Fund allocations exported to CSV");
  };

  // ==========================================
  // Render
  // ==========================================
  return (
    <div className="min-h-screen bg-slate-50/60 p-4 md:p-8 space-y-6 animate-in fade-in duration-300">
      <Toaster position="top-right" />

      {/* ──────────────── Top Navigation & Header ──────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 md:p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-slate-500 uppercase mb-1.5">
            <Link href="/staff/accounts" className="hover:text-primary transition-colors">
              Accounts
            </Link>
            <span>/</span>
            <span className="text-slate-900">Fund Allocations</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl border border-blue-100">
              <Wallet className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">Fund Allocations</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Manage accountant-to-staff fund transfers with PENDING, CONFIRMED, and SETTLED workflows.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={loadAllocations}
            disabled={loading}
            className="border-slate-200 hover:bg-slate-50 text-slate-700 h-9"
          >
            <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? "animate-spin text-primary" : ""}`} />
            Refresh
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            disabled={loading || filteredAllocations.length === 0}
            className="border-slate-200 hover:bg-slate-50 text-slate-700 h-9"
          >
            <Download className="w-4 h-4 mr-1.5" />
            Export CSV
          </Button>

          <Link href="/staff/accounts/expense-entries">
            <Button variant="outline" size="sm" className="border-slate-200 hover:bg-slate-50 text-slate-700 h-9">
              <FileText className="w-4 h-4 mr-1.5" />
              Expense Entries
            </Button>
          </Link>

          <Button
            onClick={() => setIsCreateOpen(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm font-semibold h-9 px-4 rounded-lg flex items-center gap-1.5 transition-all"
          >
            <Plus className="w-4 h-4" />
            New Allocation
          </Button>
        </div>
      </div>

      {/* ──────────────── Summary KPI Cards ──────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pending Card */}
        <Card className="border-amber-100 bg-linear-to-br from-amber-50/40 via-white to-white shadow-xs rounded-xl hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-amber-100/70 text-amber-700 rounded-xl">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-amber-700">Pending</p>
                  <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{summary.pending_count}</h3>
                </div>
              </div>
              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-[11px]">
                Awaiting Recipient
              </Badge>
            </div>
            <div className="mt-3 pt-3 border-t border-amber-100/60 flex items-center justify-between text-xs">
              <span className="text-slate-500">Volume</span>
              <span className="font-semibold text-slate-800">{formatCurrency(summary.pending_amount)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Confirmed Card */}
        <Card className="border-blue-100 bg-linear-to-br from-blue-50/40 via-white to-white shadow-xs rounded-xl hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-100/70 text-blue-700 rounded-xl">
                  <Check className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-blue-700">Confirmed</p>
                  <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{summary.confirmed_count}</h3>
                </div>
              </div>
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-[11px]">
                Active Balance
              </Badge>
            </div>
            <div className="mt-3 pt-3 border-t border-blue-100/60 flex items-center justify-between text-xs">
              <span className="text-slate-500">Active Capital</span>
              <span className="font-semibold text-slate-800">{formatCurrency(summary.confirmed_amount)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Settled Card */}
        <Card className="border-emerald-100 bg-linear-to-br from-emerald-50/40 via-white to-white shadow-xs rounded-xl hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-emerald-100/70 text-emerald-700 rounded-xl">
                  <CheckCheck className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Settled</p>
                  <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{summary.settled_count}</h3>
                </div>
              </div>
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[11px]">
                Fully Reconciled
              </Badge>
            </div>
            <div className="mt-3 pt-3 border-t border-emerald-100/60 flex items-center justify-between text-xs">
              <span className="text-slate-500">Settled Value</span>
              <span className="font-semibold text-slate-800">{formatCurrency(summary.settled_amount)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Total Card */}
        <Card className="border-slate-200 bg-linear-to-br from-slate-50/80 via-white to-white shadow-xs rounded-xl hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-100/70 text-purple-700 rounded-xl">
                  <Landmark className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-600">Total Allocations</p>
                  <h3 className="text-2xl font-bold text-slate-900 mt-0.5">{totalRecords}</h3>
                </div>
              </div>
              <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 text-[11px]">
                Total Records
              </Badge>
            </div>
            <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">Total Allocated</span>
              <span className="font-semibold text-slate-900">{formatCurrency(summary.total_amount)}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ──────────────── Filter & Search Section ──────────────── */}
      <Card className="border-slate-200/90 shadow-xs rounded-xl bg-white overflow-hidden">
        <CardContent className="p-4 md:p-5 space-y-4">
          <div className="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center justify-between">
            {/* Quick Search */}
            <div className="relative flex-1 min-w-[240px]">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input
                type="text"
                placeholder="Search by ID, staff name, reference or purpose..."
                value={filterSearch}
                onChange={(e) => setFilterSearch(e.target.value)}
                className="pl-9.5 bg-slate-50/50 border-slate-200 focus:bg-white h-10 text-sm rounded-lg"
              />
              {filterSearch && (
                <button
                  onClick={() => setFilterSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Filter Dropdowns */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:flex flex-wrap items-center gap-2.5">
              {/* Status Filter */}
              <div className="min-w-[140px]">
                <select
                  value={filterStatus}
                  onChange={(e) => {
                    setFilterStatus(e.target.value);
                    setCurrentPage(1);
                  }}
                  aria-label="Filter by status"
                  className="w-full h-10 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg shadow-2xs hover:border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="CONFIRMED">Confirmed</option>
                  <option value="SETTLED">Settled</option>
                  <option value="PARTIALLY_SETTLED">Partially Settled</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              </div>

              {/* Company Filter */}
              <div className="min-w-[160px]">
                <select
                  value={filterCompany}
                  onChange={(e) => {
                    setFilterCompany(e.target.value);
                    setCurrentPage(1);
                  }}
                  aria-label="Filter by company"
                  className="w-full h-10 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg shadow-2xs hover:border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name || `Company ${c.id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* Recipient Filter */}
              <div className="min-w-[160px]">
                <select
                  value={filterRecipient}
                  onChange={(e) => {
                    setFilterRecipient(e.target.value);
                    setCurrentPage(1);
                  }}
                  aria-label="Filter by recipient"
                  className="w-full h-10 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg shadow-2xs hover:border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Recipients</option>
                  {staffParties.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.full_name} ({s.emp_code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Payment Mode Filter */}
              <div className="min-w-[130px]">
                <select
                  value={filterPaymentMode}
                  onChange={(e) => setFilterPaymentMode(e.target.value)}
                  aria-label="Filter by payment mode"
                  className="w-full h-10 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg shadow-2xs hover:border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Modes</option>
                  <option value="CASH">Cash</option>
                  <option value="ACCOUNT">Bank Account</option>
                </select>
              </div>

              {/* Date Filters */}
              <div className="flex items-center gap-1.5">
                <input
                  type="date"
                  value={filterFromDate}
                  onChange={(e) => {
                    setFilterFromDate(e.target.value);
                    setCurrentPage(1);
                  }}
                  aria-label="From date"
                  className="h-10 px-2.5 py-1.5 text-xs text-slate-700 bg-white border border-slate-200 rounded-lg shadow-2xs focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-slate-400 text-xs">to</span>
                <input
                  type="date"
                  value={filterToDate}
                  onChange={(e) => {
                    setFilterToDate(e.target.value);
                    setCurrentPage(1);
                  }}
                  aria-label="To date"
                  className="h-10 px-2.5 py-1.5 text-xs text-slate-700 bg-white border border-slate-200 rounded-lg shadow-2xs focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Reset Filter Button */}
              {(filterStatus ||
                filterCompany ||
                filterRecipient ||
                filterPaymentMode ||
                filterFromDate ||
                filterToDate ||
                filterSearch) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleResetFilters}
                  className="h-10 text-xs text-slate-500 hover:text-slate-900"
                >
                  <X className="w-3.5 h-3.5 mr-1" />
                  Clear
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ──────────────── Data Table Card ──────────────── */}
      <Card className="border-slate-200/90 shadow-xs rounded-xl bg-white overflow-hidden">
        <CardHeader className="p-4 md:px-6 md:py-4 border-b border-slate-100 bg-slate-50/50 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-500" />
            <CardTitle className="text-sm md:text-base font-semibold text-slate-900">Fund Allocation Records</CardTitle>
            <Badge variant="secondary" className="font-normal text-xs bg-slate-200/70 text-slate-700">
              {filteredAllocations.length} records
            </Badge>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">Page {currentPage} of {totalPages}</p>
        </CardHeader>

        <CardContent className="p-0">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center text-slate-400 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              <p className="text-sm font-medium text-slate-500">Loading fund allocations...</p>
            </div>
          ) : filteredAllocations.length === 0 ? (
            <div className="py-16 text-center text-slate-500 flex flex-col items-center justify-center p-6">
              <div className="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                <FolderOpen className="w-7 h-7 text-slate-400" />
              </div>
              <h3 className="text-base font-semibold text-slate-800 mb-1">No fund allocations found</h3>
              <p className="text-xs text-slate-500 max-w-sm mb-4">
                {filterSearch || filterStatus || filterCompany
                  ? "No records match your active filters. Try resetting or adjusting your query."
                  : "No allocations have been registered yet. Create your first fund allocation to begin."}
              </p>
              {filterSearch || filterStatus || filterCompany ? (
                <Button variant="outline" size="sm" onClick={handleResetFilters} className="text-xs">
                  Reset Filters
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={() => setIsCreateOpen(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Create Allocation
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200/80 text-xs font-bold text-slate-600 uppercase tracking-wider">
                    <th className="py-3 px-4">Allocation ID</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Company</th>
                    <th className="py-3 px-4">From</th>
                    <th className="py-3 px-4">Recipient</th>
                    <th className="py-3 px-4">Mode</th>
                    <th className="py-3 px-4 text-right">Amount</th>
                    <th className="py-3 px-4 text-right">Balance Used</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredAllocations.map((alloc) => (
                    <tr
                      key={alloc.id}
                      className="hover:bg-slate-50/80 transition-colors group text-slate-700"
                    >
                      {/* ID / Code */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <code className="px-2 py-0.5 bg-slate-100 font-mono text-xs font-semibold rounded text-slate-800 border border-slate-200">
                            {alloc.allocation_number || `#FA-${alloc.id}`}
                          </code>
                          <button
                            onClick={() => copyToClipboard(alloc.allocation_number || `FA-${alloc.id}`, "Allocation ID copied")}
                            title="Copy ID"
                            className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-600 transition-opacity"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>

                      {/* Date */}
                      <td className="py-3.5 px-4 whitespace-nowrap font-medium text-slate-800 text-xs">
                        {formatDate(alloc.allocation_date || alloc.created_at)}
                      </td>

                      {/* Company */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="font-medium text-slate-900 truncate max-w-[140px]" title={alloc.company_name || ""}>
                            {alloc.company_name || "—"}
                          </span>
                        </div>
                      </td>

                      {/* From Employee */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-600">
                        {alloc.from_employee_name || "Accountant"}
                      </td>

                      {/* Recipient */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[10px] font-bold">
                            {(alloc.to_employee_name || alloc.recipient_name || "S").charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-900 text-xs">
                              {alloc.to_employee_name || alloc.recipient_name || "Staff Member"}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Payment Mode */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {alloc.payment_mode === "CASH" ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <Banknote className="w-3 h-3" />
                            Cash
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            <Landmark className="w-3 h-3" />
                            {alloc.payment_mode || "Bank"}
                          </span>
                        )}
                      </td>

                      {/* Amount */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-right font-mono font-bold text-slate-900">
                        {formatCurrency(alloc.amount)}
                      </td>

                      {/* Balance Used */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-right font-mono text-xs">
                        <span className={alloc.balance_used > 0 ? "font-semibold text-slate-800" : "text-slate-400"}>
                          {formatCurrency(alloc.balance_used)}
                        </span>
                        {alloc.balance_remaining !== undefined && alloc.balance_remaining !== alloc.amount && (
                          <div className="text-[10px] text-slate-400">
                            Bal: {formatCurrency(alloc.balance_remaining)}
                          </div>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-center">
                        {getStatusBadge(alloc.status)}
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* View Detail Button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedAllocation(alloc);
                              setIsDetailOpen(true);
                            }}
                            title="View Allocation Details"
                            className="h-7 w-7 p-0 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-md"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>

                          {/* Confirm Action (Pending) */}
                          {canConfirm(alloc) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedAllocation(alloc);
                                setConfirmRemarks("");
                                setIsConfirmOpen(true);
                              }}
                              title="Confirm Allocation Receipt"
                              className="h-7 px-2 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 hover:text-blue-800 rounded-md flex items-center gap-1"
                            >
                              <Check className="w-3.5 h-3.5" />
                              Confirm
                            </Button>
                          )}

                          {/* Settle Action (Confirmed) */}
                          {canSettle(alloc) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedAllocation(alloc);
                                setSettleAmount(alloc.balance_remaining ? alloc.balance_remaining.toString() : "");
                                setSettleRemarks("");
                                setIsSettleOpen(true);
                              }}
                              title="Mark Allocation Settled"
                              className="h-7 px-2 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 hover:text-emerald-800 rounded-md flex items-center gap-1"
                            >
                              <CheckCheck className="w-3.5 h-3.5" />
                              Settle
                            </Button>
                          )}

                          {/* Cancel Action (Pending/Confirmed with 0 expenses) */}
                          {canCancel(alloc) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedAllocation(alloc);
                                setCancelReason("");
                                setIsCancelOpen(true);
                              }}
                              title="Cancel Allocation"
                              className="h-7 w-7 p-0 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-md"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-slate-100 bg-slate-50/40 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600">
              <div>
                Showing{" "}
                <span className="font-semibold text-slate-900">
                  {(currentPage - 1) * pageSize + 1}
                </span>{" "}
                to{" "}
                <span className="font-semibold text-slate-900">
                  {Math.min(currentPage * pageSize, totalRecords)}
                </span>{" "}
                of <span className="font-semibold text-slate-900">{totalRecords}</span> entries
              </div>

              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1 || loading}
                  className="h-8 px-2.5 text-xs"
                >
                  <ChevronLeft className="w-4 h-4 mr-0.5" />
                  Prev
                </Button>

                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                  .map((p, idx, arr) => {
                    const prev = arr[idx - 1];
                    const showEllipsis = prev && p - prev > 1;
                    return (
                      <React.Fragment key={p}>
                        {showEllipsis && <span className="px-1 text-slate-400">...</span>}
                        <Button
                          variant={currentPage === p ? "default" : "outline"}
                          size="sm"
                          onClick={() => setCurrentPage(p)}
                          className={`h-8 w-8 p-0 text-xs font-semibold ${
                            currentPage === p ? "bg-blue-600 text-white" : ""
                          }`}
                        >
                          {p}
                        </Button>
                      </React.Fragment>
                    );
                  })}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages || loading}
                  className="h-8 px-2.5 text-xs"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-0.5" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ──────────────── Create Fund Allocation Dialog ──────────────── */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto bg-white p-6 rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl">
                <Wallet className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold text-slate-900">New Fund Allocation</DialogTitle>
                <DialogDescription className="text-xs text-slate-500">
                  Allocate funds to staff with party ledger tracking and approval lifecycle.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <form onSubmit={handleCreateAllocation} className="space-y-4 pt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Company */}
              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">
                  Associated Company <span className="text-rose-500">*</span>
                </Label>
                <select
                  required
                  value={createForm.company_id}
                  onChange={(e) => setCreateForm({ ...createForm, company_id: e.target.value })}
                  className="w-full h-10 px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg shadow-2xs focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— Select Company —</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name || `Company ${c.id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* Recipient Staff */}
              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">
                  Recipient Staff <span className="text-rose-500">*</span>
                </Label>
                <select
                  required
                  value={createForm.to_employee_id}
                  onChange={(e) => setCreateForm({ ...createForm, to_employee_id: e.target.value })}
                  className="w-full h-10 px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg shadow-2xs focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— Select Staff Recipient —</option>
                  {staffParties.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.full_name} ({s.emp_code}) {s.role ? `• ${s.role}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Payment Source Mode */}
              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">
                  Payment Source <span className="text-rose-500">*</span>
                </Label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setCreateForm({ ...createForm, payment_source: "CASH", bank_account_id: "" })}
                    className={`h-10 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                      createForm.payment_source === "CASH"
                        ? "bg-emerald-50 border-emerald-500 text-emerald-700 ring-2 ring-emerald-500/20"
                        : "border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <Banknote className="w-4 h-4" />
                    Cash
                  </button>
                  <button
                    type="button"
                    onClick={() => setCreateForm({ ...createForm, payment_source: "ACCOUNT" })}
                    className={`h-10 rounded-lg border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                      createForm.payment_source === "ACCOUNT"
                        ? "bg-blue-50 border-blue-500 text-blue-700 ring-2 ring-blue-500/20"
                        : "border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <Landmark className="w-4 h-4" />
                    Bank Account
                  </button>
                </div>
              </div>

              {/* Allocation Date */}
              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">
                  Allocation Date <span className="text-rose-500">*</span>
                </Label>
                <Input
                  type="date"
                  required
                  value={createForm.allocation_date}
                  onChange={(e) => setCreateForm({ ...createForm, allocation_date: e.target.value })}
                  className="h-10 text-xs"
                />
              </div>
            </div>

            {/* Bank Account Selection (Visible when ACCOUNT mode is chosen) */}
            {createForm.payment_source === "ACCOUNT" && (
              <div className="p-3.5 bg-blue-50/50 border border-blue-100 rounded-xl space-y-1.5 animate-in fade-in duration-200">
                <Label className="text-xs font-bold text-blue-900 flex items-center justify-between">
                  <span>Select Company Bank / Ledger Account <span className="text-rose-500">*</span></span>
                  {loadingBanks && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />}
                </Label>
                <select
                  required
                  value={createForm.bank_account_id}
                  onChange={(e) => setCreateForm({ ...createForm, bank_account_id: e.target.value })}
                  className="w-full h-10 px-3 py-2 text-xs bg-white border border-blue-200 rounded-lg shadow-2xs focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— Select Bank Account —</option>
                  {bankAccounts.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.bank_name} - {b.account_number} ({b.account_type})
                    </option>
                  ))}
                </select>
                {bankAccounts.length === 0 && !loadingBanks && createForm.company_id && (
                  <p className="text-[11px] text-amber-600 mt-1">
                    No active bank accounts found for this company in Ledger Masters.
                  </p>
                )}
              </div>
            )}

            {/* Amount */}
            <div className="space-y-1.5">
              <Label className="text-xs font-bold text-slate-700">
                Allocation Amount (₹) <span className="text-rose-500">*</span>
              </Label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 font-bold text-sm">₹</span>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  placeholder="0.00"
                  value={createForm.amount}
                  onChange={(e) => setCreateForm({ ...createForm, amount: e.target.value })}
                  className="pl-8 h-11 text-base font-bold text-slate-900"
                />
              </div>
            </div>

            {/* Category with Quick Add */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-bold text-slate-700">
                  Expense Category <span className="text-slate-400 font-normal">(optional)</span>
                </Label>
                <button
                  type="button"
                  onClick={() => {
                    setQuickCatMode("sub");
                    setQuickCatMainName("");
                    setQuickCatSubName("");
                    setQuickCatParentId(createForm.main_category_id || "");
                    setIsQuickCatOpen(true);
                  }}
                  className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Add Category
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {/* Main Category */}
                <select
                  value={createForm.main_category_id}
                  onChange={(e) =>
                    setCreateForm({
                      ...createForm,
                      main_category_id: e.target.value,
                      sub_category_id: "",
                    })
                  }
                  className="w-full h-10 px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg shadow-2xs focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— Main Category —</option>
                  {mainCategories.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>

                {/* Sub Category */}
                <select
                  disabled={!createForm.main_category_id}
                  value={createForm.sub_category_id}
                  onChange={(e) => setCreateForm({ ...createForm, sub_category_id: e.target.value })}
                  className="w-full h-10 px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg shadow-2xs disabled:bg-slate-100 disabled:text-slate-400 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— Sub Category (optional) —</option>
                  {availableSubCategories.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Purpose */}
            <div className="space-y-1.5">
              <Label className="text-xs font-bold text-slate-700">Purpose / Description</Label>
              <Textarea
                placeholder="Reason or purpose for this fund allocation (e.g. Travel Advance, Project Site Petty Cash)..."
                rows={2}
                value={createForm.purpose}
                onChange={(e) => setCreateForm({ ...createForm, purpose: e.target.value })}
                className="text-xs"
              />
            </div>

            {/* Reference Number */}
            <div className="space-y-1.5">
              <Label className="text-xs font-bold text-slate-700">Payment Reference / UTR Number</Label>
              <Input
                type="text"
                placeholder="Cheque no., NEFT/IMPS UTR, or receipt reference"
                value={createForm.payment_reference}
                onChange={(e) => setCreateForm({ ...createForm, payment_reference: e.target.value })}
                className="h-10 text-xs"
              />
            </div>

            <DialogFooter className="pt-4 border-t border-slate-100 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
                disabled={actionLoading}
                className="h-10 text-xs"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={actionLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold h-10 text-xs px-5 flex items-center gap-1.5"
              >
                {actionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Create Allocation
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ──────────────── Confirm Fund Allocation Dialog ──────────────── */}
      <Dialog open={isConfirmOpen} onOpenChange={setIsConfirmOpen}>
        <DialogContent className="sm:max-w-md bg-white p-6 rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl">
                <Check className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold text-slate-900">Confirm Fund Allocation</DialogTitle>
                <DialogDescription className="text-xs text-slate-500">
                  Confirm receipt of funds. This creates a credit entry on the recipient party ledger.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedAllocation && (
            <div className="space-y-4 pt-2">
              <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Allocation Code:</span>
                  <span className="font-mono font-bold text-slate-900">
                    {selectedAllocation.allocation_number || `#FA-${selectedAllocation.id}`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Recipient Staff:</span>
                  <span className="font-semibold text-slate-900">
                    {selectedAllocation.to_employee_name || selectedAllocation.recipient_name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Allocated Amount:</span>
                  <span className="font-mono font-bold text-blue-700 text-sm">
                    {formatCurrency(selectedAllocation.amount)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Company:</span>
                  <span className="text-slate-700">{selectedAllocation.company_name}</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">Confirmation Remarks / Notes</Label>
                <Textarea
                  placeholder="Optional notes or remarks upon fund confirmation..."
                  rows={2}
                  value={confirmRemarks}
                  onChange={(e) => setConfirmRemarks(e.target.value)}
                  className="text-xs"
                />
              </div>

              <DialogFooter className="pt-2 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsConfirmOpen(false)}
                  disabled={actionLoading}
                  className="h-10 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleConfirmAllocation}
                  disabled={actionLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold h-10 text-xs px-5 flex items-center gap-1.5"
                >
                  {actionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm Receipt
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ──────────────── Settle Fund Allocation Dialog ──────────────── */}
      <Dialog open={isSettleOpen} onOpenChange={setIsSettleOpen}>
        <DialogContent className="sm:max-w-md bg-white p-6 rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-50 text-emerald-700 rounded-xl">
                <CheckCheck className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold text-slate-900">Settle Fund Allocation</DialogTitle>
                <DialogDescription className="text-xs text-slate-500">
                  Mark this allocation as settled after expenses are accounted for.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedAllocation && (
            <div className="space-y-4 pt-2">
              <div className="bg-emerald-50/60 border border-emerald-100 rounded-xl p-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Allocation Code:</span>
                  <span className="font-mono font-bold text-slate-900">
                    {selectedAllocation.allocation_number || `#FA-${selectedAllocation.id}`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Amount:</span>
                  <span className="font-mono font-bold text-slate-900">
                    {formatCurrency(selectedAllocation.amount)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Balance Remaining:</span>
                  <span className="font-mono font-bold text-emerald-700 text-sm">
                    {formatCurrency(selectedAllocation.balance_remaining)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Expenses Logged:</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {formatCurrency(selectedAllocation.balance_used)}
                  </span>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">
                  Settlement Amount (₹) <span className="text-slate-400 font-normal">(leave blank for full settlement)</span>
                </Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={selectedAllocation.balance_remaining}
                  placeholder={selectedAllocation.balance_remaining?.toString() || "Full amount"}
                  value={settleAmount}
                  onChange={(e) => setSettleAmount(e.target.value)}
                  className="h-10 text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">Settlement Remarks</Label>
                <Textarea
                  placeholder="Optional settlement notes or reconciliation details..."
                  rows={2}
                  value={settleRemarks}
                  onChange={(e) => setSettleRemarks(e.target.value)}
                  className="text-xs"
                />
              </div>

              <DialogFooter className="pt-2 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsSettleOpen(false)}
                  disabled={actionLoading}
                  className="h-10 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleSettleAllocation}
                  disabled={actionLoading}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold h-10 text-xs px-5 flex items-center gap-1.5"
                >
                  {actionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Mark Settled
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ──────────────── Cancel Fund Allocation Dialog ──────────────── */}
      <Dialog open={isCancelOpen} onOpenChange={setIsCancelOpen}>
        <DialogContent className="sm:max-w-md bg-white p-6 rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-rose-50 text-rose-700 rounded-xl">
                <XCircle className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold text-slate-900">Cancel Fund Allocation</DialogTitle>
                <DialogDescription className="text-xs text-slate-500">
                  Cancelling will reverse any created ledger entries for this allocation.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedAllocation && (
            <div className="space-y-4 pt-2">
              <div className="bg-rose-50/60 border border-rose-100 rounded-xl p-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Allocation Code:</span>
                  <span className="font-mono font-bold text-slate-900">
                    {selectedAllocation.allocation_number || `#FA-${selectedAllocation.id}`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Amount:</span>
                  <span className="font-mono font-bold text-rose-700">
                    {formatCurrency(selectedAllocation.amount)}
                  </span>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">
                  Reason for Cancellation <span className="text-rose-500">*</span>
                </Label>
                <Textarea
                  required
                  placeholder="Explain why this fund allocation is being cancelled..."
                  rows={3}
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  className="text-xs"
                />
              </div>

              <DialogFooter className="pt-2 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCancelOpen(false)}
                  disabled={actionLoading}
                  className="h-10 text-xs"
                >
                  Close
                </Button>
                <Button
                  type="button"
                  onClick={handleCancelAllocation}
                  disabled={actionLoading}
                  className="bg-rose-600 hover:bg-rose-700 text-white font-semibold h-10 text-xs px-5 flex items-center gap-1.5"
                >
                  {actionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm Cancellation
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ──────────────── Detail View Sheet / Dialog ──────────────── */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto bg-white p-6 rounded-2xl">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <DialogTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                    Allocation Details
                    {selectedAllocation && (
                      <code className="text-xs font-mono px-2 py-0.5 bg-slate-100 text-slate-800 rounded">
                        {selectedAllocation.allocation_number || `#FA-${selectedAllocation.id}`}
                      </code>
                    )}
                  </DialogTitle>
                  <DialogDescription className="text-xs text-slate-500">
                    Comprehensive breakdown of this fund allocation and ledger state.
                  </DialogDescription>
                </div>
              </div>
            </div>
          </DialogHeader>

          {selectedAllocation && (
            <div className="space-y-5 pt-2">
              {/* Top Highlight Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-[11px] font-bold text-slate-500 uppercase">Allocated Amount</p>
                  <p className="text-base font-bold text-slate-900 mt-1 font-mono">
                    {formatCurrency(selectedAllocation.amount)}
                  </p>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-[11px] font-bold text-slate-500 uppercase">Balance Used</p>
                  <p className="text-base font-bold text-slate-900 mt-1 font-mono">
                    {formatCurrency(selectedAllocation.balance_used)}
                  </p>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-[11px] font-bold text-slate-500 uppercase">Remaining</p>
                  <p className="text-base font-bold text-emerald-700 mt-1 font-mono">
                    {formatCurrency(selectedAllocation.balance_remaining)}
                  </p>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-[11px] font-bold text-slate-500 uppercase">Status</p>
                  <div className="mt-1">{getStatusBadge(selectedAllocation.status)}</div>
                </div>
              </div>

              {/* Details Breakdown */}
              <div className="border border-slate-200/80 rounded-xl divide-y divide-slate-100 text-xs">
                <div className="p-3.5 flex justify-between items-center bg-slate-50/50">
                  <span className="font-semibold text-slate-700">Company</span>
                  <span className="font-medium text-slate-900">{selectedAllocation.company_name || "—"}</span>
                </div>
                <div className="p-3.5 flex justify-between items-center">
                  <span className="font-semibold text-slate-700">Allocated By</span>
                  <span className="text-slate-800">{selectedAllocation.from_employee_name || "Accountant"}</span>
                </div>
                <div className="p-3.5 flex justify-between items-center bg-slate-50/50">
                  <span className="font-semibold text-slate-700">Recipient Staff</span>
                  <span className="font-semibold text-slate-900">
                    {selectedAllocation.to_employee_name || selectedAllocation.recipient_name || "—"}
                  </span>
                </div>
                <div className="p-3.5 flex justify-between items-center">
                  <span className="font-semibold text-slate-700">Payment Mode / Source</span>
                  <span className="font-medium text-slate-900">{selectedAllocation.payment_mode || "CASH"}</span>
                </div>
                {selectedAllocation.payment_reference && (
                  <div className="p-3.5 flex justify-between items-center bg-slate-50/50">
                    <span className="font-semibold text-slate-700">Reference / UTR</span>
                    <span className="font-mono text-slate-800">{selectedAllocation.payment_reference}</span>
                  </div>
                )}
                {selectedAllocation.purpose && (
                  <div className="p-3.5 flex flex-col gap-1">
                    <span className="font-semibold text-slate-700">Purpose / Description</span>
                    <p className="text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      {selectedAllocation.purpose}
                    </p>
                  </div>
                )}
                {selectedAllocation.settlement_remarks && (
                  <div className="p-3.5 flex flex-col gap-1 bg-slate-50/50">
                    <span className="font-semibold text-slate-700">Settlement / Confirmation Notes</span>
                    <p className="text-slate-600 leading-relaxed">{selectedAllocation.settlement_remarks}</p>
                  </div>
                )}
                <div className="p-3.5 flex justify-between items-center">
                  <span className="font-semibold text-slate-700">Allocation Date</span>
                  <span className="text-slate-800">{formatDate(selectedAllocation.allocation_date)}</span>
                </div>
                {selectedAllocation.confirmed_at && (
                  <div className="p-3.5 flex justify-between items-center bg-slate-50/50">
                    <span className="font-semibold text-slate-700">Confirmed At</span>
                    <span className="text-slate-800">{formatDateTime(selectedAllocation.confirmed_at)}</span>
                  </div>
                )}
                {selectedAllocation.settlement_date && (
                  <div className="p-3.5 flex justify-between items-center">
                    <span className="font-semibold text-slate-700">Settlement Date</span>
                    <span className="text-slate-800">{formatDate(selectedAllocation.settlement_date)}</span>
                  </div>
                )}
                <div className="p-3.5 flex justify-between items-center bg-slate-50/50">
                  <span className="font-semibold text-slate-700">Created Timestamp</span>
                  <span className="text-slate-500">{formatDateTime(selectedAllocation.created_at)}</span>
                </div>
              </div>

              {/* Action shortcut bar */}
              <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-slate-100">
                {canConfirm(selectedAllocation) && (
                  <Button
                    size="sm"
                    onClick={() => {
                      setIsDetailOpen(false);
                      setIsConfirmOpen(true);
                    }}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold h-9"
                  >
                    <Check className="w-3.5 h-3.5 mr-1" />
                    Confirm Allocation
                  </Button>
                )}

                {canSettle(selectedAllocation) && (
                  <Button
                    size="sm"
                    onClick={() => {
                      setIsDetailOpen(false);
                      setSettleAmount(selectedAllocation.balance_remaining ? selectedAllocation.balance_remaining.toString() : "");
                      setIsSettleOpen(true);
                    }}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold h-9"
                  >
                    <CheckCheck className="w-3.5 h-3.5 mr-1" />
                    Settle Allocation
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDetailOpen(false)}
                  className="h-9 text-xs"
                >
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ──────────────── Quick Add Category Dialog ──────────────── */}
      <Dialog open={isQuickCatOpen} onOpenChange={setIsQuickCatOpen}>
        <DialogContent className="sm:max-w-md bg-white p-6 rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-50 text-emerald-700 rounded-xl">
                <Tag className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold text-slate-900">Add Expense Category</DialogTitle>
                <DialogDescription className="text-xs text-slate-500">
                  Quickly register a new main or sub expense category.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <form onSubmit={handleSaveQuickCat} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-bold text-slate-700">Category Type</Label>
              <select
                value={quickCatMode}
                onChange={(e) => setQuickCatMode(e.target.value as "sub" | "main")}
                className="w-full h-10 px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg shadow-2xs focus:ring-2 focus:ring-emerald-500"
              >
                <option value="sub">Sub Category (under existing Main)</option>
                <option value="main">New Main Category</option>
              </select>
            </div>

            {quickCatMode === "main" ? (
              <div className="space-y-1.5">
                <Label className="text-xs font-bold text-slate-700">
                  Main Category Name <span className="text-rose-500">*</span>
                </Label>
                <Input
                  type="text"
                  required
                  placeholder="e.g. Travel & Conveyance, Vehicle Maintenance"
                  value={quickCatMainName}
                  onChange={(e) => setQuickCatMainName(e.target.value)}
                  className="h-10 text-xs"
                />
              </div>
            ) : (
              <>
                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">
                    Under Main Category <span className="text-rose-500">*</span>
                  </Label>
                  <select
                    required
                    value={quickCatParentId}
                    onChange={(e) => setQuickCatParentId(e.target.value)}
                    className="w-full h-10 px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg shadow-2xs focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="">— Select Main Category —</option>
                    {mainCategories.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-bold text-slate-700">
                    Sub Category Name <span className="text-rose-500">*</span>
                  </Label>
                  <Input
                    type="text"
                    required
                    placeholder="e.g. Fuel Expenses, Toll Charges, Client Dinner"
                    value={quickCatSubName}
                    onChange={(e) => setQuickCatSubName(e.target.value)}
                    className="h-10 text-xs"
                  />
                </div>
              </>
            )}

            <DialogFooter className="pt-2 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsQuickCatOpen(false)}
                disabled={savingQuickCat}
                className="h-10 text-xs"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={savingQuickCat}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold h-10 text-xs px-5 flex items-center gap-1.5"
              >
                {savingQuickCat && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Save Category
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

