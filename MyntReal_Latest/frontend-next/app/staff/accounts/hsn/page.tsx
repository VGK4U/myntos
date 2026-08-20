"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import {
  Barcode,
  Plus,
  Search,
  RefreshCw,
  Edit2,
  Trash2,
  Copy,
  Check,
  Calculator,
  Percent,
  CheckCircle2,
  AlertCircle,
  X,
  Sparkles,
  Calendar,
  Info,
  ShieldAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

export interface HSNItem {
  id: number;
  hsn_code: string;
  description: string;
  cgst_rate: number | string;
  sgst_rate: number | string;
  igst_rate: number | string;
  cess_rate: number | string;
  gst_rate?: number | string;
  effective_from?: string | null;
  effective_to?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

const GST_PRESETS = [
  { label: "0% (Exempt)", cgst: 0, sgst: 0, igst: 0, cess: 0, color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { label: "5% (Reduced)", cgst: 2.5, sgst: 2.5, igst: 5, cess: 0, color: "bg-amber-50 text-amber-700 border-amber-200" },
  { label: "12% (Standard I)", cgst: 6, sgst: 6, igst: 12, cess: 0, color: "bg-sky-50 text-sky-700 border-sky-200" },
  { label: "18% (Standard II)", cgst: 9, sgst: 9, igst: 18, cess: 0, color: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  { label: "28% (Luxury)", cgst: 14, sgst: 14, igst: 28, cess: 0, color: "bg-purple-50 text-purple-700 border-purple-200" },
];

export default function HsnMasterPage() {
  const { token } = useStaffAuth();

  // Data & loading state
  const [items, setItems] = useState<HSNItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ACTIVE" | "INACTIVE">("ALL");
  const [rateFilter, setRateFilter] = useState<string>("ALL");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Notification Toast
  const [notification, setNotification] = useState<{
    type: "success" | "error" | "info";
    message: string;
  } | null>(null);

  // Modal States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isCalcOpen, setIsCalcOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  // Active items for modals
  const [selectedItem, setSelectedItem] = useState<HSNItem | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form Data for Create
  const [formData, setFormData] = useState({
    hsn_code: "",
    description: "",
    cgst_rate: 9,
    sgst_rate: 9,
    igst_rate: 18,
    cess_rate: 0,
    effective_from: new Date().toISOString().split("T")[0],
    effective_to: "",
    is_active: true,
    auto_split: true,
  });

  // Form Data for Edit
  const [editFormData, setEditFormData] = useState({
    id: 0,
    hsn_code: "",
    description: "",
    cgst_rate: 9,
    sgst_rate: 9,
    igst_rate: 18,
    cess_rate: 0,
    effective_from: "",
    effective_to: "",
    is_active: true,
    auto_split: true,
  });

  // Calculator Simulation State
  const [calcState, setCalcState] = useState({
    selectedHsnId: 0,
    hsn_code: "",
    description: "",
    baseAmount: 10000,
    supplyType: "INTRA" as "INTRA" | "INTER",
    cgst_rate: 9,
    sgst_rate: 9,
    igst_rate: 18,
    cess_rate: 0,
  });

  // Auto clear notification
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  // Fetch HSN Codes
  const fetchHSNCodes = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get("/staff/accounts/hsn?page_size=200");
      if (res.data && res.data.success) {
        setItems(res.data.hsn_codes || []);
      } else if (res.data && Array.isArray(res.data.codes)) {
        setItems(res.data.codes);
      } else {
        setItems([]);
      }
    } catch (err: any) {
      console.error("Failed to load HSN codes:", err);
      setNotification({
        type: "error",
        message: err.response?.data?.message || err.message || "Failed to load HSN codes from server.",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHSNCodes();
  }, [token]);

  // Copy code to clipboard
  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  // Open Create Modal
  const handleOpenCreate = () => {
    setFormData({
      hsn_code: "",
      description: "",
      cgst_rate: 9,
      sgst_rate: 9,
      igst_rate: 18,
      cess_rate: 0,
      effective_from: new Date().toISOString().split("T")[0],
      effective_to: "",
      is_active: true,
      auto_split: true,
    });
    setFormError(null);
    setIsCreateOpen(true);
  };

  // Apply preset to Create
  const applyCreatePreset = (preset: typeof GST_PRESETS[0]) => {
    setFormData((prev) => ({
      ...prev,
      cgst_rate: preset.cgst,
      sgst_rate: preset.sgst,
      igst_rate: preset.igst,
      cess_rate: preset.cess,
    }));
  };

  // Apply preset to Edit
  const applyEditPreset = (preset: typeof GST_PRESETS[0]) => {
    setEditFormData((prev) => ({
      ...prev,
      cgst_rate: preset.cgst,
      sgst_rate: preset.sgst,
      igst_rate: preset.igst,
      cess_rate: preset.cess,
    }));
  };

  // Handle IGST change with auto-split for Create
  const handleCreateIgstChange = (val: number) => {
    setFormData((prev) => {
      if (prev.auto_split) {
        const half = Number((val / 2).toFixed(2));
        return { ...prev, igst_rate: val, cgst_rate: half, sgst_rate: half };
      }
      return { ...prev, igst_rate: val };
    });
  };

  // Handle IGST change with auto-split for Edit
  const handleEditIgstChange = (val: number) => {
    setEditFormData((prev) => {
      if (prev.auto_split) {
        const half = Number((val / 2).toFixed(2));
        return { ...prev, igst_rate: val, cgst_rate: half, sgst_rate: half };
      }
      return { ...prev, igst_rate: val };
    });
  };

  // Open Edit Modal
  const handleOpenEdit = async (item: HSNItem) => {
    setSelectedItem(item);
    setFormError(null);
    setEditFormData({
      id: item.id,
      hsn_code: item.hsn_code,
      description: item.description,
      cgst_rate: parseFloat(String(item.cgst_rate || 0)),
      sgst_rate: parseFloat(String(item.sgst_rate || 0)),
      igst_rate: parseFloat(String(item.igst_rate || 0)),
      cess_rate: parseFloat(String(item.cess_rate || 0)),
      effective_from: item.effective_from ? item.effective_from.split("T")[0] : "",
      effective_to: item.effective_to ? item.effective_to.split("T")[0] : "",
      is_active: item.is_active !== false,
      auto_split: true,
    });
    setIsEditOpen(true);
  };

  // Open Calculator
  const handleOpenCalculator = (item?: HSNItem) => {
    if (item) {
      setCalcState({
        selectedHsnId: item.id,
        hsn_code: item.hsn_code,
        description: item.description,
        baseAmount: 10000,
        supplyType: "INTRA",
        cgst_rate: parseFloat(String(item.cgst_rate || 0)),
        sgst_rate: parseFloat(String(item.sgst_rate || 0)),
        igst_rate: parseFloat(String(item.igst_rate || 0)),
        cess_rate: parseFloat(String(item.cess_rate || 0)),
      });
    } else if (items.length > 0) {
      const first = items[0];
      setCalcState({
        selectedHsnId: first.id,
        hsn_code: first.hsn_code,
        description: first.description,
        baseAmount: 10000,
        supplyType: "INTRA",
        cgst_rate: parseFloat(String(first.cgst_rate || 0)),
        sgst_rate: parseFloat(String(first.sgst_rate || 0)),
        igst_rate: parseFloat(String(first.igst_rate || 0)),
        cess_rate: parseFloat(String(first.cess_rate || 0)),
      });
    } else {
      setCalcState({
        selectedHsnId: 0,
        hsn_code: "998311",
        description: "Consulting / Professional Services",
        baseAmount: 10000,
        supplyType: "INTRA",
        cgst_rate: 9,
        sgst_rate: 9,
        igst_rate: 18,
        cess_rate: 0,
      });
    }
    setIsCalcOpen(true);
  };

  // Handle Create Submit
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = formData.hsn_code.trim().toUpperCase();
    if (!code) {
      setFormError("HSN / SAC Code is required.");
      return;
    }
    if (!formData.description.trim()) {
      setFormError("Description is required.");
      return;
    }
    if (!formData.effective_from) {
      setFormError("Effective From date is required.");
      return;
    }

    setFormSubmitting(true);
    setFormError(null);

    try {
      const payload = {
        hsn_code: code,
        description: formData.description.trim(),
        cgst_rate: Number(formData.cgst_rate) || 0,
        sgst_rate: Number(formData.sgst_rate) || 0,
        igst_rate: Number(formData.igst_rate) || 0,
        cess_rate: Number(formData.cess_rate) || 0,
        effective_from: formData.effective_from,
        effective_to: formData.effective_to || null,
        is_active: formData.is_active,
      };

      const res = await api.post("/staff/accounts/hsn", payload);
      if (res.data?.success || res.status === 200 || res.status === 201) {
        setNotification({
          type: "success",
          message: res.data?.message || `HSN code '${code}' added successfully!`,
        });
        setIsCreateOpen(false);
        await fetchHSNCodes(true);
      } else {
        setFormError(res.data?.message || "Failed to create HSN code.");
      }
    } catch (err: any) {
      const errMsg =
        err.response?.data?.message ||
        err.response?.data?.detail?.message ||
        (typeof err.response?.data?.detail === "string" ? err.response?.data?.detail : null) ||
        err.message ||
        "Failed to create HSN code.";
      setFormError(errMsg);
    } finally {
      setFormSubmitting(false);
    }
  };

  // Handle Edit Submit
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editFormData.description.trim()) {
      setFormError("Description is required.");
      return;
    }
    if (!editFormData.effective_from) {
      setFormError("Effective From date is required.");
      return;
    }

    setFormSubmitting(true);
    setFormError(null);

    try {
      const payload = {
        description: editFormData.description.trim(),
        cgst_rate: Number(editFormData.cgst_rate) || 0,
        sgst_rate: Number(editFormData.sgst_rate) || 0,
        igst_rate: Number(editFormData.igst_rate) || 0,
        cess_rate: Number(editFormData.cess_rate) || 0,
        effective_from: editFormData.effective_from,
        effective_to: editFormData.effective_to || null,
        is_active: editFormData.is_active,
      };

      const res = await api.put(`/staff/accounts/hsn/${editFormData.id}`, payload);
      if (res.data?.success || res.status === 200) {
        setNotification({
          type: "success",
          message: res.data?.message || "HSN code updated successfully!",
        });
        setIsEditOpen(false);
        await fetchHSNCodes(true);
      } else {
        setFormError(res.data?.message || "Failed to update HSN code.");
      }
    } catch (err: any) {
      const errMsg =
        err.response?.data?.message ||
        err.response?.data?.detail?.message ||
        (typeof err.response?.data?.detail === "string" ? err.response?.data?.detail : null) ||
        err.message ||
        "Failed to update HSN code.";
      setFormError(errMsg);
    } finally {
      setFormSubmitting(false);
    }
  };

  // Handle Soft Delete / Deactivate
  const handleDeleteConfirm = async () => {
    if (!selectedItem) return;
    setFormSubmitting(true);

    try {
      const res = await api.delete(`/staff/accounts/hsn/${selectedItem.id}`);
      if (res.data?.success || res.status === 200) {
        setNotification({
          type: "success",
          message: res.data?.message || `HSN code '${selectedItem.hsn_code}' deactivated.`,
        });
        setIsDeleteOpen(false);
        await fetchHSNCodes(true);
      } else {
        setNotification({
          type: "error",
          message: res.data?.message || "Failed to deactivate HSN code.",
        });
      }
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.response?.data?.message || err.message || "Failed to deactivate.",
      });
    } finally {
      setFormSubmitting(false);
    }
  };

  // Filtered and Sorted Items
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // Search
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        (item.hsn_code && item.hsn_code.toLowerCase().includes(q)) ||
        (item.description && item.description.toLowerCase().includes(q));

      // Status
      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "ACTIVE" && item.is_active !== false) ||
        (statusFilter === "INACTIVE" && item.is_active === false);

      // Rate Filter
      let matchesRate = true;
      if (rateFilter !== "ALL") {
        const igst = parseFloat(String(item.igst_rate || 0));
        if (rateFilter === "0") matchesRate = igst === 0;
        else if (rateFilter === "5") matchesRate = igst === 5;
        else if (rateFilter === "12") matchesRate = igst === 12;
        else if (rateFilter === "18") matchesRate = igst === 18;
        else if (rateFilter === "28") matchesRate = igst === 28;
        else if (rateFilter === "OTHER") matchesRate = ![0, 5, 12, 18, 28].includes(igst);
      }

      return matchesSearch && matchesStatus && matchesRate;
    });
  }, [items, searchQuery, statusFilter, rateFilter]);

  // Statistics KPI computation
  const stats = useMemo(() => {
    const total = items.length;
    const active = items.filter((i) => i.is_active !== false).length;
    const std18 = items.filter((i) => parseFloat(String(i.igst_rate || 0)) === 18).length;
    const exempt = items.filter((i) => parseFloat(String(i.igst_rate || 0)) === 0).length;
    const reduced = items.filter((i) => [5, 12].includes(parseFloat(String(i.igst_rate || 0)))).length;
    const luxury = items.filter((i) => parseFloat(String(i.igst_rate || 0)) === 28).length;

    return { total, active, std18, exempt, reduced, luxury };
  }, [items]);

  // Calculate taxes for simulator
  const calculatedTax = useMemo(() => {
    const base = Number(calcState.baseAmount) || 0;
    const isIntra = calcState.supplyType === "INTRA";

    const cgstAmt = isIntra ? (base * calcState.cgst_rate) / 100 : 0;
    const sgstAmt = isIntra ? (base * calcState.sgst_rate) / 100 : 0;
    const igstAmt = !isIntra ? (base * calcState.igst_rate) / 100 : 0;
    const cessAmt = (base * calcState.cess_rate) / 100;

    const totalTax = cgstAmt + sgstAmt + igstAmt + cessAmt;
    const grandTotal = base + totalTax;

    return {
      base,
      cgstAmt,
      sgstAmt,
      igstAmt,
      cessAmt,
      totalTax,
      grandTotal,
    };
  }, [calcState]);

  // Helper for rate badge colors
  const getRateBadge = (igst: number | string) => {
    const rate = parseFloat(String(igst || 0));
    if (rate === 18) {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">18% GST</span>;
    }
    if (rate === 12) {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200">12% GST</span>;
    }
    if (rate === 5) {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">5% GST</span>;
    }
    if (rate === 28) {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">28% GST</span>;
    }
    if (rate === 0) {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">0% (Nil)</span>;
    }
    return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 border border-gray-200">{rate}% GST</span>;
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Toast Notification Alert */}
      {notification && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all transform animate-in slide-in-from-top-4 duration-300 ${
            notification.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : notification.type === "error"
              ? "bg-rose-50 border-rose-200 text-rose-900"
              : "bg-blue-50 border-blue-200 text-blue-900"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          ) : notification.type === "error" ? (
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          ) : (
            <Info className="w-5 h-5 text-blue-600 shrink-0" />
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

      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-amber-500/10 to-indigo-500/10 border border-amber-200/50 flex items-center justify-center text-amber-600 shadow-xs">
            <Barcode className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
              HSN / SAC Master
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Harmonized System Nomenclature &amp; Service Accounting Codes for Goods and Services Tax rates.
            </p>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchHSNCodes(true)}
            disabled={refreshing || loading}
            className="border-gray-200 text-gray-700 hover:bg-gray-50 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-amber-600" : ""}`} />
            <span>Refresh</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => handleOpenCalculator()}
            className="border-indigo-200 text-indigo-700 hover:bg-indigo-50/70 flex items-center gap-2"
          >
            <Calculator className="w-4 h-4 text-indigo-600" />
            <span>Tax Calculator</span>
          </Button>

          <Button
            onClick={handleOpenCreate}
            size="sm"
            className="bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-white shadow-xs font-semibold flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            <span>Add HSN Code</span>
          </Button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Total Codes */}
        <div
          onClick={() => {
            setStatusFilter("ALL");
            setRateFilter("ALL");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-3.5 sm:p-4 shadow-xs transition-all hover:shadow-md ${
            statusFilter === "ALL" && rateFilter === "ALL"
              ? "border-amber-500 ring-2 ring-amber-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold uppercase">
            <span>Total Codes</span>
            <Barcode className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold text-gray-900 font-mono">
              {loading ? "-" : stats.total}
            </span>
            <span className="text-[10px] font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">
              All
            </span>
          </div>
        </div>

        {/* Active Codes */}
        <div
          onClick={() => {
            setStatusFilter("ACTIVE");
            setRateFilter("ALL");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-3.5 sm:p-4 shadow-xs transition-all hover:shadow-md ${
            statusFilter === "ACTIVE" && rateFilter === "ALL"
              ? "border-emerald-500 ring-2 ring-emerald-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold uppercase">
            <span>Active</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold text-emerald-700 font-mono">
              {loading ? "-" : stats.active}
            </span>
            <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
              Live
            </span>
          </div>
        </div>

        {/* 18% Standard */}
        <div
          onClick={() => {
            setRateFilter("18");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-3.5 sm:p-4 shadow-xs transition-all hover:shadow-md ${
            rateFilter === "18"
              ? "border-indigo-500 ring-2 ring-indigo-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold uppercase">
            <span>18% Standard</span>
            <Percent className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold text-indigo-700 font-mono">
              {loading ? "-" : stats.std18}
            </span>
            <span className="text-[10px] font-medium text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">
              9+9%
            </span>
          </div>
        </div>

        {/* 12% or 5% Reduced */}
        <div
          onClick={() => {
            setRateFilter(rateFilter === "12" ? "5" : "12");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-3.5 sm:p-4 shadow-xs transition-all hover:shadow-md ${
            rateFilter === "12" || rateFilter === "5"
              ? "border-sky-500 ring-2 ring-sky-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold uppercase">
            <span>Reduced (5/12%)</span>
            <Sparkles className="w-4 h-4 text-sky-600" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold text-sky-700 font-mono">
              {loading ? "-" : stats.reduced}
            </span>
            <span className="text-[10px] font-medium text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded">
              Tier
            </span>
          </div>
        </div>

        {/* 28% Luxury */}
        <div
          onClick={() => {
            setRateFilter("28");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-3.5 sm:p-4 shadow-xs transition-all hover:shadow-md ${
            rateFilter === "28"
              ? "border-purple-500 ring-2 ring-purple-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold uppercase">
            <span>28% Luxury</span>
            <ShieldAlert className="w-4 h-4 text-purple-600" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold text-purple-700 font-mono">
              {loading ? "-" : stats.luxury}
            </span>
            <span className="text-[10px] font-medium text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded">
              14+14%
            </span>
          </div>
        </div>

        {/* Exempt (0%) */}
        <div
          onClick={() => {
            setRateFilter("0");
          }}
          className={`cursor-pointer bg-white rounded-xl border p-3.5 sm:p-4 shadow-xs transition-all hover:shadow-md ${
            rateFilter === "0"
              ? "border-emerald-500 ring-2 ring-emerald-500/15"
              : "border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold uppercase">
            <span>0% Exempt</span>
            <Check className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold text-emerald-700 font-mono">
              {loading ? "-" : stats.exempt}
            </span>
            <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
              Nil
            </span>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-gray-200 shadow-2xs">
        <div className="flex flex-wrap items-center gap-2.5 flex-1">
          {/* Search */}
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by HSN code or description..."
              className="pl-9 pr-8 py-1.5 bg-gray-50/70 border-gray-200 text-sm focus-visible:ring-amber-500/20"
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

          {/* Status Filter Toggle */}
          <div className="flex rounded-lg bg-gray-100 p-1 border border-gray-200 text-xs font-medium">
            <button
              onClick={() => setStatusFilter("ALL")}
              className={`px-3 py-1 rounded-md transition-all ${
                statusFilter === "ALL"
                  ? "bg-white text-gray-900 shadow-xs font-semibold"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              All Status
            </button>
            <button
              onClick={() => setStatusFilter("ACTIVE")}
              className={`px-3 py-1 rounded-md transition-all ${
                statusFilter === "ACTIVE"
                  ? "bg-emerald-600 text-white shadow-xs font-semibold"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Active
            </button>
            <button
              onClick={() => setStatusFilter("INACTIVE")}
              className={`px-3 py-1 rounded-md transition-all ${
                statusFilter === "INACTIVE"
                  ? "bg-rose-600 text-white shadow-xs font-semibold"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Inactive
            </button>
          </div>

          {/* Rate Filter Dropdown */}
          <div className="flex items-center gap-1">
            <select
              value={rateFilter}
              onChange={(e) => setRateFilter(e.target.value)}
              className="bg-gray-50 border border-gray-200 text-gray-700 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
            >
              <option value="ALL">All GST Rates</option>
              <option value="18">18% (Standard)</option>
              <option value="12">12% (Tier 2)</option>
              <option value="5">5% (Tier 1)</option>
              <option value="28">28% (Luxury)</option>
              <option value="0">0% (Nil / Exempt)</option>
              <option value="OTHER">Other Rates</option>
            </select>
          </div>

          {/* Reset Filters */}
          {(searchQuery || statusFilter !== "ALL" || rateFilter !== "ALL") && (
            <button
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("ALL");
                setRateFilter("ALL");
              }}
              className="text-xs text-amber-600 hover:text-amber-800 underline font-medium px-2 py-1"
            >
              Reset Filters
            </button>
          )}
        </div>

        <div className="text-xs text-gray-500 font-medium px-2 text-right">
          Showing <span className="font-semibold text-gray-900">{filteredItems.length}</span> of {items.length} records
        </div>
      </div>

      {/* Main Table Card */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-16 flex flex-col items-center justify-center gap-3 text-gray-400">
            <RefreshCw className="w-7 h-7 animate-spin text-amber-600" />
            <p className="text-sm font-medium text-gray-500">Loading HSN / SAC codes...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-14 h-14 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto mb-3.5 shadow-inner">
              <Barcode className="w-7 h-7" />
            </div>
            <h3 className="text-base font-semibold text-gray-900">
              {searchQuery || statusFilter !== "ALL" || rateFilter !== "ALL"
                ? "No matching HSN codes"
                : "No HSN / SAC Codes Found"}
            </h3>
            <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
              {searchQuery || statusFilter !== "ALL" || rateFilter !== "ALL"
                ? "Try adjusting your search filters or clear the filter query."
                : "Define GST tax rates, HSN codes for goods, and SAC codes for services to use across billing."}
            </p>
            {(!searchQuery && statusFilter === "ALL" && rateFilter === "ALL") && (
              <Button
                onClick={handleOpenCreate}
                size="sm"
                className="mt-4 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold inline-flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" /> Add First HSN Code
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50/80 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                  <th className="px-5 py-3.5">HSN / SAC Code</th>
                  <th className="px-5 py-3.5 min-w-[220px]">Description</th>
                  <th className="px-4 py-3.5 text-center">CGST %</th>
                  <th className="px-4 py-3.5 text-center">SGST %</th>
                  <th className="px-4 py-3.5 text-center">IGST %</th>
                  <th className="px-4 py-3.5 text-center">Cess %</th>
                  <th className="px-4 py-3.5 text-center">GST Tier</th>
                  <th className="px-4 py-3.5">Effective Period</th>
                  <th className="px-4 py-3.5 text-center">Status</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-sm">
                {filteredItems.map((item) => {
                  const cgst = parseFloat(String(item.cgst_rate || 0));
                  const sgst = parseFloat(String(item.sgst_rate || 0));
                  const igst = parseFloat(String(item.igst_rate || 0));
                  const cess = parseFloat(String(item.cess_rate || 0));

                  return (
                    <tr key={item.id} className="hover:bg-amber-50/20 transition-colors group">
                      {/* Code */}
                      <td className="px-5 py-3.5 font-medium text-gray-900">
                        <div className="flex items-center gap-2">
                          <span className="font-mono bg-slate-100 hover:bg-slate-200 text-slate-900 font-bold px-2.5 py-1 rounded-md text-xs tracking-wider border border-slate-200 transition-colors">
                            {item.hsn_code}
                          </span>
                          <button
                            onClick={() => handleCopyCode(item.hsn_code)}
                            title="Copy code"
                            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-700 transition-opacity p-1"
                          >
                            {copiedCode === item.hsn_code ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>

                      {/* Description */}
                      <td className="px-5 py-3.5 text-gray-700">
                        <div className="line-clamp-2 max-w-md text-xs sm:text-sm" title={item.description}>
                          {item.description || "-"}
                        </div>
                      </td>

                      {/* CGST */}
                      <td className="px-4 py-3.5 text-center font-mono text-xs font-semibold text-gray-700">
                        {cgst.toFixed(2)}%
                      </td>

                      {/* SGST */}
                      <td className="px-4 py-3.5 text-center font-mono text-xs font-semibold text-gray-700">
                        {sgst.toFixed(2)}%
                      </td>

                      {/* IGST */}
                      <td className="px-4 py-3.5 text-center font-mono text-xs font-bold text-gray-900">
                        {igst.toFixed(2)}%
                      </td>

                      {/* Cess */}
                      <td className="px-4 py-3.5 text-center font-mono text-xs text-gray-600">
                        {cess > 0 ? (
                          <span className="text-amber-700 font-semibold">{cess.toFixed(2)}%</span>
                        ) : (
                          <span className="text-gray-400">0.00%</span>
                        )}
                      </td>

                      {/* GST Tier Badge */}
                      <td className="px-4 py-3.5 text-center">
                        {getRateBadge(igst)}
                      </td>

                      {/* Effective Period */}
                      <td className="px-4 py-3.5 text-xs text-gray-500 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-gray-400" />
                          <span>
                            {item.effective_from
                              ? new Date(item.effective_from).toLocaleDateString("en-IN", {
                                  day: "2-digit",
                                  month: "short",
                                  year: "numeric",
                                })
                              : "Immediate"}
                          </span>
                          {item.effective_to && (
                            <span className="text-gray-400">
                              {" → "}
                              {new Date(item.effective_to).toLocaleDateString("en-IN", {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                              })}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5 text-center">
                        {item.is_active !== false ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                            Inactive
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-3.5 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenCalculator(item)}
                            className="h-8 w-8 p-0 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50"
                            title="Simulate Tax"
                          >
                            <Calculator className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenEdit(item)}
                            className="h-8 w-8 p-0 text-amber-600 hover:text-amber-800 hover:bg-amber-50"
                            title="Edit HSN Code"
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedItem(item);
                              setIsDeleteOpen(true);
                            }}
                            className="h-8 w-8 p-0 text-rose-600 hover:text-rose-800 hover:bg-rose-50"
                            title="Deactivate"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
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

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* ADD HSN CODE DIALOG */}
      {/* ═══════════════════════════════════════════════════════════ */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                <Plus className="w-4 h-4" />
              </div>
              Add New HSN / SAC Code
            </DialogTitle>
            <DialogDescription>
              Enter standard GST rates and applicability dates for this classification.
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleCreateSubmit} className="space-y-4">
            {/* Row 1: Code & Effective From */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">
                  HSN / SAC Code <span className="text-rose-500">*</span>
                </Label>
                <Input
                  type="text"
                  required
                  placeholder="e.g. 8503, 998222"
                  value={formData.hsn_code}
                  onChange={(e) =>
                    setFormData({ ...formData, hsn_code: e.target.value.toUpperCase().trim() })
                  }
                  className="font-mono uppercase font-semibold text-sm"
                  maxLength={20}
                />
                <p className="text-[11px] text-gray-400">Goods (2-8 digits) or Services (6 digits SAC)</p>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">
                  Effective From <span className="text-rose-500">*</span>
                </Label>
                <Input
                  type="date"
                  required
                  value={formData.effective_from}
                  onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
                  className="text-sm"
                />
              </div>
            </div>

            {/* Row 2: Description */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-gray-700">
                Item / Service Description <span className="text-rose-500">*</span>
              </Label>
              <Textarea
                required
                rows={2}
                placeholder="Description of goods or services under this tax rate..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="text-sm"
              />
            </div>

            {/* Quick GST Presets */}
            <div className="space-y-2 pt-2 border-t border-gray-100">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  Quick GST Rate Presets
                </Label>
                <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.auto_split}
                    onChange={(e) => setFormData({ ...formData, auto_split: e.target.checked })}
                    className="rounded border-gray-300 text-amber-600 focus:ring-amber-500 w-3.5 h-3.5"
                  />
                  <span>Auto split IGST to CGST/SGST</span>
                </label>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {GST_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => applyCreatePreset(preset)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-semibold border transition-all hover:scale-[1.02] text-center ${preset.color}`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Rate Inputs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50/80 p-3.5 rounded-xl border border-gray-200">
              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-gray-600 uppercase">CGST % (Central)</Label>
                <Input
                  type="number"
                  min="0"
                  max="50"
                  step="0.01"
                  value={formData.cgst_rate}
                  onChange={(e) =>
                    setFormData({ ...formData, cgst_rate: parseFloat(e.target.value) || 0 })
                  }
                  className="bg-white text-sm font-mono text-center font-bold"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-gray-600 uppercase">SGST % (State)</Label>
                <Input
                  type="number"
                  min="0"
                  max="50"
                  step="0.01"
                  value={formData.sgst_rate}
                  onChange={(e) =>
                    setFormData({ ...formData, sgst_rate: parseFloat(e.target.value) || 0 })
                  }
                  className="bg-white text-sm font-mono text-center font-bold"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-indigo-700 uppercase">IGST % (Integrated)</Label>
                <Input
                  type="number"
                  min="0"
                  max="50"
                  step="0.01"
                  value={formData.igst_rate}
                  onChange={(e) => handleCreateIgstChange(parseFloat(e.target.value) || 0)}
                  className="bg-white text-sm font-mono text-center font-bold text-indigo-700"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-gray-600 uppercase">Cess % (Optional)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={formData.cess_rate}
                  onChange={(e) =>
                    setFormData({ ...formData, cess_rate: parseFloat(e.target.value) || 0 })
                  }
                  className="bg-white text-sm font-mono text-center"
                />
              </div>
            </div>

            {/* Live GST Summary Banner */}
            <div className="bg-amber-500/10 border border-amber-200/80 rounded-xl p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calculator className="w-4 h-4 text-amber-700" />
                <span className="text-xs font-semibold text-amber-900">
                  Total Effective Tax:
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs font-bold">
                <span className="text-emerald-700 font-mono">
                  Intra-state: {(Number(formData.cgst_rate) + Number(formData.sgst_rate) + Number(formData.cess_rate)).toFixed(2)}%
                </span>
                <span className="text-gray-300">|</span>
                <span className="text-indigo-700 font-mono">
                  Inter-state (IGST): {(Number(formData.igst_rate) + Number(formData.cess_rate)).toFixed(2)}%
                </span>
              </div>
            </div>

            {/* Effective To & Active */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">Effective To (Optional)</Label>
                <Input
                  type="date"
                  value={formData.effective_to}
                  onChange={(e) => setFormData({ ...formData, effective_to: e.target.value })}
                  placeholder="Leave empty if indefinite"
                  className="text-sm"
                />
              </div>

              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="create_is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded border-gray-300 text-amber-600 focus:ring-amber-500 w-4 h-4 cursor-pointer"
                />
                <label htmlFor="create_is_active" className="text-xs font-semibold text-gray-700 cursor-pointer">
                  Code is Active for Billing
                </label>
              </div>
            </div>

            <DialogFooter className="pt-4 border-t border-gray-100 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
                disabled={formSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={formSubmitting}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-2"
              >
                {formSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    Save HSN Code
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* EDIT HSN CODE DIALOG */}
      {/* ═══════════════════════════════════════════════════════════ */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                <Edit2 className="w-4 h-4" />
              </div>
              Edit HSN / SAC Code
            </DialogTitle>
            <DialogDescription>
              Update tax rates, description, or validity period for code:{" "}
              <span className="font-mono font-bold text-gray-900">{editFormData.hsn_code}</span>
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleEditSubmit} className="space-y-4">
            {/* Row 1: Code (Readonly) & Effective From */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">HSN / SAC Code</Label>
                <Input
                  type="text"
                  disabled
                  value={editFormData.hsn_code}
                  className="font-mono uppercase font-bold text-sm bg-gray-100 cursor-not-allowed"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">
                  Effective From <span className="text-rose-500">*</span>
                </Label>
                <Input
                  type="date"
                  required
                  value={editFormData.effective_from}
                  onChange={(e) => setEditFormData({ ...editFormData, effective_from: e.target.value })}
                  className="text-sm"
                />
              </div>
            </div>

            {/* Row 2: Description */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-gray-700">
                Item / Service Description <span className="text-rose-500">*</span>
              </Label>
              <Textarea
                required
                rows={2}
                placeholder="Description of goods or services..."
                value={editFormData.description}
                onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                className="text-sm"
              />
            </div>

            {/* Quick GST Presets */}
            <div className="space-y-2 pt-2 border-t border-gray-100">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  Quick GST Rate Presets
                </Label>
                <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editFormData.auto_split}
                    onChange={(e) => setEditFormData({ ...editFormData, auto_split: e.target.checked })}
                    className="rounded border-gray-300 text-amber-600 focus:ring-amber-500 w-3.5 h-3.5"
                  />
                  <span>Auto split IGST to CGST/SGST</span>
                </label>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {GST_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => applyEditPreset(preset)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-semibold border transition-all hover:scale-[1.02] text-center ${preset.color}`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Rate Inputs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50/80 p-3.5 rounded-xl border border-gray-200">
              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-gray-600 uppercase">CGST % (Central)</Label>
                <Input
                  type="number"
                  min="0"
                  max="50"
                  step="0.01"
                  value={editFormData.cgst_rate}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, cgst_rate: parseFloat(e.target.value) || 0 })
                  }
                  className="bg-white text-sm font-mono text-center font-bold"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-gray-600 uppercase">SGST % (State)</Label>
                <Input
                  type="number"
                  min="0"
                  max="50"
                  step="0.01"
                  value={editFormData.sgst_rate}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, sgst_rate: parseFloat(e.target.value) || 0 })
                  }
                  className="bg-white text-sm font-mono text-center font-bold"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-indigo-700 uppercase">IGST % (Integrated)</Label>
                <Input
                  type="number"
                  min="0"
                  max="50"
                  step="0.01"
                  value={editFormData.igst_rate}
                  onChange={(e) => handleEditIgstChange(parseFloat(e.target.value) || 0)}
                  className="bg-white text-sm font-mono text-center font-bold text-indigo-700"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-[11px] font-bold text-gray-600 uppercase">Cess % (Optional)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={editFormData.cess_rate}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, cess_rate: parseFloat(e.target.value) || 0 })
                  }
                  className="bg-white text-sm font-mono text-center"
                />
              </div>
            </div>

            {/* Live GST Summary Banner */}
            <div className="bg-amber-500/10 border border-amber-200/80 rounded-xl p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calculator className="w-4 h-4 text-amber-700" />
                <span className="text-xs font-semibold text-amber-900">
                  Total Effective Tax:
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs font-bold">
                <span className="text-emerald-700 font-mono">
                  Intra-state: {(Number(editFormData.cgst_rate) + Number(editFormData.sgst_rate) + Number(editFormData.cess_rate)).toFixed(2)}%
                </span>
                <span className="text-gray-300">|</span>
                <span className="text-indigo-700 font-mono">
                  Inter-state (IGST): {(Number(editFormData.igst_rate) + Number(editFormData.cess_rate)).toFixed(2)}%
                </span>
              </div>
            </div>

            {/* Effective To & Active */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">Effective To (Optional)</Label>
                <Input
                  type="date"
                  value={editFormData.effective_to}
                  onChange={(e) => setEditFormData({ ...editFormData, effective_to: e.target.value })}
                  placeholder="Leave empty if indefinite"
                  className="text-sm"
                />
              </div>

              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="edit_is_active"
                  checked={editFormData.is_active}
                  onChange={(e) => setEditFormData({ ...editFormData, is_active: e.target.checked })}
                  className="rounded border-gray-300 text-amber-600 focus:ring-amber-500 w-4 h-4 cursor-pointer"
                />
                <label htmlFor="edit_is_active" className="text-xs font-semibold text-gray-700 cursor-pointer">
                  Code is Active for Billing
                </label>
              </div>
            </div>

            <DialogFooter className="pt-4 border-t border-gray-100 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditOpen(false)}
                disabled={formSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={formSubmitting}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-2"
              >
                {formSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    Update HSN Code
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* GST TAX CALCULATOR MODAL */}
      {/* ═══════════════════════════════════════════════════════════ */}
      <Dialog open={isCalcOpen} onOpenChange={setIsCalcOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
                <Calculator className="w-4 h-4" />
              </div>
              GST Tax Calculation Simulator
            </DialogTitle>
            <DialogDescription>
              Test and verify real-time invoice tax breakdowns for Intra-State vs Inter-State transactions.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* HSN Selection */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold text-gray-700">Select HSN / SAC Code</Label>
              <select
                value={calcState.selectedHsnId}
                onChange={(e) => {
                  const selectedId = Number(e.target.value);
                  const found = items.find((i) => i.id === selectedId);
                  if (found) {
                    setCalcState({
                      ...calcState,
                      selectedHsnId: found.id,
                      hsn_code: found.hsn_code,
                      description: found.description,
                      cgst_rate: parseFloat(String(found.cgst_rate || 0)),
                      sgst_rate: parseFloat(String(found.sgst_rate || 0)),
                      igst_rate: parseFloat(String(found.igst_rate || 0)),
                      cess_rate: parseFloat(String(found.cess_rate || 0)),
                    });
                  }
                }}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 text-sm font-medium focus:ring-2 focus:ring-indigo-500/20"
              >
                {items.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.hsn_code} - {i.description} (IGST: {parseFloat(String(i.igst_rate || 0))}%)
                  </option>
                ))}
              </select>
            </div>

            {/* Base Amount & Supply Type */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">Taxable Base Amount (₹)</Label>
                <Input
                  type="number"
                  min="1"
                  step="any"
                  value={calcState.baseAmount}
                  onChange={(e) =>
                    setCalcState({ ...calcState, baseAmount: parseFloat(e.target.value) || 0 })
                  }
                  className="text-base font-mono font-bold text-gray-900"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">Transaction Supply Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setCalcState({ ...calcState, supplyType: "INTRA" })}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                      calcState.supplyType === "INTRA"
                        ? "bg-emerald-600 text-white border-emerald-600 shadow-xs"
                        : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                    }`}
                  >
                    Intra-State (CGST+SGST)
                  </button>
                  <button
                    type="button"
                    onClick={() => setCalcState({ ...calcState, supplyType: "INTER" })}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                      calcState.supplyType === "INTER"
                        ? "bg-indigo-600 text-white border-indigo-600 shadow-xs"
                        : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                    }`}
                  >
                    Inter-State (IGST)
                  </button>
                </div>
              </div>
            </div>

            {/* Calculation Result Breakdown Card */}
            <div className="bg-slate-900 text-white rounded-xl p-4 space-y-3 font-mono text-sm shadow-md">
              <div className="flex justify-between items-center text-slate-300 pb-2 border-b border-slate-800 text-xs">
                <span>Taxable Amount</span>
                <span className="font-bold text-white">₹{calculatedTax.base.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
              </div>

              {calcState.supplyType === "INTRA" ? (
                <>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400">CGST ({calcState.cgst_rate}%):</span>
                    <span className="text-emerald-400 font-semibold">
                      +₹{calculatedTax.cgstAmt.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400">SGST ({calcState.sgst_rate}%):</span>
                    <span className="text-emerald-400 font-semibold">
                      +₹{calculatedTax.sgstAmt.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </>
              ) : (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">IGST ({calcState.igst_rate}%):</span>
                  <span className="text-indigo-400 font-semibold">
                    +₹{calculatedTax.igstAmt.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              )}

              {calcState.cess_rate > 0 && (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Cess ({calcState.cess_rate}%):</span>
                  <span className="text-amber-400 font-semibold">
                    +₹{calculatedTax.cessAmt.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              )}

              <div className="flex justify-between items-center pt-2 border-t border-slate-800 text-xs text-slate-400">
                <span>Total GST Amount</span>
                <span className="text-amber-400 font-bold">
                  ₹{calculatedTax.totalTax.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </span>
              </div>

              <div className="flex justify-between items-center pt-2 border-t border-slate-700 text-base font-bold">
                <span className="text-white">Total Invoice Payable</span>
                <span className="text-emerald-400 text-lg">
                  ₹{calculatedTax.grandTotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              onClick={() => setIsCalcOpen(false)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold w-full sm:w-auto"
            >
              Close Simulator
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* DEACTIVATE CONFIRMATION DIALOG */}
      {/* ═══════════════════════════════════════════════════════════ */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-rose-700">
              <AlertCircle className="w-5 h-5 text-rose-600" />
              Deactivate HSN Code
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to deactivate code{" "}
              <span className="font-mono font-bold text-gray-900">
                {selectedItem?.hsn_code}
              </span>
              ? Inactive codes will not appear in sales invoice auto-suggestions.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="pt-3 border-t border-gray-100 flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsDeleteOpen(false)}
              disabled={formSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={formSubmitting}
              className="bg-rose-600 hover:bg-rose-700 text-white font-semibold"
            >
              {formSubmitting ? "Deactivating..." : "Yes, Deactivate"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
