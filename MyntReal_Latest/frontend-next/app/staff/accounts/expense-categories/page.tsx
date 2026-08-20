"use client";

import { useState, useEffect, useMemo } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import {
  Folder,
  FolderTree,
  Plus,
  Edit2,
  Trash2,
  Search,
  Coins,
  CircleDollarSign,
  TrendingDown,
  TrendingUp,
  Layers,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  X,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

interface MainCategory {
  id: number;
  name: string;
  description?: string | null;
  is_active?: boolean;
}

interface SubCategory {
  id: number;
  name: string;
  parent_id: number;
  description?: string | null;
  is_active?: boolean;
}

interface AmountSummaryItem {
  total: number;
  count: number;
}

export default function AccountsExpenseCategoriesPage() {
  const { token } = useStaffAuth();

  // Active section & tab
  const [section, setSection] = useState<"expense" | "income">("expense");
  const [activeTab, setActiveTab] = useState<"main" | "sub">("main");
  const [searchQuery, setSearchQuery] = useState("");

  // Data states
  const [expenseMain, setExpenseMain] = useState<MainCategory[]>([]);
  const [expenseSub, setExpenseSub] = useState<SubCategory[]>([]);
  const [incomeMain, setIncomeMain] = useState<MainCategory[]>([]);
  const [incomeSub, setIncomeSub] = useState<SubCategory[]>([]);

  // Amounts summary
  const [expenseAmounts, setExpenseAmounts] = useState<{
    main: Record<string, AmountSummaryItem>;
    sub: Record<string, AmountSummaryItem>;
  }>({ main: {}, sub: {} });

  const [incomeAmounts, setIncomeAmounts] = useState<{
    main: Record<string, AmountSummaryItem>;
    sub: Record<string, AmountSummaryItem>;
  }>({ main: {}, sub: {} });

  // UI state
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Sub-category pill expansion tracker for main category tables
  const [expandedPills, setExpandedPills] = useState<Record<number, boolean>>({});

  // Modal Dialog States
  const [modalType, setModalType] = useState<
    "expense_main" | "expense_sub" | "income_main" | "income_sub" | null
  >(null);
  const [editingItem, setEditingItem] = useState<
    MainCategory | SubCategory | null
  >(null);

  // Form State
  const [formData, setFormData] = useState({
    id: 0,
    name: "",
    parent_id: "" as number | string,
    description: "",
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Delete Dialog State
  const [deleteTarget, setDeleteTarget] = useState<{
    type: "expense_main" | "expense_sub" | "income_main" | "income_sub";
    id: number;
    name: string;
  } | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Auto-clear notification after 4s
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  // Load all expense and income categories
  const loadData = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      // 1. Fetch Expense Categories
      const expRes = await api.get("/expense-categories/list");
      if (expRes.data?.success) {
        setExpenseMain(expRes.data.main_categories || []);
        setExpenseSub(expRes.data.sub_categories || []);
        if (expRes.data.income_main_categories) {
          setIncomeMain(expRes.data.income_main_categories || []);
        }
        if (expRes.data.income_sub_categories) {
          setIncomeSub(expRes.data.income_sub_categories || []);
        }
      }

      // 2. Fetch Income Categories if not populated from list
      try {
        const incRes = await api.get("/income-categories/list");
        if (incRes.data?.success) {
          setIncomeMain(incRes.data.main_categories || []);
          setIncomeSub(incRes.data.sub_categories || []);
        }
      } catch (err) {
        console.warn("Direct income-categories/list load failed, using fallback:", err);
      }

      // 3. Fetch Amounts summaries (optional enrichment)
      try {
        const [expAmtRes, incAmtRes] = await Promise.allSettled([
          api.get("/expense-categories/amounts-summary"),
          api.get("/income-categories/amounts-summary"),
        ]);

        if (expAmtRes.status === "fulfilled" && expAmtRes.value.data?.success) {
          setExpenseAmounts({
            main: expAmtRes.value.data.main || {},
            sub: expAmtRes.value.data.sub || {},
          });
        }

        if (incAmtRes.status === "fulfilled" && incAmtRes.value.data?.success) {
          setIncomeAmounts({
            main: incAmtRes.value.data.main || {},
            sub: incAmtRes.value.data.sub || {},
          });
        }
      } catch (e) {
        // Soft fail for amounts summary
      }
    } catch (err: any) {
      console.error("Failed to load categories:", err);
      setNotification({
        type: "error",
        message: err?.response?.data?.message || err?.message || "Failed to load category data.",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  // Expand / collapse subcategory pills
  const toggleSubPills = (mainId: number) => {
    setExpandedPills((prev) => ({
      ...prev,
      [mainId]: !prev[mainId],
    }));
  };

  // Filtered lists based on search
  const filteredExpenseMain = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return expenseMain;
    return expenseMain.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q)) ||
        String(c.id).includes(q)
    );
  }, [expenseMain, searchQuery]);

  const filteredExpenseSub = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return expenseSub;
    return expenseSub.filter((s) => {
      const parent = expenseMain.find((m) => m.id === s.parent_id);
      return (
        s.name.toLowerCase().includes(q) ||
        (parent && parent.name.toLowerCase().includes(q)) ||
        (s.description && s.description.toLowerCase().includes(q)) ||
        String(s.id).includes(q)
      );
    });
  }, [expenseSub, expenseMain, searchQuery]);

  const filteredIncomeMain = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return incomeMain;
    return incomeMain.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q)) ||
        String(c.id).includes(q)
    );
  }, [incomeMain, searchQuery]);

  const filteredIncomeSub = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return incomeSub;
    return incomeSub.filter((s) => {
      const parent = incomeMain.find((m) => m.id === s.parent_id);
      return (
        s.name.toLowerCase().includes(q) ||
        (parent && parent.name.toLowerCase().includes(q)) ||
        (s.description && s.description.toLowerCase().includes(q)) ||
        String(s.id).includes(q)
      );
    });
  }, [incomeSub, incomeMain, searchQuery]);

  // Modal Open Handlers
  const handleOpenAddModal = (
    type: "expense_main" | "expense_sub" | "income_main" | "income_sub"
  ) => {
    setModalType(type);
    setEditingItem(null);
    setFormData({
      id: 0,
      name: "",
      parent_id:
        type === "expense_sub"
          ? expenseMain[0]?.id || ""
          : type === "income_sub"
          ? incomeMain[0]?.id || ""
          : "",
      description: "",
    });
    setFormError(null);
  };

  const handleOpenEditModal = (
    type: "expense_main" | "expense_sub" | "income_main" | "income_sub",
    item: MainCategory | SubCategory
  ) => {
    setModalType(type);
    setEditingItem(item);
    setFormData({
      id: item.id,
      name: item.name,
      parent_id: "parent_id" in item ? item.parent_id : "",
      description: item.description || "",
    });
    setFormError(null);
  };

  const closeModal = () => {
    setModalType(null);
    setEditingItem(null);
    setFormError(null);
  };

  // Form Submit Handler
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setFormError("Category name is required.");
      return;
    }

    if (
      (modalType === "expense_sub" || modalType === "income_sub") &&
      !formData.parent_id
    ) {
      setFormError("Please select a valid parent main category.");
      return;
    }

    setFormSubmitting(true);
    setFormError(null);

    try {
      let res;
      const isEdit = !!editingItem;

      if (modalType === "expense_main") {
        const payload = {
          name: formData.name.trim(),
          description: formData.description.trim() || null,
        };
        if (isEdit) {
          res = await api.post(
            `/expense-categories/main/update/${formData.id}`,
            payload
          );
        } else {
          res = await api.post("/expense-categories/main/create", payload);
        }
      } else if (modalType === "expense_sub") {
        const payload = isEdit
          ? {
              name: formData.name.trim(),
              description: formData.description.trim() || null,
            }
          : {
              name: formData.name.trim(),
              parent_id: Number(formData.parent_id),
              description: formData.description.trim() || null,
            };
        if (isEdit) {
          res = await api.post(
            `/expense-categories/sub/update/${formData.id}`,
            payload
          );
        } else {
          res = await api.post("/expense-categories/sub/create", payload);
        }
      } else if (modalType === "income_main") {
        const payload = {
          name: formData.name.trim(),
          description: formData.description.trim() || null,
        };
        if (isEdit) {
          res = await api.post(
            `/income-categories/main/update/${formData.id}`,
            payload
          );
        } else {
          res = await api.post("/income-categories/main/create", payload);
        }
      } else if (modalType === "income_sub") {
        const payload = isEdit
          ? {
              name: formData.name.trim(),
              description: formData.description.trim() || null,
            }
          : {
              name: formData.name.trim(),
              parent_id: Number(formData.parent_id),
              description: formData.description.trim() || null,
            };
        if (isEdit) {
          res = await api.post(
            `/income-categories/sub/update/${formData.id}`,
            payload
          );
        } else {
          res = await api.post("/income-categories/sub/create", payload);
        }
      }

      if (res?.data?.success) {
        setNotification({
          type: "success",
          message:
            res.data.message ||
            `${isEdit ? "Updated" : "Created"} category successfully.`,
        });
        closeModal();
        await loadData(true);
      } else {
        setFormError(res?.data?.message || "Operation failed. Please try again.");
      }
    } catch (err: any) {
      const errMsg =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        "An unexpected error occurred.";
      setFormError(errMsg);
    } finally {
      setFormSubmitting(false);
    }
  };

  // Delete Action
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);

    try {
      let res;
      if (deleteTarget.type === "expense_main") {
        res = await api.delete(`/expense-categories/main/${deleteTarget.id}`);
      } else if (deleteTarget.type === "expense_sub") {
        res = await api.delete(`/expense-categories/sub/${deleteTarget.id}`);
      } else if (deleteTarget.type === "income_main") {
        res = await api.delete(`/income-categories/main/${deleteTarget.id}`);
      } else if (deleteTarget.type === "income_sub") {
        res = await api.delete(`/income-categories/sub/${deleteTarget.id}`);
      }

      if (res?.data?.success) {
        setNotification({
          type: "success",
          message: res.data.message || `Deleted "${deleteTarget.name}" successfully.`,
        });
        setDeleteTarget(null);
        await loadData(true);
      } else {
        setNotification({
          type: "error",
          message: res?.data?.message || "Failed to delete category.",
        });
        setDeleteTarget(null);
      }
    } catch (err: any) {
      const errMsg =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to delete category.";
      setNotification({
        type: "error",
        message: errMsg,
      });
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Toast Notification Alert */}
      {notification && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all transform animate-in slide-in-from-top-4 duration-300 ${
            notification.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-rose-50 border-rose-200 text-rose-900"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          )}
          <span>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            className="ml-2 text-gray-400 hover:text-gray-700 p-1 rounded-lg"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-xs">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
                In &amp; Out Categories
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                Hierarchical expense and income categories for SFMS journal entries and reporting.
              </p>
            </div>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing || loading}
            className="p-2.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors shadow-2xs disabled:opacity-50"
            title="Refresh Data"
          >
            <RefreshCw
              className={`w-4 h-4 ${refreshing ? "animate-spin text-indigo-600" : ""}`}
            />
          </button>

          {section === "expense" ? (
            activeTab === "main" ? (
              <button
                onClick={() => handleOpenAddModal("expense_main")}
                className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white rounded-lg text-sm font-semibold shadow-xs shadow-indigo-200 flex items-center gap-2 transition-all hover:scale-[1.01] active:scale-[0.99]"
              >
                <Plus className="w-4 h-4" />
                Add Expense Category
              </button>
            ) : (
              <button
                onClick={() => handleOpenAddModal("expense_sub")}
                className="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800 text-white rounded-lg text-sm font-semibold shadow-xs shadow-emerald-200 flex items-center gap-2 transition-all hover:scale-[1.01] active:scale-[0.99]"
              >
                <Plus className="w-4 h-4" />
                Add Expense Sub Category
              </button>
            )
          ) : activeTab === "main" ? (
            <button
              onClick={() => handleOpenAddModal("income_main")}
              className="px-4 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-white rounded-lg text-sm font-semibold shadow-xs shadow-amber-200 flex items-center gap-2 transition-all hover:scale-[1.01] active:scale-[0.99]"
            >
              <Plus className="w-4 h-4" />
              Add Income Category
            </button>
          ) : (
            <button
              onClick={() => handleOpenAddModal("income_sub")}
              className="px-4 py-2.5 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white rounded-lg text-sm font-semibold shadow-xs shadow-amber-200 flex items-center gap-2 transition-all hover:scale-[1.01] active:scale-[0.99]"
            >
              <Plus className="w-4 h-4" />
              Add Income Sub Category
            </button>
          )}
        </div>
      </div>

      {/* Metric Summary KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Expense Main */}
        <div
          onClick={() => {
            setSection("expense");
            setActiveTab("main");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-4 sm:p-5 shadow-xs transition-all hover:shadow-md ${
            section === "expense" && activeTab === "main"
              ? "border-indigo-500 ring-2 ring-indigo-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Expense Main
            </span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Folder className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 font-mono">
              {loading ? "-" : expenseMain.length}
            </h3>
            <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
              Categories
            </span>
          </div>
        </div>

        {/* Expense Sub */}
        <div
          onClick={() => {
            setSection("expense");
            setActiveTab("sub");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-4 sm:p-5 shadow-xs transition-all hover:shadow-md ${
            section === "expense" && activeTab === "sub"
              ? "border-emerald-500 ring-2 ring-emerald-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Expense Sub
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <FolderTree className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <h3 className="text-2xl sm:text-3xl font-bold text-emerald-700 font-mono">
              {loading ? "-" : expenseSub.length}
            </h3>
            <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
              Sub-items
            </span>
          </div>
        </div>

        {/* Income Main */}
        <div
          onClick={() => {
            setSection("income");
            setActiveTab("main");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-4 sm:p-5 shadow-xs transition-all hover:shadow-md ${
            section === "income" && activeTab === "main"
              ? "border-amber-500 ring-2 ring-amber-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Income Main
            </span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Coins className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <h3 className="text-2xl sm:text-3xl font-bold text-amber-700 font-mono">
              {loading ? "-" : incomeMain.length}
            </h3>
            <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
              Categories
            </span>
          </div>
        </div>

        {/* Income Sub */}
        <div
          onClick={() => {
            setSection("income");
            setActiveTab("sub");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-4 sm:p-5 shadow-xs transition-all hover:shadow-md ${
            section === "income" && activeTab === "sub"
              ? "border-orange-500 ring-2 ring-orange-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Income Sub
            </span>
            <div className="w-8 h-8 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center">
              <CircleDollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <h3 className="text-2xl sm:text-3xl font-bold text-orange-700 font-mono">
              {loading ? "-" : incomeSub.length}
            </h3>
            <span className="text-xs font-medium text-orange-700 bg-orange-50 px-2 py-0.5 rounded-full">
              Sub-items
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Controls: Section Switcher & Inner Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-3 rounded-xl border border-gray-200 shadow-2xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Main Section Toggle: Expense vs Income */}
          <div className="flex rounded-lg bg-gray-100 p-1 border border-gray-200">
            <button
              onClick={() => setSection("expense")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-sm font-semibold transition-all ${
                section === "expense"
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              <TrendingDown className="w-4 h-4" />
              Expense Heads
            </button>
            <button
              onClick={() => setSection("income")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-sm font-semibold transition-all ${
                section === "income"
                  ? "bg-amber-600 text-white shadow-xs"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              Income Heads
            </button>
          </div>

          {/* Inner Tab: Main vs Sub */}
          <div className="flex rounded-lg bg-gray-50 p-1 border border-gray-200">
            <button
              onClick={() => setActiveTab("main")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                activeTab === "main"
                  ? section === "expense"
                    ? "bg-indigo-100 text-indigo-800"
                    : "bg-amber-100 text-amber-900"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              <Folder className="w-3.5 h-3.5" />
              Main Categories
            </button>
            <button
              onClick={() => setActiveTab("sub")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                activeTab === "sub"
                  ? section === "expense"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-orange-100 text-orange-900"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              <FolderTree className="w-3.5 h-3.5" />
              Sub Categories
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Search ${section} ${activeTab} categories...`}
            className="w-full pl-9 pr-8 py-1.5 bg-gray-50/70 border border-gray-200 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
          />
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

      {/* Main Content Area */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-16 flex flex-col items-center justify-center gap-3 text-gray-400">
            <RefreshCw className="w-7 h-7 animate-spin text-indigo-600" />
            <p className="text-sm font-medium text-gray-500">Loading categories...</p>
          </div>
        ) : (
          <>
            {/* ═══════════════════════════════════════════════════════ */}
            {/* 1. EXPENSE MAIN CATEGORIES TABLE */}
            {/* ═══════════════════════════════════════════════════════ */}
            {section === "expense" && activeTab === "main" && (
              <div>
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                  <div className="flex items-center gap-2">
                    <Folder className="w-4 h-4 text-indigo-600" />
                    <h2 className="font-semibold text-gray-900 text-sm">
                      Expense Main Categories ({filteredExpenseMain.length})
                    </h2>
                  </div>
                </div>

                {filteredExpenseMain.length === 0 ? (
                  <div className="p-12 text-center">
                    <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-3">
                      <Folder className="w-6 h-6" />
                    </div>
                    <h3 className="text-base font-semibold text-gray-900">
                      {searchQuery ? "No matching categories" : "No Expense Main Categories"}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                      {searchQuery
                        ? `No main categories match "${searchQuery}". Clear search or add a new category.`
                        : "Define top-level expense categories like Office Expenses, Salaries, Utilities, etc."}
                    </p>
                    {!searchQuery && (
                      <button
                        onClick={() => handleOpenAddModal("expense_main")}
                        className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-xs transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add Category
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                          <th className="px-6 py-3.5 w-20">ID</th>
                          <th className="px-6 py-3.5">Category Name</th>
                          <th className="px-6 py-3.5">Description</th>
                          <th className="px-6 py-3.5">Sub Categories</th>
                          <th className="px-6 py-3.5">Status</th>
                          <th className="px-6 py-3.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredExpenseMain.map((cat) => {
                          const childSubs = expenseSub.filter(
                            (s) => s.parent_id === cat.id
                          );
                          const isExpanded = expandedPills[cat.id];
                          const amtSummary = expenseAmounts.main[String(cat.id)];

                          return (
                            <tr
                              key={cat.id}
                              className="hover:bg-indigo-50/30 transition-colors group"
                            >
                              <td className="px-6 py-4 text-xs font-mono font-bold text-gray-400">
                                #{cat.id}
                              </td>
                              <td className="px-6 py-4">
                                <div className="font-semibold text-gray-900 text-sm flex items-center gap-2">
                                  <span>{cat.name}</span>
                                  {amtSummary && amtSummary.count > 0 && (
                                    <span className="text-[11px] font-mono font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md">
                                      ₹{amtSummary.total.toLocaleString("en-IN")} ({amtSummary.count})
                                    </span>
                                  )}
                                </div>
                                {isExpanded && childSubs.length > 0 && (
                                  <div className="mt-2.5 flex flex-wrap gap-1.5 animate-in fade-in duration-200">
                                    {childSubs.map((s) => (
                                      <span
                                        key={s.id}
                                        className="inline-flex items-center text-[11px] bg-emerald-50 border border-emerald-200 text-emerald-800 font-medium px-2 py-0.5 rounded-md"
                                      >
                                        {s.name}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="px-6 py-4 text-xs text-gray-600 max-w-xs truncate">
                                {cat.description || (
                                  <span className="text-gray-400 italic">No description</span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                {childSubs.length > 0 ? (
                                  <button
                                    onClick={() => toggleSubPills(cat.id)}
                                    className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-2.5 py-1 rounded-full transition-colors"
                                  >
                                    <span>{childSubs.length} sub{childSubs.length > 1 ? "s" : ""}</span>
                                    {isExpanded ? (
                                      <ChevronDown className="w-3 h-3" />
                                    ) : (
                                      <ChevronRight className="w-3 h-3" />
                                    )}
                                  </button>
                                ) : (
                                  <span className="text-xs text-gray-400">0 subs</span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  Active
                                </span>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    onClick={() => handleOpenEditModal("expense_main", cat)}
                                    className="p-1.5 text-indigo-600 hover:text-indigo-900 hover:bg-indigo-50 rounded-lg transition-colors"
                                    title="Edit Category"
                                  >
                                    <Edit2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() =>
                                      setDeleteTarget({
                                        type: "expense_main",
                                        id: cat.id,
                                        name: cat.name,
                                      })
                                    }
                                    className="p-1.5 text-rose-600 hover:text-rose-900 hover:bg-rose-50 rounded-lg transition-colors"
                                    title="Delete Category"
                                  >
                                    <Trash2 className="w-4 h-4" />
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

            {/* ═══════════════════════════════════════════════════════ */}
            {/* 2. EXPENSE SUB CATEGORIES TABLE */}
            {/* ═══════════════════════════════════════════════════════ */}
            {section === "expense" && activeTab === "sub" && (
              <div>
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                  <div className="flex items-center gap-2">
                    <FolderTree className="w-4 h-4 text-emerald-600" />
                    <h2 className="font-semibold text-gray-900 text-sm">
                      Expense Sub Categories ({filteredExpenseSub.length})
                    </h2>
                  </div>
                </div>

                {filteredExpenseSub.length === 0 ? (
                  <div className="p-12 text-center">
                    <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
                      <FolderTree className="w-6 h-6" />
                    </div>
                    <h3 className="text-base font-semibold text-gray-900">
                      {searchQuery ? "No matching sub-categories" : "No Expense Sub Categories"}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                      {searchQuery
                        ? `No sub categories match "${searchQuery}". Clear search or add a new sub category.`
                        : "Break down expense main heads into specific items like Stationery, Fuel, Internet, etc."}
                    </p>
                    {!searchQuery && (
                      <button
                        onClick={() => handleOpenAddModal("expense_sub")}
                        className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-xs transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add Sub Category
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                          <th className="px-6 py-3.5 w-20">ID</th>
                          <th className="px-6 py-3.5">Sub Category Name</th>
                          <th className="px-6 py-3.5">Main Category</th>
                          <th className="px-6 py-3.5">Description</th>
                          <th className="px-6 py-3.5">Status</th>
                          <th className="px-6 py-3.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredExpenseSub.map((sub) => {
                          const parent = expenseMain.find((m) => m.id === sub.parent_id);
                          const amtSummary = expenseAmounts.sub[String(sub.id)];

                          return (
                            <tr
                              key={sub.id}
                              className="hover:bg-emerald-50/30 transition-colors group"
                            >
                              <td className="px-6 py-4 text-xs font-mono font-bold text-gray-400">
                                #{sub.id}
                              </td>
                              <td className="px-6 py-4">
                                <div className="font-semibold text-gray-900 text-sm flex items-center gap-2">
                                  <span>{sub.name}</span>
                                  {amtSummary && amtSummary.count > 0 && (
                                    <span className="text-[11px] font-mono font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md">
                                      ₹{amtSummary.total.toLocaleString("en-IN")} ({amtSummary.count})
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="px-6 py-4">
                                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-700 bg-gray-100 border border-gray-200 px-2.5 py-1 rounded-md">
                                  <Folder className="w-3.5 h-3.5 text-indigo-600" />
                                  {parent ? parent.name : "Unknown"}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-xs text-gray-600 max-w-xs truncate">
                                {sub.description || (
                                  <span className="text-gray-400 italic">No description</span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  Active
                                </span>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    onClick={() => handleOpenEditModal("expense_sub", sub)}
                                    className="p-1.5 text-emerald-600 hover:text-emerald-900 hover:bg-emerald-50 rounded-lg transition-colors"
                                    title="Edit Sub Category"
                                  >
                                    <Edit2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() =>
                                      setDeleteTarget({
                                        type: "expense_sub",
                                        id: sub.id,
                                        name: sub.name,
                                      })
                                    }
                                    className="p-1.5 text-rose-600 hover:text-rose-900 hover:bg-rose-50 rounded-lg transition-colors"
                                    title="Delete Sub Category"
                                  >
                                    <Trash2 className="w-4 h-4" />
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

            {/* ═══════════════════════════════════════════════════════ */}
            {/* 3. INCOME MAIN CATEGORIES TABLE */}
            {/* ═══════════════════════════════════════════════════════ */}
            {section === "income" && activeTab === "main" && (
              <div>
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                  <div className="flex items-center gap-2">
                    <Coins className="w-4 h-4 text-amber-600" />
                    <h2 className="font-semibold text-gray-900 text-sm">
                      Income Main Categories ({filteredIncomeMain.length})
                    </h2>
                  </div>
                </div>

                {filteredIncomeMain.length === 0 ? (
                  <div className="p-12 text-center">
                    <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto mb-3">
                      <Coins className="w-6 h-6" />
                    </div>
                    <h3 className="text-base font-semibold text-gray-900">
                      {searchQuery ? "No matching income categories" : "No Income Main Categories"}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                      {searchQuery
                        ? `No income categories match "${searchQuery}". Clear search or add a new category.`
                        : "Define top-level revenue heads like Sales Revenue, Services, Interest, etc."}
                    </p>
                    {!searchQuery && (
                      <button
                        onClick={() => handleOpenAddModal("income_main")}
                        className="mt-4 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-xs transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add Category
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                          <th className="px-6 py-3.5 w-20">ID</th>
                          <th className="px-6 py-3.5">Category Name</th>
                          <th className="px-6 py-3.5">Description</th>
                          <th className="px-6 py-3.5">Sub Categories</th>
                          <th className="px-6 py-3.5">Status</th>
                          <th className="px-6 py-3.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredIncomeMain.map((cat) => {
                          const childSubs = incomeSub.filter(
                            (s) => s.parent_id === cat.id
                          );
                          const isExpanded = expandedPills[cat.id];
                          const amtSummary = incomeAmounts.main[String(cat.id)];

                          return (
                            <tr
                              key={cat.id}
                              className="hover:bg-amber-50/30 transition-colors group"
                            >
                              <td className="px-6 py-4 text-xs font-mono font-bold text-gray-400">
                                #{cat.id}
                              </td>
                              <td className="px-6 py-4">
                                <div className="font-semibold text-gray-900 text-sm flex items-center gap-2">
                                  <span>{cat.name}</span>
                                  {amtSummary && amtSummary.count > 0 && (
                                    <span className="text-[11px] font-mono font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md">
                                      ₹{amtSummary.total.toLocaleString("en-IN")} ({amtSummary.count})
                                    </span>
                                  )}
                                </div>
                                {isExpanded && childSubs.length > 0 && (
                                  <div className="mt-2.5 flex flex-wrap gap-1.5 animate-in fade-in duration-200">
                                    {childSubs.map((s) => (
                                      <span
                                        key={s.id}
                                        className="inline-flex items-center text-[11px] bg-amber-50 border border-amber-200 text-amber-900 font-medium px-2 py-0.5 rounded-md"
                                      >
                                        {s.name}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="px-6 py-4 text-xs text-gray-600 max-w-xs truncate">
                                {cat.description || (
                                  <span className="text-gray-400 italic">No description</span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                {childSubs.length > 0 ? (
                                  <button
                                    onClick={() => toggleSubPills(cat.id)}
                                    className="inline-flex items-center gap-1 text-xs font-medium text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 px-2.5 py-1 rounded-full transition-colors"
                                  >
                                    <span>{childSubs.length} sub{childSubs.length > 1 ? "s" : ""}</span>
                                    {isExpanded ? (
                                      <ChevronDown className="w-3 h-3" />
                                    ) : (
                                      <ChevronRight className="w-3 h-3" />
                                    )}
                                  </button>
                                ) : (
                                  <span className="text-xs text-gray-400">0 subs</span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                                  Active
                                </span>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    onClick={() => handleOpenEditModal("income_main", cat)}
                                    className="p-1.5 text-amber-600 hover:text-amber-900 hover:bg-amber-50 rounded-lg transition-colors"
                                    title="Edit Category"
                                  >
                                    <Edit2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() =>
                                      setDeleteTarget({
                                        type: "income_main",
                                        id: cat.id,
                                        name: cat.name,
                                      })
                                    }
                                    className="p-1.5 text-rose-600 hover:text-rose-900 hover:bg-rose-50 rounded-lg transition-colors"
                                    title="Delete Category"
                                  >
                                    <Trash2 className="w-4 h-4" />
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

            {/* ═══════════════════════════════════════════════════════ */}
            {/* 4. INCOME SUB CATEGORIES TABLE */}
            {/* ═══════════════════════════════════════════════════════ */}
            {section === "income" && activeTab === "sub" && (
              <div>
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                  <div className="flex items-center gap-2">
                    <CircleDollarSign className="w-4 h-4 text-orange-600" />
                    <h2 className="font-semibold text-gray-900 text-sm">
                      Income Sub Categories ({filteredIncomeSub.length})
                    </h2>
                  </div>
                </div>

                {filteredIncomeSub.length === 0 ? (
                  <div className="p-12 text-center">
                    <div className="w-12 h-12 rounded-full bg-orange-50 text-orange-600 flex items-center justify-center mx-auto mb-3">
                      <CircleDollarSign className="w-6 h-6" />
                    </div>
                    <h3 className="text-base font-semibold text-gray-900">
                      {searchQuery ? "No matching sub-categories" : "No Income Sub Categories"}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                      {searchQuery
                        ? `No sub categories match "${searchQuery}". Clear search or add a new sub category.`
                        : "Break down income categories into distinct heads like Product Sales, Consulting, etc."}
                    </p>
                    {!searchQuery && (
                      <button
                        onClick={() => handleOpenAddModal("income_sub")}
                        className="mt-4 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-xs transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add Sub Category
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                          <th className="px-6 py-3.5 w-20">ID</th>
                          <th className="px-6 py-3.5">Sub Category Name</th>
                          <th className="px-6 py-3.5">Main Category</th>
                          <th className="px-6 py-3.5">Description</th>
                          <th className="px-6 py-3.5">Status</th>
                          <th className="px-6 py-3.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredIncomeSub.map((sub) => {
                          const parent = incomeMain.find((m) => m.id === sub.parent_id);
                          const amtSummary = incomeAmounts.sub[String(sub.id)];

                          return (
                            <tr
                              key={sub.id}
                              className="hover:bg-orange-50/30 transition-colors group"
                            >
                              <td className="px-6 py-4 text-xs font-mono font-bold text-gray-400">
                                #{sub.id}
                              </td>
                              <td className="px-6 py-4">
                                <div className="font-semibold text-gray-900 text-sm flex items-center gap-2">
                                  <span>{sub.name}</span>
                                  {amtSummary && amtSummary.count > 0 && (
                                    <span className="text-[11px] font-mono font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md">
                                      ₹{amtSummary.total.toLocaleString("en-IN")} ({amtSummary.count})
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="px-6 py-4">
                                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-700 bg-gray-100 border border-gray-200 px-2.5 py-1 rounded-md">
                                  <Coins className="w-3.5 h-3.5 text-amber-600" />
                                  {parent ? parent.name : "Unknown"}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-xs text-gray-600 max-w-xs truncate">
                                {sub.description || (
                                  <span className="text-gray-400 italic">No description</span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                                  Active
                                </span>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    onClick={() => handleOpenEditModal("income_sub", sub)}
                                    className="p-1.5 text-orange-600 hover:text-orange-900 hover:bg-orange-50 rounded-lg transition-colors"
                                    title="Edit Sub Category"
                                  >
                                    <Edit2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() =>
                                      setDeleteTarget({
                                        type: "income_sub",
                                        id: sub.id,
                                        name: sub.name,
                                      })
                                    }
                                    className="p-1.5 text-rose-600 hover:text-rose-900 hover:bg-rose-50 rounded-lg transition-colors"
                                    title="Delete Sub Category"
                                  >
                                    <Trash2 className="w-4 h-4" />
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
          </>
        )}
      </div>

      {/* ═════════════════════════════════════════════════════════════ */}
      {/* ADD / EDIT MODAL DIALOG */}
      {/* ═════════════════════════════════════════════════════════════ */}
      {modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-100 overflow-hidden transform animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/70">
              <div className="flex items-center gap-2.5">
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    modalType.includes("expense")
                      ? modalType.includes("sub")
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-indigo-100 text-indigo-700"
                      : modalType.includes("sub")
                      ? "bg-orange-100 text-orange-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {modalType.includes("sub") ? (
                    <FolderTree className="w-4 h-4" />
                  ) : (
                    <Folder className="w-4 h-4" />
                  )}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-base">
                    {editingItem ? "Edit" : "Add"}{" "}
                    {modalType === "expense_main"
                      ? "Expense Category"
                      : modalType === "expense_sub"
                      ? "Expense Sub Category"
                      : modalType === "income_main"
                      ? "Income Category"
                      : "Income Sub Category"}
                  </h3>
                </div>
              </div>
              <button
                onClick={closeModal}
                disabled={formSubmitting}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form Body */}
            <form onSubmit={handleFormSubmit}>
              <div className="p-6 space-y-4">
                {formError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span>{formError}</span>
                  </div>
                )}

                {/* Subcategory Parent Selector */}
                {(modalType === "expense_sub" || modalType === "income_sub") && (
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                      Main Category <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={formData.parent_id}
                      disabled={!!editingItem || formSubmitting}
                      onChange={(e) =>
                        setFormData({ ...formData, parent_id: e.target.value })
                      }
                      className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 disabled:bg-gray-50 disabled:text-gray-500"
                    >
                      <option value="">Select Main Category</option>
                      {modalType === "expense_sub"
                        ? expenseMain.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))
                        : incomeMain.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                    </select>
                    {editingItem && (
                      <p className="text-[11px] text-gray-400 mt-1">
                        Parent category cannot be changed once created.
                      </p>
                    )}
                  </div>
                )}

                {/* Category Name */}
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                    {modalType.includes("sub") ? "Sub Category Name" : "Category Name"}{" "}
                    <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    disabled={formSubmitting}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder={
                      modalType === "expense_main"
                        ? "e.g. Office Expenses"
                        : modalType === "expense_sub"
                        ? "e.g. Stationery & Printing"
                        : modalType === "income_main"
                        ? "e.g. Sales Revenue"
                        : "e.g. Product Sales"
                    }
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                    Description <span className="text-gray-400 font-normal text-[11px]">(Optional)</span>
                  </label>
                  <textarea
                    rows={3}
                    value={formData.description}
                    disabled={formSubmitting}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    placeholder="Brief description of transactions for this category..."
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none"
                  />
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-3.5 bg-gray-50 border-t border-gray-100 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={formSubmitting}
                  className="px-4 py-2 border border-gray-300 text-gray-700 hover:bg-white rounded-lg text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className={`px-4 py-2 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all ${
                    modalType.includes("expense")
                      ? modalType.includes("sub")
                        ? "bg-emerald-600 hover:bg-emerald-700"
                        : "bg-indigo-600 hover:bg-indigo-700"
                      : modalType.includes("sub")
                      ? "bg-orange-600 hover:bg-orange-700"
                      : "bg-amber-600 hover:bg-amber-700"
                  } disabled:opacity-50`}
                >
                  {formSubmitting && (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  )}
                  <span>{editingItem ? "Save Changes" : "Create Category"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════ */}
      {/* DELETE CONFIRMATION DIALOG */}
      {/* ═════════════════════════════════════════════════════════════ */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-100 overflow-hidden transform animate-in zoom-in-95 duration-200">
            <div className="p-6 text-center">
              <div className="w-12 h-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto mb-4">
                <Trash2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-gray-900">
                Confirm Deletion
              </h3>
              <p className="text-xs text-gray-500 mt-2">
                Are you sure you want to delete category{" "}
                <span className="font-semibold text-gray-900">
                  &quot;{deleteTarget.name}&quot;
                </span>
                ?
              </p>
              {deleteTarget.type.includes("main") && (
                <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-800 text-left">
                  <strong>Note:</strong> You cannot delete a main category that still has active sub-categories attached to it.
                </div>
              )}
            </div>

            <div className="px-6 py-3.5 bg-gray-50 border-t border-gray-100 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="px-4 py-2 border border-gray-300 text-gray-700 hover:bg-white rounded-lg text-xs font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={deleting}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all disabled:opacity-50"
              >
                {deleting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Delete</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

