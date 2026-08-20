"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import toast, { Toaster } from "react-hot-toast";

// UI Components
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

// Lucide Icons
import {
  Factory,
  Plus,
  Search,
  RefreshCw,
  Eye,
  Edit,
  Play,
  CheckCircle,
  XCircle,
  Trash2,
  AlertTriangle,
  Boxes,
  ShoppingCart,
  Layers,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Info,
  Clock,
  Check,
  ExternalLink,
  Loader2,
} from "lucide-react";

// Types & Interfaces
interface Company {
  id: number;
  company_name: string;
  company_code?: string;
}

interface BOM {
  id: number;
  bom_code?: string;
  bom_name: string;
  finished_product_name: string;
  status: string;
}

interface StockCheckComponent {
  component_id: number;
  component_name: string;
  component_code?: string;
  required_qty: number;
  available_qty: number;
  shortage_qty: number;
  is_sufficient: boolean;
}

interface StockCheckResult {
  can_manufacture: boolean;
  components: StockCheckComponent[];
}

interface ManufacturingLineItem {
  id: number;
  manufacturing_order_id?: number;
  component_id: number;
  component_name?: string;
  component_code?: string;
  planned_qty: number;
  actual_qty_consumed?: number;
  unit_of_measure?: string;
  status?: string;
  is_additional?: boolean;
  notes?: string;
}

interface ManufacturingOrder {
  id: number;
  order_number: string;
  company_id: number;
  company_name?: string;
  bom_id: number;
  bom_name?: string;
  finished_product_id?: number;
  finished_product_name?: string;
  planned_qty: number;
  actual_qty?: number;
  rejected_qty?: number;
  unit_of_measure?: string;
  priority: "URGENT" | "HIGH" | "NORMAL" | "LOW" | string;
  estimated_cost?: number;
  actual_cost?: number;
  status: "PLANNED" | "APPROVED" | "IN_PROGRESS" | "COMPLETED" | "PARTIALLY_COMPLETED" | "CANCELLED" | string;
  material_status?: "READY" | "PARTIAL" | "MISSING" | "UNKNOWN" | string;
  planned_start_date?: string;
  planned_end_date?: string;
  notes?: string;
  created_at?: string;
  line_items?: ManufacturingLineItem[];
}

interface AggregatedShortage {
  company_id: number;
  component_id: number;
  component_code: string;
  component_name: string;
  total_required: number;
  available_qty: number;
  total_shortage: number;
  source_orders: {
    type: string;
    order_id: number;
    order_number: string;
    shortage_qty: number;
  }[];
}

interface StockItem {
  id: number;
  item_code?: string;
  item_name: string;
  unit_of_measure?: string;
}

// Helpers
const formatCurrency = (amt?: number | string | null) => {
  const num = typeof amt === "string" ? parseFloat(amt) : amt || 0;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(num);
};

const formatNumber = (val?: number | string | null) => {
  if (val === null || val === undefined) return "0";
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return "0";
  return num.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
};

const _MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const fmtOrderDate = (dtStr?: string) => {
  if (!dtStr) return "-";
  const d = new Date(dtStr);
  if (isNaN(d.getTime())) return "-";
  return `${String(d.getDate()).padStart(2, "0")} ${_MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`;
};

const fmtOrderMonth = (dtStr?: string) => {
  if (!dtStr) return "-";
  const d = new Date(dtStr);
  if (isNaN(d.getTime())) return "-";
  return `${_MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`;
};

export default function ManufacturingPage() {
  const { token } = useStaffAuth();

  // Active Main Tab: 'orders' | 'shortages'
  const [activeTab, setActiveTab] = useState<"orders" | "shortages">("orders");

  // Companies & BOMs Master Lists
  const [companies, setCompanies] = useState<Company[]>([]);
  const [boms, setBoms] = useState<BOM[]>([]);

  // Orders State
  const [orders, setOrders] = useState<ManufacturingOrder[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(true);

  // Filters State
  const [filterCompany, setFilterCompany] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterPriority, setFilterPriority] = useState<string>("");
  const [filterMonth, setFilterMonth] = useState<string>("");
  const [filterYear, setFilterYear] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Sorting State
  const [sortKey, setSortKey] = useState<string>("order_number");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  // Shortages Tab State
  const [shortageCompanyFilter, setShortageCompanyFilter] = useState<string>("");
  const [shortages, setShortages] = useState<AggregatedShortage[]>([]);
  const [loadingShortages, setLoadingShortages] = useState(false);
  const [selectedShortages, setSelectedShortages] = useState<number[]>([]);
  const [shortageBadgeCount, setShortageBadgeCount] = useState<number>(0);
  const [procurementSubmitting, setProcurementSubmitting] = useState(false);

  // Modals Open State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isCompleteOpen, setIsCompleteOpen] = useState(false);
  const [isMaterialStatusOpen, setIsMaterialStatusOpen] = useState(false);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isMaterialItemModalOpen, setIsMaterialItemModalOpen] = useState(false);
  const [isRemoveMaterialModalOpen, setIsRemoveMaterialModalOpen] = useState(false);

  // Active Item States for Modals
  const [selectedOrder, setSelectedOrder] = useState<ManufacturingOrder | null>(null);
  const [materialStatusData, setMaterialStatusData] = useState<{
    orderId: number;
    orderNumber: string;
    companyId: number;
    loading: boolean;
    refreshing: boolean;
    data: {
      ready_components: number;
      shortage_components: number;
      can_manufacture: boolean;
      last_checked_at?: string;
      components: StockCheckComponent[];
    } | null;
  }>({
    orderId: 0,
    orderNumber: "",
    companyId: 0,
    loading: false,
    refreshing: false,
    data: null,
  });

  // Create Form State
  const [createForm, setCreateForm] = useState({
    company_id: "",
    bom_id: "",
    planned_qty: 1,
    priority: "NORMAL",
    planned_start_date: "",
    planned_end_date: "",
    notes: "",
  });
  const [bomsLoading, setBomsLoading] = useState(false);
  const [stockCheckLoading, setStockCheckLoading] = useState(false);
  const [stockCheckResult, setStockCheckResult] = useState<StockCheckResult | null>(null);
  const [createSubmitting, setCreateSubmitting] = useState(false);

  // Complete Form State
  const [completeForm, setCompleteForm] = useState({
    orderId: 0,
    actual_qty: 0,
    rejected_qty: 0,
    remarks: "",
  });
  const [completeSubmitting, setCompleteSubmitting] = useState(false);

  // Cancel Form State
  const [cancelForm, setCancelForm] = useState({
    orderId: 0,
    orderNumber: "",
    reason: "",
  });
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  // Delete Form State
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; orderNumber: string } | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // Edit Form State
  const [editForm, setEditForm] = useState({
    id: 0,
    company_name: "",
    bom_name: "",
    finished_product_name: "",
    planned_qty: 1,
    priority: "NORMAL",
    planned_start_date: "",
    planned_end_date: "",
    notes: "",
    status: "",
    company_id: 0,
  });
  const [editStockItems, setEditStockItems] = useState<StockItem[]>([]);
  const [editMaterialsLoading, setEditMaterialsLoading] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);

  // Material Sub-Item Modal State (Add / Edit)
  const [materialItemForm, setMaterialItemForm] = useState<{
    mode: "add" | "edit";
    lineId?: number;
    component_id: string;
    planned_qty: number;
    unit_of_measure: string;
    notes: string;
  }>({
    mode: "add",
    component_id: "",
    planned_qty: 1,
    unit_of_measure: "PCS",
    notes: "",
  });
  const [materialItemSubmitting, setMaterialItemSubmitting] = useState(false);

  // Remove Material Modal State
  const [removeMaterialTarget, setRemoveMaterialTarget] = useState<{
    lineId: number;
    name: string;
    plannedQty: number;
    reason: string;
  } | null>(null);
  const [removeMaterialSubmitting, setRemoveMaterialSubmitting] = useState(false);

  // Load Companies
  const loadCompanies = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/companies");
      const compList = res.data?.companies || [];
      setCompanies(compList);
    } catch (e) {
      console.error("Failed to load companies", e);
    }
  }, []);

  // Preload Shortages Count Badge Silently
  const loadShortagesBadge = useCallback(async () => {
    try {
      const res = await api.get("/staff/accounts/procurement/aggregated-shortages");
      const data = res.data?.shortages || [];
      setShortageBadgeCount(data.length);
    } catch (e) {
      // silent
    }
  }, []);

  // Load Manufacturing Orders
  const loadOrders = useCallback(async () => {
    setLoadingOrders(true);
    try {
      let url = `/staff/accounts/manufacturing?page=1&page_size=100`;
      if (filterCompany) url += `&company_id=${filterCompany}`;
      if (filterStatus) url += `&status=${filterStatus}`;
      if (filterPriority) url += `&priority=${filterPriority}`;

      const res = await api.get(url);
      setOrders(res.data?.orders || []);
    } catch (e) {
      console.error("Failed to load manufacturing orders", e);
      toast.error("Failed to load manufacturing orders");
      setOrders([]);
    } finally {
      setLoadingOrders(false);
    }
  }, [filterCompany, filterStatus, filterPriority]);

  // Load Shortages List
  const loadShortages = useCallback(async () => {
    setLoadingShortages(true);
    try {
      let url = `/staff/accounts/procurement/aggregated-shortages`;
      if (shortageCompanyFilter) url += `?company_id=${shortageCompanyFilter}`;
      const res = await api.get(url);
      const data = res.data?.shortages || [];
      setShortages(data);
      setShortageBadgeCount(data.length);
      setSelectedShortages([]);
    } catch (e) {
      console.error("Failed to load aggregated shortages", e);
      toast.error("Failed to load shortages");
      setShortages([]);
    } finally {
      setLoadingShortages(false);
    }
  }, [shortageCompanyFilter]);

  // Initial Data Load
  useEffect(() => {
    if (token) {
      loadCompanies();
      loadOrders();
      loadShortagesBadge();
    }
  }, [token, loadCompanies, loadOrders, loadShortagesBadge]);

  // Dynamic Year Options from Orders
  const yearOptions = useMemo(() => {
    const years = [
      ...new Set(
        orders
          .map((o) => {
            if (!o.created_at) return null;
            const d = new Date(o.created_at);
            return isNaN(d.getTime()) ? null : d.getFullYear();
          })
          .filter(Boolean) as number[]
      ),
    ].sort((a, b) => b - a);
    return years;
  }, [orders]);

  // Client-side Filtered and Sorted Orders
  const filteredAndSortedOrders = useMemo(() => {
    let list = [...orders];

    // Filter Month & Year & Search
    if (filterMonth) {
      list = list.filter((o) => {
        if (!o.created_at) return false;
        const d = new Date(o.created_at);
        return !isNaN(d.getTime()) && d.getMonth() + 1 === parseInt(filterMonth);
      });
    }

    if (filterYear) {
      list = list.filter((o) => {
        if (!o.created_at) return false;
        const d = new Date(o.created_at);
        return !isNaN(d.getTime()) && d.getFullYear() === parseInt(filterYear);
      });
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (o) =>
          o.order_number?.toLowerCase().includes(q) ||
          o.finished_product_name?.toLowerCase().includes(q) ||
          o.company_name?.toLowerCase().includes(q) ||
          o.bom_name?.toLowerCase().includes(q)
      );
    }

    // Sort
    list.sort((a: any, b: any) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];

      if (sortKey === "estimated_cost" || sortKey === "planned_qty" || sortKey === "actual_qty") {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
      } else {
        aVal = String(aVal || "").toLowerCase();
        bVal = String(bVal || "").toLowerCase();
      }

      if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return list;
  }, [orders, filterMonth, filterYear, searchQuery, sortKey, sortDir]);

  // Summary Metrics
  const summaryMetrics = useMemo(() => {
    const total = orders.length;
    const inProgress = orders.filter((o) => o.status === "IN_PROGRESS").length;
    const completed = orders.filter((o) => o.status === "COMPLETED" || o.status === "PARTIALLY_COMPLETED").length;
    const planned = orders.filter((o) => o.status === "PLANNED" || o.status === "APPROVED").length;
    return { total, inProgress, completed, planned };
  }, [orders]);

  // Handle Sort Toggle
  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  // Switch Main Tabs
  const handleTabSwitch = (tab: "orders" | "shortages") => {
    setActiveTab(tab);
    if (tab === "shortages") {
      loadShortages();
    }
  };

  // -------------------------------------------------------------
  // CREATE ORDER HANDLERS & STOCK CHECK
  // -------------------------------------------------------------
  const handleCreateOpen = () => {
    setCreateForm({
      company_id: "",
      bom_id: "",
      planned_qty: 1,
      priority: "NORMAL",
      planned_start_date: "",
      planned_end_date: "",
      notes: "",
    });
    setBoms([]);
    setStockCheckResult(null);
    setIsCreateOpen(true);
  };

  const handleCompanyChangeForCreate = async (companyId: string) => {
    setCreateForm((prev) => ({ ...prev, company_id: companyId, bom_id: "" }));
    setStockCheckResult(null);
    if (!companyId) {
      setBoms([]);
      return;
    }
    setBomsLoading(true);
    try {
      const res = await api.get(`/staff/accounts/bom?company_id=${companyId}&page_size=100`);
      setBoms(res.data?.boms || []);
    } catch (e) {
      console.error("Failed to load BOMs", e);
      toast.error("Failed to load BOMs for selected company");
      setBoms([]);
    } finally {
      setBomsLoading(false);
    }
  };

  const triggerStockCheck = async (bomId: string, companyId: string, qty: number) => {
    if (!bomId || !companyId || !qty || qty <= 0) {
      setStockCheckResult(null);
      return;
    }
    setStockCheckLoading(true);
    try {
      const res = await api.get(
        `/staff/accounts/manufacturing/check-stock?bom_id=${bomId}&company_id=${companyId}&planned_qty=${qty}`
      );
      setStockCheckResult(res.data);
    } catch (e) {
      console.error("Failed to check stock", e);
      setStockCheckResult(null);
    } finally {
      setStockCheckLoading(false);
    }
  };

  const handleBomChangeForCreate = (bomId: string) => {
    setCreateForm((prev) => ({ ...prev, bom_id: bomId }));
    triggerStockCheck(bomId, createForm.company_id, createForm.planned_qty);
  };

  const handleQtyChangeForCreate = (qty: number) => {
    setCreateForm((prev) => ({ ...prev, planned_qty: qty }));
    triggerStockCheck(createForm.bom_id, createForm.company_id, qty);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.company_id || !createForm.bom_id || !createForm.planned_qty) {
      toast.error("Please fill all required fields");
      return;
    }

    if (stockCheckResult && !stockCheckResult.can_manufacture) {
      const proceed = confirm(
        "Stock shortage detected for one or more components.\n\nThe order will be created with PLANNED status. You will need to procure missing stock before starting production.\n\nCreate order anyway?"
      );
      if (!proceed) return;
    }

    setCreateSubmitting(true);
    try {
      const payload = {
        company_id: parseInt(createForm.company_id),
        bom_id: parseInt(createForm.bom_id),
        planned_qty: parseFloat(String(createForm.planned_qty)),
        priority: createForm.priority,
        planned_start_date: createForm.planned_start_date || null,
        planned_end_date: createForm.planned_end_date || null,
        notes: createForm.notes || null,
      };

      await api.post("/staff/accounts/manufacturing", payload);
      toast.success("Manufacturing order created successfully!");
      setIsCreateOpen(false);
      loadOrders();
      loadShortagesBadge();
    } catch (err: any) {
      console.error("Create order failed", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to create manufacturing order");
    } finally {
      setCreateSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // VIEW ORDER MODAL
  // -------------------------------------------------------------
  const handleViewOrder = async (orderId: number) => {
    try {
      const res = await api.get(`/staff/accounts/manufacturing/${orderId}`);
      setSelectedOrder(res.data);
      setIsViewOpen(true);
    } catch (e) {
      console.error("Failed to load order details", e);
      toast.error("Failed to load order details");
    }
  };

  // -------------------------------------------------------------
  // START ORDER
  // -------------------------------------------------------------
  const handleStartOrder = async (orderId: number, orderNumber: string) => {
    if (!confirm(`Start manufacturing for ${orderNumber}?\n\nThis will allocate and consume required components from stock.`)) {
      return;
    }
    try {
      await api.post(`/staff/accounts/manufacturing/${orderId}/start`, {});
      toast.success(`Manufacturing started for order ${orderNumber}`);
      loadOrders();
    } catch (err: any) {
      console.error("Failed to start order", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to start manufacturing");
    }
  };

  // -------------------------------------------------------------
  // COMPLETE ORDER MODAL & SUBMIT
  // -------------------------------------------------------------
  const handleOpenCompleteModal = (order: ManufacturingOrder) => {
    setCompleteForm({
      orderId: order.id,
      actual_qty: order.planned_qty || 1,
      rejected_qty: 0,
      remarks: "",
    });
    setSelectedOrder(order);
    setIsCompleteOpen(true);
  };

  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (completeForm.actual_qty === undefined || completeForm.actual_qty < 0) {
      toast.error("Valid actual quantity produced is required");
      return;
    }

    setCompleteSubmitting(true);
    try {
      await api.post(`/staff/accounts/manufacturing/${completeForm.orderId}/complete`, {
        actual_qty: parseFloat(String(completeForm.actual_qty)),
        rejected_qty: parseFloat(String(completeForm.rejected_qty || 0)),
        remarks: completeForm.remarks || null,
      });
      toast.success("Order marked as completed!");
      setIsCompleteOpen(false);
      loadOrders();
    } catch (err: any) {
      console.error("Failed to complete order", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to complete order");
    } finally {
      setCompleteSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // CANCEL ORDER MODAL & SUBMIT
  // -------------------------------------------------------------
  const handleOpenCancelModal = (order: ManufacturingOrder) => {
    setCancelForm({
      orderId: order.id,
      orderNumber: order.order_number,
      reason: "",
    });
    setIsCancelModalOpen(true);
  };

  const handleCancelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelForm.reason.trim()) {
      toast.error("Please provide a reason for cancellation");
      return;
    }

    setCancelSubmitting(true);
    try {
      await api.post(`/staff/accounts/manufacturing/${cancelForm.orderId}/cancel`, {
        reason: cancelForm.reason.trim(),
      });
      toast.success(`Order ${cancelForm.orderNumber} cancelled`);
      setIsCancelModalOpen(false);
      loadOrders();
    } catch (err: any) {
      console.error("Failed to cancel order", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to cancel order");
    } finally {
      setCancelSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // DELETE ORDER MODAL & SUBMIT
  // -------------------------------------------------------------
  const handleOpenDeleteModal = (order: ManufacturingOrder) => {
    setDeleteTarget({ id: order.id, orderNumber: order.order_number });
    setIsDeleteModalOpen(true);
  };

  const handleDeleteSubmit = async () => {
    if (!deleteTarget) return;
    setDeleteSubmitting(true);
    try {
      await api.delete(`/staff/accounts/manufacturing/${deleteTarget.id}`);
      toast.success(`Order ${deleteTarget.orderNumber} deleted successfully`);
      setIsDeleteModalOpen(false);
      setDeleteTarget(null);
      loadOrders();
    } catch (err: any) {
      console.error("Failed to delete order", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to delete order");
    } finally {
      setDeleteSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // MATERIAL STATUS MODAL & LIVE REFRESH & PROCUREMENT
  // -------------------------------------------------------------
  const handleViewMaterialStatus = async (order: ManufacturingOrder) => {
    if (!order.company_id) {
      toast.error("Company segregation error: Company ID not found for this order");
      return;
    }

    setMaterialStatusData({
      orderId: order.id,
      orderNumber: order.order_number,
      companyId: order.company_id,
      loading: true,
      refreshing: false,
      data: null,
    });
    setIsMaterialStatusOpen(true);

    try {
      const res = await api.get(
        `/staff/accounts/manufacturing/${order.id}/material-status?company_id=${order.company_id}`
      );
      setMaterialStatusData((prev) => ({
        ...prev,
        loading: false,
        data: res.data,
      }));
    } catch (err: any) {
      console.error("Failed to load material status", err);
      toast.error(err.response?.data?.detail || "Failed to load material status");
      setIsMaterialStatusOpen(false);
    }
  };

  const handleRefreshMaterialStatus = async () => {
    const { orderId, companyId } = materialStatusData;
    if (!orderId || !companyId) return;

    setMaterialStatusData((prev) => ({ ...prev, refreshing: true }));
    try {
      const res = await api.post(
        `/staff/accounts/manufacturing/${orderId}/material-status/refresh?company_id=${companyId}`
      );
      setMaterialStatusData((prev) => ({
        ...prev,
        refreshing: false,
        data: res.data,
      }));
      toast.success("Material status refreshed successfully");
      loadOrders();
    } catch (err: any) {
      console.error("Failed to refresh material status", err);
      toast.error(err.response?.data?.detail || "Failed to refresh material status");
      setMaterialStatusData((prev) => ({ ...prev, refreshing: false }));
    }
  };

  const handleCreateProcurementFromShortage = async () => {
    const { orderId, orderNumber, companyId, data } = materialStatusData;
    if (!data || !data.components) return;

    const shortages = data.components.filter((c) => !c.is_sufficient);
    if (shortages.length === 0) {
      toast.error("No shortages to procure");
      return;
    }

    if (!confirm(`Create procurement request for ${shortages.length} component(s) with shortage?`)) {
      return;
    }

    try {
      const lineItems = shortages.map((c) => ({
        component_id: c.component_id,
        required_qty: c.required_qty,
        available_qty: c.available_qty,
        shortage_qty: c.shortage_qty,
        unit_of_measure: "PCS",
        source_order_ids: [
          {
            type: "MANUFACTURING",
            order_id: orderId,
            order_number: orderNumber,
          },
        ],
      }));

      const res = await api.post("/staff/accounts/procurement/requirements", {
        company_id: companyId,
        source_type: "MANUFACTURING",
        priority: "NORMAL",
        notes: `Procurement for Manufacturing Order ${orderNumber}`,
        line_items: lineItems,
      });

      const reqNum = res.data?.requirement?.requirement_number || "";
      toast.success(`Procurement request ${reqNum} created successfully!`);
      setIsMaterialStatusOpen(false);
      loadShortagesBadge();
    } catch (err: any) {
      console.error("Failed to create procurement request", err);
      toast.error(err.response?.data?.detail || "Failed to create procurement request");
    }
  };

  // -------------------------------------------------------------
  // EDIT ORDER MODAL & MATERIALS SUB-SECTION
  // -------------------------------------------------------------
  const loadEditStockItems = async (companyId: number) => {
    try {
      const res = await api.get(`/staff/accounts/stock-items?company_id=${companyId}&page_size=100`);
      setEditStockItems(res.data?.stock_items || []);
    } catch (e) {
      console.error("Failed to load stock items for edit", e);
      setEditStockItems([]);
    }
  };

  const refreshOrderForEdit = async (orderId: number) => {
    setEditMaterialsLoading(true);
    try {
      const res = await api.get(`/staff/accounts/manufacturing/${orderId}`);
      setSelectedOrder(res.data);
    } catch (e) {
      console.error("Failed to refresh order details", e);
    } finally {
      setEditMaterialsLoading(false);
    }
  };

  const handleOpenEditModal = async (orderId: number) => {
    try {
      const res = await api.get(`/staff/accounts/manufacturing/${orderId}`);
      const ord: ManufacturingOrder = res.data;
      setSelectedOrder(ord);

      setEditForm({
        id: ord.id,
        company_name: ord.company_name || "-",
        bom_name: `${ord.bom_name || "-"} (${ord.finished_product_name || "-"})`,
        finished_product_name: ord.finished_product_name || "-",
        planned_qty: ord.planned_qty || 1,
        priority: ord.priority || "NORMAL",
        planned_start_date: ord.planned_start_date ? ord.planned_start_date.split("T")[0] : "",
        planned_end_date: ord.planned_end_date ? ord.planned_end_date.split("T")[0] : "",
        notes: ord.notes || "",
        status: ord.status,
        company_id: ord.company_id,
      });

      setIsEditOpen(true);
      await loadEditStockItems(ord.company_id);
    } catch (e) {
      console.error("Failed to load order for edit", e);
      toast.error("Failed to load order for editing");
    }
  };

  const handleUpdateOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editForm.planned_qty || editForm.planned_qty <= 0) {
      toast.error("Quantity must be greater than 0");
      return;
    }

    setEditSubmitting(true);
    try {
      const payload = {
        planned_qty: parseFloat(String(editForm.planned_qty)),
        priority: editForm.priority,
        planned_start_date: editForm.planned_start_date || null,
        planned_end_date: editForm.planned_end_date || null,
        notes: editForm.notes || null,
      };

      await api.put(`/staff/accounts/manufacturing/${editForm.id}`, payload);
      toast.success("Order updated successfully!");
      setIsEditOpen(false);
      loadOrders();
    } catch (err: any) {
      console.error("Failed to update order", err);
      toast.error(err.response?.data?.detail || err.response?.data?.message || "Failed to update order");
    } finally {
      setEditSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // EXTRA MATERIAL ADD / EDIT / REMOVE SUB-MODALS
  // -------------------------------------------------------------
  const handleOpenAddMaterialModal = () => {
    if (!selectedOrder) return;
    setMaterialItemForm({
      mode: "add",
      component_id: "",
      planned_qty: 1,
      unit_of_measure: "PCS",
      notes: "",
    });
    setIsMaterialItemModalOpen(true);
  };

  const handleOpenEditMaterialModal = (line: ManufacturingLineItem) => {
    setMaterialItemForm({
      mode: "edit",
      lineId: line.id,
      component_id: String(line.component_id),
      planned_qty: line.planned_qty,
      unit_of_measure: line.unit_of_measure || "PCS",
      notes: line.notes || "",
    });
    setIsMaterialItemModalOpen(true);
  };

  const handleSaveMaterialItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;

    if (materialItemForm.mode === "add" && !materialItemForm.component_id) {
      toast.error("Please select a component");
      return;
    }
    if (!materialItemForm.planned_qty || materialItemForm.planned_qty <= 0) {
      toast.error("Planned quantity must be greater than 0");
      return;
    }

    setMaterialItemSubmitting(true);
    try {
      if (materialItemForm.mode === "add") {
        await api.post(`/staff/accounts/manufacturing/${selectedOrder.id}/line-items`, {
          component_id: parseInt(materialItemForm.component_id),
          planned_qty: parseFloat(String(materialItemForm.planned_qty)),
          unit_of_measure: materialItemForm.unit_of_measure,
          notes: materialItemForm.notes.trim() || null,
        });
        toast.success("Extra material added successfully");
      } else {
        await api.put(`/staff/accounts/manufacturing/line-items/${materialItemForm.lineId}`, {
          planned_qty: parseFloat(String(materialItemForm.planned_qty)),
          unit_of_measure: materialItemForm.unit_of_measure,
          notes: materialItemForm.notes.trim() || null,
        });
        toast.success("Material updated successfully");
      }

      setIsMaterialItemModalOpen(false);
      await refreshOrderForEdit(selectedOrder.id);
      loadOrders();
    } catch (err: any) {
      console.error("Save material failed", err);
      toast.error(err.response?.data?.detail || "Failed to save material");
    } finally {
      setMaterialItemSubmitting(false);
    }
  };

  const handleOpenRemoveMaterialModal = (line: ManufacturingLineItem) => {
    if (!line.is_additional) {
      toast.error("Cannot remove BOM-originated materials. Only extra materials can be removed.");
      return;
    }
    setRemoveMaterialTarget({
      lineId: line.id,
      name: `${line.component_name || "-"} (${line.component_code || "N/A"})`,
      plannedQty: line.planned_qty,
      reason: "",
    });
    setIsRemoveMaterialModalOpen(true);
  };

  const handleConfirmRemoveMaterial = async () => {
    if (!removeMaterialTarget || !selectedOrder) return;
    setRemoveMaterialSubmitting(true);
    try {
      let url = `/staff/accounts/manufacturing/line-items/${removeMaterialTarget.lineId}`;
      if (removeMaterialTarget.reason.trim()) {
        url += `?reason=${encodeURIComponent(removeMaterialTarget.reason.trim())}`;
      }
      await api.delete(url);
      toast.success("Material removed successfully");
      setIsRemoveMaterialModalOpen(false);
      setRemoveMaterialTarget(null);
      await refreshOrderForEdit(selectedOrder.id);
      loadOrders();
    } catch (err: any) {
      console.error("Remove material failed", err);
      toast.error(err.response?.data?.detail || "Failed to remove material");
    } finally {
      setRemoveMaterialSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // SHORTAGES TAB BATCH PROCUREMENT HANDLERS
  // -------------------------------------------------------------
  const handleToggleShortageItem = (idx: number, checked: boolean) => {
    if (checked) {
      setSelectedShortages((prev) => [...new Set([...prev, idx])]);
    } else {
      setSelectedShortages((prev) => prev.filter((i) => i !== idx));
    }
  };

  const handleToggleAllShortages = (checked: boolean) => {
    if (checked) {
      setSelectedShortages(shortages.map((_, i) => i));
    } else {
      setSelectedShortages([]);
    }
  };

  const handleCreateProcurementFromAllShortages = async () => {
    const toCreate = selectedShortages.length > 0
      ? selectedShortages.map((i) => shortages[i])
      : shortages;

    if (!toCreate.length) {
      toast.error("No shortage items to create procurement for.");
      return;
    }

    // Group by company_id
    const byCompany: Record<number, AggregatedShortage[]> = {};
    toCreate.forEach((s) => {
      if (!byCompany[s.company_id]) byCompany[s.company_id] = [];
      byCompany[s.company_id].push(s);
    });

    const companyIds = Object.keys(byCompany).map(Number);
    const confirmMsg = `Create ${companyIds.length} procurement requirement(s) for ${toCreate.length} component(s) across ${companyIds.length} company/companies?`;
    if (!confirm(confirmMsg)) return;

    setProcurementSubmitting(true);
    let createdCount = 0;
    try {
      for (const compId of companyIds) {
        const items = byCompany[compId];
        const lineItems = items.map((s) => ({
          component_id: s.component_id,
          required_qty: s.total_shortage,
          available_qty: s.available_qty,
          shortage_qty: s.total_shortage,
          unit_of_measure: "PCS",
          source_order_ids: (s.source_orders || []).map((o) => ({
            type: o.type,
            order_id: o.order_id,
            order_number: o.order_number,
          })),
        }));

        await api.post("/staff/accounts/procurement/requirements", {
          company_id: compId,
          source_type: "MANUFACTURING",
          priority: "NORMAL",
          notes: `Aggregated procurement from Manufacturing Shortages tab — ${items.length} component(s)`,
          line_items: lineItems,
        });
        createdCount++;
      }

      toast.success(`Created ${createdCount} procurement requirement(s)!`);
      setSelectedShortages([]);
      loadShortages();
    } catch (err: any) {
      console.error("Procurement batch creation error", err);
      toast.error("Failed to create some procurement requirements. Please check console.");
    } finally {
      setProcurementSubmitting(false);
    }
  };

  // Status Badge Component
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "PLANNED":
        return <Badge variant="secondary" className="bg-slate-100 text-slate-700 font-semibold">PLANNED</Badge>;
      case "APPROVED":
        return <Badge variant="secondary" className="bg-blue-100 text-blue-700 font-semibold">APPROVED</Badge>;
      case "IN_PROGRESS":
        return <Badge variant="secondary" className="bg-amber-100 text-amber-800 font-semibold animate-pulse">IN PROGRESS</Badge>;
      case "COMPLETED":
        return <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 font-semibold">COMPLETED</Badge>;
      case "PARTIALLY_COMPLETED":
        return <Badge variant="secondary" className="bg-pink-100 text-pink-800 font-semibold">PARTIAL</Badge>;
      case "CANCELLED":
        return <Badge variant="secondary" className="bg-rose-100 text-rose-800 font-semibold">CANCELLED</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  // Priority Badge Component
  const renderPriorityBadge = (priority: string) => {
    switch (priority) {
      case "URGENT":
        return <span className="text-xs font-bold text-red-600 uppercase tracking-wider">URGENT</span>;
      case "HIGH":
        return <span className="text-xs font-bold text-amber-600 uppercase tracking-wider">HIGH</span>;
      case "NORMAL":
        return <span className="text-xs font-medium text-slate-700 uppercase tracking-wider">NORMAL</span>;
      case "LOW":
        return <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">LOW</span>;
      default:
        return <span className="text-xs text-slate-600">{priority}</span>;
    }
  };

  // Material Status Pill Button
  const renderMaterialPill = (order: ManufacturingOrder) => {
    const isApplicable = ["PLANNED", "APPROVED", "IN_PROGRESS"].includes(order.status);
    if (!isApplicable) return <span className="text-slate-400 text-xs">-</span>;

    const status = order.material_status || "UNKNOWN";
    let bg = "bg-slate-100 text-slate-600 hover:bg-slate-200";
    let label = "Check";
    let icon = <Info className="h-3 w-3 mr-1" />;

    if (status === "READY") {
      bg = "bg-emerald-100 text-emerald-800 hover:bg-emerald-200 border-emerald-300";
      label = "Ready";
      icon = <CheckCircle className="h-3 w-3 mr-1 text-emerald-600" />;
    } else if (status === "PARTIAL") {
      bg = "bg-amber-100 text-amber-800 hover:bg-amber-200 border-amber-300";
      label = "Partial";
      icon = <AlertTriangle className="h-3 w-3 mr-1 text-amber-600" />;
    } else if (status === "MISSING") {
      bg = "bg-rose-100 text-rose-800 hover:bg-rose-200 border-rose-300";
      label = "Missing";
      icon = <XCircle className="h-3 w-3 mr-1 text-rose-600" />;
    }

    return (
      <button
        type="button"
        onClick={() => handleViewMaterialStatus(order)}
        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border transition-all cursor-pointer shadow-xs ${bg}`}
        title="Click to view material availability & check shortages"
      >
        {icon}
        {label}
      </button>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <Toaster position="top-right" />

      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-6 rounded-2xl shadow-lg border border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/30 rounded-xl border border-indigo-400/20">
              <Factory className="h-7 w-7 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Manufacturing Orders</h1>
              <p className="text-xs text-slate-300">Create, schedule, track production runs, and manage component stock consumption.</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <Button
            asChild
            variant="outline"
            className="bg-slate-800/80 hover:bg-slate-800 text-slate-200 border-slate-700 shadow-sm"
          >
            <Link href="/staff/accounts/bom">
              <Layers className="h-4 w-4 mr-2 text-indigo-400" /> BOM Master
            </Link>
          </Button>

          <Button
            onClick={handleCreateOpen}
            className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-500/20"
          >
            <Plus className="h-4 w-4 mr-2" /> New Order
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="shadow-xs border-slate-200 bg-white border-l-4 border-l-indigo-600 hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Orders</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{summaryMetrics.total}</p>
            </div>
            <div className="p-3 bg-indigo-50 rounded-xl text-indigo-600">
              <Factory className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs border-slate-200 bg-white border-l-4 border-l-amber-500 hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">In Progress</p>
              <p className="text-2xl font-bold text-amber-600 mt-1">{summaryMetrics.inProgress}</p>
            </div>
            <div className="p-3 bg-amber-50 rounded-xl text-amber-600">
              <Clock className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs border-slate-200 bg-white border-l-4 border-l-emerald-500 hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completed</p>
              <p className="text-2xl font-bold text-emerald-600 mt-1">{summaryMetrics.completed}</p>
            </div>
            <div className="p-3 bg-emerald-50 rounded-xl text-emerald-600">
              <CheckCircle className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs border-slate-200 bg-white border-l-4 border-l-blue-500 hover:shadow-md transition-shadow">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Planned / Approved</p>
              <p className="text-2xl font-bold text-blue-600 mt-1">{summaryMetrics.planned}</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-xl text-blue-600">
              <Boxes className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tab Switcher Bar */}
      <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 max-w-md">
        <button
          type="button"
          onClick={() => handleTabSwitch("orders")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
            activeTab === "orders"
              ? "bg-white text-indigo-700 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <Factory className="h-4 w-4" />
          Manufacturing Orders
        </button>

        <button
          type="button"
          onClick={() => handleTabSwitch("shortages")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
            activeTab === "shortages"
              ? "bg-white text-indigo-700 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Procurement Needed
          {shortageBadgeCount > 0 && (
            <span className="bg-rose-100 text-rose-700 text-xs px-2 py-0.5 rounded-full font-bold">
              {shortageBadgeCount}
            </span>
          )}
        </button>
      </div>

      {/* TAB 1: MANUFACTURING ORDERS */}
      {activeTab === "orders" && (
        <Card className="shadow-sm border-slate-200 overflow-hidden">
          {/* Filters Bar */}
          <div className="p-4 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3 flex-1">
              {/* Search Box */}
              <div className="relative min-w-[200px] flex-1 md:flex-initial">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  type="text"
                  placeholder="Search order #, product, company..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 bg-white text-sm h-9 w-full md:w-64"
                />
              </div>

              {/* Company Filter */}
              <select
                value={filterCompany}
                onChange={(e) => setFilterCompany(e.target.value)}
                className="h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Companies</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name}
                  </option>
                ))}
              </select>

              {/* Status Filter */}
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="PLANNED">Planned</option>
                <option value="APPROVED">Approved</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
                <option value="PARTIALLY_COMPLETED">Partially Completed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>

              {/* Priority Filter */}
              <select
                value={filterPriority}
                onChange={(e) => setFilterPriority(e.target.value)}
                className="h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Priorities</option>
                <option value="URGENT">Urgent</option>
                <option value="HIGH">High</option>
                <option value="NORMAL">Normal</option>
                <option value="LOW">Low</option>
              </select>

              {/* Month Filter */}
              <select
                value={filterMonth}
                onChange={(e) => setFilterMonth(e.target.value)}
                className="h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Months</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
              </select>

              {/* Year Filter */}
              <select
                value={filterYear}
                onChange={(e) => setFilterYear(e.target.value)}
                className="h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Years</option>
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">
                {filteredAndSortedOrders.length} order{filteredAndSortedOrders.length !== 1 ? "s" : ""}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={loadOrders}
                className="text-slate-600 hover:text-slate-900"
                title="Refresh order list"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Orders Table */}
          <div className="overflow-x-auto">
            {loadingOrders ? (
              <div className="p-12 flex flex-col items-center justify-center text-slate-500">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600 mb-2" />
                <p className="text-sm font-medium">Loading manufacturing orders...</p>
              </div>
            ) : filteredAndSortedOrders.length === 0 ? (
              <div className="p-16 flex flex-col items-center justify-center text-slate-400">
                <Factory className="h-12 w-12 text-slate-300 mb-3" />
                <h3 className="text-base font-semibold text-slate-700">No manufacturing orders found</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm text-center">
                  Create a new manufacturing order to schedule production and track stock consumption.
                </p>
                <Button onClick={handleCreateOpen} size="sm" className="mt-4 bg-indigo-600 hover:bg-indigo-700 text-white">
                  <Plus className="h-4 w-4 mr-1" /> Create Order
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader className="bg-slate-50 text-slate-600">
                  <TableRow>
                    <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("order_number")}>
                      <div className="flex items-center gap-1">
                        Order #
                        {sortKey === "order_number" ? (
                          sortDir === "asc" ? <ArrowUp className="h-3 w-3 text-indigo-600" /> : <ArrowDown className="h-3 w-3 text-indigo-600" />
                        ) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </div>
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("created_at")}>
                      <div className="flex items-center gap-1">
                        Date
                        {sortKey === "created_at" ? (
                          sortDir === "asc" ? <ArrowUp className="h-3 w-3 text-indigo-600" /> : <ArrowDown className="h-3 w-3 text-indigo-600" />
                        ) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </div>
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("created_at")}>
                      Month
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("finished_product_name")}>
                      <div className="flex items-center gap-1">
                        Product
                        {sortKey === "finished_product_name" ? (
                          sortDir === "asc" ? <ArrowUp className="h-3 w-3 text-indigo-600" /> : <ArrowDown className="h-3 w-3 text-indigo-600" />
                        ) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </div>
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("company_name")}>
                      <div className="flex items-center gap-1">
                        Company
                        {sortKey === "company_name" ? (
                          sortDir === "asc" ? <ArrowUp className="h-3 w-3 text-indigo-600" /> : <ArrowDown className="h-3 w-3 text-indigo-600" />
                        ) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </div>
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold text-right" onClick={() => handleSort("planned_qty")}>
                      <div className="flex items-center justify-end gap-1">
                        Qty
                        {sortKey === "planned_qty" ? (
                          sortDir === "asc" ? <ArrowUp className="h-3 w-3 text-indigo-600" /> : <ArrowDown className="h-3 w-3 text-indigo-600" />
                        ) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </div>
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold text-center" onClick={() => handleSort("priority")}>
                      Priority
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold text-right" onClick={() => handleSort("estimated_cost")}>
                      <div className="flex items-center justify-end gap-1">
                        Est. Cost
                        {sortKey === "estimated_cost" ? (
                          sortDir === "asc" ? <ArrowUp className="h-3 w-3 text-indigo-600" /> : <ArrowDown className="h-3 w-3 text-indigo-600" />
                        ) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </div>
                    </TableHead>
                    <TableHead className="cursor-pointer font-semibold text-center" onClick={() => handleSort("status")}>
                      Status
                    </TableHead>
                    <TableHead className="font-semibold text-center">Material</TableHead>
                    <TableHead className="font-semibold text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedOrders.map((o) => (
                    <TableRow key={o.id} className="hover:bg-slate-50/80 transition-colors">
                      <TableCell className="font-mono text-xs font-semibold text-indigo-600">
                        {o.order_number}
                      </TableCell>
                      <TableCell className="text-xs text-slate-600 whitespace-nowrap">
                        {fmtOrderDate(o.created_at)}
                      </TableCell>
                      <TableCell className="text-xs text-slate-600 whitespace-nowrap">
                        {fmtOrderMonth(o.created_at)}
                      </TableCell>
                      <TableCell className="text-sm font-semibold text-slate-900">
                        {o.finished_product_name || "-"}
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {o.company_name || "-"}
                      </TableCell>
                      <TableCell className="text-sm font-semibold text-slate-800 text-right whitespace-nowrap">
                        {o.planned_qty} <span className="text-xs font-normal text-slate-500">{o.unit_of_measure || "PCS"}</span>
                      </TableCell>
                      <TableCell className="text-center whitespace-nowrap">
                        {renderPriorityBadge(o.priority)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm font-semibold text-slate-900 whitespace-nowrap">
                        {formatCurrency(o.estimated_cost)}
                      </TableCell>
                      <TableCell className="text-center whitespace-nowrap">
                        {renderStatusBadge(o.status)}
                      </TableCell>
                      <TableCell className="text-center whitespace-nowrap">
                        {renderMaterialPill(o)}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1">
                          {/* View Button */}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-blue-600 hover:bg-blue-50"
                            title="View Details"
                            onClick={() => handleViewOrder(o.id)}
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>

                          {/* Edit Button */}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-amber-600 hover:bg-amber-50"
                            title="Edit Order"
                            onClick={() => handleOpenEditModal(o.id)}
                          >
                            <Edit className="h-3.5 w-3.5" />
                          </Button>

                          {/* Start Order Button (PLANNED or APPROVED) */}
                          {(o.status === "PLANNED" || o.status === "APPROVED") && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-emerald-600 hover:bg-emerald-50"
                              title="Start Manufacturing (Consume Stock)"
                              onClick={() => handleStartOrder(o.id, o.order_number)}
                            >
                              <Play className="h-3.5 w-3.5" />
                            </Button>
                          )}

                          {/* Complete Order Button (IN_PROGRESS) */}
                          {o.status === "IN_PROGRESS" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-emerald-600 hover:bg-emerald-50"
                              title="Mark Complete"
                              onClick={() => handleOpenCompleteModal(o)}
                            >
                              <CheckCircle className="h-3.5 w-3.5" />
                            </Button>
                          )}

                          {/* Cancel Order Button */}
                          {["PLANNED", "APPROVED", "IN_PROGRESS"].includes(o.status) && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-rose-600 hover:bg-rose-50"
                              title="Cancel Order"
                              onClick={() => handleOpenCancelModal(o)}
                            >
                              <XCircle className="h-3.5 w-3.5" />
                            </Button>
                          )}

                          {/* Delete Order Button (PLANNED or CANCELLED) */}
                          {["PLANNED", "CANCELLED"].includes(o.status) && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-pink-700 hover:bg-pink-50"
                              title="Delete Order"
                              onClick={() => handleOpenDeleteModal(o)}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </Card>
      )}

      {/* TAB 2: PROCUREMENT NEEDED (AGGREGATED SHORTAGES) */}
      {activeTab === "shortages" && (
        <div className="space-y-4">
          <Card className="shadow-xs border-slate-200 bg-white">
            <CardContent className="p-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex flex-col gap-1 min-w-[200px]">
                  <Label className="text-xs font-semibold text-slate-500">Filter Company</Label>
                  <select
                    value={shortageCompanyFilter}
                    onChange={(e) => setShortageCompanyFilter(e.target.value)}
                    className="h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">All Companies</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="pt-5 flex gap-2">
                  <Button
                    onClick={loadShortages}
                    variant="outline"
                    size="sm"
                    className="h-9"
                  >
                    <RefreshCw className="h-4 w-4 mr-1 text-slate-600" /> Refresh Shortages
                  </Button>

                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="h-9 bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100"
                  >
                    <Link href="/staff/inventory/procurement">
                      <ExternalLink className="h-4 w-4 mr-1" /> Full Procurement Page
                    </Link>
                  </Button>
                </div>
              </div>

              {shortages.length > 0 && (
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-slate-500">
                    {shortages.length} component(s) with shortage
                  </span>
                  <Button
                    onClick={handleCreateProcurementFromAllShortages}
                    disabled={procurementSubmitting}
                    className="bg-amber-600 hover:bg-amber-700 text-white shadow-xs font-semibold"
                  >
                    {procurementSubmitting ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <ShoppingCart className="h-4 w-4 mr-2" />
                    )}
                    Create Procurement Request {selectedShortages.length > 0 ? `(${selectedShortages.length})` : ""}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {loadingShortages ? (
            <div className="p-16 flex flex-col items-center justify-center text-slate-500">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-600 mb-2" />
              <p className="text-sm font-medium">Checking component stock across active orders...</p>
            </div>
          ) : shortages.length === 0 ? (
            <Card className="shadow-xs border-slate-200 bg-white">
              <CardContent className="p-16 flex flex-col items-center justify-center text-center">
                <div className="p-3 bg-emerald-50 rounded-full text-emerald-600 mb-3">
                  <CheckCircle className="h-10 w-10" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">No Material Shortages</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  All active manufacturing orders have sufficient component stock in inventory.
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card className="shadow-xs border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead className="w-12 text-center">
                        <Checkbox
                          checked={selectedShortages.length === shortages.length && shortages.length > 0}
                          onCheckedChange={(c) => handleToggleAllShortages(!!c)}
                        />
                      </TableHead>
                      <TableHead className="font-semibold text-slate-600">Code</TableHead>
                      <TableHead className="font-semibold text-slate-600">Component</TableHead>
                      <TableHead className="font-semibold text-slate-600 text-right">Required</TableHead>
                      <TableHead className="font-semibold text-slate-600 text-right">Available</TableHead>
                      <TableHead className="font-semibold text-slate-600 text-right">Shortage</TableHead>
                      <TableHead className="font-semibold text-slate-600">Manufacturing Orders Impacted</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {shortages.map((s, idx) => {
                      const isSelected = selectedShortages.includes(idx);
                      const shortageColor = s.total_shortage > 10 ? "text-rose-600 font-bold" : "text-amber-600 font-bold";
                      return (
                        <TableRow key={`${s.company_id}-${s.component_id}-${idx}`} className={isSelected ? "bg-indigo-50/50" : ""}>
                          <TableCell className="text-center">
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={(c) => handleToggleShortageItem(idx, !!c)}
                            />
                          </TableCell>
                          <TableCell>
                            <code className="bg-slate-100 px-2 py-0.5 rounded text-xs text-slate-700 font-mono">
                              {s.component_code}
                            </code>
                          </TableCell>
                          <TableCell className="font-semibold text-slate-900 text-sm">
                            {s.component_name}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm text-slate-700">
                            {formatNumber(s.total_required)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm text-emerald-600 font-semibold">
                            {formatNumber(s.available_qty)}
                          </TableCell>
                          <TableCell className={`text-right font-mono text-sm ${shortageColor}`}>
                            {formatNumber(s.total_shortage)}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {(s.source_orders || []).map((o, oIdx) => (
                                <span
                                  key={oIdx}
                                  className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200"
                                >
                                  {o.order_number}
                                  <span className="text-[10px] text-rose-600 ml-1 font-bold">
                                    (-{Number(o.shortage_qty).toFixed(0)})
                                  </span>
                                </span>
                              ))}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 1: CREATE NEW MANUFACTURING ORDER                      */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Factory className="h-5 w-5 text-indigo-600" /> New Manufacturing Order
            </DialogTitle>
            <DialogDescription>
              Schedule a production order. Components stock will be verified against inventory.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateSubmit} className="space-y-4 pt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Company *</Label>
                <select
                  required
                  value={createForm.company_id}
                  onChange={(e) => handleCompanyChangeForCreate(e.target.value)}
                  className="w-full h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Select Company</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Bill of Materials (BOM) *</Label>
                <select
                  required
                  disabled={!createForm.company_id || bomsLoading}
                  value={createForm.bom_id}
                  onChange={(e) => handleBomChangeForCreate(e.target.value)}
                  className="w-full h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
                >
                  <option value="">
                    {bomsLoading ? "Loading BOMs..." : !createForm.company_id ? "Select Company First" : "Select BOM"}
                  </option>
                  {boms.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.bom_name} ({b.finished_product_name}) {b.status !== "APPROVED" ? `[${b.status}]` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Quantity to Produce *</Label>
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  required
                  value={createForm.planned_qty}
                  onChange={(e) => handleQtyChangeForCreate(parseFloat(e.target.value) || 0)}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Priority</Label>
                <select
                  value={createForm.priority}
                  onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                  className="w-full h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="NORMAL">Normal</option>
                  <option value="LOW">Low</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Planned Start Date</Label>
                <Input
                  type="date"
                  value={createForm.planned_start_date}
                  onChange={(e) => setCreateForm({ ...createForm, planned_start_date: e.target.value })}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Planned End Date</Label>
                <Input
                  type="date"
                  value={createForm.planned_end_date}
                  onChange={(e) => setCreateForm({ ...createForm, planned_end_date: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Notes / Instructions</Label>
              <Textarea
                rows={2}
                placeholder="Additional notes for production floor..."
                value={createForm.notes}
                onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
              />
            </div>

            {/* Live Stock Check Preview */}
            {stockCheckLoading && (
              <div className="p-3 bg-slate-50 border rounded-lg flex items-center justify-center gap-2 text-xs text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                Checking stock availability for selected BOM & quantity...
              </div>
            )}

            {stockCheckResult && !stockCheckLoading && (
              <div className="border rounded-xl p-4 bg-slate-50/80 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 uppercase">Stock Verification:</span>
                  {stockCheckResult.can_manufacture ? (
                    <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300">
                      <CheckCircle className="h-3 w-3 mr-1 text-emerald-600" /> Stock Available
                    </Badge>
                  ) : (
                    <Badge className="bg-rose-100 text-rose-800 border-rose-300">
                      <AlertTriangle className="h-3 w-3 mr-1 text-rose-600" /> Stock Shortage Detected
                    </Badge>
                  )}
                </div>

                {!stockCheckResult.can_manufacture && (
                  <p className="text-xs text-amber-700 bg-amber-50 p-2 rounded border border-amber-200">
                    <Info className="h-3.5 w-3.5 inline mr-1 text-amber-600" />
                    You can still create a PLANNED order — stock is only deducted when you Start manufacturing.
                  </p>
                )}

                <div className="max-h-40 overflow-y-auto rounded-lg border bg-white">
                  <Table className="text-xs">
                    <TableHeader className="bg-slate-100">
                      <TableRow>
                        <TableHead className="py-1">Component</TableHead>
                        <TableHead className="py-1 text-right">Required</TableHead>
                        <TableHead className="py-1 text-right">Available</TableHead>
                        <TableHead className="py-1 text-center">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {stockCheckResult.components.map((c, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="py-1 font-medium">{c.component_name}</TableCell>
                          <TableCell className="py-1 text-right font-mono">{formatNumber(c.required_qty)}</TableCell>
                          <TableCell className="py-1 text-right font-mono text-emerald-600 font-semibold">{formatNumber(c.available_qty)}</TableCell>
                          <TableCell className="py-1 text-center">
                            {c.is_sufficient ? (
                              <span className="text-emerald-600 font-bold">OK</span>
                            ) : (
                              <span className="text-rose-600 font-bold">Short: {formatNumber(c.shortage_qty)}</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createSubmitting} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                {createSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Check className="h-4 w-4 mr-2" />}
                Create Order
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 2: VIEW ORDER DETAILS                                  */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isViewOpen} onOpenChange={setIsViewOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-indigo-600" /> Order Details — {selectedOrder?.order_number}
            </DialogTitle>
            <DialogDescription>
              Detailed view of manufacturing order, output product, and consumed components.
            </DialogDescription>
          </DialogHeader>

          {selectedOrder && (
            <div className="space-y-4 pt-2">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 p-4 bg-slate-50 rounded-xl border">
                <div>
                  <span className="text-xs text-slate-500 block">Product</span>
                  <span className="text-sm font-bold text-slate-900">{selectedOrder.finished_product_name || "-"}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">BOM Recipe</span>
                  <span className="text-sm font-semibold text-slate-800">{selectedOrder.bom_name || "-"}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Company</span>
                  <span className="text-sm font-semibold text-slate-800">{selectedOrder.company_name || "-"}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Planned Qty</span>
                  <span className="text-sm font-bold text-slate-900">{selectedOrder.planned_qty} {selectedOrder.unit_of_measure || "PCS"}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Actual Qty Produced</span>
                  <span className="text-sm font-bold text-emerald-600">{selectedOrder.actual_qty ?? "-"}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Rejected Qty</span>
                  <span className="text-sm font-bold text-rose-600">{selectedOrder.rejected_qty ?? "0"}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Priority</span>
                  <div>{renderPriorityBadge(selectedOrder.priority)}</div>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Status</span>
                  <div>{renderStatusBadge(selectedOrder.status)}</div>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Est. Cost / Actual Cost</span>
                  <span className="text-xs font-mono font-semibold text-slate-900">
                    {formatCurrency(selectedOrder.estimated_cost)} / {formatCurrency(selectedOrder.actual_cost)}
                  </span>
                </div>
              </div>

              {selectedOrder.notes && (
                <div className="p-3 bg-blue-50/60 rounded-lg border border-blue-200 text-xs text-slate-700">
                  <span className="font-semibold text-blue-900 block mb-1">Notes:</span>
                  {selectedOrder.notes}
                </div>
              )}

              {/* Line Items Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Boxes className="h-4 w-4 text-indigo-600" /> Components Consumed
                </h4>

                <div className="rounded-xl border overflow-hidden">
                  <Table className="text-xs">
                    <TableHeader className="bg-slate-100">
                      <TableRow>
                        <TableHead>Component</TableHead>
                        <TableHead className="text-right">Planned Qty</TableHead>
                        <TableHead className="text-right">Consumed Qty</TableHead>
                        <TableHead className="text-center">Status</TableHead>
                        <TableHead className="text-center">Type</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(selectedOrder.line_items || []).length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center py-4 text-slate-400">
                            No component line items recorded
                          </TableCell>
                        </TableRow>
                      ) : (
                        selectedOrder.line_items?.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell className="font-semibold text-slate-900">
                              {item.component_name || "-"}
                              <span className="text-slate-400 font-mono text-[11px] ml-1.5">
                                ({item.component_code || "N/A"})
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {item.planned_qty} {item.unit_of_measure || "PCS"}
                            </TableCell>
                            <TableCell className="text-right font-mono font-semibold text-emerald-700">
                              {item.actual_qty_consumed ?? 0}
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge variant="outline" className="text-[10px]">
                                {item.status || "PENDING"}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-center">
                              {item.is_additional ? (
                                <Badge className="bg-blue-100 text-blue-800 text-[10px]">EXTRA</Badge>
                              ) : (
                                <Badge variant="secondary" className="text-[10px]">BOM</Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsViewOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 3: COMPLETE ORDER                                      */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isCompleteOpen} onOpenChange={setIsCompleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-emerald-600" /> Complete Manufacturing Order
            </DialogTitle>
            <DialogDescription>
              Record final production quantities and mark order completed.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCompleteSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Actual Quantity Produced *</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                required
                value={completeForm.actual_qty}
                onChange={(e) => setCompleteForm({ ...completeForm, actual_qty: parseFloat(e.target.value) || 0 })}
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Rejected / Scrapped Quantity</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={completeForm.rejected_qty}
                onChange={(e) => setCompleteForm({ ...completeForm, rejected_qty: parseFloat(e.target.value) || 0 })}
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Remarks</Label>
              <Textarea
                rows={2}
                placeholder="Production quality notes, inspection remarks..."
                value={completeForm.remarks}
                onChange={(e) => setCompleteForm({ ...completeForm, remarks: e.target.value })}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsCompleteOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={completeSubmitting} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {completeSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Check className="h-4 w-4 mr-2" />}
                Complete Order
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 4: CANCEL ORDER                                        */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isCancelModalOpen} onOpenChange={setIsCancelModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-rose-600">
              <XCircle className="h-5 w-5" /> Cancel Order — {cancelForm.orderNumber}
            </DialogTitle>
            <DialogDescription>
              Please enter the cancellation reason. This will cancel the production schedule.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCancelSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Reason for Cancellation *</Label>
              <Textarea
                rows={3}
                required
                placeholder="Specify reason for cancelling this order..."
                value={cancelForm.reason}
                onChange={(e) => setCancelForm({ ...cancelForm, reason: e.target.value })}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsCancelModalOpen(false)}>
                Go Back
              </Button>
              <Button type="submit" disabled={cancelSubmitting} className="bg-rose-600 hover:bg-rose-700 text-white">
                {cancelSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <XCircle className="h-4 w-4 mr-2" />}
                Confirm Cancellation
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 5: DELETE ORDER PERMANENTLY                            */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-rose-600">
              <Trash2 className="h-5 w-5" /> Delete Manufacturing Order
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete order <span className="font-mono font-bold text-slate-900">{deleteTarget?.orderNumber}</span>? This action is permanent and cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={() => setIsDeleteModalOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={deleteSubmitting}
              onClick={handleDeleteSubmit}
              className="bg-rose-600 hover:bg-rose-700 text-white"
            >
              {deleteSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete Permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 6: MATERIAL STATUS & SHORTAGE DETAILS                  */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isMaterialStatusOpen} onOpenChange={setIsMaterialStatusOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Boxes className="h-5 w-5 text-indigo-600" /> Material Status — {materialStatusData.orderNumber}
              </div>
            </DialogTitle>
            <DialogDescription>
              Stock availability verification across all required components for this order.
            </DialogDescription>
          </DialogHeader>

          {materialStatusData.loading ? (
            <div className="p-12 flex flex-col items-center justify-center text-slate-500">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-600 mb-2" />
              <p className="text-xs">Checking stock availability...</p>
            </div>
          ) : materialStatusData.data ? (
            <div className="space-y-4 pt-2">
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-center">
                  <p className="text-xl font-bold text-emerald-700">{materialStatusData.data.ready_components}</p>
                  <p className="text-xs text-emerald-600 font-medium">Ready Components</p>
                </div>
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-center">
                  <p className="text-xl font-bold text-amber-700">{materialStatusData.data.shortage_components}</p>
                  <p className="text-xs text-amber-600 font-medium">Shortage Components</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-center">
                  <p className="text-xl font-bold text-slate-800">
                    {materialStatusData.data.can_manufacture ? "Yes" : "No"}
                  </p>
                  <p className="text-xs text-slate-600 font-medium">Can Manufacture</p>
                </div>
              </div>

              {/* Table */}
              <div className="rounded-xl border overflow-hidden">
                <Table className="text-xs">
                  <TableHeader className="bg-slate-100">
                    <TableRow>
                      <TableHead>Component</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead className="text-right">Required</TableHead>
                      <TableHead className="text-right">Available</TableHead>
                      <TableHead className="text-right">Shortage</TableHead>
                      <TableHead className="text-center">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(materialStatusData.data.components || []).map((c, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-semibold text-slate-900">{c.component_name}</TableCell>
                        <TableCell><code className="bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">{c.component_code || "-"}</code></TableCell>
                        <TableCell className="text-right font-mono">{formatNumber(c.required_qty)}</TableCell>
                        <TableCell className="text-right font-mono text-emerald-600 font-semibold">{formatNumber(c.available_qty)}</TableCell>
                        <TableCell className={`text-right font-mono font-bold ${c.shortage_qty > 0 ? "text-rose-600" : "text-slate-400"}`}>
                          {formatNumber(c.shortage_qty)}
                        </TableCell>
                        <TableCell className="text-center">
                          {c.is_sufficient ? (
                            <Badge className="bg-emerald-100 text-emerald-800 text-[10px]">OK</Badge>
                          ) : (
                            <Badge className="bg-rose-100 text-rose-800 text-[10px]">Short</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {materialStatusData.data.last_checked_at && (
                <p className="text-[11px] text-slate-400 text-right">
                  Last checked: {new Date(materialStatusData.data.last_checked_at).toLocaleString("en-IN")}
                </p>
              )}
            </div>
          ) : null}

          <DialogFooter className="flex flex-col sm:flex-row justify-between items-center gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              disabled={materialStatusData.refreshing}
              onClick={handleRefreshMaterialStatus}
              className="w-full sm:w-auto"
            >
              {materialStatusData.refreshing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Refresh Status
            </Button>

            <div className="flex gap-2 w-full sm:w-auto justify-end">
              <Button variant="secondary" onClick={() => setIsMaterialStatusOpen(false)}>
                Close
              </Button>

              {materialStatusData.data && materialStatusData.data.shortage_components > 0 && (
                <Button
                  onClick={handleCreateProcurementFromShortage}
                  className="bg-amber-600 hover:bg-amber-700 text-white font-semibold"
                >
                  <ShoppingCart className="h-4 w-4 mr-1.5" /> Create Procurement Request
                </Button>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 7: EDIT ORDER & MATERIALS                               */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="h-5 w-5 text-amber-600" /> Edit Order — {selectedOrder?.order_number}
            </DialogTitle>
            <DialogDescription>
              Update order schedule parameters or attach extra components beyond the BOM recipe.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleUpdateOrderSubmit} className="space-y-4 pt-2">
            {/* Status Warning Banners */}
            {editForm.status === "APPROVED" && (
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                <div>
                  <strong>Re-approval Required:</strong> Editing this APPROVED order will change its status to PENDING_APPROVAL and require re-approval.
                </div>
              </div>
            )}

            {editForm.status === "IN_PROGRESS" && (
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 text-xs text-blue-800 flex items-start gap-2">
                <Info className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                <div>
                  <strong>Production In Progress:</strong> Core order quantity and dates are locked. You may add extra materials if required.
                </div>
              </div>
            )}

            {["COMPLETED", "CANCELLED"].includes(editForm.status) && (
              <div className="p-3 bg-slate-100 rounded-lg border border-slate-300 text-xs text-slate-700 flex items-start gap-2">
                <Info className="h-4 w-4 text-slate-500 mt-0.5 shrink-0" />
                <div>
                  <strong>{editForm.status} Order:</strong> Only the Notes field can be edited. All other fields are locked.
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Company</Label>
                <Input value={editForm.company_name} disabled className="bg-slate-100 text-slate-600" />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">BOM / Product</Label>
                <Input value={editForm.bom_name} disabled className="bg-slate-100 text-slate-600" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Quantity to Produce *</Label>
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  required
                  disabled={["IN_PROGRESS", "COMPLETED", "CANCELLED"].includes(editForm.status)}
                  value={editForm.planned_qty}
                  onChange={(e) => setEditForm({ ...editForm, planned_qty: parseFloat(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Priority</Label>
                <select
                  disabled={["IN_PROGRESS", "COMPLETED", "CANCELLED"].includes(editForm.status)}
                  value={editForm.priority}
                  onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
                  className="w-full h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
                >
                  <option value="NORMAL">Normal</option>
                  <option value="LOW">Low</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Planned Start Date</Label>
                <Input
                  type="date"
                  disabled={["IN_PROGRESS", "COMPLETED", "CANCELLED"].includes(editForm.status)}
                  value={editForm.planned_start_date}
                  onChange={(e) => setEditForm({ ...editForm, planned_start_date: e.target.value })}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Planned End Date</Label>
                <Input
                  type="date"
                  disabled={["IN_PROGRESS", "COMPLETED", "CANCELLED"].includes(editForm.status)}
                  value={editForm.planned_end_date}
                  onChange={(e) => setEditForm({ ...editForm, planned_end_date: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Notes</Label>
              <Textarea
                rows={2}
                placeholder="Additional instructions..."
                value={editForm.notes}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
              />
            </div>

            {/* Extra Materials Management Section */}
            <div className="border-t pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <Boxes className="h-4 w-4 text-indigo-600" /> Order Materials
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    BOM items are locked to recipe. You can add extra materials as needed.
                  </p>
                </div>

                {["PLANNED", "APPROVED", "IN_PROGRESS"].includes(editForm.status) && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleOpenAddMaterialModal}
                    className="text-xs"
                  >
                    <Plus className="h-3.5 w-3.5 mr-1" /> Add Extra Material
                  </Button>
                )}
              </div>

              {editMaterialsLoading ? (
                <div className="p-4 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-indigo-600" /> Loading materials...
                </div>
              ) : (
                <div className="rounded-xl border overflow-hidden">
                  <Table className="text-xs">
                    <TableHeader className="bg-slate-100">
                      <TableRow>
                        <TableHead>Material</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-center">Status</TableHead>
                        <TableHead className="text-center">Type</TableHead>
                        {["PLANNED", "APPROVED", "IN_PROGRESS"].includes(editForm.status) && (
                          <TableHead className="text-right">Actions</TableHead>
                        )}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(selectedOrder?.line_items || []).length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center py-3 text-slate-400">
                            No materials recorded
                          </TableCell>
                        </TableRow>
                      ) : (
                        selectedOrder?.line_items?.map((l) => (
                          <TableRow key={l.id}>
                            <TableCell className="font-semibold text-slate-900">
                              {l.component_name || "-"}
                              <span className="text-slate-400 font-mono text-[11px] ml-1">
                                ({l.component_code || "N/A"})
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {l.planned_qty} {l.unit_of_measure || "PCS"}
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge variant="outline" className="text-[10px]">
                                {l.status || "PENDING"}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-center">
                              {l.is_additional ? (
                                <Badge className="bg-blue-100 text-blue-800 text-[10px]">EXTRA</Badge>
                              ) : (
                                <Badge variant="secondary" className="text-[10px]">BOM</Badge>
                              )}
                            </TableCell>
                            {["PLANNED", "APPROVED", "IN_PROGRESS"].includes(editForm.status) && (
                              <TableCell className="text-right">
                                <div className="flex items-center justify-end gap-1">
                                  {l.status === "PENDING" && (
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="icon"
                                      className="h-6 w-6 text-amber-600"
                                      title="Edit material quantity"
                                      onClick={() => handleOpenEditMaterialModal(l)}
                                    >
                                      <Edit className="h-3 w-3" />
                                    </Button>
                                  )}
                                  {["PLANNED", "APPROVED"].includes(editForm.status) && l.is_additional && (
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="icon"
                                      className="h-6 w-6 text-rose-600"
                                      title="Remove extra material"
                                      onClick={() => handleOpenRemoveMaterialModal(l)}
                                    >
                                      <Trash2 className="h-3 w-3" />
                                    </Button>
                                  )}
                                </div>
                              </TableCell>
                            )}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              )}

              {selectedOrder?.line_items && (
                <p className="text-[11px] text-slate-500">
                  {selectedOrder.line_items.filter((l) => !l.is_additional).length} BOM materials +{" "}
                  {selectedOrder.line_items.filter((l) => l.is_additional).length} extra materials ={" "}
                  {selectedOrder.line_items.length} total
                </p>
              )}
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsEditOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={editSubmitting} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                {editSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Check className="h-4 w-4 mr-2" />}
                Save Changes
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 8: ADD / EDIT EXTRA MATERIAL SUB-MODAL                  */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isMaterialItemModalOpen} onOpenChange={setIsMaterialItemModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Boxes className="h-5 w-5 text-indigo-600" />
              {materialItemForm.mode === "add" ? "Add Extra Material" : "Edit Material"}
            </DialogTitle>
            <DialogDescription>
              {materialItemForm.mode === "add"
                ? "Attach extra component materials needed for this production run."
                : "Modify planned quantity for this pending line item."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveMaterialItem} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Component *</Label>
              {materialItemForm.mode === "add" ? (
                <select
                  required
                  value={materialItemForm.component_id}
                  onChange={(e) => setMaterialItemForm({ ...materialItemForm, component_id: e.target.value })}
                  className="w-full h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">-- Select Material --</option>
                  {editStockItems
                    .filter((s) => !(selectedOrder?.line_items || []).some((l) => l.component_id === s.id))
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.item_name} ({s.item_code || "N/A"})
                      </option>
                    ))}
                </select>
              ) : (
                <Input
                  disabled
                  value={
                    selectedOrder?.line_items?.find((l) => l.id === materialItemForm.lineId)?.component_name || "Component"
                  }
                  className="bg-slate-100 text-slate-600"
                />
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Planned Quantity *</Label>
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  required
                  value={materialItemForm.planned_qty}
                  onChange={(e) => setMaterialItemForm({ ...materialItemForm, planned_qty: parseFloat(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Unit of Measure</Label>
                <select
                  value={materialItemForm.unit_of_measure}
                  onChange={(e) => setMaterialItemForm({ ...materialItemForm, unit_of_measure: e.target.value })}
                  className="w-full h-9 px-3 border border-slate-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="PCS">Pieces (PCS)</option>
                  <option value="KG">Kilograms (KG)</option>
                  <option value="SET">Sets (SET)</option>
                  <option value="UNIT">Units (UNIT)</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Notes / Reason</Label>
              <Textarea
                rows={2}
                placeholder="Reason for adding extra material..."
                value={materialItemForm.notes}
                onChange={(e) => setMaterialItemForm({ ...materialItemForm, notes: e.target.value })}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsMaterialItemModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={materialItemSubmitting} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                {materialItemSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Check className="h-4 w-4 mr-2" />}
                Save Material
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* MODAL 9: REMOVE EXTRA MATERIAL CONFIRMATION                   */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={isRemoveMaterialModalOpen} onOpenChange={setIsRemoveMaterialModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-rose-600">
              <Trash2 className="h-5 w-5" /> Remove Extra Material
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this extra material from the manufacturing order?
            </DialogDescription>
          </DialogHeader>

          {removeMaterialTarget && (
            <div className="space-y-3 pt-2">
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs">
                <strong>Material:</strong> {removeMaterialTarget.name} — Qty: {removeMaterialTarget.plannedQty}
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Reason for Removal (Optional)</Label>
                <Textarea
                  rows={2}
                  placeholder="Why is this extra material being removed..."
                  value={removeMaterialTarget.reason}
                  onChange={(e) => setRemoveMaterialTarget({ ...removeMaterialTarget, reason: e.target.value })}
                />
              </div>
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={() => setIsRemoveMaterialModalOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={removeMaterialSubmitting}
              onClick={handleConfirmRemoveMaterial}
              className="bg-rose-600 hover:bg-rose-700 text-white"
            >
              {removeMaterialSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Remove Material
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

