"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Building2,
  Percent,
  Calculator,
  Sliders,
  Info,
  Edit,
  Save,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Coins,
  TrendingUp,
  RefreshCw,
  Sparkles,
  DollarSign,
  ShieldCheck,
  Tag,
  ArrowRight,
  Plus,
} from "lucide-react";

interface Company {
  id: number;
  company_name?: string;
  name?: string;
  company_code?: string;
  code?: string;
  address?: string;
  gst_number?: string;
  is_active: boolean;
  is_marketplace_endpoint?: boolean;
}

interface PricingConfig {
  id: number;
  company_id: number;
  company_name?: string;
  config_type?: string;
  default_markup_pct: number | string;
  incentive_pct: number | string;
  min_markup_pct: number | string;
  max_markup_pct?: number | string | null;
  allow_below_cost?: boolean;
  description?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  // Extended pricing & tax fields (for UI & legacy compatibility)
  default_cgst_rate?: number | string;
  default_sgst_rate?: number | string;
  default_igst_rate?: number | string;
  tds_rate?: number | string;
  currency?: string;
  decimal_places?: number | string;
  rounding_method?: string;
}

interface CalculationResult {
  purchaseCost: number;
  quantity: number;
  markupPct: number;
  unitCost: number;
  defaultPrice: number;
  unitSellingPrice: number;
  subtotal: number;
  profitPerUnit: number;
  totalProfit: number;
  incentivePct: number;
  incentiveAmount: number;
  companyNetProfit: number;
  taxType: "GST" | "IGST" | "NONE";
  cgstRate: number;
  sgstRate: number;
  igstRate: number;
  cgstAmount: number;
  sgstAmount: number;
  igstAmount: number;
  totalTax: number;
  grandTotal: number;
  isBelowCost: boolean;
}

export default function PricingConfigurationPage() {
  const { token, user } = useStaffAuth();

  // Company and configuration state
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [currentConfig, setCurrentConfig] = useState<PricingConfig | null>(null);

  // Loading & notification states
  const [loadingCompanies, setLoadingCompanies] = useState<boolean>(true);
  const [loadingConfig, setLoadingConfig] = useState<boolean>(false);
  const [savingConfig, setSavingConfig] = useState<boolean>(false);
  const [calculatingApi, setCalculatingApi] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{
    type: "success" | "error" | "info";
    text: string;
  } | null>(null);

  // Edit Modal State
  const [isEditOpen, setIsEditOpen] = useState<boolean>(false);
  const [formData, setFormData] = useState<Partial<PricingConfig>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Calculator State
  const [calcBaseAmount, setCalcBaseAmount] = useState<string>("1000");
  const [calcQuantity, setCalcQuantity] = useState<string>("1");
  const [calcCustomPrice, setCalcCustomPrice] = useState<string>("");
  const [calcMarkupOverride, setCalcMarkupOverride] = useState<string>("");
  const [calcIncentiveOverride, setCalcIncentiveOverride] = useState<string>("");
  const [calcTaxType, setCalcTaxType] = useState<"GST" | "IGST" | "NONE">("GST");
  const [calcCustomTaxRate, setCalcCustomTaxRate] = useState<string>("18");

  // Load Companies
  const fetchCompanies = async () => {
    try {
      setLoadingCompanies(true);
      const res = await api.get("/staff/accounts/companies?status_filter=ALL&page_size=100");
      const companyList: Company[] = res.data.companies || [];
      setCompanies(companyList);

      // Auto-select first company if none selected
      if (companyList.length > 0 && !selectedCompanyId) {
        setSelectedCompanyId(String(companyList[0].id));
      }
    } catch (err: any) {
      console.error("Failed to load companies:", err);
      setStatusMessage({
        type: "error",
        text: "Failed to load companies. Please check your connection.",
      });
    } finally {
      setLoadingCompanies(false);
    }
  };

  // Load Pricing Configuration for Selected Company
  const fetchPricingConfig = async (companyId: string) => {
    if (!companyId) {
      setCurrentConfig(null);
      return;
    }

    try {
      setLoadingConfig(true);
      setStatusMessage(null);

      const res = await api.get(`/staff/accounts/pricing-config/${companyId}`);
      if (res.data && res.data.success && res.data.pricing_config) {
        const configData = res.data.pricing_config;
        // Merge with sensible defaults for extra display settings
        setCurrentConfig({
          ...configData,
          default_cgst_rate: configData.default_cgst_rate ?? 9.0,
          default_sgst_rate: configData.default_sgst_rate ?? 9.0,
          default_igst_rate: configData.default_igst_rate ?? 18.0,
          tds_rate: configData.tds_rate ?? 0.1,
          currency: configData.currency ?? "INR",
          decimal_places: configData.decimal_places ?? 2,
          rounding_method: configData.rounding_method ?? "ROUND",
        });
      } else {
        setCurrentConfig(null);
      }
    } catch (err: any) {
      console.error("Failed to fetch pricing configuration:", err);
      setCurrentConfig(null);
      setStatusMessage({
        type: "error",
        text: err.response?.data?.detail || "Failed to load pricing configuration for this company.",
      });
    } finally {
      setLoadingConfig(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchCompanies();
    }
  }, [token]);

  useEffect(() => {
    if (selectedCompanyId) {
      fetchPricingConfig(selectedCompanyId);
    }
  }, [selectedCompanyId]);

  const selectedCompany = useMemo(() => {
    return companies.find((c) => String(c.id) === selectedCompanyId) || null;
  }, [companies, selectedCompanyId]);

  // Open Edit Modal with current values
  const openEditModal = () => {
    if (!currentConfig) return;

    setFormData({
      id: currentConfig.id,
      company_id: currentConfig.company_id,
      config_type: currentConfig.config_type || "SERVICE_ITEM_MARKUP",
      default_markup_pct: Number(currentConfig.default_markup_pct ?? 20),
      incentive_pct: Number(currentConfig.incentive_pct ?? 50),
      min_markup_pct: Number(currentConfig.min_markup_pct ?? 0),
      max_markup_pct: currentConfig.max_markup_pct ? Number(currentConfig.max_markup_pct) : undefined,
      allow_below_cost: Boolean(currentConfig.allow_below_cost),
      default_cgst_rate: Number(currentConfig.default_cgst_rate ?? 9),
      default_sgst_rate: Number(currentConfig.default_sgst_rate ?? 9),
      default_igst_rate: Number(currentConfig.default_igst_rate ?? 18),
      tds_rate: Number(currentConfig.tds_rate ?? 0.1),
      currency: currentConfig.currency || "INR",
      decimal_places: Number(currentConfig.decimal_places ?? 2),
      rounding_method: currentConfig.rounding_method || "ROUND",
      description: currentConfig.description || "",
      is_active: currentConfig.is_active !== false,
    });
    setFormErrors({});
    setIsEditOpen(true);
  };

  // Validate form
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    const defaultMarkup = Number(formData.default_markup_pct ?? 0);
    const minMarkup = Number(formData.min_markup_pct ?? 0);
    const incentive = Number(formData.incentive_pct ?? 0);

    if (isNaN(defaultMarkup) || defaultMarkup < 0 || defaultMarkup > 100) {
      errors.default_markup_pct = "Default markup must be between 0% and 100%.";
    }

    if (isNaN(minMarkup) || minMarkup < 0 || minMarkup > 100) {
      errors.min_markup_pct = "Minimum markup must be between 0% and 100%.";
    }

    if (minMarkup > defaultMarkup) {
      errors.min_markup_pct = "Minimum markup cannot exceed default markup.";
    }

    if (isNaN(incentive) || incentive < 0 || incentive > 100) {
      errors.incentive_pct = "Incentive share must be between 0% and 100%.";
    }

    if (formData.max_markup_pct !== undefined && formData.max_markup_pct !== null) {
      const maxMarkup = Number(formData.max_markup_pct);
      if (maxMarkup < defaultMarkup) {
        errors.max_markup_pct = "Maximum markup cannot be less than default markup.";
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Save changes
  const handleSaveConfig = async () => {
    if (!validateForm()) return;
    if (!currentConfig?.id) return;

    try {
      setSavingConfig(true);

      const payload = {
        default_markup_pct: Number(formData.default_markup_pct),
        incentive_share_pct: Number(formData.incentive_pct),
        min_markup_pct: Number(formData.min_markup_pct),
        description: formData.description || null,
        is_active: formData.is_active,
      };

      const res = await api.put(`/staff/accounts/pricing-config/${currentConfig.id}`, payload);

      if (res.data && res.data.success) {
        setIsEditOpen(false);
        setStatusMessage({
          type: "success",
          text: "Pricing configuration updated successfully!",
        });
        await fetchPricingConfig(selectedCompanyId);
      } else {
        setStatusMessage({
          type: "error",
          text: res.data?.message || "Failed to update pricing configuration.",
        });
      }
    } catch (err: any) {
      console.error("Failed to update pricing configuration:", err);
      setStatusMessage({
        type: "error",
        text: err.response?.data?.detail || err.response?.data?.message || "Failed to update pricing configuration.",
      });
    } finally {
      setSavingConfig(false);
    }
  };

  // Live Price Calculation
  const calculationResult: CalculationResult = useMemo(() => {
    const cost = Math.max(0, parseFloat(calcBaseAmount) || 0);
    const qty = Math.max(1, parseInt(calcQuantity) || 1);

    const defaultMarkup = Number(currentConfig?.default_markup_pct ?? 20);
    const effectiveMarkup = calcMarkupOverride !== "" ? parseFloat(calcMarkupOverride) || 0 : defaultMarkup;

    const defaultIncentive = Number(currentConfig?.incentive_pct ?? 50);
    const effectiveIncentive = calcIncentiveOverride !== "" ? parseFloat(calcIncentiveOverride) || 0 : defaultIncentive;

    const calculatedDefaultPrice = cost + (cost * effectiveMarkup) / 100;

    let unitSellingPrice = calculatedDefaultPrice;
    let isBelowCost = false;

    if (calcCustomPrice !== "") {
      const parsedCustom = parseFloat(calcCustomPrice);
      if (!isNaN(parsedCustom)) {
        unitSellingPrice = parsedCustom;
        isBelowCost = unitSellingPrice < cost;
      }
    }

    const subtotal = unitSellingPrice * qty;
    const profitPerUnit = Math.max(0, unitSellingPrice - cost);
    const totalProfit = profitPerUnit * qty;
    const incentiveAmount = totalProfit * (effectiveIncentive / 100);
    const companyNetProfit = totalProfit - incentiveAmount;

    let cgstRate = 0;
    let sgstRate = 0;
    let igstRate = 0;
    let cgstAmount = 0;
    let sgstAmount = 0;
    let igstAmount = 0;
    let totalTax = 0;

    const taxRatePct = parseFloat(calcCustomTaxRate) || 18;

    if (calcTaxType === "GST") {
      cgstRate = taxRatePct / 2;
      sgstRate = taxRatePct / 2;
      cgstAmount = (subtotal * cgstRate) / 100;
      sgstAmount = (subtotal * sgstRate) / 100;
      totalTax = cgstAmount + sgstAmount;
    } else if (calcTaxType === "IGST") {
      igstRate = taxRatePct;
      igstAmount = (subtotal * igstRate) / 100;
      totalTax = igstAmount;
    }

    const grandTotal = subtotal + totalTax;

    return {
      purchaseCost: cost * qty,
      quantity: qty,
      markupPct: effectiveMarkup,
      unitCost: cost,
      defaultPrice: calculatedDefaultPrice,
      unitSellingPrice,
      subtotal,
      profitPerUnit,
      totalProfit,
      incentivePct: effectiveIncentive,
      incentiveAmount,
      companyNetProfit,
      taxType: calcTaxType,
      cgstRate,
      sgstRate,
      igstRate,
      cgstAmount,
      sgstAmount,
      igstAmount,
      totalTax,
      grandTotal,
      isBelowCost,
    };
  }, [
    calcBaseAmount,
    calcQuantity,
    calcCustomPrice,
    calcMarkupOverride,
    calcIncentiveOverride,
    calcTaxType,
    calcCustomTaxRate,
    currentConfig,
  ]);

  // Verify calculation against backend API endpoint
  const testBackendCalculation = async () => {
    try {
      setCalculatingApi(true);
      const res = await api.post("/staff/accounts/pricing-config/calculate", {
        purchase_cost: parseFloat(calcBaseAmount) || 0,
        markup_pct: calcMarkupOverride !== "" ? parseFloat(calcMarkupOverride) : undefined,
        custom_price: calcCustomPrice !== "" ? parseFloat(calcCustomPrice) : undefined,
        quantity: parseInt(calcQuantity) || 1,
        incentive_pct: calcIncentiveOverride !== "" ? parseFloat(calcIncentiveOverride) : undefined,
        company_id: selectedCompanyId ? parseInt(selectedCompanyId) : undefined,
      });

      if (res.data?.success && res.data.calculation) {
        setStatusMessage({
          type: "success",
          text: `Backend Calculation Verified: Profit = ₹${res.data.calculation.profit_per_unit}, Incentive = ₹${res.data.calculation.incentive_amount}`,
        });
      }
    } catch (err: any) {
      console.error("Backend calculation error:", err);
      setStatusMessage({
        type: "error",
        text: err.response?.data?.detail || "Calculation request failed.",
      });
    } finally {
      setCalculatingApi(false);
    }
  };

  const currencySymbol = currentConfig?.currency === "USD" ? "$" : currentConfig?.currency === "EUR" ? "€" : "₹";
  const decimals = Number(currentConfig?.decimal_places ?? 2);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200/80 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-indigo-700 text-white rounded-xl shadow-md">
              <Coins className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
                Pricing & Markup Configuration
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                Manage company-wide markup percentages, employee incentives, tax defaults, and price simulations.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => {
              if (selectedCompanyId) fetchPricingConfig(selectedCompanyId);
            }}
            disabled={loadingConfig}
            className="border-gray-200 hover:bg-gray-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loadingConfig ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          {currentConfig && (
            <Button
              onClick={openEditModal}
              className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm"
            >
              <Edit className="w-4 h-4 mr-2" />
              Edit Configuration
            </Button>
          )}
        </div>
      </div>

      {/* Notifications / Alerts */}
      {statusMessage && (
        <Alert
          className={`${
            statusMessage.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : statusMessage.type === "error"
              ? "bg-red-50 border-red-200 text-red-900"
              : "bg-blue-50 border-blue-200 text-blue-900"
          }`}
        >
          {statusMessage.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : statusMessage.type === "error" ? (
            <AlertTriangle className="w-4 h-4 text-red-600" />
          ) : (
            <Info className="w-4 h-4 text-blue-600" />
          )}
          <AlertTitle className="font-semibold text-sm">
            {statusMessage.type === "success" ? "Success" : statusMessage.type === "error" ? "Notice" : "Information"}
          </AlertTitle>
          <AlertDescription className="text-xs">{statusMessage.text}</AlertDescription>
        </Alert>
      )}

      {/* Company Selector Card */}
      <Card className="border-gray-200 shadow-sm bg-white overflow-hidden">
        <CardContent className="p-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Building2 className="w-5 h-5 text-indigo-600 flex-shrink-0" />
              <div>
                <Label htmlFor="company-select" className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Select Associated Company
                </Label>
                <div className="mt-1">
                  {loadingCompanies ? (
                    <div className="flex items-center gap-2 text-sm text-gray-500 py-1.5">
                      <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                      Loading companies...
                    </div>
                  ) : (
                    <Select
                      value={selectedCompanyId}
                      onValueChange={(val) => setSelectedCompanyId(val)}
                    >
                      <SelectTrigger id="company-select" className="w-full md:w-80 bg-white">
                        <SelectValue placeholder="Choose a company..." />
                      </SelectTrigger>
                      <SelectContent>
                        {companies.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)}>
                            <div className="flex items-center justify-between w-full gap-3">
                              <span className="font-medium text-gray-900">{c.company_name || c.name}</span>
                              <span className="text-xs text-gray-400 font-mono">({c.company_code || c.code || `#${c.id}`})</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
            </div>

            {selectedCompany && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600 bg-gray-50 p-2.5 rounded-lg border border-gray-100">
                <Badge variant="outline" className="bg-white border-gray-200 text-gray-700">
                  Code: {selectedCompany.company_code || selectedCompany.code || "-"}
                </Badge>
                {selectedCompany.gst_number && (
                  <Badge variant="outline" className="bg-white border-gray-200 text-gray-700">
                    GST: {selectedCompany.gst_number}
                  </Badge>
                )}
                <Badge
                  className={
                    selectedCompany.is_active
                      ? "bg-emerald-100 text-emerald-800 hover:bg-emerald-100"
                      : "bg-red-100 text-red-800 hover:bg-red-100"
                  }
                >
                  {selectedCompany.is_active ? "Active Entity" : "Inactive Entity"}
                </Badge>
                {selectedCompany.is_marketplace_endpoint && (
                  <Badge className="bg-indigo-100 text-indigo-800 hover:bg-indigo-100">
                    Marketplace Endpoint
                  </Badge>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Area */}
      {loadingConfig ? (
        <div className="p-16 flex flex-col items-center justify-center bg-white rounded-xl border border-gray-200 shadow-sm text-gray-500">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-600 mb-3" />
          <p className="font-medium text-gray-700">Loading pricing configuration...</p>
          <p className="text-xs text-gray-400 mt-1">Retrieving DC markup constraints & tax parameters</p>
        </div>
      ) : !currentConfig ? (
        <Card className="border-dashed border-2 border-gray-300 p-12 text-center bg-gray-50/50">
          <div className="w-14 h-14 bg-indigo-50 text-indigo-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <Tag className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">No Pricing Configuration Found</h3>
          <p className="text-sm text-gray-500 max-w-md mx-auto mt-1 mb-6">
            Please select a valid associated company from the dropdown to load or initialize its pricing configuration.
          </p>
          {companies.length > 0 && (
            <Button
              onClick={() => fetchPricingConfig(String(companies[0].id))}
              className="bg-indigo-600 hover:bg-indigo-700"
            >
              Load Default Company
            </Button>
          )}
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Default Markup</span>
                  <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                    <Percent className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-indigo-600">
                    {Number(currentConfig.default_markup_pct || 0).toFixed(1)}%
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Standard cost multiplier markup</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Employee Incentive</span>
                  <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
                    <TrendingUp className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-emerald-600">
                    {Number(currentConfig.incentive_pct || 0).toFixed(1)}%
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Share of profit allocated to employee</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Min Markup Floor</span>
                  <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-amber-600">
                    {Number(currentConfig.min_markup_pct || 0).toFixed(1)}%
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {currentConfig.allow_below_cost ? "Allows sale below cost" : "Enforced minimum profit floor"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Status & Currency</span>
                  <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
                    <DollarSign className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-gray-900">{currentConfig.currency || "INR"}</span>
                  <Badge
                    className={
                      currentConfig.is_active
                        ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100"
                        : "bg-red-100 text-red-700 hover:bg-red-100"
                    }
                  >
                    {currentConfig.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <p className="text-xs text-gray-500 mt-1">Decimals: {currentConfig.decimal_places ?? 2} | {currentConfig.rounding_method ?? "ROUND"}</p>
              </CardContent>
            </Card>
          </div>

          {/* Tabbed View: Overview, Simulator, Tax Settings */}
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-2 md:w-96 bg-gray-100/80 p-1">
              <TabsTrigger value="overview" className="text-sm font-medium">
                Configuration Details
              </TabsTrigger>
              <TabsTrigger value="calculator" className="text-sm font-medium">
                Price Simulator
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: Configuration Details */}
            <TabsContent value="overview" className="space-y-6 pt-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Card 1: Markup & Profit Policy */}
                <Card className="border-gray-200 shadow-sm">
                  <CardHeader className="bg-gradient-to-r from-indigo-50/70 to-indigo-100/30 border-b border-gray-100 py-4">
                    <CardTitle className="text-base font-semibold text-indigo-950 flex items-center gap-2">
                      <Percent className="w-4 h-4 text-indigo-600" />
                      Markup & Margin Rules
                    </CardTitle>
                    <CardDescription className="text-xs">
                      DC rules governing cost markups & incentives
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-5 space-y-3.5">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Default Markup</span>
                      <span className="font-semibold text-indigo-600">
                        {Number(currentConfig.default_markup_pct || 0).toFixed(2)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Incentive Share</span>
                      <span className="font-semibold text-emerald-600">
                        {Number(currentConfig.incentive_pct || 0).toFixed(2)}% of profit
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Minimum Markup</span>
                      <span className="font-semibold text-gray-800">
                        {Number(currentConfig.min_markup_pct || 0).toFixed(2)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Maximum Markup</span>
                      <span className="font-semibold text-gray-800">
                        {currentConfig.max_markup_pct ? `${Number(currentConfig.max_markup_pct).toFixed(2)}%` : "No limit"}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 text-sm">
                      <span className="text-gray-500">Allow Below Cost Sale</span>
                      <Badge variant={currentConfig.allow_below_cost ? "default" : "secondary"}>
                        {currentConfig.allow_below_cost ? "Allowed" : "Blocked (Strict Cost Protection)"}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                {/* Card 2: Default Tax Rates & Currency */}
                <Card className="border-gray-200 shadow-sm">
                  <CardHeader className="bg-gradient-to-r from-emerald-50/70 to-emerald-100/30 border-b border-gray-100 py-4">
                    <CardTitle className="text-base font-semibold text-emerald-950 flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-emerald-600" />
                      Tax Defaults & Formats
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Default tax rates and currency parameters
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-5 space-y-3.5">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Default CGST Rate</span>
                      <span className="font-semibold text-emerald-700">
                        {Number(currentConfig.default_cgst_rate || 9.0).toFixed(2)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Default SGST Rate</span>
                      <span className="font-semibold text-emerald-700">
                        {Number(currentConfig.default_sgst_rate || 9.0).toFixed(2)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Default IGST Rate</span>
                      <span className="font-semibold text-emerald-700">
                        {Number(currentConfig.default_igst_rate || 18.0).toFixed(2)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">TDS Rate</span>
                      <span className="font-semibold text-emerald-700">
                        {Number(currentConfig.tds_rate || 0.1).toFixed(2)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 text-sm">
                      <span className="text-gray-500">Rounding & Decimals</span>
                      <span className="font-semibold text-gray-800">
                        {currentConfig.rounding_method || "ROUND"} ({currentConfig.decimal_places ?? 2} pl)
                      </span>
                    </div>
                  </CardContent>
                </Card>

                {/* Card 3: Configuration Audit & Metadata */}
                <Card className="border-gray-200 shadow-sm">
                  <CardHeader className="bg-gradient-to-r from-blue-50/70 to-blue-100/30 border-b border-gray-100 py-4">
                    <CardTitle className="text-base font-semibold text-blue-950 flex items-center gap-2">
                      <Info className="w-4 h-4 text-blue-600" />
                      Config Metadata & Audit
                    </CardTitle>
                    <CardDescription className="text-xs">
                      DC system timestamps and tracking IDs
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-5 space-y-3.5">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Configuration ID</span>
                      <span className="font-mono text-xs font-bold text-gray-700">
                        #{currentConfig.id}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Config Type</span>
                      <Badge variant="outline" className="text-xs">
                        {currentConfig.config_type || "SERVICE_ITEM_MARKUP"}
                      </Badge>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Company ID</span>
                      <span className="font-mono text-xs text-gray-700">
                        Comp #{currentConfig.company_id} ({currentConfig.company_name || selectedCompany?.company_name || "-"})
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 border-b border-gray-100 text-sm">
                      <span className="text-gray-500">Last Modified</span>
                      <span className="text-xs text-gray-700">
                        {currentConfig.updated_at
                          ? new Date(currentConfig.updated_at).toLocaleString()
                          : "Initial Creation"}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-2 text-sm">
                      <span className="text-gray-500">Description</span>
                      <span className="text-xs text-gray-600 italic">
                        {currentConfig.description || "Default Pricing Rule"}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Action Bar */}
              <div className="flex justify-end gap-3 pt-2">
                <Button
                  onClick={openEditModal}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Edit Pricing Configuration
                </Button>
              </div>
            </TabsContent>

            {/* TAB 2: Live Price Simulator */}
            <TabsContent value="calculator" className="space-y-6 pt-4">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Inputs Column */}
                <div className="lg:col-span-5 space-y-4">
                  <Card className="border-gray-200 shadow-sm">
                    <CardHeader className="bg-indigo-50/50 pb-4">
                      <CardTitle className="text-base font-semibold text-indigo-900 flex items-center gap-2">
                        <Calculator className="w-4 h-4 text-indigo-600" />
                        Simulation Inputs
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Simulate gross margins, taxes, and employee incentive shares.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-5 space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-gray-700">
                            Unit Purchase Cost ({currencySymbol}) *
                          </Label>
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            value={calcBaseAmount}
                            onChange={(e) => setCalcBaseAmount(e.target.value)}
                            placeholder="e.g. 1000"
                            className="font-medium"
                          />
                        </div>

                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-gray-700">
                            Quantity *
                          </Label>
                          <Input
                            type="number"
                            min="1"
                            step="1"
                            value={calcQuantity}
                            onChange={(e) => setCalcQuantity(e.target.value)}
                            placeholder="1"
                            className="font-medium"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-gray-700">
                            Markup % (Default: {Number(currentConfig.default_markup_pct || 20)}%)
                          </Label>
                          <Input
                            type="number"
                            min="0"
                            max="500"
                            step="0.1"
                            value={calcMarkupOverride}
                            onChange={(e) => setCalcMarkupOverride(e.target.value)}
                            placeholder={String(currentConfig.default_markup_pct || 20)}
                          />
                        </div>

                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-gray-700">
                            Custom Unit Price (Optional)
                          </Label>
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            value={calcCustomPrice}
                            onChange={(e) => setCalcCustomPrice(e.target.value)}
                            placeholder="Override default price"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-gray-700">
                            Incentive Share % (Default: {Number(currentConfig.incentive_pct || 50)}%)
                          </Label>
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="1"
                            value={calcIncentiveOverride}
                            onChange={(e) => setCalcIncentiveOverride(e.target.value)}
                            placeholder={String(currentConfig.incentive_pct || 50)}
                          />
                        </div>

                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-gray-700">
                            Tax Application
                          </Label>
                          <Select
                            value={calcTaxType}
                            onValueChange={(val: any) => setCalcTaxType(val)}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="GST">GST (CGST + SGST)</SelectItem>
                              <SelectItem value="IGST">IGST (Inter-State)</SelectItem>
                              <SelectItem value="NONE">No Tax (Exempt)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {calcTaxType !== "NONE" && (
                        <div className="space-y-1.5">
                          <Label className="text-xs font-semibold text-gray-700">
                            Total GST Rate %
                          </Label>
                          <Select
                            value={calcCustomTaxRate}
                            onValueChange={(val) => setCalcCustomTaxRate(val)}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="0">0% (Nil Rate)</SelectItem>
                              <SelectItem value="5">5% (2.5% CGST + 2.5% SGST)</SelectItem>
                              <SelectItem value="12">12% (6% CGST + 6% SGST)</SelectItem>
                              <SelectItem value="18">18% (9% CGST + 9% SGST)</SelectItem>
                              <SelectItem value="28">28% (14% CGST + 14% SGST)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}

                      <div className="pt-2 flex justify-between gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setCalcBaseAmount("1000");
                            setCalcQuantity("1");
                            setCalcCustomPrice("");
                            setCalcMarkupOverride("");
                            setCalcIncentiveOverride("");
                            setCalcTaxType("GST");
                            setCalcCustomTaxRate("18");
                          }}
                        >
                          Reset Inputs
                        </Button>

                        <Button
                          type="button"
                          size="sm"
                          onClick={testBackendCalculation}
                          disabled={calculatingApi}
                          className="bg-indigo-600 hover:bg-indigo-700 text-white"
                        >
                          {calculatingApi ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                              Verifying...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                              Test in API
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Live Output & Breakdown Column */}
                <div className="lg:col-span-7 space-y-4">
                  <Card className="border-gray-200 shadow-md bg-white overflow-hidden">
                    <CardHeader className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white py-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-amber-300" />
                            Calculation & Profit Distribution Breakdown
                          </CardTitle>
                          <CardDescription className="text-xs text-slate-300">
                            Real-time simulation based on active DC pricing policy
                          </CardDescription>
                        </div>
                        {calculationResult.isBelowCost && (
                          <Badge variant="destructive" className="animate-pulse">
                            Warning: Below Cost
                          </Badge>
                        )}
                      </div>
                    </CardHeader>

                    <CardContent className="p-6 space-y-5">
                      {/* KPI Row */}
                      <div className="grid grid-cols-3 gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100 text-center">
                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 uppercase">Unit Selling Price</p>
                          <p className="text-lg font-bold text-gray-900 mt-0.5">
                            {currencySymbol}{calculationResult.unitSellingPrice.toFixed(decimals)}
                          </p>
                          <p className="text-[10px] text-gray-400">Cost: {currencySymbol}{calculationResult.unitCost.toFixed(decimals)}</p>
                        </div>

                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 uppercase">Staff Incentive</p>
                          <p className="text-lg font-bold text-emerald-600 mt-0.5">
                            {currencySymbol}{calculationResult.incentiveAmount.toFixed(decimals)}
                          </p>
                          <p className="text-[10px] text-emerald-600 font-medium">({calculationResult.incentivePct}% of profit)</p>
                        </div>

                        <div>
                          <p className="text-[11px] font-semibold text-gray-500 uppercase">Grand Total (Incl Tax)</p>
                          <p className="text-lg font-bold text-indigo-600 mt-0.5">
                            {currencySymbol}{calculationResult.grandTotal.toFixed(decimals)}
                          </p>
                          <p className="text-[10px] text-gray-400">Qty: {calculationResult.quantity}</p>
                        </div>
                      </div>

                      {/* Detailed Line Items */}
                      <div className="space-y-2.5 text-sm">
                        <div className="flex justify-between items-center py-1.5 border-b border-gray-100">
                          <span className="text-gray-600">Total Purchase Cost ({calculationResult.quantity} × {currencySymbol}{calculationResult.unitCost.toFixed(decimals)})</span>
                          <span className="font-semibold text-gray-900">
                            {currencySymbol}{calculationResult.purchaseCost.toFixed(decimals)}
                          </span>
                        </div>

                        <div className="flex justify-between items-center py-1.5 border-b border-gray-100">
                          <span className="text-gray-600">Calculated Default Price (+{calculationResult.markupPct}% markup)</span>
                          <span className="text-gray-700">
                            {currencySymbol}{(calculationResult.defaultPrice * calculationResult.quantity).toFixed(decimals)}
                          </span>
                        </div>

                        <div className="flex justify-between items-center py-1.5 border-b border-gray-100 bg-indigo-50/40 px-2 rounded">
                          <span className="font-medium text-indigo-950">Subtotal (Pre-Tax Revenue)</span>
                          <span className="font-bold text-indigo-950">
                            {currencySymbol}{calculationResult.subtotal.toFixed(decimals)}
                          </span>
                        </div>

                        <div className="flex justify-between items-center py-1.5 border-b border-gray-100">
                          <span className="text-gray-600">Gross Margin / Profit</span>
                          <span className="font-semibold text-gray-900">
                            {currencySymbol}{calculationResult.totalProfit.toFixed(decimals)}
                          </span>
                        </div>

                        <div className="flex justify-between items-center py-1.5 border-b border-gray-100 text-emerald-800 bg-emerald-50/30 px-2 rounded">
                          <span className="flex items-center gap-1.5">
                            <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
                            Employee Incentive Share ({calculationResult.incentivePct}%)
                          </span>
                          <span className="font-bold text-emerald-700">
                            +{currencySymbol}{calculationResult.incentiveAmount.toFixed(decimals)}
                          </span>
                        </div>

                        <div className="flex justify-between items-center py-1.5 border-b border-gray-100 text-blue-900 bg-blue-50/30 px-2 rounded">
                          <span className="flex items-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                            Company Net Retained Profit
                          </span>
                          <span className="font-bold text-blue-800">
                            {currencySymbol}{calculationResult.companyNetProfit.toFixed(decimals)}
                          </span>
                        </div>

                        {/* Tax section */}
                        {calculationResult.taxType === "GST" && (
                          <>
                            <div className="flex justify-between items-center py-1 text-xs text-gray-500 pl-4">
                              <span>CGST ({calculationResult.cgstRate}%)</span>
                              <span>{currencySymbol}{calculationResult.cgstAmount.toFixed(decimals)}</span>
                            </div>
                            <div className="flex justify-between items-center py-1 text-xs text-gray-500 pl-4">
                              <span>SGST ({calculationResult.sgstRate}%)</span>
                              <span>{currencySymbol}{calculationResult.sgstAmount.toFixed(decimals)}</span>
                            </div>
                          </>
                        )}

                        {calculationResult.taxType === "IGST" && (
                          <div className="flex justify-between items-center py-1 text-xs text-gray-500 pl-4">
                            <span>IGST ({calculationResult.igstRate}%)</span>
                            <span>{currencySymbol}{calculationResult.igstAmount.toFixed(decimals)}</span>
                          </div>
                        )}

                        <div className="flex justify-between items-center py-1.5 border-b border-gray-100">
                          <span className="text-gray-600">Total Applicable Taxes</span>
                          <span className="font-semibold text-gray-900">
                            {currencySymbol}{calculationResult.totalTax.toFixed(decimals)}
                          </span>
                        </div>

                        {/* Grand Total */}
                        <div className="flex justify-between items-center pt-3 border-t-2 border-indigo-200 text-base">
                          <span className="font-bold text-gray-950">Grand Total (Customer Payable)</span>
                          <span className="text-xl font-extrabold text-indigo-700">
                            {currencySymbol}{calculationResult.grandTotal.toFixed(decimals)}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      )}

      {/* Edit Configuration Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-gray-900">
              <Edit className="w-5 h-5 text-indigo-600" />
              Edit Pricing Configuration
            </DialogTitle>
            <DialogDescription className="text-xs text-gray-500">
              Update DC markup constraints, incentive shares, and default tax parameters for{" "}
              <span className="font-semibold text-gray-800">
                {selectedCompany?.company_name || `Company #${selectedCompanyId}`}
              </span>.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-3">
            {/* Markup & Incentive Group */}
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200/80 space-y-4">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <Percent className="w-4 h-4 text-indigo-600" />
                Markup & Incentive Parameters
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Default Markup (%) *
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    value={formData.default_markup_pct ?? ""}
                    onChange={(e) =>
                      setFormData({ ...formData, default_markup_pct: e.target.value })
                    }
                    placeholder="20.00"
                  />
                  {formErrors.default_markup_pct && (
                    <p className="text-xs text-red-600">{formErrors.default_markup_pct}</p>
                  )}
                  <p className="text-[11px] text-gray-400">Standard profit markup over cost</p>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Employee Incentive Share (%) *
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    value={formData.incentive_pct ?? ""}
                    onChange={(e) =>
                      setFormData({ ...formData, incentive_pct: e.target.value })
                    }
                    placeholder="50.00"
                  />
                  {formErrors.incentive_pct && (
                    <p className="text-xs text-red-600">{formErrors.incentive_pct}</p>
                  )}
                  <p className="text-[11px] text-gray-400">Share of unit profit credited to employee</p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Minimum Allowed Markup (%) *
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    value={formData.min_markup_pct ?? ""}
                    onChange={(e) =>
                      setFormData({ ...formData, min_markup_pct: e.target.value })
                    }
                    placeholder="0.00"
                  />
                  {formErrors.min_markup_pct && (
                    <p className="text-xs text-red-600">{formErrors.min_markup_pct}</p>
                  )}
                  <p className="text-[11px] text-gray-400">Floor price threshold (cannot sell lower)</p>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Config Type
                  </Label>
                  <Select
                    value={formData.config_type || "SERVICE_ITEM_MARKUP"}
                    onValueChange={(val) => setFormData({ ...formData, config_type: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SERVICE_ITEM_MARKUP">SERVICE_ITEM_MARKUP</SelectItem>
                      <SelectItem value="PRODUCT_MARKUP">PRODUCT_MARKUP</SelectItem>
                      <SelectItem value="GENERAL">GENERAL</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Tax & Regional Settings */}
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200/80 space-y-4">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-600" />
                Default Tax Rates & Formatting
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Default CGST Rate (%)
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="50"
                    value={formData.default_cgst_rate ?? ""}
                    onChange={(e) =>
                      setFormData({ ...formData, default_cgst_rate: e.target.value })
                    }
                    placeholder="9.00"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Default SGST Rate (%)
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="50"
                    value={formData.default_sgst_rate ?? ""}
                    onChange={(e) =>
                      setFormData({ ...formData, default_sgst_rate: e.target.value })
                    }
                    placeholder="9.00"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Default IGST Rate (%)
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="50"
                    value={formData.default_igst_rate ?? ""}
                    onChange={(e) =>
                      setFormData({ ...formData, default_igst_rate: e.target.value })
                    }
                    placeholder="18.00"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    TDS Rate (%)
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="50"
                    value={formData.tds_rate ?? ""}
                    onChange={(e) =>
                      setFormData({ ...formData, tds_rate: e.target.value })
                    }
                    placeholder="0.10"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Currency
                  </Label>
                  <Select
                    value={formData.currency || "INR"}
                    onValueChange={(val) => setFormData({ ...formData, currency: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="INR">INR (₹)</SelectItem>
                      <SelectItem value="USD">USD ($)</SelectItem>
                      <SelectItem value="EUR">EUR (€)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Decimal Places
                  </Label>
                  <Select
                    value={String(formData.decimal_places ?? 2)}
                    onValueChange={(val) =>
                      setFormData({ ...formData, decimal_places: parseInt(val) || 2 })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">0</SelectItem>
                      <SelectItem value="2">2</SelectItem>
                      <SelectItem value="3">3</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold text-gray-700">
                    Rounding Method
                  </Label>
                  <Select
                    value={formData.rounding_method || "ROUND"}
                    onValueChange={(val) => setFormData({ ...formData, rounding_method: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ROUND">Round (Normal)</SelectItem>
                      <SelectItem value="FLOOR">Floor (Round Down)</SelectItem>
                      <SelectItem value="CEIL">Ceil (Round Up)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Description & Active Status */}
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-gray-700">
                  Description / Internal Notes
                </Label>
                <Textarea
                  value={formData.description || ""}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Optional notes regarding pricing logic or customer tiers..."
                  rows={2}
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <Checkbox
                  id="is_active_config"
                  checked={formData.is_active !== false}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_active: checked as boolean })
                  }
                />
                <label
                  htmlFor="is_active_config"
                  className="text-sm font-medium leading-none cursor-pointer text-gray-800"
                >
                  Configuration is Active
                </label>
              </div>
            </div>
          </div>

          <DialogFooter className="border-t border-gray-100 pt-4 flex justify-between sm:justify-between items-center">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsEditOpen(false)}
            >
              Cancel
            </Button>

            <Button
              type="button"
              onClick={handleSaveConfig}
              disabled={savingConfig}
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              {savingConfig ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Saving Changes...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Configuration
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

