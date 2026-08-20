"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import Link from "next/link";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import {
  BookOpen,
  Plus,
  Search,
  RotateCcw,
  Save,
  Table as TableIcon,
  FileText,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Eye,
  Edit,
  Trash2,
  Building2,
  Calendar,
  ArrowRight,
  ArrowLeft,
  User,
  UserCheck,
  UserPlus,
  X,
  ChevronLeft,
  ChevronRight,
  Coins,
  Receipt,
  CreditCard,
  Wallet,
  Banknote,
  Check,
  ExternalLink,
  Sparkles,
  Layers,
  Phone,
  Mail,
  Globe,
  MapPin,
  Truck,
  Info,
  ShieldCheck,
  RefreshCw,
  SlidersHorizontal,
  Landmark,
  Scale,
  HandCoins,
  History,
  Building,
  Store,
  Crown,
  IdCard,
  Handshake,
  Star,
  Wrench,
  Package
} from "lucide-react";

// ==========================================
// Types & Metadata
// ==========================================

export type VoucherType = "PAYMENT" | "RECEIPT" | "CONTRA" | "JOURNAL";

export interface Company {
  id: number;
  company_name?: string;
  name?: string;
}

export interface BankAccount {
  id: number;
  account_name: string;
  bank_name?: string;
  account_number?: string;
  account_type?: string;
  ifsc_code?: string;
  branch?: string;
  is_primary?: boolean;
}

export interface PartySearchResult {
  id: string | number;
  name: string;
  type: string;
  sub?: string;
  phone?: string;
}

export interface LedgerMaster {
  id: number;
  account_name: string;
  account_type: string;
  group_name?: string;
  parent_group?: string;
  opening_balance?: number;
  is_primary?: boolean;
}

export interface CategoryItem {
  id: number;
  name: string;
  parent_id?: number;
}

export interface InvoiceLinkItem {
  value: number;
  label: string;
  balance: number;
  docType: "PURCHASE" | "SALE";
}

export interface JournalVoucherLine {
  id?: number;
  entry_type: "DEBIT" | "CREDIT";
  account_type: string;
  account_name: string;
  amount: number;
  party_name?: string;
  party_id?: number | string;
}

export interface JournalVoucherItem {
  id: number;
  voucher_number: string;
  voucher_date: string;
  voucher_type: VoucherType;
  company_id: number;
  company_name?: string;
  dr_account_type: string;
  dr_account_name: string;
  cr_account_type: string;
  cr_account_name: string;
  amount: number;
  party_name?: string;
  party_type?: string;
  party_id?: number;
  payment_mode?: string;
  reference_number?: string;
  narration?: string;
  main_category_name?: string;
  sub_category_name?: string;
  category_id?: number;
  income_category_id?: number;
  status: "POSTED" | "CANCELLED";
  cancel_reason?: string;
  created_at?: string;
  creator_name?: string;
  is_compound?: boolean;
}

export interface CompoundRow {
  id: string;
  entry_type: "DEBIT" | "CREDIT";
  account_type: string;
  account_name: string;
  amount: string;
}

const PARTY_META: Record<string, { label: string; bg: string; color: string; icon: string }> = {
  VGK_MEMBER: { label: "VGK Member", bg: "bg-purple-100 text-purple-700 border-purple-200", color: "#7c3aed", icon: "crown" },
  MNR_MEMBER: { label: "MNR Member", bg: "bg-sky-100 text-sky-700 border-sky-200", color: "#0369a1", icon: "id-card" },
  DEALER: { label: "Dealer", bg: "bg-emerald-100 text-emerald-700 border-emerald-200", color: "#047857", icon: "handshake" },
  DISTRIBUTOR: { label: "Distributor", bg: "bg-amber-100 text-amber-700 border-amber-200", color: "#b45309", icon: "truck" },
  RD_PARTNER: { label: "Real Dream Partner", bg: "bg-rose-100 text-rose-700 border-rose-200", color: "#be123c", icon: "star" },
  SERVICE_CENTER: { label: "Service Center", bg: "bg-teal-100 text-teal-700 border-teal-200", color: "#0f766e", icon: "wrench" },
  PARTNER_VENDOR: { label: "Partner / Vendor", bg: "bg-violet-100 text-violet-700 border-violet-200", color: "#6d28d9", icon: "box" },
  VENDOR: { label: "Vendor", bg: "bg-cyan-100 text-cyan-700 border-cyan-200", color: "#0e7490", icon: "store" },
  STAFF: { label: "Staff", bg: "bg-blue-100 text-blue-700 border-blue-200", color: "#1d4ed8", icon: "user-tie" },
  COMPANY: { label: "Company", bg: "bg-gray-100 text-gray-700 border-gray-200", color: "#374151", icon: "building" },
  EXTERNAL: { label: "External", bg: "bg-slate-100 text-slate-700 border-slate-200", color: "#6b7280", icon: "user-plus" }
};

const ACCOUNT_TYPES = [
  "BANK",
  "CASH",
  "UPI",
  "PARTY",
  "INCOME",
  "EXPENSE",
  "ASSET",
  "LIABILITY",
  "CAPITAL",
  "LOAN",
  "STOCK"
];

const CREATABLE_LEDGER_TYPES = new Set([
  "EXPENSE",
  "INCOME",
  "ASSET",
  "LIABILITY",
  "CAPITAL",
  "LOAN",
  "STOCK"
]);

const VT_PRESETS: Record<
  VoucherType,
  {
    drType: string;
    drHint: string;
    crType: string;
    crHint: string;
    showInvoice: boolean;
    invoiceType: "PURCHASE" | "SALE" | null;
    invoiceDesc: string;
  }
> = {
  PAYMENT: {
    drType: "PARTY",
    drHint: "Vendor / Person Name",
    crType: "BANK",
    crHint: "Bank Account Name",
    showInvoice: true,
    invoiceType: "PURCHASE",
    invoiceDesc: "Link to open purchase invoice"
  },
  RECEIPT: {
    drType: "BANK",
    drHint: "Bank Account Name",
    crType: "PARTY",
    crHint: "Payer / Customer Name",
    showInvoice: true,
    invoiceType: "SALE",
    invoiceDesc: "Link to open sales invoice"
  },
  CONTRA: {
    drType: "CASH",
    drHint: "Cash Account",
    crType: "BANK",
    crHint: "Bank Account Name",
    showInvoice: false,
    invoiceType: null,
    invoiceDesc: ""
  },
  JOURNAL: {
    drType: "EXPENSE",
    drHint: "Expense Account Name",
    crType: "BANK",
    crHint: "Bank Account Name",
    showInvoice: false,
    invoiceType: null,
    invoiceDesc: ""
  }
};

const STAFF_PAY_HEADS: Record<string, { head: string | null; drType: string; isAdvance: boolean }> = {
  SALARY: { head: "Salary Expense", drType: "EXPENSE", isAdvance: false },
  INCENTIVE: { head: "Staff Incentive Expense", drType: "EXPENSE", isAdvance: false },
  CONVEYANCE: { head: "Conveyance Expense", drType: "EXPENSE", isAdvance: false },
  TRAVEL: { head: "Travel Allowance Expense", drType: "EXPENSE", isAdvance: false },
  ADVANCE: { head: null, drType: "PARTY", isAdvance: true },
  REIMBURSEMENT: { head: "Staff Reimbursement", drType: "EXPENSE", isAdvance: false },
  OTHER: { head: null, drType: "EXPENSE", isAdvance: false }
};

const QCL_GROUP_CHIPS: Record<string, { default: string; chips: string[] }> = {
  EXPENSE: {
    default: "Indirect Expenses",
    chips: [
      "Direct Expenses",
      "Indirect Expenses",
      "Salary & Wages",
      "Rent & Utilities",
      "Administration",
      "Marketing & Sales",
      "Commission",
      "Interest & Bank Charges",
      "Depreciation",
      "Miscellaneous Expense"
    ]
  },
  INCOME: {
    default: "Revenue",
    chips: [
      "Direct Income",
      "Indirect Income",
      "Revenue",
      "Commission Income",
      "Interest Income",
      "Rental Income",
      "Other Income"
    ]
  },
  ASSET: {
    default: "Fixed Assets",
    chips: ["Fixed Assets", "Current Assets", "Investments", "Loans & Advances"]
  },
  LIABILITY: {
    default: "Current Liabilities",
    chips: ["Current Liabilities", "Long-term Liabilities", "Provisions", "Duties & Taxes"]
  },
  CAPITAL: {
    default: "Capital",
    chips: ["Capital", "Equity", "Reserves & Surplus"]
  },
  LOAN: {
    default: "Loans & Advances",
    chips: ["Loans & Advances", "Borrowings", "Bank Overdraft", "Secured Loans", "Unsecured Loans"]
  },
  STOCK: { default: "Stock / Inventory", chips: [] },
  PARTY: { default: "", chips: [] }
};

export default function JournalVoucherPage() {
  const { user } = useStaffAuth();

  // ----------------------------------------------------
  // Global / Page State
  // ----------------------------------------------------
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyMap, setCompanyMap] = useState<Record<number, string>>({});
  const [activeTab, setActiveTab] = useState<"POSTED" | "CANCELLED">("POSTED");

  // Notifications
  const [formSuccess, setFormSuccess] = useState<string>("");
  const [formError, setFormError] = useState<string>("");
  const [posting, setPosting] = useState<boolean>(false);

  // Form State
  const [vtype, setVtype] = useState<VoucherType>("PAYMENT");
  const [compoundMode, setCompoundMode] = useState<boolean>(false);
  const [companyId, setCompanyId] = useState<string>("");
  const [voucherDate, setVoucherDate] = useState<string>(new Date().toISOString().slice(0, 10));

  // Simple Form Fields
  const [drType, setDrType] = useState<string>("PARTY");
  const [drName, setDrName] = useState<string>("");
  const [crType, setCrType] = useState<string>("BANK");
  const [crName, setCrName] = useState<string>("");
  const [amount, setAmount] = useState<string>("");
  const [payMode, setPayMode] = useState<string>("");
  const [refNum, setRefNum] = useState<string>("");
  const [narration, setNarration] = useState<string>("");
  const [autoNarrationDirty, setAutoNarrationDirty] = useState<boolean>(false);

  // Selected Party Tracking
  const [selectedParty, setSelectedParty] = useState<{
    id: number | string | null;
    name: string;
    type: string;
  } | null>(null);
  const [drConfirmedParty, setDrConfirmedParty] = useState<{ id: any; name: string } | null>(null);
  const [crConfirmedParty, setCrConfirmedParty] = useState<{ id: any; name: string } | null>(null);

  // Staff Payment Category
  const [staffPayType, setStaffPayType] = useState<string>("");
  const [staffPayOtherHead, setStaffPayOtherHead] = useState<string>("");

  // Invoice Linking
  const [invoiceLinkLoading, setInvoiceLinkLoading] = useState<boolean>(false);
  const [openInvoices, setOpenInvoices] = useState<InvoiceLinkItem[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceLinkItem | null>(null);

  // Categories
  const [mainCats, setMainCats] = useState<CategoryItem[]>([]);
  const [subCats, setSubCats] = useState<CategoryItem[]>([]);
  const [incMainCats, setIncMainCats] = useState<CategoryItem[]>([]);
  const [incSubCats, setIncSubCats] = useState<CategoryItem[]>([]);
  const [selectedMainCat, setSelectedMainCat] = useState<string>("");
  const [selectedSubCat, setSelectedSubCat] = useState<string>("");

  // Bank & Ledger Data
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [ledgerCache, setLedgerCache] = useState<Record<string, LedgerMaster[]>>({});

  // Dropdowns Visibility & Autocomplete
  const [drDropOpen, setDrDropOpen] = useState<"BANK" | "PARTY" | "LEDGER" | null>(null);
  const [crDropOpen, setCrDropOpen] = useState<"BANK" | "PARTY" | "LEDGER" | null>(null);
  const [partySearchResults, setPartySearchResults] = useState<PartySearchResult[]>([]);
  const [partySearchLoading, setPartySearchLoading] = useState<boolean>(false);
  const [ledgerSearchResults, setLedgerSearchResults] = useState<LedgerMaster[]>([]);
  const [ledgerSearchLoading, setLedgerSearchLoading] = useState<boolean>(false);

  // Compound Entry Lines
  const [compoundLines, setCompoundLines] = useState<CompoundRow[]>([
    { id: "dr-1", entry_type: "DEBIT", account_type: "EXPENSE", account_name: "", amount: "" },
    { id: "dr-2", entry_type: "DEBIT", account_type: "EXPENSE", account_name: "", amount: "" },
    { id: "cr-1", entry_type: "CREDIT", account_type: "BANK", account_name: "", amount: "" },
    { id: "cr-2", entry_type: "CREDIT", account_type: "BANK", account_name: "", amount: "" }
  ]);
  const [compActiveDrop, setCompActiveDrop] = useState<{
    rowId: string;
    type: "PARTY" | "LEDGER" | "BANK";
  } | null>(null);

  // Voucher List State
  const [vouchers, setVouchers] = useState<JournalVoucherItem[]>([]);
  const [listLoading, setListLoading] = useState<boolean>(true);
  const [listTotal, setListTotal] = useState<number>(0);
  const [listTotalAmount, setListTotalAmount] = useState<number>(0);
  const [listPage, setListPage] = useState<number>(1);
  const [listTotalPages, setListTotalPages] = useState<number>(1);

  // List Filters
  const [filterCompany, setFilterCompany] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("");
  const [filterParty, setFilterParty] = useState<string>("");
  const [filterFromDate, setFilterFromDate] = useState<string>("");
  const [filterToDate, setFilterToDate] = useState<string>("");

  // Modals
  // 1. View Voucher Modal
  const [viewModalOpen, setViewModalOpen] = useState<boolean>(false);
  const [viewVoucherData, setViewVoucherData] = useState<{
    voucher: JournalVoucherItem;
    lines: JournalVoucherLine[];
    company_name?: string;
    creator_name?: string;
    is_compound?: boolean;
  } | null>(null);
  const [viewLoading, setViewLoading] = useState<boolean>(false);

  // 2. Edit Voucher Modal
  const [editModalOpen, setEditModalOpen] = useState<boolean>(false);
  const [editLoading, setEditLoading] = useState<boolean>(false);
  const [editError, setEditError] = useState<string>("");
  const [editVoucherId, setEditVoucherId] = useState<number | null>(null);
  const [editFields, setEditFields] = useState({
    voucherNumber: "",
    voucherType: "PAYMENT",
    date: "",
    amount: "",
    drType: "BANK",
    drName: "",
    crType: "BANK",
    crName: "",
    payMode: "",
    refNum: "",
    partyType: "EXTERNAL",
    partyName: "",
    mainCat: "",
    subCat: "",
    narration: ""
  });
  const [editBankAccounts, setEditBankAccounts] = useState<BankAccount[]>([]);
  const [editDrDropOpen, setEditDrDropOpen] = useState<"BANK" | "PARTY" | null>(null);
  const [editCrDropOpen, setEditCrDropOpen] = useState<"BANK" | "PARTY" | null>(null);
  const [editPartyResults, setEditPartyResults] = useState<PartySearchResult[]>([]);

  // 3. Cancel / Delete Modal
  const [cancelModalOpen, setCancelModalOpen] = useState<boolean>(false);
  const [cancelJvId, setCancelJvId] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState<string>("");
  const [cancelLoading, setCancelLoading] = useState<boolean>(false);

  // 4. Quick Add Party Modal
  const [addPartyModalOpen, setAddPartyModalOpen] = useState<boolean>(false);
  const [apStep, setApStep] = useState<1 | 2>(1);
  const [apType, setApType] = useState<"VENDOR" | "EXTERNAL" | "PARTNER">("VENDOR");
  const [apVendorTab, setApVendorTab] = useState<"basic" | "contacts" | "address" | "bank">("basic");
  const [apSelectedCos, setApSelectedCos] = useState<{ id: number; name: string }[]>([]);
  const [apError, setApError] = useState<string>("");
  const [apSuccess, setApSuccess] = useState<string>("");
  const [apLoading, setApLoading] = useState<boolean>(false);

  // Vendor Form Data
  const [vendorForm, setVendorForm] = useState({
    vendor_name: "",
    vendor_code: "",
    vendor_type: "BOTH",
    phone: "",
    email: "",
    gst_number: "",
    pan_number: "",
    gst_type: "CGST_SGST",
    contact_person_1_name: "",
    contact_person_1_phone: "",
    contact_person_1_designation: "",
    contact_person_2_name: "",
    contact_person_2_phone: "",
    contact_person_2_designation: "",
    website_url: "",
    address: "",
    pincode: "",
    city: "",
    state: "",
    map_link_1_label: "",
    map_link_1: "",
    map_link_2_label: "",
    map_link_2: "",
    ship_to_address: "",
    ship_to_pincode: "",
    ship_to_city: "",
    ship_to_state: "",
    bank_name: "",
    bank_branch: "",
    account_number: "",
    ifsc_code: "",
    account_holder_name: "",
    upi_id: "",
    payment_terms: "COD",
    credit_limit: "0",
    credit_days: "0",
    terms_conditions: ""
  });

  // External Party Form Data
  const [extPartyForm, setExtPartyForm] = useState({
    name: "",
    phone: "",
    email: "",
    notes: ""
  });

  // 5. External Phone Prompt Mini Modal
  const [extPhoneModalOpen, setExtPhoneModalOpen] = useState<boolean>(false);
  const [extPhoneSide, setExtPhoneSide] = useState<"dr" | "cr" | "comp">("dr");
  const [extPhoneCompRowId, setExtPhoneCompRowId] = useState<string>("");
  const [extPhoneName, setExtPhoneName] = useState<string>("");
  const [extPhoneVal, setExtPhoneVal] = useState<string>("");
  const [extPhoneError, setExtPhoneError] = useState<string>("");
  const [extPhoneLoading, setExtPhoneLoading] = useState<boolean>(false);

  // 6. Quick Create Ledger Modal
  const [qclModalOpen, setQclModalOpen] = useState<boolean>(false);
  const [qclSide, setQclSide] = useState<"dr" | "cr">("dr");
  const [qclCompany, setQclCompany] = useState<string>("");
  const [qclType, setQclType] = useState<string>("EXPENSE");
  const [qclName, setQclName] = useState<string>("");
  const [qclGroup, setQclGroup] = useState<string>("Indirect Expenses");
  const [qclOB, setQclOB] = useState<string>("");
  const [qclOBType, setQclOBType] = useState<"DEBIT" | "CREDIT">("DEBIT");
  const [qclOBDate, setQclOBDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [qclError, setQclError] = useState<string>("");
  const [qclSuccess, setQclSuccess] = useState<string>("");
  const [qclLoading, setQclLoading] = useState<boolean>(false);

  // 7. Quick Add Expense Category Modal
  const [expCatModalOpen, setExpCatModalOpen] = useState<boolean>(false);
  const [ecqaMode, setEcqaMode] = useState<"sub" | "main">("sub");
  const [ecqaMainName, setEcqaMainName] = useState<string>("");
  const [ecqaParentId, setEcqaParentId] = useState<string>("");
  const [ecqaSubName, setEcqaSubName] = useState<string>("");
  const [ecqaLoading, setEcqaLoading] = useState<boolean>(false);

  // Debounce references
  const partySearchSeq = useRef(0);
  const ledgerSearchSeq = useRef(0);

  // ----------------------------------------------------
  // Initialization & Data Fetching
  // ----------------------------------------------------
  useEffect(() => {
    loadCompanies();
    loadCategories();
  }, []);

  useEffect(() => {
    loadVouchers(1);
  }, [filterCompany, filterType, activeTab]);

  const loadCompanies = async () => {
    try {
      const resp = await api.get("/staff/accounts/companies?page_size=100");
      const d = resp.data || {};
      const cos: Company[] = d.companies || d.items || (Array.isArray(d) ? d : []);
      setCompanies(cos);
      const cmap: Record<number, string> = {};
      cos.forEach((c) => {
        cmap[c.id] = c.company_name || c.name || `Company ${c.id}`;
      });
      setCompanyMap(cmap);
      if (cos.length > 0 && !companyId) {
        setCompanyId(String(cos[0].id));
      }
    } catch (e) {
      console.warn("Failed to load companies:", e);
    }
  };

  const loadCategories = async () => {
    try {
      const resp = await api.get("/expense-categories/list");
      const d = resp.data || {};
      setMainCats(d.main_categories || []);
      setSubCats(d.sub_categories || []);
      setIncMainCats(d.income_main_categories || []);
      setIncSubCats(d.income_sub_categories || []);
    } catch (e) {
      console.warn("Failed to load categories:", e);
    }
  };

  // When company changes, refresh bank accounts and invoice links
  useEffect(() => {
    if (!companyId) {
      setBankAccounts([]);
      setOpenInvoices([]);
      setSelectedInvoice(null);
      return;
    }
    loadBankAccounts(companyId);
    if (VT_PRESETS[vtype].showInvoice) {
      loadOpenInvoices(companyId, vtype, selectedParty?.id);
    }
  }, [companyId, vtype]);

  const loadBankAccounts = async (cid: string) => {
    try {
      const resp = await api.get(
        `/staff/accounts/ledger-masters?account_type=BANK&company_id=${cid}&page_size=500&is_active=true`
      );
      const items = (resp.data.masters || []).map((b: any) => ({
        id: b.id,
        account_name: b.account_name,
        bank_name: b.bank_name || b.group_name,
        account_number: b.account_number,
        account_type: b.account_type,
        ifsc_code: b.ifsc_code,
        branch: b.parent_group || null,
        is_primary: b.is_primary || false
      }));
      setBankAccounts(items);
    } catch (e) {
      setBankAccounts([]);
    }
  };

  const loadOpenInvoices = async (cid: string, currentVType: VoucherType, partyId?: any) => {
    if (!cid) return;
    const preset = VT_PRESETS[currentVType];
    if (!preset.showInvoice) {
      setOpenInvoices([]);
      setSelectedInvoice(null);
      return;
    }

    setInvoiceLinkLoading(true);
    try {
      if (preset.invoiceType === "PURCHASE") {
        let url = `/staff/accounts/journal-vouchers/open-purchases?company_id=${cid}`;
        if (partyId && typeof partyId === "number") {
          url += `&vendor_id=${partyId}`;
        }
        const resp = await api.get(url);
        const list = (resp.data?.purchases || []).map((x: any) => ({
          value: x.id,
          label: x.label || `PO #${x.id} - ₹${x.balance_due}`,
          balance: Number(x.balance_due) || 0,
          docType: "PURCHASE" as const
        }));
        setOpenInvoices(list);
      } else {
        const partyNameQuery = selectedParty?.name || crName || drName;
        let url = `/staff/accounts/journal-vouchers/open-sales?company_id=${cid}`;
        if (partyNameQuery) {
          url += `&party_name=${encodeURIComponent(partyNameQuery)}`;
        }
        const resp = await api.get(url);
        const list = (resp.data?.sales || []).map((x: any) => ({
          value: x.id,
          label: x.label || `Invoice #${x.id} - ₹${x.balance_due}`,
          balance: Number(x.balance_due) || 0,
          docType: "SALE" as const
        }));
        setOpenInvoices(list);
      }
    } catch (e) {
      setOpenInvoices([]);
    } finally {
      setInvoiceLinkLoading(false);
    }
  };

  // ----------------------------------------------------
  // Voucher List Fetching
  // ----------------------------------------------------
  const loadVouchers = async (page = 1) => {
    setListPage(page);
    setListLoading(true);
    try {
      let url = `/staff/accounts/journal-vouchers?page=${page}&page_size=30&status=${activeTab}`;
      if (filterCompany) url += `&company_id=${filterCompany}`;
      if (filterType) url += `&voucher_type=${filterType}`;
      if (filterParty) url += `&party_name=${encodeURIComponent(filterParty)}`;
      if (filterFromDate) url += `&date_from=${filterFromDate}`;
      if (filterToDate) url += `&date_to=${filterToDate}`;

      const resp = await api.get(url);
      const d = resp.data || {};
      setVouchers(d.vouchers || []);
      setListTotal(d.total || 0);
      setListTotalAmount(d.total_amount || 0);
      setListTotalPages(d.total_pages || 1);
    } catch (e: any) {
      console.error("Failed to load journal vouchers:", e);
      setVouchers([]);
    } finally {
      setListLoading(false);
    }
  };

  // ----------------------------------------------------
  // Live Auto-Narration
  // ----------------------------------------------------
  useEffect(() => {
    if (autoNarrationDirty) return;
    if (compoundMode) {
      const drNames = compoundLines
        .filter((l) => l.entry_type === "DEBIT" && l.account_name.trim())
        .map((l) => l.account_name.trim());
      const crNames = compoundLines
        .filter((l) => l.entry_type === "CREDIT" && l.account_name.trim())
        .map((l) => l.account_name.trim());
      if (!drNames.length && !crNames.length) return;

      const formatNames = (names: string[]) =>
        names.slice(0, 2).join(", ") + (names.length > 2 ? ` +${names.length - 2} more` : "");
      const totalDr = compoundLines
        .filter((l) => l.entry_type === "DEBIT")
        .reduce((sum, l) => sum + (parseFloat(l.amount) || 0), 0);
      const amtFmt = totalDr ? ` | ₹${totalDr.toLocaleString("en-IN")}` : "";
      const vtLabel = vtype === "JOURNAL" ? "Journal" : vtype;
      setNarration(
        `${vtLabel} | ${drNames.length ? formatNames(drNames) : "—"} → ${
          crNames.length ? formatNames(crNames) : "—"
        }${amtFmt}`
      );
      return;
    }

    const party = selectedParty?.name || crName || drName;
    const amtFmt = amount ? `₹${parseFloat(amount).toLocaleString("en-IN")}` : "";
    const modePart = payMode ? ` | ${payMode}` : "";

    let text = "";
    switch (vtype) {
      case "PAYMENT": {
        const staffLabels: Record<string, string> = {
          SALARY: "Salary",
          INCENTIVE: "Incentive",
          CONVEYANCE: "Conveyance",
          TRAVEL: "Travel Allowance",
          ADVANCE: "Advance",
          REIMBURSEMENT: "Reimbursement",
          OTHER: "Staff Payment"
        };
        const catLabel = staffLabels[staffPayType] || "";
        const sName = selectedParty?.name || "";
        if (catLabel && sName) {
          text = `${catLabel} to ${sName}${modePart}${amtFmt ? " | " + amtFmt : ""}`;
        } else {
          text = `Payment to ${crName || party}${drName ? " from " + drName : ""}${modePart}${
            amtFmt ? " | " + amtFmt : ""
          }`;
        }
        break;
      }
      case "RECEIPT":
        text = `Receipt from ${drName || party}${crName ? " to " + crName : ""}${modePart}${
          amtFmt ? " | " + amtFmt : ""
        }`;
        break;
      case "CONTRA":
        text = `Bank transfer ${drName} → ${crName}${amtFmt ? " | " + amtFmt : ""}`;
        break;
      default:
        text = `Journal | ${drName} → ${crName}${amtFmt ? " | " + amtFmt : ""}`;
    }
    if (text.trim()) setNarration(text.trim());
  }, [
    vtype,
    compoundMode,
    drName,
    crName,
    amount,
    payMode,
    selectedParty,
    staffPayType,
    compoundLines,
    autoNarrationDirty
  ]);

  // ----------------------------------------------------
  // Voucher Type Switching
  // ----------------------------------------------------
  const handleSelectVType = (t: VoucherType) => {
    setVtype(t);
    const p = VT_PRESETS[t];
    setDrType(p.drType);
    setCrType(p.crType);

    if (t === "CONTRA") {
      setSelectedParty(null);
      setDrConfirmedParty(null);
      setCrConfirmedParty(null);
    }

    // Reset compound rows to match new type
    setCompoundLines([
      { id: "dr-1", entry_type: "DEBIT", account_type: p.drType, account_name: "", amount: "" },
      { id: "dr-2", entry_type: "DEBIT", account_type: p.drType, account_name: "", amount: "" },
      { id: "cr-1", entry_type: "CREDIT", account_type: p.crType, account_name: "", amount: "" },
      { id: "cr-2", entry_type: "CREDIT", account_type: p.crType, account_name: "", amount: "" }
    ]);
  };

  // ----------------------------------------------------
  // Autocomplete & Search Logic
  // ----------------------------------------------------
  const searchParties = async (q: string) => {
    if (!q || q.trim().length < 2) {
      setPartySearchResults([]);
      return;
    }
    setPartySearchLoading(true);
    const seq = ++partySearchSeq.current;
    try {
      const resp = await api.get(
        `/staff/accounts/party-search?q=${encodeURIComponent(q.trim())}&company_id=${companyId}&limit=30`
      );
      if (seq === partySearchSeq.current) {
        setPartySearchResults(resp.data?.results || []);
      }
    } catch (e) {
      if (seq === partySearchSeq.current) setPartySearchResults([]);
    } finally {
      if (seq === partySearchSeq.current) setPartySearchLoading(false);
    }
  };

  const searchLedgers = async (type: string, q: string) => {
    if (!companyId) return;
    const cacheKey = `${companyId}:${type}`;
    if (ledgerCache[cacheKey]) {
      const filtered = ledgerCache[cacheKey].filter(
        (m) =>
          m.account_name.toLowerCase().includes(q.toLowerCase()) ||
          (m.group_name && m.group_name.toLowerCase().includes(q.toLowerCase()))
      );
      setLedgerSearchResults(filtered);
      return;
    }

    setLedgerSearchLoading(true);
    const seq = ++ledgerSearchSeq.current;
    try {
      const resp = await api.get(
        `/staff/accounts/ledger-masters?account_type=${type}&company_id=${companyId}&page_size=500&is_active=true`
      );
      if (seq === ledgerSearchSeq.current) {
        const masters: LedgerMaster[] = resp.data.masters || [];
        setLedgerCache((prev) => ({ ...prev, [cacheKey]: masters }));
        const filtered = masters.filter(
          (m) =>
            m.account_name.toLowerCase().includes(q.toLowerCase()) ||
            (m.group_name && m.group_name.toLowerCase().includes(q.toLowerCase()))
        );
        setLedgerSearchResults(filtered);
      }
    } catch (e) {
      if (seq === ledgerSearchSeq.current) setLedgerSearchResults([]);
    } finally {
      if (seq === ledgerSearchSeq.current) setLedgerSearchLoading(false);
    }
  };

  const handleNameInput = (side: "dr" | "cr", val: string) => {
    const type = side === "dr" ? drType : crType;
    if (side === "dr") {
      setDrName(val);
      if (type === "PARTY") setDrConfirmedParty(null);
    } else {
      setCrName(val);
      if (type === "PARTY") setCrConfirmedParty(null);
    }

    if (type === "BANK" || type === "UPI" || type === "CASH") {
      if (side === "dr") setDrDropOpen("BANK");
      else setCrDropOpen("BANK");
    } else if (type === "PARTY") {
      if (side === "dr") setDrDropOpen("PARTY");
      else setCrDropOpen("PARTY");
      searchParties(val);
    } else {
      if (side === "dr") setDrDropOpen("LEDGER");
      else setCrDropOpen("LEDGER");
      searchLedgers(type, val);
    }
  };

  const selectParty = (side: "dr" | "cr", p: PartySearchResult) => {
    if (side === "dr") {
      setDrName(p.name);
      setDrConfirmedParty({ id: p.id, name: p.name });
      setDrDropOpen(null);
    } else {
      setCrName(p.name);
      setCrConfirmedParty({ id: p.id, name: p.name });
      setCrDropOpen(null);
    }
    setSelectedParty({ id: p.id, name: p.name, type: p.type || "EXTERNAL" });

    // If STAFF selected on PAYMENT, open staff pay section
    if (p.type === "STAFF" && vtype === "PAYMENT") {
      setStaffPayType("SALARY");
      setDrType("EXPENSE");
      setDrName("Salary Expense");
    }

    // Auto-load invoice links if appropriate
    if (vtype === "PAYMENT" && side === "dr") {
      loadOpenInvoices(companyId, vtype, p.id);
    } else if (vtype === "RECEIPT" && side === "cr") {
      loadOpenInvoices(companyId, vtype, p.id);
    }
  };

  const handleStaffPayCatChange = (cat: string) => {
    setStaffPayType(cat);
    const info = STAFF_PAY_HEADS[cat];
    if (!info) return;

    if (info.isAdvance) {
      setDrType("PARTY");
      if (selectedParty?.name) setDrName(selectedParty.name);
    } else {
      const headName =
        cat === "OTHER" ? staffPayOtherHead.trim() || "Staff Expense" : info.head || "Staff Expense";
      setDrType("EXPENSE");
      setDrName(headName);
    }
  };

  // Payment Mode Auto-Adjust
  const handlePayModeChange = (mode: string) => {
    setPayMode(mode);
    if (mode === "CASH" && vtype === "PAYMENT") {
      if (crType === "BANK" || crType === "UPI") {
        setCrType("CASH");
        setCrName("Cash Account");
      }
    } else if (mode !== "CASH" && vtype === "PAYMENT") {
      if (crType === "CASH" && crName === "Cash Account") {
        setCrType("BANK");
        setCrName("");
      }
    }
  };

  // ----------------------------------------------------
  // Compound Mode Calculations
  // ----------------------------------------------------
  const compoundDebitTotal = useMemo(() => {
    return compoundLines
      .filter((l) => l.entry_type === "DEBIT")
      .reduce((sum, l) => sum + (parseFloat(l.amount) || 0), 0);
  }, [compoundLines]);

  const compoundCreditTotal = useMemo(() => {
    return compoundLines
      .filter((l) => l.entry_type === "CREDIT")
      .reduce((sum, l) => sum + (parseFloat(l.amount) || 0), 0);
  }, [compoundLines]);

  const compoundDiff = Math.abs(compoundDebitTotal - compoundCreditTotal);
  const isCompoundBalanced =
    compoundDebitTotal > 0 && compoundCreditTotal > 0 && compoundDiff < 0.01;

  const addCompoundLine = (type: "DEBIT" | "CREDIT") => {
    const id = `${type.toLowerCase()}-${Date.now()}`;
    const preset = VT_PRESETS[vtype];
    const defaultType = type === "DEBIT" ? preset.drType : preset.crType;
    setCompoundLines((prev) => [
      ...prev,
      { id, entry_type: type, account_type: defaultType, account_name: "", amount: "" }
    ]);
  };

  const removeCompoundLine = (id: string) => {
    setCompoundLines((prev) => prev.filter((l) => l.id !== id));
  };

  const updateCompoundLine = (id: string, field: keyof CompoundRow, value: string) => {
    setCompoundLines((prev) =>
      prev.map((l) => {
        if (l.id === id) {
          const updated = { ...l, [field]: value };
          if (field === "account_type") updated.account_name = "";
          return updated;
        }
        return l;
      })
    );
  };

  // ----------------------------------------------------
  // Form Submission
  // ----------------------------------------------------
  const resetForm = () => {
    setVoucherDate(new Date().toISOString().slice(0, 10));
    setDrName("");
    setCrName("");
    setAmount("");
    setPayMode("");
    setRefNum("");
    setNarration("");
    setAutoNarrationDirty(false);
    setSelectedParty(null);
    setDrConfirmedParty(null);
    setCrConfirmedParty(null);
    setStaffPayType("");
    setStaffPayOtherHead("");
    setSelectedInvoice(null);
    setSelectedMainCat("");
    setSelectedSubCat("");
    setFormSuccess("");
    setFormError("");
    setCompoundLines([
      { id: "dr-1", entry_type: "DEBIT", account_type: "EXPENSE", account_name: "", amount: "" },
      { id: "dr-2", entry_type: "DEBIT", account_type: "EXPENSE", account_name: "", amount: "" },
      { id: "cr-1", entry_type: "CREDIT", account_type: "BANK", account_name: "", amount: "" },
      { id: "cr-2", entry_type: "CREDIT", account_type: "BANK", account_name: "", amount: "" }
    ]);
    handleSelectVType("PAYMENT");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    setFormSuccess("");

    if (!companyId) {
      setFormError("Please select a company.");
      return;
    }
    if (!voucherDate) {
      setFormError("Please select a date.");
      return;
    }
    if (!narration.trim()) {
      setFormError("Please enter a narration / description.");
      return;
    }

    // Compound Mode Posting
    if (compoundMode) {
      const drLines = compoundLines.filter((l) => l.entry_type === "DEBIT" && l.account_name.trim());
      const crLines = compoundLines.filter((l) => l.entry_type === "CREDIT" && l.account_name.trim());

      if (!drLines.length) {
        setFormError("Please add at least one DR (Debit) line with an account name.");
        return;
      }
      if (!crLines.length) {
        setFormError("Please add at least one CR (Credit) line with an account name.");
        return;
      }
      if (!isCompoundBalanced) {
        setFormError(
          `Voucher is unbalanced! DR Total (₹${compoundDebitTotal.toFixed(
            2
          )}) must equal CR Total (₹${compoundCreditTotal.toFixed(2)}).`
        );
        return;
      }

      setPosting(true);
      try {
        const linesPayload = [
          ...drLines.map((l) => ({
            entry_type: "DEBIT",
            account_type: l.account_type,
            account_name: l.account_name.trim(),
            amount: parseFloat(l.amount) || 0
          })),
          ...crLines.map((l) => ({
            entry_type: "CREDIT",
            account_type: l.account_type,
            account_name: l.account_name.trim(),
            amount: parseFloat(l.amount) || 0
          }))
        ];

        const isIncomeCat = selectedSubCat.startsWith("inc_");
        const category_id = isIncomeCat ? null : parseInt(selectedSubCat) || null;
        const income_category_id = isIncomeCat
          ? parseInt(selectedSubCat.replace("inc_", "")) || null
          : null;

        const payload = {
          company_id: parseInt(companyId),
          voucher_date: voucherDate,
          voucher_type: vtype,
          lines: linesPayload,
          narration: narration.trim(),
          payment_mode: payMode || null,
          reference_number: refNum.trim() || null,
          category_id,
          income_category_id
        };

        const resp = await api.post("/staff/accounts/journal-vouchers", payload);
        const vnum = resp.data?.voucher?.voucher_number || "JV";
        setFormSuccess(
          `Compound Voucher ${vnum} posted successfully! ${linesPayload.length} ledger entries created.`
        );
        resetForm();
        loadVouchers(1);
      } catch (err: any) {
        setFormError(
          err.response?.data?.detail || err.response?.data?.message || err.message || "Failed to post compound voucher."
        );
      } finally {
        setPosting(false);
      }
      return;
    }

    // Simple Mode Posting
    if (!drName.trim()) {
      setFormError("Please enter or select the Debit (DR) account name.");
      return;
    }
    if (!crName.trim()) {
      setFormError("Please enter or select the Credit (CR) account name.");
      return;
    }
    const numAmt = parseFloat(amount);
    if (!numAmt || numAmt <= 0) {
      setFormError("Please enter a valid positive amount.");
      return;
    }

    // Party confirmation check on Payment/Journal
    if (vtype !== "RECEIPT") {
      if (drType === "PARTY" && drName && !drConfirmedParty) {
        setFormError(
          "Please pick the Debit party from the dropdown suggestions or click 'Use as external party'."
        );
        return;
      }
      if (crType === "PARTY" && crName && !crConfirmedParty) {
        setFormError(
          "Please pick the Credit party from the dropdown suggestions or click 'Use as external party'."
        );
        return;
      }
    }

    setPosting(true);
    try {
      const isIncomeCat = selectedSubCat.startsWith("inc_");
      const category_id = isIncomeCat ? null : parseInt(selectedSubCat) || null;
      const income_category_id = isIncomeCat
        ? parseInt(selectedSubCat.replace("inc_", "")) || null
        : null;

      const party_name =
        selectedParty?.name ||
        (drType === "PARTY" ? drName : "") ||
        (crType === "PARTY" ? crName : "");
      const party_type = selectedParty?.type || "EXTERNAL";
      const rawPid = selectedParty?.id ? String(selectedParty.id) : "";
      const party_id = rawPid.startsWith("MP:")
        ? parseInt(rawPid.slice(3)) || null
        : rawPid && /^\d+$/.test(rawPid)
        ? parseInt(rawPid)
        : null;

      const payload: any = {
        company_id: parseInt(companyId),
        voucher_date: voucherDate,
        voucher_type: vtype,
        dr_account_type: drType,
        dr_account_name: drName.trim(),
        cr_account_type: crType,
        cr_account_name: crName.trim(),
        amount: numAmt,
        narration: narration.trim(),
        payment_mode: payMode || null,
        reference_number: refNum.trim() || null,
        category_id,
        income_category_id
      };

      if (party_name) {
        payload.party_name = party_name;
        payload.party_type = party_type;
        if (party_id) payload.party_id = party_id;
      }

      if (selectedInvoice) {
        payload.linked_doc_type = selectedInvoice.docType;
        payload.linked_doc_id = selectedInvoice.value;
      }

      const resp = await api.post("/staff/accounts/journal-vouchers", payload);
      const vnum = resp.data?.voucher?.voucher_number || "JV";
      setFormSuccess(`Voucher ${vnum} posted successfully! All ledger entries have been updated.`);
      resetForm();
      loadVouchers(1);
    } catch (err: any) {
      setFormError(
        err.response?.data?.detail || err.response?.data?.message || err.message || "Failed to post voucher."
      );
    } finally {
      setPosting(false);
    }
  };

  // ----------------------------------------------------
  // View Voucher Details Modal
  // ----------------------------------------------------
  const handleOpenViewModal = async (id: number) => {
    setViewModalOpen(true);
    setViewLoading(true);
    try {
      const resp = await api.get(`/staff/accounts/journal-vouchers/${id}`);
      const d = resp.data || {};
      setViewVoucherData({
        voucher: d.voucher,
        lines: d.lines || [],
        company_name: d.company_name || companyMap[d.voucher?.company_id],
        creator_name: d.creator_name || "Staff",
        is_compound: d.is_compound
      });
    } catch (e) {
      console.error("Failed to load voucher details:", e);
    } finally {
      setViewLoading(false);
    }
  };

  // ----------------------------------------------------
  // Edit Voucher Modal
  // ----------------------------------------------------
  const handleOpenEditModal = async (v: JournalVoucherItem) => {
    setEditVoucherId(v.id);
    setEditError("");
    setEditFields({
      voucherNumber: v.voucher_number,
      voucherType: v.voucher_type,
      date: v.voucher_date || "",
      amount: String(v.amount || ""),
      drType: v.dr_account_type || "BANK",
      drName: v.dr_account_name || "",
      crType: v.cr_account_type || "BANK",
      crName: v.cr_account_name || "",
      payMode: v.payment_mode || "",
      refNum: v.reference_number || "",
      partyType: v.party_type || "EXTERNAL",
      partyName: v.party_name || "",
      mainCat: "",
      subCat: "",
      narration: v.narration || ""
    });

    if (v.company_id) {
      try {
        const resp = await api.get(
          `/staff/accounts/ledger-masters?account_type=BANK&company_id=${v.company_id}&page_size=500&is_active=true`
        );
        setEditBankAccounts(resp.data?.masters || []);
      } catch (e) {}
    }

    setEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editVoucherId) return;
    setEditLoading(true);
    setEditError("");
    try {
      const isIncome = editFields.subCat.startsWith("inc_");
      const category_id = isIncome ? null : parseInt(editFields.subCat) || null;
      const income_category_id = isIncome
        ? parseInt(editFields.subCat.replace("inc_", "")) || null
        : null;

      const payload = {
        voucher_date: editFields.date,
        amount: parseFloat(editFields.amount),
        dr_account_type: editFields.drType,
        dr_account_name: editFields.drName.trim(),
        cr_account_type: editFields.crType,
        cr_account_name: editFields.crName.trim(),
        payment_mode: editFields.payMode || null,
        reference_number: editFields.refNum.trim() || null,
        party_type: editFields.partyType || null,
        party_name: editFields.partyName.trim() || null,
        narration: editFields.narration.trim() || null,
        category_id,
        income_category_id
      };

      const resp = await api.put(`/staff/accounts/journal-vouchers/${editVoucherId}`, payload);
      if (resp.data.success || resp.status === 200) {
        setEditModalOpen(false);
        loadVouchers(listPage);
      } else {
        throw new Error(resp.data.message || "Failed to update voucher");
      }
    } catch (e: any) {
      setEditError(e.response?.data?.detail || e.message || "Save failed.");
    } finally {
      setEditLoading(false);
    }
  };

  // ----------------------------------------------------
  // Cancel / Delete Voucher Modal
  // ----------------------------------------------------
  const handleOpenCancelModal = (id: number) => {
    setCancelJvId(id);
    setCancelReason("");
    setCancelModalOpen(true);
  };

  const handleConfirmCancel = async () => {
    if (!cancelJvId) return;
    setCancelLoading(true);
    try {
      await api.post(`/staff/accounts/journal-vouchers/${cancelJvId}/cancel`, {
        cancel_reason: cancelReason.trim() || "Cancelled by user"
      });
      setCancelModalOpen(false);
      loadVouchers(listPage);
    } catch (e: any) {
      alert("Error deleting voucher: " + (e.response?.data?.detail || e.message));
    } finally {
      setCancelLoading(false);
    }
  };

  // ----------------------------------------------------
  // Quick Party Prompts & Submissions
  // ----------------------------------------------------
  const promptExternalPartyPhone = (side: "dr" | "cr" | "comp", name: string, compRowId?: string) => {
    setExtPhoneSide(side);
    setExtPhoneName(name);
    setExtPhoneCompRowId(compRowId || "");
    setExtPhoneVal("");
    setExtPhoneError("");
    setExtPhoneModalOpen(true);
  };

  const handleSaveExternalPhone = async () => {
    if (!extPhoneVal.trim()) {
      setExtPhoneError("Mobile number is required.");
      return;
    }
    setExtPhoneLoading(true);
    try {
      const resp = await api.post("/staff/accounts/party-search/add-manual", {
        name: extPhoneName.trim(),
        phone: extPhoneVal.trim()
      });
      const savedParty = resp.data;
      if (extPhoneSide === "comp") {
        updateCompoundLine(extPhoneCompRowId, "account_name", extPhoneName.trim());
      } else {
        selectParty(extPhoneSide, {
          id: savedParty.id || 0,
          name: extPhoneName.trim(),
          type: "EXTERNAL",
          phone: extPhoneVal.trim()
        });
      }
      setExtPhoneModalOpen(false);
    } catch (e: any) {
      setExtPhoneError("Failed to save external party.");
    } finally {
      setExtPhoneLoading(false);
    }
  };

  const handlePincodeLookup = async (pincode: string, isVendorShip = false) => {
    if (pincode.length !== 6) return;
    try {
      const resp = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
      const data = await resp.json();
      if (data[0]?.Status === "Success") {
        const po = data[0].PostOffice[0];
        if (isVendorShip) {
          setVendorForm((prev) => ({
            ...prev,
            ship_to_city: prev.ship_to_city || po.Division || po.Name || "",
            ship_to_state: prev.ship_to_state || po.State || ""
          }));
        } else {
          setVendorForm((prev) => ({
            ...prev,
            city: prev.city || po.Division || po.Name || "",
            state: prev.state || po.State || ""
          }));
        }
      }
    } catch (e) {}
  };

  const handleSubmitVendor = async () => {
    if (!vendorForm.vendor_name.trim()) {
      setApError("Vendor name is required.");
      return;
    }
    if (!vendorForm.vendor_code.trim()) {
      setApError("Vendor code is required.");
      return;
    }
    if (!apSelectedCos.length) {
      setApError("Please select at least one applicable company.");
      return;
    }

    setApLoading(true);
    setApError("");
    try {
      const payload = {
        ...vendorForm,
        credit_limit: parseFloat(vendorForm.credit_limit) || 0,
        credit_days: parseInt(vendorForm.credit_days) || 0,
        applicable_companies: apSelectedCos.map((c) => c.id)
      };
      const resp = await api.post("/staff/accounts/vendors", payload);
      const v = resp.data?.vendor || resp.data;
      setApSuccess(`Vendor "${vendorForm.vendor_name}" created successfully!`);
      setTimeout(() => {
        setAddPartyModalOpen(false);
        selectParty("dr", {
          id: v.id || 0,
          name: v.vendor_name || vendorForm.vendor_name,
          type: "VENDOR"
        });
      }, 1000);
    } catch (e: any) {
      setApError(e.response?.data?.detail || e.message || "Failed to create vendor.");
    } finally {
      setApLoading(false);
    }
  };

  const handleSubmitExternalParty = async () => {
    if (!extPartyForm.name.trim()) {
      setApError("Name is required.");
      return;
    }
    if (!extPartyForm.phone.trim()) {
      setApError("Mobile number is required.");
      return;
    }

    setApLoading(true);
    setApError("");
    try {
      const resp = await api.post("/staff/accounts/party-search/add-manual", extPartyForm);
      const p = resp.data;
      setApSuccess(`External Party "${extPartyForm.name}" created!`);
      setTimeout(() => {
        setAddPartyModalOpen(false);
        selectParty("dr", {
          id: p.id || 0,
          name: extPartyForm.name,
          type: "EXTERNAL",
          phone: extPartyForm.phone
        });
      }, 1000);
    } catch (e: any) {
      setApError(e.response?.data?.detail || e.message || "Failed to save external party.");
    } finally {
      setApLoading(false);
    }
  };

  // ----------------------------------------------------
  // Quick Create Ledger Handler
  // ----------------------------------------------------
  const handleOpenQuickCreateLedger = (side: "dr" | "cr") => {
    setQclSide(side);
    setQclCompany(companyId);
    const sideType = side === "dr" ? drType : crType;
    setQclType(CREATABLE_LEDGER_TYPES.has(sideType) ? sideType : "EXPENSE");
    setQclGroup(QCL_GROUP_CHIPS[sideType]?.default || "Indirect Expenses");
    setQclName("");
    setQclOB("");
    setQclOBType("DEBIT");
    setQclOBDate(new Date().toISOString().slice(0, 10));
    setQclError("");
    setQclSuccess("");
    setQclModalOpen(true);
  };

  const handleSaveQuickLedger = async () => {
    if (!qclCompany) {
      setQclError("Please select a company.");
      return;
    }
    if (!qclName.trim()) {
      setQclError("Please enter an account name.");
      return;
    }

    setQclLoading(true);
    setQclError("");
    try {
      const payload = {
        company_id: parseInt(qclCompany),
        account_type: qclType,
        account_name: qclName.trim(),
        parent_group: qclGroup.trim() || null,
        opening_balance: parseFloat(qclOB) || 0,
        opening_balance_type: qclOBType,
        opening_balance_date: qclOBDate || null
      };
      const resp = await api.post("/staff/accounts/ledger-masters", payload);
      const created = resp.data?.master || {};
      const newName = created.account_name || qclName.trim();
      setQclSuccess(`✓ Account "${newName}" created successfully!`);

      // Clear cache for this company/type
      setLedgerCache((prev) => {
        const next = { ...prev };
        delete next[`${qclCompany}:${qclType}`];
        return next;
      });

      if (qclSide === "dr") {
        setDrName(newName);
      } else {
        setCrName(newName);
      }

      setTimeout(() => setQclModalOpen(false), 1000);
    } catch (e: any) {
      setQclError(e.response?.data?.detail || e.message || "Failed to create ledger.");
    } finally {
      setQclLoading(false);
    }
  };

  // ----------------------------------------------------
  // Quick Add Expense Category Handler
  // ----------------------------------------------------
  const handleSaveQuickCat = async () => {
    setEcqaLoading(true);
    try {
      if (ecqaMode === "main") {
        if (!ecqaMainName.trim()) {
          alert("Main category name is required");
          return;
        }
        await api.post("/expense-categories/main/create", { name: ecqaMainName.trim() });
      } else {
        if (!ecqaParentId) {
          alert("Please select a main category");
          return;
        }
        if (!ecqaSubName.trim()) {
          alert("Sub category name is required");
          return;
        }
        await api.post("/expense-categories/sub/create", {
          parent_id: parseInt(ecqaParentId),
          name: ecqaSubName.trim()
        });
      }
      await loadCategories();
      setExpCatModalOpen(false);
    } catch (e: any) {
      alert("Error saving category: " + (e.response?.data?.message || e.message));
    } finally {
      setEcqaLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 pb-16 font-sans antialiased text-slate-800">
      {/* ═══════════════════════════════════════════════════════════ */}
      {/* Header Bar */}
      {/* ═══════════════════════════════════════════════════════════ */}
      <header className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-slate-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-200">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Journal Vouchers & Entries</h1>
                <span className="bg-indigo-50 text-indigo-700 text-xs font-semibold px-2 py-0.5 rounded-full border border-indigo-100">
                  SFMS Double-Entry
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Post payment, receipt, contra, and journal entries — with bank selection, Tally F7 compound mode & invoice linking
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/staff/accounts/general-ledger"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 hover:text-indigo-600 transition shadow-2xs"
            >
              <Landmark className="w-4 h-4 text-slate-400" />
              General Ledger
            </Link>
            <button
              onClick={() => loadVouchers(listPage)}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
              title="Refresh vouchers list"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${listLoading ? "animate-spin text-indigo-600" : ""}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Alerts */}
        {formSuccess && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl p-4 flex items-start gap-3 shadow-xs animate-in fade-in">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-sm font-medium">{formSuccess}</div>
            <button onClick={() => setFormSuccess("")} className="text-emerald-500 hover:text-emerald-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {formError && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-4 flex items-start gap-3 shadow-xs animate-in fade-in">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-sm font-medium">{formError}</div>
            <button onClick={() => setFormError("")} className="text-rose-500 hover:text-rose-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════ */}
        {/* NEW VOUCHER ENTRY FORM CARD */}
        {/* ═══════════════════════════════════════════════════════════ */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-700">
                <Plus className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">New Voucher Entry</h2>
            </div>

            {/* Mode Switch: Simple vs Compound */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCompoundMode(!compoundMode)}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition border ${
                  compoundMode
                    ? "bg-purple-700 text-white border-purple-800 shadow-xs"
                    : "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100"
                }`}
              >
                <TableIcon className="w-3.5 h-3.5" />
                {compoundMode ? "Compound Mode Active" : "Compound Entry (Tally F7)"}
              </button>
              <span className="text-[11px] text-slate-500 hidden sm:inline">
                {compoundMode
                  ? "Multi-line DR & CR balanced voucher"
                  : "Switch for multiple debit/credit lines"}
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* 1. Voucher Type Selector */}
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5">
                Voucher Type
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  {
                    type: "PAYMENT" as const,
                    icon: "💸",
                    name: "Payment",
                    desc: "Bank / Cash → Person / Vendor"
                  },
                  {
                    type: "RECEIPT" as const,
                    icon: "💰",
                    name: "Receipt",
                    desc: "Person / Company → Bank / Cash"
                  },
                  {
                    type: "CONTRA" as const,
                    icon: "🔄",
                    name: "Contra",
                    desc: "Bank ↔ Bank / Cash transfer"
                  },
                  {
                    type: "JOURNAL" as const,
                    icon: "📓",
                    name: "Journal",
                    desc: "Manual adjustment entry"
                  }
                ].map((item) => {
                  const selected = vtype === item.type;
                  return (
                    <button
                      key={item.type}
                      type="button"
                      onClick={() => handleSelectVType(item.type)}
                      className={`p-3.5 rounded-xl border text-center transition flex flex-col items-center justify-center cursor-pointer ${
                        selected
                          ? "border-indigo-600 bg-indigo-50/70 shadow-xs ring-2 ring-indigo-500/20"
                          : "border-slate-200 bg-white hover:border-indigo-200 hover:bg-slate-50/70"
                      }`}
                    >
                      <span className="text-2xl mb-1">{item.icon}</span>
                      <span className={`text-xs font-bold ${selected ? "text-indigo-900" : "text-slate-800"}`}>
                        {item.name}
                      </span>
                      <span className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">{item.desc}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 2. Visual DR / CR Summary Card (Simple Mode) */}
            {!compoundMode && (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 sm:p-4 grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] items-center gap-3">
                <div className="bg-rose-50/80 border border-rose-200 rounded-lg p-3 text-center">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-rose-600">
                    DR (Debit — Money Goes To)
                  </div>
                  <div className="text-xs font-bold text-slate-900 mt-1 truncate">
                    {drName || VT_PRESETS[vtype].drHint}
                  </div>
                  <div className="text-[10px] font-semibold text-rose-500 mt-0.5">{drType}</div>
                </div>

                <div className="flex justify-center text-slate-400">
                  <ArrowRight className="w-5 h-5 hidden sm:block" />
                  <span className="sm:hidden text-xs font-bold">↓</span>
                </div>

                <div className="bg-emerald-50/80 border border-emerald-200 rounded-lg p-3 text-center">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                    CR (Credit — Money Comes From)
                  </div>
                  <div className="text-xs font-bold text-slate-900 mt-1 truncate">
                    {crName || VT_PRESETS[vtype].crHint}
                  </div>
                  <div className="text-[10px] font-semibold text-emerald-600 mt-0.5">{crType}</div>
                </div>
              </div>
            )}

            {/* 3. Company + Date Picker */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Company <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <select
                    value={companyId}
                    onChange={(e) => setCompanyId(e.target.value)}
                    required
                    className="w-full pl-3 pr-8 py-2.5 bg-white border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  >
                    <option value="">— Select Company —</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name || `Company ${c.id}`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Voucher Date <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="date"
                    value={voucherDate}
                    onChange={(e) => setVoucherDate(e.target.value)}
                    required
                    className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  />
                </div>
              </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════ */}
            {/* SIMPLE ENTRY MODE (1 DR + 1 CR) */}
            {/* ═══════════════════════════════════════════════════════════ */}
            {!compoundMode ? (
              <div className="space-y-4">
                {/* DR Account Selection */}
                <div className="relative">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <span className="bg-rose-100 text-rose-700 text-[10px] font-extrabold px-1.5 py-0.5 rounded">
                        DR
                      </span>
                      Debit Account (Where Money Goes) <span className="text-rose-500">*</span>
                    </label>
                    {CREATABLE_LEDGER_TYPES.has(drType) && (
                      <button
                        type="button"
                        onClick={() => handleOpenQuickCreateLedger("dr")}
                        className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" /> Create New Ledger
                      </button>
                    )}
                  </div>

                  <div className="flex flex-col sm:flex-row gap-2">
                    <select
                      value={drType}
                      onChange={(e) => {
                        setDrType(e.target.value);
                        setDrDropOpen(null);
                        if (e.target.value !== "PARTY") setSelectedParty(null);
                      }}
                      className="sm:w-44 px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-bold uppercase tracking-wider focus:ring-2 focus:ring-indigo-500/20"
                    >
                      {ACCOUNT_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>

                    <div className="flex-1 relative">
                      <input
                        type="text"
                        value={drName}
                        onChange={(e) => handleNameInput("dr", e.target.value)}
                        onFocus={() => handleNameInput("dr", drName)}
                        placeholder="Search or enter account name..."
                        autoComplete="off"
                        required
                        className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                      />

                      {/* Autocomplete Dropdowns for DR */}
                      {drDropOpen === "BANK" && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-blue-200 rounded-xl shadow-xl z-30 max-h-56 overflow-y-auto divide-y divide-slate-100">
                          {bankAccounts.length === 0 ? (
                            <div className="p-3 text-xs text-slate-500">No bank accounts found for company.</div>
                          ) : (
                            bankAccounts.map((b) => (
                              <div
                                key={b.id}
                                onMouseDown={() => {
                                  setDrName(b.account_name);
                                  setDrDropOpen(null);
                                }}
                                className="p-2.5 hover:bg-blue-50/70 cursor-pointer flex items-center justify-between"
                              >
                                <div>
                                  <div className="text-xs font-bold text-slate-800">{b.account_name}</div>
                                  <div className="text-[11px] text-slate-500 font-mono">
                                    {b.bank_name} {b.account_number ? `••••${b.account_number.slice(-4)}` : ""}
                                  </div>
                                </div>
                                {b.is_primary && (
                                  <span className="text-[9px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                    PRIMARY
                                  </span>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      )}

                      {drDropOpen === "PARTY" && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-purple-200 rounded-xl shadow-xl z-30 max-h-64 overflow-y-auto divide-y divide-slate-100">
                          {partySearchLoading ? (
                            <div className="p-3 text-xs text-slate-500 flex items-center gap-2">
                              <RefreshCw className="w-3.5 h-3.5 animate-spin text-purple-600" /> Searching parties...
                            </div>
                          ) : partySearchResults.length === 0 ? (
                            <div className="p-3">
                              <div className="text-xs text-slate-500 mb-2">No matching party found.</div>
                              <button
                                type="button"
                                onMouseDown={() => promptExternalPartyPhone("dr", drName)}
                                className="w-full text-left p-2 rounded-lg bg-purple-50 text-purple-700 text-xs font-bold hover:bg-purple-100 flex items-center gap-1.5"
                              >
                                <UserPlus className="w-3.5 h-3.5" /> Use &ldquo;{drName}&rdquo; as External Party
                              </button>
                            </div>
                          ) : (
                            partySearchResults.map((p) => {
                              const meta = PARTY_META[p.type] || PARTY_META.EXTERNAL;
                              return (
                                <div
                                  key={p.id + "-" + p.name}
                                  onMouseDown={() => selectParty("dr", p)}
                                  className="p-2.5 hover:bg-purple-50/70 cursor-pointer flex items-center justify-between gap-2"
                                >
                                  <div>
                                    <div className="text-xs font-bold text-slate-800">{p.name}</div>
                                    <div className="text-[10px] text-slate-500">
                                      {p.sub} {p.phone ? `· ${p.phone}` : ""}
                                    </div>
                                  </div>
                                  <span
                                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${meta.bg}`}
                                  >
                                    {meta.label}
                                  </span>
                                </div>
                              );
                            })
                          )}
                        </div>
                      )}

                      {drDropOpen === "LEDGER" && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-emerald-200 rounded-xl shadow-xl z-30 max-h-56 overflow-y-auto divide-y divide-slate-100">
                          {ledgerSearchLoading ? (
                            <div className="p-3 text-xs text-slate-500">Loading ledger accounts...</div>
                          ) : ledgerSearchResults.length === 0 ? (
                            <div className="p-3 text-xs text-slate-500">No ledger accounts found.</div>
                          ) : (
                            ledgerSearchResults.map((m) => (
                              <div
                                key={m.id}
                                onMouseDown={() => {
                                  setDrName(m.account_name);
                                  setDrDropOpen(null);
                                }}
                                className="p-2.5 hover:bg-emerald-50/70 cursor-pointer flex items-center justify-between"
                              >
                                <div>
                                  <div className="text-xs font-bold text-slate-800">{m.account_name}</div>
                                  {m.group_name && (
                                    <div className="text-[10px] text-slate-400">{m.group_name}</div>
                                  )}
                                </div>
                                {m.opening_balance !== undefined && (
                                  <span className="text-[10px] font-mono text-slate-500">
                                    ₹{Number(m.opening_balance).toLocaleString("en-IN")}
                                  </span>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* CR Account Selection */}
                <div className="relative">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <span className="bg-emerald-100 text-emerald-700 text-[10px] font-extrabold px-1.5 py-0.5 rounded">
                        CR
                      </span>
                      Credit Account (Where Money Comes From) <span className="text-rose-500">*</span>
                    </label>
                    {CREATABLE_LEDGER_TYPES.has(crType) && (
                      <button
                        type="button"
                        onClick={() => handleOpenQuickCreateLedger("cr")}
                        className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" /> Create New Ledger
                      </button>
                    )}
                  </div>

                  <div className="flex flex-col sm:flex-row gap-2">
                    <select
                      value={crType}
                      onChange={(e) => {
                        setCrType(e.target.value);
                        setCrDropOpen(null);
                        if (e.target.value !== "PARTY") setSelectedParty(null);
                      }}
                      className="sm:w-44 px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-bold uppercase tracking-wider focus:ring-2 focus:ring-indigo-500/20"
                    >
                      {ACCOUNT_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>

                    <div className="flex-1 relative">
                      <input
                        type="text"
                        value={crName}
                        onChange={(e) => handleNameInput("cr", e.target.value)}
                        onFocus={() => handleNameInput("cr", crName)}
                        placeholder="Search or enter account name..."
                        autoComplete="off"
                        required
                        className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                      />

                      {/* Autocomplete Dropdowns for CR */}
                      {crDropOpen === "BANK" && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-blue-200 rounded-xl shadow-xl z-30 max-h-56 overflow-y-auto divide-y divide-slate-100">
                          {bankAccounts.length === 0 ? (
                            <div className="p-3 text-xs text-slate-500">No bank accounts found for company.</div>
                          ) : (
                            bankAccounts.map((b) => (
                              <div
                                key={b.id}
                                onMouseDown={() => {
                                  setCrName(b.account_name);
                                  setCrDropOpen(null);
                                }}
                                className="p-2.5 hover:bg-blue-50/70 cursor-pointer flex items-center justify-between"
                              >
                                <div>
                                  <div className="text-xs font-bold text-slate-800">{b.account_name}</div>
                                  <div className="text-[11px] text-slate-500 font-mono">
                                    {b.bank_name} {b.account_number ? `••••${b.account_number.slice(-4)}` : ""}
                                  </div>
                                </div>
                                {b.is_primary && (
                                  <span className="text-[9px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                    PRIMARY
                                  </span>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      )}

                      {crDropOpen === "PARTY" && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-purple-200 rounded-xl shadow-xl z-30 max-h-64 overflow-y-auto divide-y divide-slate-100">
                          {partySearchLoading ? (
                            <div className="p-3 text-xs text-slate-500 flex items-center gap-2">
                              <RefreshCw className="w-3.5 h-3.5 animate-spin text-purple-600" /> Searching parties...
                            </div>
                          ) : partySearchResults.length === 0 ? (
                            <div className="p-3">
                              <div className="text-xs text-slate-500 mb-2">No matching party found.</div>
                              <button
                                type="button"
                                onMouseDown={() => promptExternalPartyPhone("cr", crName)}
                                className="w-full text-left p-2 rounded-lg bg-purple-50 text-purple-700 text-xs font-bold hover:bg-purple-100 flex items-center gap-1.5"
                              >
                                <UserPlus className="w-3.5 h-3.5" /> Use &ldquo;{crName}&rdquo; as External Party
                              </button>
                            </div>
                          ) : (
                            partySearchResults.map((p) => {
                              const meta = PARTY_META[p.type] || PARTY_META.EXTERNAL;
                              return (
                                <div
                                  key={p.id + "-" + p.name}
                                  onMouseDown={() => selectParty("cr", p)}
                                  className="p-2.5 hover:bg-purple-50/70 cursor-pointer flex items-center justify-between gap-2"
                                >
                                  <div>
                                    <div className="text-xs font-bold text-slate-800">{p.name}</div>
                                    <div className="text-[10px] text-slate-500">
                                      {p.sub} {p.phone ? `· ${p.phone}` : ""}
                                    </div>
                                  </div>
                                  <span
                                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${meta.bg}`}
                                  >
                                    {meta.label}
                                  </span>
                                </div>
                              );
                            })
                          )}
                        </div>
                      )}

                      {crDropOpen === "LEDGER" && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-emerald-200 rounded-xl shadow-xl z-30 max-h-56 overflow-y-auto divide-y divide-slate-100">
                          {ledgerSearchLoading ? (
                            <div className="p-3 text-xs text-slate-500">Loading ledger accounts...</div>
                          ) : ledgerSearchResults.length === 0 ? (
                            <div className="p-3 text-xs text-slate-500">No ledger accounts found.</div>
                          ) : (
                            ledgerSearchResults.map((m) => (
                              <div
                                key={m.id}
                                onMouseDown={() => {
                                  setCrName(m.account_name);
                                  setCrDropOpen(null);
                                }}
                                className="p-2.5 hover:bg-emerald-50/70 cursor-pointer flex items-center justify-between"
                              >
                                <div>
                                  <div className="text-xs font-bold text-slate-800">{m.account_name}</div>
                                  {m.group_name && (
                                    <div className="text-[10px] text-slate-400">{m.group_name}</div>
                                  )}
                                </div>
                                {m.opening_balance !== undefined && (
                                  <span className="text-[10px] font-mono text-slate-500">
                                    ₹{Number(m.opening_balance).toLocaleString("en-IN")}
                                  </span>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Selected Party Pill */}
                {selectedParty && (
                  <div className="flex items-center justify-between bg-indigo-50/90 border border-indigo-100 rounded-lg px-3.5 py-2">
                    <div className="flex items-center gap-2">
                      <UserCheck className="w-4 h-4 text-indigo-600" />
                      <span className="text-xs font-bold text-indigo-900">{selectedParty.name}</span>
                      <span
                        className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${
                          PARTY_META[selectedParty.type]?.bg || "bg-slate-100"
                        }`}
                      >
                        {PARTY_META[selectedParty.type]?.label || selectedParty.type}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedParty(null);
                        setDrConfirmedParty(null);
                        setCrConfirmedParty(null);
                        setStaffPayType("");
                      }}
                      className="text-indigo-400 hover:text-indigo-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* Staff Payment Category Section */}
                {selectedParty?.type === "STAFF" && vtype === "PAYMENT" && (
                  <div className="bg-emerald-50/90 border border-emerald-200 rounded-xl p-4 space-y-3">
                    <div className="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" /> Staff Payment Category
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Payment Type <span className="text-rose-500">*</span>
                        </label>
                        <select
                          value={staffPayType}
                          onChange={(e) => handleStaffPayCatChange(e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-emerald-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-emerald-500/20"
                        >
                          <option value="">— Select Category —</option>
                          <option value="SALARY">Salary</option>
                          <option value="INCENTIVE">Incentive / Commission</option>
                          <option value="CONVEYANCE">Conveyance Allowance</option>
                          <option value="TRAVEL">Travel Allowance</option>
                          <option value="ADVANCE">Advance (Recoverable)</option>
                          <option value="REIMBURSEMENT">Reimbursement</option>
                          <option value="OTHER">Other</option>
                        </select>
                      </div>

                      {staffPayType === "OTHER" && (
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                            Expense Head Name
                          </label>
                          <input
                            type="text"
                            value={staffPayOtherHead}
                            onChange={(e) => {
                              setStaffPayOtherHead(e.target.value);
                              setDrName(e.target.value || "Staff Expense");
                            }}
                            placeholder="e.g. Medical Allowance"
                            className="w-full px-3 py-2 bg-white border border-emerald-300 rounded-lg text-xs font-medium"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Quick Add Party Link Button */}
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setApStep(1);
                      setAddPartyModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 bg-indigo-50/50 hover:bg-indigo-50 border border-dashed border-indigo-300 px-3 py-1.5 rounded-lg transition"
                  >
                    <UserPlus className="w-3.5 h-3.5" /> Add New Party
                  </button>
                </div>

                {/* Invoice Linking (Payment → purchase, Receipt → sale) */}
                {VT_PRESETS[vtype].showInvoice && (
                  <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-amber-600" /> Link to Invoice
                      </label>
                      <span className="text-[11px] text-amber-700 font-medium">
                        {VT_PRESETS[vtype].invoiceDesc}
                      </span>
                    </div>

                    <select
                      value={selectedInvoice?.value || ""}
                      onChange={(e) => {
                        const val = parseInt(e.target.value);
                        const match = openInvoices.find((i) => i.value === val) || null;
                        setSelectedInvoice(match);
                        if (match && !amount) {
                          setAmount(match.balance.toFixed(2));
                        }
                      }}
                      disabled={invoiceLinkLoading}
                      className="w-full px-3 py-2 bg-white border border-amber-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-amber-500/20"
                    >
                      <option value="">— No invoice link (standalone entry) —</option>
                      {openInvoices.map((inv) => (
                        <option key={inv.value} value={inv.value}>
                          {inv.label} (Bal: ₹{inv.balance.toLocaleString("en-IN")})
                        </option>
                      ))}
                    </select>

                    {selectedInvoice && (
                      <div className="text-[11px] text-emerald-700 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Balance Due: ₹
                        {selectedInvoice.balance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </div>
                    )}
                  </div>
                )}

                {/* Amount + Payment Mode + Reference # */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                      Amount (₹) <span className="text-rose-500">*</span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 font-bold text-sm">
                        ₹
                      </div>
                      <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="0.00"
                        required
                        className="w-full pl-8 pr-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-bold text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                      Payment Mode
                    </label>
                    <select
                      value={payMode}
                      onChange={(e) => handlePayModeChange(e.target.value)}
                      className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                    >
                      <option value="">— Select Mode —</option>
                      <option value="NEFT">NEFT</option>
                      <option value="RTGS">RTGS</option>
                      <option value="CHEQUE">CHEQUE</option>
                      <option value="UPI">UPI</option>
                      <option value="CASH">CASH</option>
                      <option value="IMPS">IMPS</option>
                      <option value="CARD">CARD</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                      Reference / UTR / Cheque #
                    </label>
                    <input
                      type="text"
                      value={refNum}
                      onChange={(e) => setRefNum(e.target.value)}
                      placeholder="UTR, cheque number, etc."
                      className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20"
                    />
                  </div>
                </div>
              </div>
            ) : (
              /* ═══════════════════════════════════════════════════════════ */
              /* COMPOUND ENTRY MODE (Tally F7 - Multiple DR & CR lines) */
              /* ═══════════════════════════════════════════════════════════ */
              <div className="space-y-4">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* DR Lines Column */}
                  <div className="space-y-3">
                    <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg px-3 py-2 text-xs font-extrabold uppercase tracking-wider flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <ArrowRight className="w-3.5 h-3.5" /> DR (Debit) Lines — Where Money Goes
                      </span>
                    </div>

                    <div className="space-y-2">
                      {compoundLines
                        .filter((l) => l.entry_type === "DEBIT")
                        .map((line) => (
                          <div
                            key={line.id}
                            className="grid grid-cols-[90px_1fr_90px_32px] gap-2 items-center relative"
                          >
                            <select
                              value={line.account_type}
                              onChange={(e) => updateCompoundLine(line.id, "account_type", e.target.value)}
                              className="px-2 py-2 bg-white border border-slate-300 rounded-lg text-xs font-bold uppercase tracking-wider"
                            >
                              {ACCOUNT_TYPES.map((t) => (
                                <option key={t} value={t}>
                                  {t}
                                </option>
                              ))}
                            </select>

                            <div className="relative">
                              <input
                                type="text"
                                value={line.account_name}
                                onChange={(e) => {
                                  updateCompoundLine(line.id, "account_name", e.target.value);
                                  if (line.account_type === "PARTY") {
                                    setCompActiveDrop({ rowId: line.id, type: "PARTY" });
                                    searchParties(e.target.value);
                                  } else {
                                    setCompActiveDrop({ rowId: line.id, type: "LEDGER" });
                                    searchLedgers(line.account_type, e.target.value);
                                  }
                                }}
                                onFocus={() => {
                                  if (line.account_type === "PARTY") {
                                    setCompActiveDrop({ rowId: line.id, type: "PARTY" });
                                    searchParties(line.account_name);
                                  } else {
                                    setCompActiveDrop({ rowId: line.id, type: "LEDGER" });
                                    searchLedgers(line.account_type, line.account_name);
                                  }
                                }}
                                placeholder="Account Name"
                                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs font-medium"
                              />

                              {/* Autocomplete for compound row */}
                              {compActiveDrop?.rowId === line.id && (
                                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-xl z-30 max-h-48 overflow-y-auto divide-y divide-slate-100">
                                  {compActiveDrop.type === "PARTY" ? (
                                    partySearchResults.length === 0 ? (
                                      <div className="p-2 text-[11px] text-slate-500">
                                        No party.{" "}
                                        <button
                                          type="button"
                                          onMouseDown={() =>
                                            promptExternalPartyPhone("comp", line.account_name, line.id)
                                          }
                                          className="text-purple-600 font-bold"
                                        >
                                          Use external
                                        </button>
                                      </div>
                                    ) : (
                                      partySearchResults.map((p) => (
                                        <div
                                          key={p.id + "-" + p.name}
                                          onMouseDown={() => {
                                            updateCompoundLine(line.id, "account_name", p.name);
                                            setCompActiveDrop(null);
                                          }}
                                          className="p-2 text-xs hover:bg-slate-50 cursor-pointer flex justify-between"
                                        >
                                          <span className="font-semibold">{p.name}</span>
                                          <span className="text-[10px] text-slate-400">{p.type}</span>
                                        </div>
                                      ))
                                    )
                                  ) : ledgerSearchResults.length === 0 ? (
                                    <div className="p-2 text-[11px] text-slate-500">No ledgers.</div>
                                  ) : (
                                    ledgerSearchResults.map((m) => (
                                      <div
                                        key={m.id}
                                        onMouseDown={() => {
                                          updateCompoundLine(line.id, "account_name", m.account_name);
                                          setCompActiveDrop(null);
                                        }}
                                        className="p-2 text-xs hover:bg-slate-50 cursor-pointer flex justify-between"
                                      >
                                        <span className="font-semibold">{m.account_name}</span>
                                        <span className="text-[10px] text-slate-400">{m.group_name}</span>
                                      </div>
                                    ))
                                  )}
                                </div>
                              )}
                            </div>

                            <input
                              type="number"
                              step="0.01"
                              min="0.01"
                              value={line.amount}
                              onChange={(e) => updateCompoundLine(line.id, "amount", e.target.value)}
                              placeholder="0.00"
                              className="px-2 py-2 bg-white border border-slate-300 rounded-lg text-xs font-bold text-right"
                            />

                            <button
                              type="button"
                              onClick={() => removeCompoundLine(line.id)}
                              className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100 flex items-center justify-center transition"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => addCompoundLine("DEBIT")}
                      className="w-full py-2 bg-rose-50/50 hover:bg-rose-50 border border-dashed border-rose-300 text-rose-700 rounded-lg text-xs font-bold flex items-center justify-center gap-1 transition"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add DR Line
                    </button>
                  </div>

                  {/* CR Lines Column */}
                  <div className="space-y-3">
                    <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg px-3 py-2 text-xs font-extrabold uppercase tracking-wider flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <ArrowLeft className="w-3.5 h-3.5" /> CR (Credit) Lines — Where Money From
                      </span>
                    </div>

                    <div className="space-y-2">
                      {compoundLines
                        .filter((l) => l.entry_type === "CREDIT")
                        .map((line) => (
                          <div
                            key={line.id}
                            className="grid grid-cols-[90px_1fr_90px_32px] gap-2 items-center relative"
                          >
                            <select
                              value={line.account_type}
                              onChange={(e) => updateCompoundLine(line.id, "account_type", e.target.value)}
                              className="px-2 py-2 bg-white border border-slate-300 rounded-lg text-xs font-bold uppercase tracking-wider"
                            >
                              {ACCOUNT_TYPES.map((t) => (
                                <option key={t} value={t}>
                                  {t}
                                </option>
                              ))}
                            </select>

                            <div className="relative">
                              <input
                                type="text"
                                value={line.account_name}
                                onChange={(e) => {
                                  updateCompoundLine(line.id, "account_name", e.target.value);
                                  if (line.account_type === "PARTY") {
                                    setCompActiveDrop({ rowId: line.id, type: "PARTY" });
                                    searchParties(e.target.value);
                                  } else {
                                    setCompActiveDrop({ rowId: line.id, type: "LEDGER" });
                                    searchLedgers(line.account_type, e.target.value);
                                  }
                                }}
                                onFocus={() => {
                                  if (line.account_type === "PARTY") {
                                    setCompActiveDrop({ rowId: line.id, type: "PARTY" });
                                    searchParties(line.account_name);
                                  } else {
                                    setCompActiveDrop({ rowId: line.id, type: "LEDGER" });
                                    searchLedgers(line.account_type, line.account_name);
                                  }
                                }}
                                placeholder="Account Name"
                                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs font-medium"
                              />

                              {/* Autocomplete for compound row */}
                              {compActiveDrop?.rowId === line.id && (
                                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-xl z-30 max-h-48 overflow-y-auto divide-y divide-slate-100">
                                  {compActiveDrop.type === "PARTY" ? (
                                    partySearchResults.length === 0 ? (
                                      <div className="p-2 text-[11px] text-slate-500">
                                        No party.{" "}
                                        <button
                                          type="button"
                                          onMouseDown={() =>
                                            promptExternalPartyPhone("comp", line.account_name, line.id)
                                          }
                                          className="text-purple-600 font-bold"
                                        >
                                          Use external
                                        </button>
                                      </div>
                                    ) : (
                                      partySearchResults.map((p) => (
                                        <div
                                          key={p.id + "-" + p.name}
                                          onMouseDown={() => {
                                            updateCompoundLine(line.id, "account_name", p.name);
                                            setCompActiveDrop(null);
                                          }}
                                          className="p-2 text-xs hover:bg-slate-50 cursor-pointer flex justify-between"
                                        >
                                          <span className="font-semibold">{p.name}</span>
                                          <span className="text-[10px] text-slate-400">{p.type}</span>
                                        </div>
                                      ))
                                    )
                                  ) : ledgerSearchResults.length === 0 ? (
                                    <div className="p-2 text-[11px] text-slate-500">No ledgers.</div>
                                  ) : (
                                    ledgerSearchResults.map((m) => (
                                      <div
                                        key={m.id}
                                        onMouseDown={() => {
                                          updateCompoundLine(line.id, "account_name", m.account_name);
                                          setCompActiveDrop(null);
                                        }}
                                        className="p-2 text-xs hover:bg-slate-50 cursor-pointer flex justify-between"
                                      >
                                        <span className="font-semibold">{m.account_name}</span>
                                        <span className="text-[10px] text-slate-400">{m.group_name}</span>
                                      </div>
                                    ))
                                  )}
                                </div>
                              )}
                            </div>

                            <input
                              type="number"
                              step="0.01"
                              min="0.01"
                              value={line.amount}
                              onChange={(e) => updateCompoundLine(line.id, "amount", e.target.value)}
                              placeholder="0.00"
                              className="px-2 py-2 bg-white border border-slate-300 rounded-lg text-xs font-bold text-right"
                            />

                            <button
                              type="button"
                              onClick={() => removeCompoundLine(line.id)}
                              className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100 flex items-center justify-center transition"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => addCompoundLine("CREDIT")}
                      className="w-full py-2 bg-emerald-50/50 hover:bg-emerald-50 border border-dashed border-emerald-300 text-emerald-700 rounded-lg text-xs font-bold flex items-center justify-center gap-1 transition"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add CR Line
                    </button>
                  </div>
                </div>

                {/* Balance Summary Bar */}
                <div
                  className={`p-4 rounded-xl border flex flex-col sm:flex-row items-center justify-between gap-4 ${
                    isCompoundBalanced
                      ? "bg-emerald-50 border-emerald-300"
                      : "bg-rose-50 border-rose-300"
                  }`}
                >
                  <div className="text-center sm:text-left">
                    <span className="text-[10px] font-bold uppercase text-slate-500">DR Total</span>
                    <div className="text-base font-extrabold font-mono text-rose-600">
                      ₹{compoundDebitTotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-xs font-bold">
                    {isCompoundBalanced ? (
                      <span className="text-emerald-700 flex items-center gap-1.5 bg-emerald-100 px-3 py-1 rounded-full border border-emerald-200">
                        <CheckCircle2 className="w-4 h-4" /> Balanced Entry
                      </span>
                    ) : (
                      <span className="text-rose-700 flex items-center gap-1.5 bg-rose-100 px-3 py-1 rounded-full border border-rose-200">
                        <AlertTriangle className="w-4 h-4" /> Unbalanced — Diff: ₹
                        {compoundDiff.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </span>
                    )}
                  </div>

                  <div className="text-center sm:text-right">
                    <span className="text-[10px] font-bold uppercase text-slate-500">CR Total</span>
                    <div className="text-base font-extrabold font-mono text-emerald-600">
                      ₹{compoundCreditTotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 4. Category Picker (Expense & Income Categories) */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                  Category <span className="text-slate-400 font-normal lowercase">(optional)</span>
                </label>
                <button
                  type="button"
                  onClick={() => setExpCatModalOpen(true)}
                  className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-800 inline-flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Add Category
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <select
                  value={selectedMainCat}
                  onChange={(e) => {
                    setSelectedMainCat(e.target.value);
                    setSelectedSubCat("");
                  }}
                  className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="">— Main Category —</option>
                  <optgroup label="Expense Heads">
                    {mainCats.map((m) => (
                      <option key={m.id} value={String(m.id)}>
                        {m.name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Income Heads">
                    {incMainCats.map((m) => (
                      <option key={m.id} value={`inc_${m.id}`}>
                        {m.name}
                      </option>
                    ))}
                  </optgroup>
                </select>

                <select
                  value={selectedSubCat}
                  onChange={(e) => setSelectedSubCat(e.target.value)}
                  disabled={!selectedMainCat}
                  className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-indigo-500/20 disabled:bg-slate-100 disabled:text-slate-400"
                >
                  <option value="">— Sub Category —</option>
                  {selectedMainCat.startsWith("inc_")
                    ? incSubCats
                        .filter((s) => s.parent_id === parseInt(selectedMainCat.replace("inc_", "")))
                        .map((s) => (
                          <option key={s.id} value={`inc_${s.id}`}>
                            {s.name}
                          </option>
                        ))
                    : subCats
                        .filter((s) => s.parent_id === parseInt(selectedMainCat))
                        .map((s) => (
                          <option key={s.id} value={String(s.id)}>
                            {s.name}
                          </option>
                        ))}
                </select>
              </div>
            </div>

            {/* 5. Narration */}
            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                Narration / Description <span className="text-rose-500">*</span>
              </label>
              <textarea
                value={narration}
                onChange={(e) => {
                  setNarration(e.target.value);
                  setAutoNarrationDirty(true);
                }}
                rows={2}
                required
                placeholder="Describe the purpose of this entry..."
                className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            {/* 6. Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
              >
                <RotateCcw className="w-3.5 h-3.5 inline-block mr-1.5" /> Reset
              </button>

              <button
                type="submit"
                disabled={posting || (compoundMode && !isCompoundBalanced)}
                className="px-6 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition disabled:opacity-50 flex items-center gap-1.5"
              >
                {posting ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Save className="w-3.5 h-3.5" />
                )}
                Post Voucher
              </button>
            </div>
          </form>
        </section>

        {/* ═══════════════════════════════════════════════════════════ */}
        {/* VOUCHER HISTORY & FILTER TABLE */}
        {/* ═══════════════════════════════════════════════════════════ */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-6 border-b border-slate-100 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-700">
                  <BookOpen className="w-4 h-4" />
                </div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">Journal Vouchers</h2>
              </div>
              <span className="text-xs font-semibold text-slate-500">
                {listTotal} entries · Total ₹
                {listTotalAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>

            {/* Filter Tabs: Posted vs Deleted */}
            <div className="flex gap-2 border-b border-slate-200 pb-2">
              <button
                type="button"
                onClick={() => setActiveTab("POSTED")}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                  activeTab === "POSTED"
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs"
                    : "text-slate-500 hover:bg-slate-50"
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Posted Entries
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("CANCELLED")}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                  activeTab === "CANCELLED"
                    ? "bg-rose-50 text-rose-700 border border-rose-200 shadow-2xs"
                    : "text-slate-500 hover:bg-slate-50"
                }`}
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600" /> Deleted Entries
              </button>
            </div>

            {/* Advanced Search & Filter Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 pt-2">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Company</label>
                <select
                  value={filterCompany}
                  onChange={(e) => setFilterCompany(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name || `Company ${c.id}`}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Type</label>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                >
                  <option value="">All Types</option>
                  <option value="PAYMENT">PAYMENT</option>
                  <option value="RECEIPT">RECEIPT</option>
                  <option value="CONTRA">CONTRA</option>
                  <option value="JOURNAL">JOURNAL</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Party Name</label>
                <input
                  type="text"
                  value={filterParty}
                  onChange={(e) => setFilterParty(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadVouchers(1)}
                  placeholder="Search party..."
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">From Date</label>
                <input
                  type="date"
                  value={filterFromDate}
                  onChange={(e) => setFilterFromDate(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">To Date</label>
                <div className="flex gap-2">
                  <input
                    type="date"
                    value={filterToDate}
                    onChange={(e) => setFilterToDate(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => loadVouchers(1)}
                    className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition shrink-0"
                    title="Search"
                  >
                    <Search className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto">
            {listLoading ? (
              <div className="p-12 text-center text-slate-500 space-y-3">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600" />
                <p className="text-xs">Loading journal vouchers...</p>
              </div>
            ) : vouchers.length === 0 ? (
              <div className="p-16 text-center text-slate-500 space-y-2">
                <div className="text-3xl">📓</div>
                <h3 className="text-sm font-bold text-slate-800">No vouchers found</h3>
                <p className="text-xs text-slate-400">Use the form above to post a new accounting entry.</p>
              </div>
            ) : (
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  <tr>
                    {!filterCompany && <th className="p-3.5">Company</th>}
                    <th className="p-3.5">Voucher #</th>
                    <th className="p-3.5">Date</th>
                    <th className="p-3.5">Type</th>
                    <th className="p-3.5">DR Account</th>
                    <th className="p-3.5">CR Account</th>
                    <th className="p-3.5">Party</th>
                    <th className="p-3.5 text-right">Debit (₹)</th>
                    <th className="p-3.5 text-right">Credit (₹)</th>
                    <th className="p-3.5">Mode / Ref</th>
                    <th className="p-3.5 max-w-[150px]">Narration</th>
                    <th className="p-3.5">Category</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {vouchers.map((v) => (
                    <tr
                      key={v.id}
                      className={`hover:bg-slate-50/70 transition-colors ${
                        v.status === "CANCELLED" ? "opacity-60 bg-slate-50/30" : ""
                      }`}
                    >
                      {!filterCompany && (
                        <td className="p-3.5 font-medium text-slate-700 max-w-[120px] truncate" title={companyMap[v.company_id]}>
                          {companyMap[v.company_id] || `Co ${v.company_id}`}
                        </td>
                      )}
                      <td className="p-3.5 font-mono font-bold text-indigo-600 whitespace-nowrap">
                        {v.voucher_number}
                      </td>
                      <td className="p-3.5 whitespace-nowrap text-slate-600">{v.voucher_date || "—"}</td>
                      <td className="p-3.5 whitespace-nowrap">
                        <span
                          className={`text-[9px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider ${
                            v.voucher_type === "PAYMENT"
                              ? "bg-rose-100 text-rose-700"
                              : v.voucher_type === "RECEIPT"
                              ? "bg-emerald-100 text-emerald-700"
                              : v.voucher_type === "CONTRA"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-purple-100 text-purple-700"
                          }`}
                        >
                          {v.voucher_type}
                        </span>
                      </td>
                      <td className="p-3.5 max-w-[130px] truncate" title={v.dr_account_name}>
                        <span className="text-rose-600 font-bold mr-1">DR</span>
                        {v.dr_account_name}
                      </td>
                      <td className="p-3.5 max-w-[130px] truncate" title={v.cr_account_name}>
                        <span className="text-emerald-600 font-bold mr-1">CR</span>
                        {v.cr_account_name}
                      </td>
                      <td className="p-3.5 max-w-[120px] truncate" title={v.party_name || ""}>
                        {v.party_name || "—"}
                      </td>
                      <td className="p-3.5 text-right font-mono font-bold text-rose-600 whitespace-nowrap">
                        ₹{Number(v.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="p-3.5 text-right font-mono font-bold text-emerald-600 whitespace-nowrap">
                        ₹{Number(v.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="p-3.5 whitespace-nowrap text-[11px] text-slate-500">
                        {v.payment_mode && <div className="font-semibold text-slate-700">{v.payment_mode}</div>}
                        {v.reference_number && <div className="font-mono text-[10px]">{v.reference_number}</div>}
                        {!v.payment_mode && !v.reference_number && "—"}
                      </td>
                      <td className="p-3.5 max-w-[160px] truncate text-slate-600" title={v.narration || ""}>
                        {v.narration || "—"}
                      </td>
                      <td className="p-3.5 whitespace-nowrap">
                        {v.main_category_name ? (
                          <span className="bg-sky-50 text-sky-700 text-[10px] font-semibold px-2 py-0.5 rounded border border-sky-200">
                            {v.main_category_name}
                          </span>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="p-3.5 whitespace-nowrap">
                        <span
                          className={`text-[9px] font-bold px-2 py-0.5 rounded ${
                            v.status === "POSTED" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                          }`}
                        >
                          {v.status}
                        </span>
                        {v.cancel_reason && (
                          <div className="text-[10px] text-rose-500 max-w-[100px] truncate" title={v.cancel_reason}>
                            {v.cancel_reason}
                          </div>
                        )}
                      </td>
                      <td className="p-3.5 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleOpenViewModal(v.id)}
                            className="p-1.5 rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 transition"
                            title="View Voucher Details"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>

                          {v.status === "POSTED" && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleOpenEditModal(v)}
                                className="p-1.5 rounded-md bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition"
                                title="Edit Voucher"
                              >
                                <Edit className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleOpenCancelModal(v.id)}
                                className="p-1.5 rounded-md bg-rose-50 text-rose-600 hover:bg-rose-100 transition"
                                title="Delete / Cancel Voucher"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {listTotalPages > 1 && (
            <div className="p-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Page {listPage} of {listTotalPages} ({listTotal} total)
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={listPage <= 1}
                  onClick={() => loadVouchers(listPage - 1)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-md border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40"
                >
                  <ChevronLeft className="w-3.5 h-3.5 inline-block mr-1" /> Prev
                </button>
                <button
                  type="button"
                  disabled={listPage >= listTotalPages}
                  onClick={() => loadVouchers(listPage + 1)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-md border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40"
                >
                  Next <ChevronRight className="w-3.5 h-3.5 inline-block ml-1" />
                </button>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* 1. VIEW VOUCHER MODAL */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {viewModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl flex flex-col animate-in zoom-in-95">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-indigo-600 to-indigo-800 p-5 text-white flex items-center justify-between">
              <div>
                <div className="text-base font-bold flex items-center gap-2">
                  <span>{viewVoucherData?.voucher?.voucher_type}</span>
                  <span>{viewVoucherData?.voucher?.voucher_number}</span>
                </div>
                <div className="text-xs text-indigo-200 mt-0.5">
                  {viewVoucherData?.voucher?.voucher_date} · {viewVoucherData?.company_name} · Created by{" "}
                  {viewVoucherData?.creator_name}
                </div>
              </div>
              <button
                onClick={() => setViewModalOpen(false)}
                className="w-8 h-8 rounded-lg bg-white/20 hover:bg-white/30 flex items-center justify-center text-white transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {viewLoading ? (
                <div className="p-12 text-center text-slate-500">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600" />
                  <p className="text-xs mt-2">Loading details...</p>
                </div>
              ) : viewVoucherData?.voucher ? (
                <>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                        viewVoucherData.voucher.status === "POSTED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {viewVoucherData.voucher.status}
                    </span>
                    {viewVoucherData.is_compound && (
                      <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-purple-100 text-purple-800">
                        COMPOUND (Tally F7)
                      </span>
                    )}
                    {viewVoucherData.voucher.narration && (
                      <span className="text-xs italic text-slate-600">
                        &ldquo;{viewVoucherData.voucher.narration}&rdquo;
                      </span>
                    )}
                  </div>

                  {/* Lines Breakdown */}
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 text-[10px] font-bold uppercase text-slate-500 border-b border-slate-200">
                        <tr>
                          <th className="p-3">Type</th>
                          <th className="p-3">Acct Type</th>
                          <th className="p-3">Particulars / Account</th>
                          <th className="p-3 text-right">Amount (₹)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {viewVoucherData.lines.map((line, idx) => {
                          const isDr = line.entry_type === "DEBIT";
                          return (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="p-3">
                                <span
                                  className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded ${
                                    isDr ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                                  }`}
                                >
                                  {line.entry_type}
                                </span>
                              </td>
                              <td className="p-3">
                                <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px]">
                                  {line.account_type}
                                </span>
                              </td>
                              <td className="p-3 font-semibold text-slate-800">
                                {line.account_name}
                                {line.party_name && (
                                  <div className="text-[10px] text-slate-400 font-normal">{line.party_name}</div>
                                )}
                              </td>
                              <td
                                className={`p-3 text-right font-mono font-bold ${
                                  isDr ? "text-rose-600" : "text-emerald-600"
                                }`}
                              >
                                ₹{Number(line.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {viewVoucherData.voucher.cancel_reason && (
                    <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800">
                      <strong>Cancellation Reason:</strong> {viewVoucherData.voucher.cancel_reason}
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setViewModalOpen(false)}
                className="px-4 py-2 bg-white border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-100 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* 2. EDIT VOUCHER MODAL */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {editModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-4 animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600">
                  <Edit className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Edit Voucher</h3>
                  <p className="text-xs text-slate-500">
                    {editFields.voucherNumber} ({editFields.voucherType})
                  </p>
                </div>
              </div>
              <button onClick={() => setEditModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {editError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs font-medium">
                {editError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Date</label>
                <input
                  type="date"
                  value={editFields.date}
                  onChange={(e) => setEditFields({ ...editFields, date: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={editFields.amount}
                  onChange={(e) => setEditFields({ ...editFields, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">DR Account Type</label>
                <select
                  value={editFields.drType}
                  onChange={(e) => setEditFields({ ...editFields, drType: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-bold"
                >
                  {ACCOUNT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">DR Account Name</label>
                <input
                  type="text"
                  value={editFields.drName}
                  onChange={(e) => setEditFields({ ...editFields, drName: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">CR Account Type</label>
                <select
                  value={editFields.crType}
                  onChange={(e) => setEditFields({ ...editFields, crType: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-bold"
                >
                  {ACCOUNT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">CR Account Name</label>
                <input
                  type="text"
                  value={editFields.crName}
                  onChange={(e) => setEditFields({ ...editFields, crName: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Payment Mode</label>
                <select
                  value={editFields.payMode}
                  onChange={(e) => setEditFields({ ...editFields, payMode: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                >
                  <option value="">— None —</option>
                  <option value="NEFT">NEFT</option>
                  <option value="RTGS">RTGS</option>
                  <option value="CHEQUE">CHEQUE</option>
                  <option value="UPI">UPI</option>
                  <option value="CASH">CASH</option>
                  <option value="IMPS">IMPS</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Reference #</label>
                <input
                  type="text"
                  value={editFields.refNum}
                  onChange={(e) => setEditFields({ ...editFields, refNum: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Narration</label>
              <textarea
                value={editFields.narration}
                onChange={(e) => setEditFields({ ...editFields, narration: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                disabled={editLoading}
                className="px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm flex items-center gap-1.5"
              >
                {editLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* 3. CANCEL / DELETE VOUCHER MODAL */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {cancelModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Delete Voucher</h3>
                <p className="text-xs text-rose-600 font-semibold">
                  This permanently removes the voucher and reverts all ledger entries.
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
                Reason for Deletion (Optional)
              </label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Reason..."
                rows={3}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCancelModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Keep Voucher
              </button>
              <button
                type="button"
                onClick={handleConfirmCancel}
                disabled={cancelLoading}
                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-sm flex items-center gap-1.5"
              >
                {cancelLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* 4. ADD PARTY MODAL (Vendor, External, Partner) */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {addPartyModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col animate-in zoom-in-95">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Add New Party</h3>
              </div>
              <button onClick={() => setAddPartyModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 flex-1">
              {apError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs">
                  {apError}
                </div>
              )}
              {apSuccess && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs">
                  {apSuccess}
                </div>
              )}

              {/* Step 1: Type Selection */}
              {apStep === 1 ? (
                <div className="space-y-4">
                  <p className="text-xs text-slate-500">
                    Select the type of party to add. Once saved, it will be automatically selected in this voucher.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        setApType("VENDOR");
                        setApStep(2);
                      }}
                      className="p-5 border-2 border-amber-300 bg-amber-50/50 hover:bg-amber-50 rounded-xl text-center transition cursor-pointer"
                    >
                      <Store className="w-8 h-8 text-amber-600 mx-auto mb-2" />
                      <div className="text-sm font-bold text-slate-900">Vendor</div>
                      <div className="text-[10px] text-slate-500 mt-1">Supplier · Full GST & bank info</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setApType("EXTERNAL");
                        setApStep(2);
                      }}
                      className="p-5 border-2 border-purple-300 bg-purple-50/50 hover:bg-purple-50 rounded-xl text-center transition cursor-pointer"
                    >
                      <User className="w-8 h-8 text-purple-600 mx-auto mb-2" />
                      <div className="text-sm font-bold text-slate-900">External Party</div>
                      <div className="text-[10px] text-slate-500 mt-1">Person or company · Quick entry</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setApType("PARTNER");
                        setApStep(2);
                      }}
                      className="p-5 border-2 border-emerald-300 bg-emerald-50/50 hover:bg-emerald-50 rounded-xl text-center transition cursor-pointer"
                    >
                      <Handshake className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
                      <div className="text-sm font-bold text-slate-900">Official Partner</div>
                      <div className="text-[10px] text-slate-500 mt-1">Dealer · Distributor · Service Ctr</div>
                    </button>
                  </div>
                </div>
              ) : (
                /* Step 2: Forms */
                <div className="space-y-4">
                  <button
                    type="button"
                    onClick={() => setApStep(1)}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" /> Back to Party Types
                  </button>

                  {apType === "VENDOR" && (
                    <div className="space-y-4">
                      {/* Vendor Subtabs */}
                      <div className="flex gap-2 border-b border-slate-200 pb-2">
                        {(["basic", "contacts", "address", "bank"] as const).map((tab) => (
                          <button
                            key={tab}
                            type="button"
                            onClick={() => setApVendorTab(tab)}
                            className={`px-3 py-1 text-xs font-bold rounded-lg capitalize ${
                              apVendorTab === tab
                                ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                                : "text-slate-500"
                            }`}
                          >
                            {tab}
                          </button>
                        ))}
                      </div>

                      {apVendorTab === "basic" && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Vendor Name <span className="text-rose-500">*</span>
                            </label>
                            <input
                              type="text"
                              value={vendorForm.vendor_name}
                              onChange={(e) => {
                                const name = e.target.value;
                                const words = name
                                  .toUpperCase()
                                  .replace(/[^A-Z0-9 ]/g, "")
                                  .split(" ")
                                  .filter(Boolean);
                                const prefix = words
                                  .slice(0, 4)
                                  .map((w) => w[0])
                                  .join("");
                                setVendorForm({
                                  ...vendorForm,
                                  vendor_name: name,
                                  vendor_code: prefix + Date.now().toString().slice(-4)
                                });
                              }}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Vendor Code <span className="text-rose-500">*</span>
                            </label>
                            <input
                              type="text"
                              value={vendorForm.vendor_code}
                              onChange={(e) =>
                                setVendorForm({ ...vendorForm, vendor_code: e.target.value.toUpperCase() })
                              }
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono font-bold"
                            />
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Phone</label>
                            <input
                              type="text"
                              value={vendorForm.phone}
                              onChange={(e) => setVendorForm({ ...vendorForm, phone: e.target.value })}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Email</label>
                            <input
                              type="email"
                              value={vendorForm.email}
                              onChange={(e) => setVendorForm({ ...vendorForm, email: e.target.value })}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">GSTIN</label>
                            <input
                              type="text"
                              value={vendorForm.gst_number}
                              onChange={(e) =>
                                setVendorForm({ ...vendorForm, gst_number: e.target.value.toUpperCase() })
                              }
                              maxLength={15}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">PAN</label>
                            <input
                              type="text"
                              value={vendorForm.pan_number}
                              onChange={(e) =>
                                setVendorForm({ ...vendorForm, pan_number: e.target.value.toUpperCase() })
                              }
                              maxLength={10}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>

                          <div className="sm:col-span-2 bg-slate-50 p-3 rounded-lg border border-slate-200">
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Applicable Companies <span className="text-rose-500">*</span>
                            </label>
                            <div className="flex flex-wrap gap-2 mb-2">
                              {apSelectedCos.map((c) => (
                                <span
                                  key={c.id}
                                  className="inline-flex items-center gap-1 bg-indigo-100 text-indigo-700 text-xs font-semibold px-2.5 py-1 rounded-full"
                                >
                                  {c.name}
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setApSelectedCos((prev) => prev.filter((item) => item.id !== c.id))
                                    }
                                  >
                                    <X className="w-3 h-3" />
                                  </button>
                                </span>
                              ))}
                            </div>
                            <select
                              onChange={(e) => {
                                const val = parseInt(e.target.value);
                                if (!val) return;
                                const comp = companies.find((c) => c.id === val);
                                if (comp && !apSelectedCos.some((c) => c.id === val)) {
                                  setApSelectedCos((prev) => [
                                    ...prev,
                                    { id: comp.id, name: comp.company_name || comp.name || `Company ${comp.id}` }
                                  ]);
                                }
                              }}
                              className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                            >
                              <option value="">+ Add Applicable Company</option>
                              {companies.map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.company_name || c.name || `Company ${c.id}`}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                      )}

                      {apVendorTab === "contacts" && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Contact 1 Name
                            </label>
                            <input
                              type="text"
                              value={vendorForm.contact_person_1_name}
                              onChange={(e) =>
                                setVendorForm({ ...vendorForm, contact_person_1_name: e.target.value })
                              }
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Contact 1 Phone
                            </label>
                            <input
                              type="text"
                              value={vendorForm.contact_person_1_phone}
                              onChange={(e) =>
                                setVendorForm({ ...vendorForm, contact_person_1_phone: e.target.value })
                              }
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Designation
                            </label>
                            <input
                              type="text"
                              value={vendorForm.contact_person_1_designation}
                              onChange={(e) =>
                                setVendorForm({ ...vendorForm, contact_person_1_designation: e.target.value })
                              }
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>
                        </div>
                      )}

                      {apVendorTab === "address" && (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Full Address
                            </label>
                            <textarea
                              value={vendorForm.address}
                              onChange={(e) => setVendorForm({ ...vendorForm, address: e.target.value })}
                              rows={2}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>
                          <div className="grid grid-cols-3 gap-3">
                            <div>
                              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                                Pincode
                              </label>
                              <input
                                type="text"
                                maxLength={6}
                                value={vendorForm.pincode}
                                onChange={(e) => {
                                  setVendorForm({ ...vendorForm, pincode: e.target.value });
                                  handlePincodeLookup(e.target.value);
                                }}
                                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                              />
                            </div>
                            <div>
                              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">City</label>
                              <input
                                type="text"
                                value={vendorForm.city}
                                onChange={(e) => setVendorForm({ ...vendorForm, city: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                              />
                            </div>
                            <div>
                              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">State</label>
                              <input
                                type="text"
                                value={vendorForm.state}
                                onChange={(e) => setVendorForm({ ...vendorForm, state: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                              />
                            </div>
                          </div>
                        </div>
                      )}

                      {apVendorTab === "bank" && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Bank Name
                            </label>
                            <input
                              type="text"
                              value={vendorForm.bank_name}
                              onChange={(e) => setVendorForm({ ...vendorForm, bank_name: e.target.value })}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              Account Number
                            </label>
                            <input
                              type="text"
                              value={vendorForm.account_number}
                              onChange={(e) => setVendorForm({ ...vendorForm, account_number: e.target.value })}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                              IFSC Code
                            </label>
                            <input
                              type="text"
                              value={vendorForm.ifsc_code}
                              onChange={(e) =>
                                setVendorForm({ ...vendorForm, ifsc_code: e.target.value.toUpperCase() })
                              }
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">UPI ID</label>
                            <input
                              type="text"
                              value={vendorForm.upi_id}
                              onChange={(e) => setVendorForm({ ...vendorForm, upi_id: e.target.value })}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                            />
                          </div>
                        </div>
                      )}

                      <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                        <button
                          type="button"
                          onClick={() => setAddPartyModalOpen(false)}
                          className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={handleSubmitVendor}
                          disabled={apLoading}
                          className="px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm flex items-center gap-1.5"
                        >
                          {apLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                          Save Vendor
                        </button>
                      </div>
                    </div>
                  )}

                  {apType === "EXTERNAL" && (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
                          Full Name <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={extPartyForm.name}
                          onChange={(e) => setExtPartyForm({ ...extPartyForm, name: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
                          Mobile Number <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="tel"
                          value={extPartyForm.phone}
                          onChange={(e) => setExtPartyForm({ ...extPartyForm, phone: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Email</label>
                        <input
                          type="email"
                          value={extPartyForm.email}
                          onChange={(e) => setExtPartyForm({ ...extPartyForm, email: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Notes</label>
                        <textarea
                          value={extPartyForm.notes}
                          onChange={(e) => setExtPartyForm({ ...extPartyForm, notes: e.target.value })}
                          rows={2}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                        />
                      </div>

                      <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                        <button
                          type="button"
                          onClick={() => setAddPartyModalOpen(false)}
                          className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={handleSubmitExternalParty}
                          disabled={apLoading}
                          className="px-5 py-2 text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 rounded-lg shadow-sm flex items-center gap-1.5"
                        >
                          {apLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                          Save Party
                        </button>
                      </div>
                    </div>
                  )}

                  {apType === "PARTNER" && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 text-center space-y-3">
                      <Handshake className="w-10 h-10 text-emerald-600 mx-auto" />
                      <h4 className="text-sm font-bold text-slate-900">Official Partner Onboarding</h4>
                      <p className="text-xs text-slate-600 max-w-sm mx-auto">
                        Dealers, Distributors, and Service Centers are registered via the Partner Management portal.
                      </p>
                      <Link
                        href="/staff/accounts/community-services"
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 transition shadow-sm"
                      >
                        Go to Partners Portal <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* 5. EXTERNAL PARTY PHONE PROMPT MINI MODAL */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {extPhoneModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-purple-100 flex items-center justify-center text-purple-600">
                <UserPlus className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">Add External Party</h4>
                <p className="text-xs text-slate-500 font-medium">Saving: &ldquo;{extPhoneName}&rdquo;</p>
              </div>
            </div>

            {extPhoneError && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs">
                {extPhoneError}
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
                Mobile Number <span className="text-rose-500">*</span>
              </label>
              <input
                type="tel"
                value={extPhoneVal}
                onChange={(e) => setExtPhoneVal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveExternalPhone()}
                placeholder="10-digit phone number"
                className="w-full px-3 py-2 border border-purple-300 rounded-lg text-sm font-medium focus:ring-2 focus:ring-purple-500/20"
                autoFocus
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setExtPhoneModalOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveExternalPhone}
                disabled={extPhoneLoading}
                className="px-4 py-1.5 text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 rounded-lg shadow-sm flex items-center gap-1.5"
              >
                {extPhoneLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Save & Use
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* 6. QUICK CREATE LEDGER MODAL */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {qclModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Create New Ledger Account</h3>
              </div>
              <button onClick={() => setQclModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {qclError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs">
                {qclError}
              </div>
            )}
            {qclSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs">
                {qclSuccess}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Company *</label>
                <select
                  value={qclCompany}
                  onChange={(e) => setQclCompany(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                >
                  <option value="">— Select Company —</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name || `Company ${c.id}`}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Account Type *</label>
                <select
                  value={qclType}
                  onChange={(e) => {
                    setQclType(e.target.value);
                    setQclGroup(QCL_GROUP_CHIPS[e.target.value]?.default || "");
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-bold"
                >
                  {ACCOUNT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Account Name *</label>
                <input
                  type="text"
                  value={qclName}
                  onChange={(e) => setQclName(e.target.value)}
                  placeholder="e.g. Salary Expense, Rent Payable"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Account Group</label>
                <input
                  type="text"
                  value={qclGroup}
                  onChange={(e) => setQclGroup(e.target.value)}
                  placeholder="e.g. Indirect Expenses"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
                {/* Smart Chips */}
                {QCL_GROUP_CHIPS[qclType]?.chips?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {QCL_GROUP_CHIPS[qclType].chips.map((chip) => (
                      <button
                        key={chip}
                        type="button"
                        onClick={() => setQclGroup(chip)}
                        className="text-[10px] font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 px-2 py-0.5 rounded-full border border-indigo-200"
                      >
                        {chip}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setQclModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveQuickLedger}
                disabled={qclLoading}
                className="px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm flex items-center gap-1.5"
              >
                {qclLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Create Ledger
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* 7. QUICK ADD EXPENSE CATEGORY MODAL */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {expCatModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Add Expense Category</h3>
              <button onClick={() => setExpCatModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Create Type</label>
                <select
                  value={ecqaMode}
                  onChange={(e) => setEcqaMode(e.target.value as "sub" | "main")}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium"
                >
                  <option value="sub">Sub Category (Under Existing Main)</option>
                  <option value="main">New Main Category</option>
                </select>
              </div>

              {ecqaMode === "main" ? (
                <div>
                  <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
                    Main Category Name *
                  </label>
                  <input
                    type="text"
                    value={ecqaMainName}
                    onChange={(e) => setEcqaMainName(e.target.value)}
                    placeholder="e.g. Vehicle Expenses"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
                      Under Main Category *
                    </label>
                    <select
                      value={ecqaParentId}
                      onChange={(e) => setEcqaParentId(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                    >
                      <option value="">— Select Main —</option>
                      {mainCats.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
                      Sub Category Name *
                    </label>
                    <input
                      type="text"
                      value={ecqaSubName}
                      onChange={(e) => setEcqaSubName(e.target.value)}
                      placeholder="e.g. Fuel Expenses"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setExpCatModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveQuickCat}
                disabled={ecqaLoading}
                className="px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm flex items-center gap-1.5"
              >
                {ecqaLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Save Category
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
