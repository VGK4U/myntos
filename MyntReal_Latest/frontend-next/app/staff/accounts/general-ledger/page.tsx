"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  BookOpen,
  PlusCircle,
  Layers,
  Landmark,
  ListFilter,
  Users,
  Building2,
  Search,
  RotateCcw,
  RefreshCw,
  Eye,
  Edit,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  X,
  ExternalLink,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Store,
  UserPlus,
  Handshake,
  Info,
  Scale,
  Sparkles,
  Bookmark
} from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

// ── Types ────────────────────────────────────────────────────────────

interface Company {
  id: number | string;
  company_name?: string;
  name?: string;
}

interface LedgerEntry {
  id: number;
  company_id: number;
  transaction_date: string;
  account_type: string;
  account_name: string;
  entry_type: "DEBIT" | "CREDIT";
  debit_amount: number;
  credit_amount: number;
  running_balance: number;
  voucher_type?: string | null;
  reference_type?: string | null;
  reference_number?: string | null;
  particulars?: string | null;
  narration?: string | null;
  main_category_name?: string | null;
  sub_category_name?: string | null;
  source_status?: string | null;
  party_type?: string | null;
}

interface LedgerMaster {
  id: number;
  company_id: number;
  account_type: string;
  account_name: string;
  account_code?: string | null;
  parent_group?: string | null;
  description?: string | null;
  opening_balance?: number;
  opening_balance_type?: "DEBIT" | "CREDIT";
  opening_balance_date?: string | null;
  opening_balance_posted?: boolean;
  account_number?: string | null;
  ifsc_code?: string | null;
  bank_name?: string | null;
  is_active: boolean;
}

interface GLHead {
  account_type: string;
  account_name: string;
  company_id: number;
  total_debit: number;
  total_credit: number;
  balance: number;
  last_date?: string | null;
}

interface CompanyBank {
  id: number;
  company_id: number;
  bank_name: string;
  branch?: string | null;
  account_number?: string | null;
  ifsc_code?: string | null;
  is_primary?: boolean;
}

interface PartyVendorRow {
  id?: number;
  kind: "PARTY" | "SUNDRY_DEBTOR" | "SUNDRY_CREDITOR" | "VENDOR";
  name: string;
  code?: string;
  phone?: string;
  email?: string;
  gstin?: string;
  acct?: string;
  ifsc?: string;
  bank?: string;
  ob: number;
  ob_type: string;
  company_id?: number;
}

interface CompanySummaryRow {
  account_type: string;
  account_name: string;
  company_id: number;
  master_id?: number;
  total_debit: number;
  total_credit: number;
  balance: number;
  last_date?: string | null;
  has_gl: boolean;
}

// ── Helpers ──────────────────────────────────────────────────────────

const DEBIT_NORMAL_TYPES = ["BANK", "CASH", "UPI", "EXPENSE", "ASSET"];

const fmt = (n: number | string | null | undefined): string => {
  if (n === null || n === undefined || n === "") return "—";
  const num = Number(n);
  if (isNaN(num)) return "—";
  return "₹" + num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const fmtBal = (val: number | string | null | undefined, accountType?: string) => {
  const n = parseFloat(String(val || 0));
  if (!n) return { text: "Nil", label: "", isDr: false, isZero: true };
  const abs = Math.abs(n);
  const isDebitNormal = DEBIT_NORMAL_TYPES.includes((accountType || "").toUpperCase());
  const isDr = isDebitNormal ? n > 0 : n < 0;
  return {
    text: "₹" + abs.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    label: isDr ? "Dr" : "Cr",
    isDr,
    isZero: false
  };
};

const getTypeBadgeClass = (type: string) => {
  switch ((type || "").toUpperCase()) {
    case "CASH":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "BANK":
      return "bg-blue-100 text-blue-800 border-blue-200";
    case "UPI":
      return "bg-purple-100 text-purple-800 border-purple-200";
    case "INCOME":
      return "bg-cyan-100 text-cyan-800 border-cyan-200";
    case "EXPENSE":
      return "bg-red-100 text-red-800 border-red-200";
    case "STOCK":
      return "bg-amber-100 text-amber-800 border-amber-200";
    case "PARTY":
      return "bg-violet-100 text-violet-800 border-violet-200";
    case "SUNDRY_DEBTOR":
      return "bg-sky-100 text-sky-800 border-sky-200";
    case "SUNDRY_CREDITOR":
      return "bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200";
    case "DUTIES_TAXES":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "CAPITAL":
      return "bg-teal-100 text-teal-800 border-teal-200";
    case "LOAN":
      return "bg-amber-100 text-amber-900 border-amber-300";
    case "LIABILITY":
      return "bg-pink-100 text-pink-800 border-pink-200";
    case "ASSET":
      return "bg-indigo-100 text-indigo-800 border-indigo-200";
    case "VENDOR":
      return "bg-orange-100 text-orange-800 border-orange-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
};

const GROUP_CHIPS: Record<string, { default: string; chips: string[] }> = {
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
    chips: ["Direct Income", "Indirect Income", "Revenue", "Commission Income", "Interest Income", "Rental Income", "Other Income"]
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
  PARTY: { default: "", chips: [] },
  SUNDRY_DEBTOR: { default: "Sundry Debtors", chips: ["Sundry Debtors", "Trade Receivables", "Customers"] },
  SUNDRY_CREDITOR: { default: "Sundry Creditors", chips: ["Sundry Creditors", "Trade Payables", "Suppliers"] },
  DUTIES_TAXES: { default: "Duties & Taxes", chips: ["GST Payable", "CGST Payable", "SGST Payable", "TDS Payable", "Service Tax"] },
  CASH: { default: "Current Assets", chips: [] },
  BANK: { default: "Current Assets", chips: [] },
  UPI: { default: "Current Assets", chips: [] }
};

const AUTO_REF_TYPES = new Set([
  "INCOME",
  "EXPENSE",
  "PURCHASE_INVOICE",
  "SALES_INVOICE",
  "VENDOR_TXN",
  "CRM_REVENUE",
  "FUND_TRANSFER",
  "STOCK_TRANSFER"
]);

const PARTY_LIKE_TYPES = new Set(["PARTY", "SUNDRY_DEBTOR", "SUNDRY_CREDITOR"]);

export default function GeneralLedgerPage() {
  const { token, isAuthenticated } = useStaffAuth();

  // Navigation tabs
  const [activeTab, setActiveTab] = useState<"entries" | "create" | "cards" | "banks" | "txaccounts" | "parties" | "cwise">("entries");
  const [glTabStatus, setGlTabStatus] = useState<"ACTIVE" | "DELETED">("ACTIVE");

  // Companies state
  const [companies, setCompanies] = useState<Company[]>([]);

  // ── Tab 1: Day Book Entries State ────────────────────────────────
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [entriesTotals, setEntriesTotals] = useState({ total_debit: 0, total_credit: 0, net_balance: 0, total: 0 });
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [entriesLoading, setEntriesLoading] = useState<boolean>(false);

  // Filters for Day Book
  const [fCompany, setFCompany] = useState<string>("");
  const [fType, setFType] = useState<string>("");
  const [fAcctName, setFAcctName] = useState<string>("");
  const [fPeriod, setFPeriod] = useState<string>("month");
  const [fFrom, setFFrom] = useState<string>("");
  const [fTo, setFTo] = useState<string>("");
  const [fRefType, setFRefType] = useState<string>("");
  const [fRefNum, setFRefNum] = useState<string>("");
  const [fStatuses, setFStatuses] = useState<string[]>([]);
  const [statusDropdownOpen, setStatusDropdownOpen] = useState<boolean>(false);

  // ── Tab 2: Create Ledger Form State ──────────────────────────────
  const [cCompany, setCCompany] = useState<string>("");
  const [cType, setCType] = useState<string>("CASH");
  const [cName, setCName] = useState<string>("");
  const [cCode, setCCode] = useState<string>("");
  const [cGroup, setCGroup] = useState<string>("");
  const [cDesc, setCDesc] = useState<string>("");
  const [cAccountNumber, setCAccountNumber] = useState<string>("");
  const [cIfscCode, setCIfscCode] = useState<string>("");
  const [cBankName, setCBankName] = useState<string>("");
  const [cOB, setCOB] = useState<string>("");
  const [cOBType, setCOBType] = useState<"DEBIT" | "CREDIT">("DEBIT");
  const [cOBDate, setCOBDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [creatingLedger, setCreatingLedger] = useState<boolean>(false);

  // ── Tab 3: Chart of Accounts State ───────────────────────────────
  const [masters, setMasters] = useState<LedgerMaster[]>([]);
  const [mastersLoading, setMastersLoading] = useState<boolean>(false);
  const [lCompany, setLCompany] = useState<string>("");
  const [lType, setLType] = useState<string>("");
  const [lStatus, setLStatus] = useState<string>("");
  const [lSearch, setLSearch] = useState<string>("");

  // ── Tab 4: Bank Accounts State ───────────────────────────────────
  const [bankMasters, setBankMasters] = useState<LedgerMaster[]>([]);
  const [bankHeads, setBankHeads] = useState<GLHead[]>([]);
  const [companyBanks, setCompanyBanks] = useState<CompanyBank[]>([]);
  const [banksLoading, setBanksLoading] = useState<boolean>(false);
  const [headsCompany, setHeadsCompany] = useState<string>("");

  // ── Tab 5: Transaction Accounts State ────────────────────────────
  const [txHeads, setTxHeads] = useState<GLHead[]>([]);
  const [txMastersMap, setTxMastersMap] = useState<Record<string, LedgerMaster>>({});
  const [txLoading, setTxLoading] = useState<boolean>(false);
  const [aCompany, setACompany] = useState<string>("");
  const [aType, setAType] = useState<string>("");
  const [aSearch, setASearch] = useState<string>("");
  const [acctSort, setAcctSort] = useState<{ col: keyof GLHead; dir: number }>({ col: "account_name", dir: 1 });

  // ── Tab 6: Parties & Vendors State ───────────────────────────────
  const [partiesList, setPartiesList] = useState<PartyVendorRow[]>([]);
  const [partiesLoading, setPartiesLoading] = useState<boolean>(false);
  const [pvCompany, setPvCompany] = useState<string>("");
  const [pvShow, setPvShow] = useState<"all" | "party" | "vendor">("all");
  const [pvSearch, setPvSearch] = useState<string>("");

  // ── Tab 7: Company Summary State ─────────────────────────────────
  const [cwiseRows, setCwiseRows] = useState<CompanySummaryRow[]>([]);
  const [cwiseLoading, setCwiseLoading] = useState<boolean>(false);
  const [cwCompany, setCwCompany] = useState<string>("");
  const [cwType, setCwType] = useState<string>("");

  // ── Modals State ─────────────────────────────────────────────────
  // 1. Voucher View Modal
  const [voucherModalOpen, setVoucherModalOpen] = useState<boolean>(false);
  const [voucherRef, setVoucherRef] = useState<string>("");
  const [voucherEntries, setVoucherEntries] = useState<LedgerEntry[]>([]);
  const [voucherLoading, setVoucherLoading] = useState<boolean>(false);

  // 2. Edit Day Book Entry Modal
  const [editEntryModalOpen, setEditEntryModalOpen] = useState<boolean>(false);
  const [eeEntryId, setEeEntryId] = useState<number | null>(null);
  const [eeDate, setEeDate] = useState<string>("");
  const [eeEntryType, setEeEntryType] = useState<"DEBIT" | "CREDIT">("DEBIT");
  const [eeAmount, setEeAmount] = useState<string>("");
  const [eeVoucherType, setEeVoucherType] = useState<string>("");
  const [eeAccountType, setEeAccountType] = useState<string>("CASH");
  const [eeAccountName, setEeAccountName] = useState<string>("");
  const [eePartyType, setEePartyType] = useState<string>("CUSTOMER");
  const [eeRefNum, setEeRefNum] = useState<string>("");
  const [eeParticulars, setEeParticulars] = useState<string>("");
  const [eeNarration, setEeNarration] = useState<string>("");
  const [eeCounterId, setEeCounterId] = useState<string>("");
  const [eeRefType, setEeRefType] = useState<string>("");
  const [eeCompanyId, setEeCompanyId] = useState<number | null>(null);
  const [eeSaving, setEeSaving] = useState<boolean>(false);
  const [eeAcctSuggestions, setEeAcctSuggestions] = useState<string[]>([]);
  const [eeParticularsSuggestions, setEeParticularsSuggestions] = useState<string[]>([]);
  const [showAcctDrop, setShowAcctDrop] = useState<boolean>(false);
  const [showPartDrop, setShowPartDrop] = useState<boolean>(false);

  // 3. Edit Ledger Master Modal
  const [editMasterModalOpen, setEditMasterModalOpen] = useState<boolean>(false);
  const [eMasterId, setEMasterId] = useState<number | null>(null);
  const [eName, setEName] = useState<string>("");
  const [eCode, setECode] = useState<string>("");
  const [eGroup, setEGroup] = useState<string>("");
  const [eDesc, setEDesc] = useState<string>("");
  const [eTypeDisplay, setETypeDisplay] = useState<string>("");
  const [eCompanyDisplay, setECompanyDisplay] = useState<string>("");
  const [eAccountNumber, setEAccountNumber] = useState<string>("");
  const [eIfscCode, setEIfscCode] = useState<string>("");
  const [eBankName, setEBankName] = useState<string>("");
  const [eOB, setEOB] = useState<string>("");
  const [eOBType, setEOBType] = useState<"DEBIT" | "CREDIT">("DEBIT");
  const [eOBDate, setEOBDate] = useState<string>("");
  const [eSaving, setESaving] = useState<boolean>(false);

  // 4. Add Party Modal
  const [addPartyModalOpen, setAddPartyModalOpen] = useState<boolean>(false);
  const [apStep, setApStep] = useState<1 | 2>(1);
  const [apType, setApType] = useState<"VENDOR" | "EXTERNAL" | "PARTNER">("VENDOR");
  const [apVendorTab, setApVendorTab] = useState<"basic" | "contacts" | "address" | "bank">("basic");
  const [apSelectedCos, setApSelectedCos] = useState<{ id: string | number; name: string }[]>([]);
  const [apSaving, setApSaving] = useState<boolean>(false);

  // Vendor Form fields
  const [apVName, setApVName] = useState<string>("");
  const [apVCode, setApVCode] = useState<string>("");
  const [apVType, setApVType] = useState<string>("BOTH");
  const [apVPhone, setApVPhone] = useState<string>("");
  const [apVEmail, setApVEmail] = useState<string>("");
  const [apVGst, setApVGst] = useState<string>("");
  const [apVPan, setApVPan] = useState<string>("");
  const [apVGstType, setApVGstType] = useState<string>("CGST_SGST");
  const [apVC1Name, setApVC1Name] = useState<string>("");
  const [apVC1Phone, setApVC1Phone] = useState<string>("");
  const [apVC1Desig, setApVC1Desig] = useState<string>("");
  const [apVC2Name, setApVC2Name] = useState<string>("");
  const [apVC2Phone, setApVC2Phone] = useState<string>("");
  const [apVC2Desig, setApVC2Desig] = useState<string>("");
  const [apVWebsite, setApVWebsite] = useState<string>("");
  const [apVAddress, setApVAddress] = useState<string>("");
  const [apVPincode, setApVPincode] = useState<string>("");
  const [apVCity, setApVCity] = useState<string>("");
  const [apVState, setApVState] = useState<string>("");
  const [apVML1Label, setApVML1Label] = useState<string>("");
  const [apVML1, setApVML1] = useState<string>("");
  const [apVML2Label, setApVML2Label] = useState<string>("");
  const [apVML2, setApVML2] = useState<string>("");
  const [apVShipAddress, setApVShipAddress] = useState<string>("");
  const [apVShipPincode, setApVShipPincode] = useState<string>("");
  const [apVShipCity, setApVShipCity] = useState<string>("");
  const [apVShipState, setApVShipState] = useState<string>("");
  const [apVBankName, setApVBankName] = useState<string>("");
  const [apVBankBranch, setApVBankBranch] = useState<string>("");
  const [apVAcctNo, setApVAcctNo] = useState<string>("");
  const [apVIfsc, setApVIfsc] = useState<string>("");
  const [apVAcctHolder, setApVAcctHolder] = useState<string>("");
  const [apVUpi, setApVUpi] = useState<string>("");
  const [apVPayTerms, setApVPayTerms] = useState<string>("COD");
  const [apVCreditLimit, setApVCreditLimit] = useState<string>("");
  const [apVCreditDays, setApVCreditDays] = useState<string>("");
  const [apVTerms, setApVTerms] = useState<string>("");

  // External Party Form fields
  const [apExtName, setApExtName] = useState<string>("");
  const [apExtPhone, setApExtPhone] = useState<string>("");
  const [apExtEmail, setApExtEmail] = useState<string>("");
  const [apExtNotes, setApExtNotes] = useState<string>("");

  // ── Company Name Resolver ────────────────────────────────────────
  const getCompanyName = useCallback(
    (coId: number | string | undefined | null) => {
      if (!coId) return "All Companies";
      const c = companies.find((x) => String(x.id) === String(coId));
      return c ? c.company_name || c.name || `Company #${coId}` : `Company #${coId}`;
    },
    [companies]
  );

  // ── Load Companies on mount ──────────────────────────────────────
  const loadCompanies = async () => {
    try {
      const resp = await api.get("/staff/accounts/companies?page_size=100");
      const list = resp.data.companies || resp.data.items || (Array.isArray(resp.data) ? resp.data : []);
      setCompanies(list);
    } catch (e) {
      console.error("Failed to load companies", e);
    }
  };

  // ── Period Shortcut Calculator ───────────────────────────────────
  const applyPeriodPreset = (preset: string) => {
    setFPeriod(preset);
    const today = new Date();
    const toIso = (d: Date) => d.toISOString().split("T")[0];
    const endOfMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth() + 1, 0);
    const endOfQuarter = (d: Date) => {
      const q = [2, 2, 2, 5, 5, 5, 8, 8, 8, 11, 11, 11][d.getMonth()];
      return new Date(d.getFullYear(), q + 1, 0);
    };
    const fyStart = () => {
      const m = today.getMonth();
      const y = m >= 3 ? today.getFullYear() : today.getFullYear() - 1;
      return new Date(y, 3, 1);
    };
    const cap = (d: Date) => (d > today ? today : d);

    if (preset === "month") {
      setFFrom(toIso(new Date(today.getFullYear(), today.getMonth(), 1)));
      setFTo(toIso(cap(endOfMonth(today))));
    } else if (preset === "quarter") {
      const qStart = [0, 0, 0, 3, 3, 3, 6, 6, 6, 9, 9, 9][today.getMonth()];
      setFFrom(toIso(new Date(today.getFullYear(), qStart, 1)));
      setFTo(toIso(cap(endOfQuarter(today))));
    } else if (preset === "fy") {
      setFFrom(toIso(fyStart()));
      setFTo(toIso(today));
    } else if (preset === "overall") {
      setFFrom("");
      setFTo(toIso(today));
    }
  };

  // ── Load Day Book Entries ────────────────────────────────────────
  const loadLedgerEntries = async (targetPage: number = 1) => {
    setEntriesLoading(true);
    setPage(targetPage);
    try {
      const params: Record<string, string | number> = {
        page: targetPage,
        page_size: 50
      };
      if (fCompany) params.company_id = fCompany;
      if (fType) params.account_type = fType;
      if (fAcctName) params.account_name = fAcctName;
      if (fFrom) params.date_from = fFrom;
      if (fTo) params.date_to = fTo;
      if (fRefType) params.reference_type = fRefType;
      if (fRefNum) params.reference_number = fRefNum;
      if (glTabStatus === "DELETED") {
        params.source_status = "CANCELLED";
      } else if (fStatuses.length > 0) {
        params.source_status = fStatuses.join(",");
      }

      const resp = await api.get("/staff/accounts/general-ledger/entries", { params });
      const d = resp.data || {};
      setEntries(d.entries || []);
      setTotalPages(d.total_pages || 1);
      setEntriesTotals({
        total_debit: d.totals?.total_debit || 0,
        total_credit: d.totals?.total_credit || 0,
        net_balance: d.totals?.net_balance || 0,
        total: d.total || 0
      });
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load ledger entries");
    } finally {
      setEntriesLoading(false);
    }
  };

  // ── Load Chart of Accounts (Masters) ─────────────────────────────
  const loadMasters = async () => {
    setMastersLoading(true);
    try {
      const params: Record<string, string | number> = { page_size: 500 };
      if (lCompany) params.company_id = lCompany;
      if (lType) params.account_type = lType;
      if (lStatus !== "") params.is_active = lStatus;
      if (lSearch) params.search = lSearch;

      const resp = await api.get("/staff/accounts/ledger-masters", { params });
      setMasters(resp.data?.masters || []);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load ledger accounts");
    } finally {
      setMastersLoading(false);
    }
  };

  // ── Load Bank Accounts ───────────────────────────────────────────
  const loadBankAccounts = async () => {
    setBanksLoading(true);
    try {
      const mParams: Record<string, string | number> = { page_size: 500, account_type: "BANK" };
      const hParams: Record<string, string | number> = { account_type: "BANK" };
      const bParams: Record<string, string | number> = {};
      if (headsCompany) {
        mParams.company_id = headsCompany;
        hParams.company_id = headsCompany;
        bParams.company_id = headsCompany;
      }

      const [mr, hr, br] = await Promise.all([
        api.get("/staff/accounts/ledger-masters", { params: mParams }),
        api.get("/staff/accounts/general-ledger/heads", { params: hParams }),
        api.get("/staff/accounts/general-ledger/company-banks", { params: bParams })
      ]);

      setBankMasters(mr.data?.masters || []);
      setBankHeads(hr.data?.heads || []);
      setCompanyBanks(br.data?.banks || []);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load bank accounts");
    } finally {
      setBanksLoading(false);
    }
  };

  // ── Load Transaction Accounts ────────────────────────────────────
  const loadTransactionAccounts = async () => {
    setTxLoading(true);
    try {
      const params: Record<string, string | number> = {};
      if (aCompany) params.company_id = aCompany;
      if (aType) params.account_type = aType;

      const mParams: Record<string, string | number> = { page_size: 500 };
      if (aCompany) mParams.company_id = aCompany;
      if (aType) mParams.account_type = aType;

      const [resp, mResp] = await Promise.all([
        api.get("/staff/accounts/general-ledger/heads", { params }),
        api.get("/staff/accounts/ledger-masters", { params: mParams })
      ]);

      const heads = resp.data?.heads || [];
      const mastersList: LedgerMaster[] = mResp.data?.masters || [];
      const map: Record<string, LedgerMaster> = {};
      mastersList.forEach((m) => {
        map[`${m.account_name}|${m.company_id}`] = m;
      });

      setTxHeads(heads);
      setTxMastersMap(map);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load transaction accounts");
    } finally {
      setTxLoading(false);
    }
  };

  // ── Load Parties & Vendors ───────────────────────────────────────
  const loadParties = async () => {
    setPartiesLoading(true);
    try {
      const rows: PartyVendorRow[] = [];
      const co = pvCompany;

      if (pvShow !== "vendor") {
        for (const ptype of ["PARTY", "SUNDRY_DEBTOR", "SUNDRY_CREDITOR"] as const) {
          const params: Record<string, string | number> = { page_size: 500, account_type: ptype };
          if (co) params.company_id = co;
          const r = await api.get("/staff/accounts/ledger-masters", { params });
          (r.data?.masters || []).forEach((m: LedgerMaster) => {
            rows.push({
              id: m.id,
              kind: ptype,
              name: m.account_name,
              code: m.account_code || "",
              phone: "",
              email: "",
              ob: m.opening_balance || 0,
              ob_type: m.opening_balance_type || "DEBIT",
              company_id: m.company_id
            });
          });
        }
      }

      if (pvShow !== "party") {
        const vParams: Record<string, string | number> = { page_size: 100 };
        if (co) vParams.company_id = co;
        const vr = await api.get("/staff/accounts/vendors", { params: vParams });
        const list = vr.data?.vendors || vr.data?.items || (Array.isArray(vr.data) ? vr.data : []);
        list.forEach((v: any) => {
          rows.push({
            id: v.id,
            kind: "VENDOR",
            name: v.vendor_name || v.name,
            code: v.vendor_code || "",
            phone: v.phone || "",
            email: v.email || "",
            gstin: v.gst_number || "",
            acct: v.account_number || "",
            ifsc: v.ifsc_code || "",
            bank: v.bank_name || "",
            ob: v.opening_balance || 0,
            ob_type: v.opening_balance_type || "DEBIT",
            company_id: v.company_id
          });
        });
      }

      setPartiesList(rows);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load parties & vendors");
    } finally {
      setPartiesLoading(false);
    }
  };

  // ── Load Company Summary ─────────────────────────────────────────
  const loadCompanySummary = async () => {
    setCwiseLoading(true);
    try {
      const mParams: Record<string, string | number> = { page_size: 500 };
      if (cwCompany) mParams.company_id = cwCompany;
      if (cwType) mParams.account_type = cwType;

      const hParams: Record<string, string | number> = { x: 1 };
      if (cwCompany) hParams.company_id = cwCompany;
      if (cwType) hParams.account_type = cwType;

      const [mr, hr] = await Promise.all([
        api.get("/staff/accounts/ledger-masters", { params: mParams }),
        api.get("/staff/accounts/general-ledger/heads", { params: hParams })
      ]);

      const mList: LedgerMaster[] = mr.data?.masters || [];
      const glList: GLHead[] = hr.data?.heads || [];

      const headMap: Record<string, GLHead> = {};
      glList.forEach((h) => {
        headMap[`${h.account_name}|${h.company_id}`] = h;
      });

      const seen = new Set<string>();
      const merged: CompanySummaryRow[] = mList.map((m) => {
        const key = `${m.account_name}|${m.company_id}`;
        seen.add(key);
        const gl = headMap[key];
        const ob = parseFloat(String(m.opening_balance || 0));
        const obSigned = ob * (m.opening_balance_type === "DEBIT" ? 1 : -1);
        return {
          account_type: m.account_type,
          account_name: m.account_name,
          company_id: m.company_id,
          master_id: m.id,
          total_debit: gl ? gl.total_debit || 0 : obSigned > 0 ? ob : 0,
          total_credit: gl ? gl.total_credit || 0 : obSigned < 0 ? ob : 0,
          balance: gl ? gl.balance || 0 : obSigned,
          last_date: gl ? gl.last_date || null : m.opening_balance_date || null,
          has_gl: !!gl
        };
      });

      glList.forEach((h) => {
        const key = `${h.account_name}|${h.company_id}`;
        if (!seen.has(key)) {
          merged.push({
            account_type: h.account_type,
            account_name: h.account_name,
            company_id: h.company_id,
            total_debit: h.total_debit || 0,
            total_credit: h.total_credit || 0,
            balance: h.balance || 0,
            last_date: h.last_date || null,
            has_gl: true
          });
        }
      });

      setCwiseRows(merged);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load company summary");
    } finally {
      setCwiseLoading(false);
    }
  };

  // ── Refresh all active views helper ──────────────────────────────
  const refreshAllViews = useCallback(() => {
    loadLedgerEntries(page);
    if (activeTab === "cards") loadMasters();
    else if (activeTab === "banks") loadBankAccounts();
    else if (activeTab === "txaccounts") loadTransactionAccounts();
    else if (activeTab === "parties") loadParties();
    else if (activeTab === "cwise") loadCompanySummary();
  }, [activeTab, page]);

  // ── Initialize ───────────────────────────────────────────────────
  useEffect(() => {
    loadCompanies();
    applyPeriodPreset("month");
  }, []);

  useEffect(() => {
    loadLedgerEntries(1);
  }, [glTabStatus]);

  // Switch tabs effect
  useEffect(() => {
    if (activeTab === "cards") loadMasters();
    else if (activeTab === "banks") loadBankAccounts();
    else if (activeTab === "txaccounts") loadTransactionAccounts();
    else if (activeTab === "parties") loadParties();
    else if (activeTab === "cwise") loadCompanySummary();
  }, [activeTab]);

  // ── Drill Down to Day Book ───────────────────────────────────────
  const drillDown = (type: string, name: string, co?: number | string) => {
    setFType(type);
    setFAcctName(name);
    if (co) setFCompany(String(co));
    setActiveTab("entries");
    // Trigger load
    setTimeout(() => {
      loadLedgerEntries(1);
    }, 50);
  };

  // ── Create Ledger Form Handler ───────────────────────────────────
  const handleCreateLedger = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cCompany) {
      toast.error("Please select a company.");
      return;
    }
    if (!cName.trim()) {
      toast.error("Please enter an account name.");
      return;
    }

    setCreatingLedger(true);
    try {
      const obNum = parseFloat(cOB) || 0;
      const payload = {
        company_id: parseInt(cCompany),
        account_type: cType,
        account_name: cName.trim(),
        account_code: cCode.trim() || null,
        parent_group: cGroup.trim() || null,
        description: cDesc.trim() || null,
        opening_balance: obNum > 0 ? obNum : 0,
        opening_balance_type: cOBType,
        opening_balance_date: cOBDate || null,
        account_number: cAccountNumber.trim() || null,
        ifsc_code: cIfscCode.trim().toUpperCase() || null,
        bank_name: cBankName.trim() || null
      };

      await api.post("/staff/accounts/ledger-masters", payload);
      toast.success(`Ledger "${cName.trim()}" created successfully!`);
      // Reset form
      setCName("");
      setCCode("");
      setCGroup("");
      setCDesc("");
      setCAccountNumber("");
      setCIfscCode("");
      setCBankName("");
      setCOB("");
      setCOBType("DEBIT");
      setCOBDate(new Date().toISOString().slice(0, 10));

      refreshAllViews();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.response?.data?.message || err.message || "Failed to create ledger");
    } finally {
      setCreatingLedger(false);
    }
  };

  // ── Toggle / Delete Ledger Master ────────────────────────────────
  const toggleMasterActive = async (id: number, current: boolean) => {
    try {
      await api.put(`/staff/accounts/ledger-masters/${id}`, { is_active: !current });
      toast.success(`Ledger account marked as ${!current ? "Active" : "Inactive"}`);
      refreshAllViews();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to update status");
    }
  };

  const deleteMaster = async (id: number, name: string) => {
    if (!confirm(`Delete ledger master "${name}"?\n\nThis action cannot be undone. Only permitted if no transactions are linked.`)) return;
    try {
      await api.delete(`/staff/accounts/ledger-masters/${id}`);
      toast.success(`Ledger "${name}" deleted`);
      refreshAllViews();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.response?.data?.message || e.message || "Cannot delete ledger");
    }
  };

  // ── Delete Day Book Entry ────────────────────────────────────────
  const deleteEntry = async (entryId: number) => {
    if (!confirm(`Delete ledger entry #${entryId}? This will recompute running balances for the affected account.`)) return;
    try {
      await api.delete(`/staff/accounts/general-ledger/entries/${entryId}`);
      toast.success("Entry deleted and balances recomputed.");
      refreshAllViews();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Delete failed");
    }
  };

  // ── Edit Day Book Entry Modal Handlers ───────────────────────────
  const openEntryEdit = async (id: number) => {
    try {
      const resp = await api.get(`/staff/accounts/general-ledger/entries/${id}`);
      const entry: LedgerEntry = resp.data.entry || resp.data;
      setEeEntryId(entry.id);
      setEeRefType(entry.reference_type || "");
      setEeDate(entry.transaction_date || "");
      setEeEntryType(entry.entry_type || "DEBIT");
      setEeAmount(String(entry.debit_amount > 0 ? entry.debit_amount : entry.credit_amount));
      setEeVoucherType(entry.voucher_type || "");
      setEeAccountType(entry.account_type || "CASH");
      setEeAccountName(entry.account_name || "");
      setEeCompanyId(entry.company_id);
      setEeRefNum(entry.reference_number || "");
      setEeParticulars(entry.particulars || "");
      setEeNarration(entry.narration || "");
      setEeCounterId("");
      if (entry.party_type) setEePartyType(entry.party_type);
      setEditEntryModalOpen(true);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load entry");
    }
  };

  const saveEntryEdit = async () => {
    if (!eeEntryId) return;
    const amt = parseFloat(eeAmount);
    if (isNaN(amt) || amt <= 0) {
      toast.error("Amount must be greater than zero.");
      return;
    }
    if (!eeAccountName.trim()) {
      toast.error("Account name is required.");
      return;
    }

    setEeSaving(true);
    try {
      const payload: Record<string, any> = {
        transaction_date: eeDate,
        entry_type: eeEntryType,
        amount: amt,
        voucher_type: eeVoucherType || null,
        account_type: eeAccountType,
        account_name: eeAccountName.trim(),
        reference_number: eeRefNum.trim() || null,
        particulars: eeParticulars.trim() || null,
        narration: eeNarration.trim() || null
      };
      if (PARTY_LIKE_TYPES.has(eeAccountType)) {
        payload.party_type = eePartyType;
      }
      if (eeCounterId.trim()) {
        payload.counter_entry_id = parseInt(eeCounterId.trim());
      }

      await api.patch(`/staff/accounts/general-ledger/entries/${eeEntryId}`, payload);
      toast.success("Entry updated and running balances recomputed!");
      setEditEntryModalOpen(false);
      refreshAllViews();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.response?.data?.message || e.message || "Failed to update entry");
    } finally {
      setEeSaving(false);
    }
  };

  // Search accounts for entry edit modal
  const searchEeAccounts = async () => {
    try {
      if (PARTY_LIKE_TYPES.has(eeAccountType)) {
        const resp = await api.get("/staff/accounts/party-ledger/summary", {
          params: eeCompanyId ? { company_id: eeCompanyId } : {}
        });
        const names = (resp.data?.parties || []).map((p: any) => p.party_name);
        setEeAcctSuggestions(names);
      } else {
        const resp = await api.get("/staff/accounts/ledger-masters", {
          params: {
            page_size: 200,
            account_type: eeAccountType,
            ...(eeCompanyId ? { company_id: eeCompanyId } : {})
          }
        });
        const names = (resp.data?.masters || []).map((m: any) => m.account_name);
        setEeAcctSuggestions(names);
      }
      setShowAcctDrop(true);
    } catch (e) {
      setEeAcctSuggestions([]);
    }
  };

  const searchEeParticulars = async () => {
    try {
      const [r1, r2] = await Promise.all([
        api.get("/staff/accounts/ledger-masters", {
          params: { page_size: 200, ...(eeCompanyId ? { company_id: eeCompanyId } : {}) }
        }),
        api.get("/staff/accounts/party-ledger/summary", {
          params: eeCompanyId ? { company_id: eeCompanyId } : {}
        })
      ]);
      const mNames = (r1.data?.masters || []).map((m: any) => m.account_name);
      const pNames = (r2.data?.parties || []).map((p: any) => p.party_name);
      const unique = Array.from(new Set([...mNames, ...pNames]));
      setEeParticularsSuggestions(unique);
      setShowPartDrop(true);
    } catch (e) {
      setEeParticularsSuggestions([]);
    }
  };

  // ── Edit Ledger Master Modal Handlers ────────────────────────────
  const openMasterEdit = async (id: number) => {
    try {
      const resp = await api.get(`/staff/accounts/ledger-masters/${id}`);
      const m: LedgerMaster = resp.data.master || resp.data;
      setEMasterId(m.id);
      setEName(m.account_name || "");
      setECode(m.account_code || "");
      setEGroup(m.parent_group || "");
      setEDesc(m.description || "");
      setETypeDisplay(m.account_type || "");
      setECompanyDisplay(getCompanyName(m.company_id));
      setEAccountNumber(m.account_number || "");
      setEIfscCode(m.ifsc_code || "");
      setEBankName(m.bank_name || "");
      setEOB(m.opening_balance ? String(m.opening_balance) : "");
      setEOBType(m.opening_balance_type || "DEBIT");
      setEOBDate(m.opening_balance_date || new Date().toISOString().slice(0, 10));
      setEditMasterModalOpen(true);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || "Failed to load ledger details");
    }
  };

  const saveMasterEdit = async () => {
    if (!eMasterId) return;
    if (!eName.trim()) {
      toast.error("Account name is required.");
      return;
    }

    setESaving(true);
    try {
      const obVal = parseFloat(eOB) || 0;
      await api.put(`/staff/accounts/ledger-masters/${eMasterId}`, {
        account_name: eName.trim(),
        account_code: eCode.trim() || null,
        parent_group: eGroup.trim() || null,
        description: eDesc.trim() || null,
        opening_balance: obVal,
        opening_balance_type: eOBType,
        opening_balance_date: eOBDate || null,
        account_number: eAccountNumber.trim() || null,
        ifsc_code: eIfscCode.trim().toUpperCase() || null,
        bank_name: eBankName.trim() || null
      });

      toast.success("Ledger updated! Opening balance synced to ledger.");
      setEditMasterModalOpen(false);
      refreshAllViews();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.response?.data?.message || e.message || "Failed to save changes");
    } finally {
      setESaving(false);
    }
  };

  // ── Voucher View Modal Handler ───────────────────────────────────
  const openVoucherView = async (refNo: string, coId?: number | string) => {
    setVoucherRef(refNo);
    setVoucherModalOpen(true);
    setVoucherLoading(true);
    try {
      const params: Record<string, string | number> = {
        page: 1,
        page_size: 100,
        reference_number: refNo
      };
      if (coId) params.company_id = coId;
      const resp = await api.get("/staff/accounts/general-ledger/entries", { params });
      setVoucherEntries(resp.data?.entries || resp.data?.items || []);
    } catch (e: any) {
      toast.error("Failed to load voucher entries");
    } finally {
      setVoucherLoading(false);
    }
  };

  // ── Add Party Modal Handlers ─────────────────────────────────────
  const openAddParty = () => {
    setApStep(1);
    setApType("VENDOR");
    setApVendorTab("basic");
    setApSelectedCos([]);
    setAddPartyModalOpen(true);
  };

  const apLookupPin = async (pin: string, target: "Vendor" | "VendorShip") => {
    if (!pin || pin.length !== 6) return;
    try {
      const r = await fetch(`https://api.postalpincode.in/pincode/${pin}`);
      const d = await r.json();
      if (d[0]?.Status === "Success") {
        const p = d[0].PostOffice[0];
        if (target === "Vendor") {
          if (!apVCity) setApVCity(p.Division || p.Name || "");
          if (!apVState) setApVState(p.State || "");
        } else {
          if (!apVShipCity) setApVShipCity(p.Division || p.Name || "");
          if (!apVShipState) setApVShipState(p.State || "");
        }
      }
    } catch (e) {}
  };

  const handleVendorSubmit = async () => {
    if (!apVName.trim()) {
      toast.error("Vendor name is required.");
      return;
    }
    if (!apVCode.trim()) {
      toast.error("Vendor code is required.");
      return;
    }
    if (!apSelectedCos.length) {
      toast.error("Please select at least one applicable company.");
      return;
    }

    setApSaving(true);
    try {
      await api.post("/staff/accounts/vendors", {
        vendor_name: apVName.trim(),
        vendor_code: apVCode.trim().toUpperCase(),
        vendor_type: apVType,
        phone: apVPhone.trim() || null,
        email: apVEmail.trim().toLowerCase() || null,
        gst_number: apVGst.trim().toUpperCase() || null,
        pan_number: apVPan.trim().toUpperCase() || null,
        gst_type: apVGstType,
        contact_person_1_name: apVC1Name.trim() || null,
        contact_person_1_phone: apVC1Phone.trim() || null,
        contact_person_1_designation: apVC1Desig.trim() || null,
        contact_person_2_name: apVC2Name.trim() || null,
        contact_person_2_phone: apVC2Phone.trim() || null,
        contact_person_2_designation: apVC2Desig.trim() || null,
        website_url: apVWebsite.trim() || null,
        address: apVAddress.trim() || null,
        pincode: apVPincode.trim() || null,
        city: apVCity.trim() || null,
        state: apVState.trim() || null,
        map_link_1_label: apVML1Label.trim() || null,
        map_link_1: apVML1.trim() || null,
        map_link_2_label: apVML2Label.trim() || null,
        map_link_2: apVML2.trim() || null,
        ship_to_address: apVShipAddress.trim() || null,
        ship_to_pincode: apVShipPincode.trim() || null,
        ship_to_city: apVShipCity.trim() || null,
        ship_to_state: apVShipState.trim() || null,
        bank_name: apVBankName.trim() || null,
        bank_branch: apVBankBranch.trim() || null,
        account_number: apVAcctNo.trim() || null,
        ifsc_code: apVIfsc.trim().toUpperCase() || null,
        account_holder_name: apVAcctHolder.trim() || null,
        upi_id: apVUpi.trim() || null,
        payment_terms: apVPayTerms,
        credit_limit: parseFloat(apVCreditLimit) || 0,
        credit_days: parseInt(apVCreditDays) || 0,
        terms_conditions: apVTerms.trim() || null,
        applicable_companies: apSelectedCos.map((c) => parseInt(String(c.id)))
      });

      toast.success(`Vendor "${apVName}" created! Party ledger added.`);
      setAddPartyModalOpen(false);
      refreshAllViews();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.response?.data?.message || e.message || "Failed to create vendor");
    } finally {
      setApSaving(false);
    }
  };

  const handleExternalSubmit = async () => {
    if (!apExtName.trim()) {
      toast.error("Name is required.");
      return;
    }
    if (!apExtPhone.trim()) {
      toast.error("Mobile number is required.");
      return;
    }

    setApSaving(true);
    try {
      await api.post("/staff/accounts/party-search/add-manual", {
        name: apExtName.trim(),
        phone: apExtPhone.trim() || null,
        email: apExtEmail.trim() || null,
        notes: apExtNotes.trim() || null
      });

      toast.success(`External party "${apExtName}" added!`);
      setAddPartyModalOpen(false);
      refreshAllViews();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.response?.data?.message || e.message || "Failed to save party");
    } finally {
      setApSaving(false);
    }
  };

  // ── Calculated Day Book Opening Balance ──────────────────────────
  const dayBookOpeningBalance = useMemo(() => {
    if (!entries.length) return 0;
    const isMultiAccount = !fAcctName;
    const totDr = entriesTotals.total_debit;
    const totCr = entriesTotals.total_credit;

    let closingBal = 0;
    if (isMultiAccount) {
      const uniqueBals: Record<string, number> = {};
      entries.forEach((e) => {
        if (!(e.account_name in uniqueBals)) {
          uniqueBals[e.account_name] = parseFloat(String(e.running_balance || 0));
        }
      });
      closingBal = Object.values(uniqueBals).reduce((s, v) => s + v, 0);
    } else {
      closingBal = parseFloat(String(entries[0].running_balance || 0));
    }

    const isDebitNorm = DEBIT_NORMAL_TYPES.includes((fType || entries[0]?.account_type || "").toUpperCase());
    return isDebitNorm ? closingBal - (totDr - totCr) : closingBal - (totCr - totDr);
  }, [entries, fAcctName, fType, entriesTotals]);

  // Distinct days count
  const dayCount = useMemo(() => {
    return new Set(entries.map((e) => e.transaction_date)).size || 1;
  }, [entries]);

  return (
    <div className="min-h-screen bg-slate-50/60 pb-16">
      <Toaster position="top-right" />

      {/* ── Page Header ────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center shadow-md shadow-indigo-200">
                  <BookOpen className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">General Ledger</h1>
                  <p className="text-xs text-slate-500 font-medium mt-0.5">
                    Day Book · Chart of Accounts · Bank Accounts · Transaction Accounts · Parties · Company Summary
                  </p>
                </div>
              </div>
            </div>

            {/* Header Action Buttons */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={openAddParty}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:text-indigo-600 transition-all shadow-xs"
              >
                <UserPlus className="h-3.5 w-3.5 text-indigo-500" />
                Add Party
              </button>
              <Link
                href="/staff/accounts/vendors"
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:text-indigo-600 transition-all shadow-xs"
              >
                <Store className="h-3.5 w-3.5 text-amber-500" />
                Add Vendor
              </Link>
              <button
                type="button"
                onClick={() => {
                  setActiveTab("create");
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-all shadow-xs"
              >
                <PlusCircle className="h-3.5 w-3.5" />
                Add Ledger
              </button>
              <Link
                href="/staff/accounts/journal-voucher"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-all shadow-sm shadow-emerald-200"
              >
                <Scale className="h-3.5 w-3.5" />
                New Journal / Transfer
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-6">
        {/* Company context bar */}
        {fCompany && (
          <div className="bg-indigo-50/80 border border-indigo-200 rounded-xl px-4 py-2.5 flex items-center gap-2 text-xs text-indigo-800">
            <Building2 className="h-4 w-4 text-indigo-600 shrink-0" />
            <span>
              Showing data filtered for: <strong className="font-semibold text-indigo-950">{getCompanyName(fCompany)}</strong>
            </span>
          </div>
        )}

        {/* ── Entry-Level Summary Cards (Always Visible) ─────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs border-l-4 border-l-indigo-500 flex flex-col justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Total Entries</span>
            <div className="mt-2 text-2xl font-bold text-slate-900">{entriesTotals.total.toLocaleString("en-IN")}</div>
            <span className="text-[11px] text-slate-400 mt-1">Based on current filters</span>
          </div>

          <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs border-l-4 border-l-red-500 flex flex-col justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Total Debit (Dr)</span>
            <div className="mt-2 text-2xl font-bold text-red-600">{fmt(entriesTotals.total_debit)}</div>
            <span className="text-[11px] text-red-400 mt-1">Money out / Asset addition</span>
          </div>

          <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs border-l-4 border-l-emerald-500 flex flex-col justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Total Credit (Cr)</span>
            <div className="mt-2 text-2xl font-bold text-emerald-600">{fmt(entriesTotals.total_credit)}</div>
            <span className="text-[11px] text-emerald-500 mt-1">Money in / Liabilities</span>
          </div>

          <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs border-l-4 border-l-purple-500 flex flex-col justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Net (Dr − Cr)</span>
            <div className={`mt-2 text-2xl font-bold ${entriesTotals.net_balance >= 0 ? "text-purple-700" : "text-amber-600"}`}>
              {entriesTotals.net_balance < 0 ? "−" : ""}
              {fmt(Math.abs(entriesTotals.net_balance))}
            </div>
            <span className="text-[11px] text-purple-400 mt-1">Overall balance delta</span>
          </div>
        </div>

        {/* ── Main Tab Navigation ────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-slate-200 p-1.5 shadow-xs overflow-x-auto">
          <div className="flex gap-1 min-w-max">
            {[
              { id: "entries", label: "Day Book", icon: BookOpen },
              { id: "create", label: "Add Account", icon: PlusCircle },
              { id: "cards", label: "Chart of Accounts", icon: Layers },
              { id: "banks", label: "Bank Accounts", icon: Landmark },
              { id: "txaccounts", label: "Transaction Accounts", icon: ListFilter },
              { id: "parties", label: "Parties & Vendors", icon: Users },
              { id: "cwise", label: "Company Summary", icon: Building2 }
            ].map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-all ${
                    active
                      ? "bg-indigo-600 text-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/70"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${active ? "text-white" : "text-slate-500"}`} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════
            TAB 1: DAY BOOK / LEDGER ENTRIES
        ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "entries" && (
          <div className="space-y-4">
            {/* Sub-tabs: Active vs Deleted */}
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <button
                onClick={() => setGlTabStatus("ACTIVE")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  glTabStatus === "ACTIVE"
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-300"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                Active Entries
              </button>
              <button
                onClick={() => setGlTabStatus("DELETED")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  glTabStatus === "DELETED"
                    ? "bg-red-50 text-red-700 border border-red-300"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <Trash2 className="h-3.5 w-3.5 text-red-600" />
                Deleted / Cancelled Entries
              </button>
            </div>

            {/* Filter Bar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Company</label>
                  <select
                    value={fCompany}
                    onChange={(e) => setFCompany(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  >
                    <option value="">All Companies</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Account Type</label>
                  <select
                    value={fType}
                    onChange={(e) => setFType(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  >
                    <option value="">All Types</option>
                    <optgroup label="Cash & Bank">
                      <option value="CASH">CASH</option>
                      <option value="BANK">BANK</option>
                      <option value="UPI">UPI</option>
                    </optgroup>
                    <optgroup label="P&L">
                      <option value="INCOME">INCOME</option>
                      <option value="EXPENSE">EXPENSE</option>
                    </optgroup>
                    <optgroup label="Balance Sheet">
                      <option value="SUNDRY_DEBTOR">SUNDRY_DEBTOR</option>
                      <option value="SUNDRY_CREDITOR">SUNDRY_CREDITOR</option>
                      <option value="DUTIES_TAXES">DUTIES_TAXES</option>
                      <option value="STOCK">STOCK</option>
                      <option value="CAPITAL">CAPITAL</option>
                      <option value="LOAN">LOAN</option>
                      <option value="LIABILITY">LIABILITY</option>
                      <option value="ASSET">ASSET</option>
                    </optgroup>
                    <optgroup label="Legacy">
                      <option value="PARTY">PARTY</option>
                    </optgroup>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Account Name</label>
                  <input
                    type="text"
                    value={fAcctName}
                    onChange={(e) => setFAcctName(e.target.value)}
                    placeholder="e.g. Cash Account"
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Ref Type</label>
                  <select
                    value={fRefType}
                    onChange={(e) => setFRefType(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  >
                    <option value="">All</option>
                    <option value="INCOME">INCOME</option>
                    <option value="EXPENSE">EXPENSE</option>
                    <option value="JOURNAL">JOURNAL</option>
                    <option value="PO">PO</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Ref / Voucher #</label>
                  <input
                    type="text"
                    value={fRefNum}
                    onChange={(e) => setFRefNum(e.target.value)}
                    placeholder="IE/JV/PV number"
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  />
                </div>

                {/* Status dropdown */}
                <div className="relative">
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Voucher Status</label>
                  <button
                    type="button"
                    onClick={() => setStatusDropdownOpen(!statusDropdownOpen)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white text-left flex items-center justify-between focus:ring-2 focus:ring-indigo-500 outline-none"
                  >
                    <span className="truncate">
                      {fStatuses.length === 0
                        ? "All Statuses"
                        : fStatuses.length === 1
                        ? fStatuses[0]
                        : `${fStatuses.length} selected`}
                    </span>
                    <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                  </button>

                  {statusDropdownOpen && (
                    <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg z-30 p-2 space-y-1">
                      {[
                        { val: "CONFIRMED", label: "Confirmed" },
                        { val: "MANUAL", label: "Manual Entry" },
                        { val: "TALLY_IMPORT", label: "Tally Import" },
                        { val: "OPENING_BALANCE", label: "Opening Balance" }
                      ].map((item) => {
                        const checked = fStatuses.includes(item.val);
                        return (
                          <label key={item.val} className="flex items-center gap-2 p-1.5 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(e) => {
                                if (e.target.checked) setFStatuses([...fStatuses, item.val]);
                                else setFStatuses(fStatuses.filter((s) => s !== item.val));
                              }}
                              className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            {item.label}
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* Period Quick Presets & Date Range */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Period:</span>
                  {["month", "quarter", "fy", "overall", "custom"].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => applyPeriodPreset(preset)}
                      className={`px-2.5 py-1 text-xs font-semibold rounded-md border transition-all ${
                        fPeriod === preset
                          ? "bg-blue-600 text-white border-blue-600"
                          : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      {preset === "month"
                        ? "This Month"
                        : preset === "quarter"
                        ? "This Quarter"
                        : preset === "fy"
                        ? "This FY"
                        : preset === "overall"
                        ? "Overall"
                        : "Custom"}
                    </button>
                  ))}
                  <div className="flex items-center gap-1.5 ml-2">
                    <input
                      type="date"
                      value={fFrom}
                      onChange={(e) => {
                        setFFrom(e.target.value);
                        setFPeriod("custom");
                      }}
                      className="text-xs border border-slate-300 rounded-md px-2 py-1 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                    <span className="text-xs text-slate-400">to</span>
                    <input
                      type="date"
                      value={fTo}
                      onChange={(e) => {
                        setFTo(e.target.value);
                        setFPeriod("custom");
                      }}
                      className="text-xs border border-slate-300 rounded-md px-2 py-1 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => loadLedgerEntries(1)}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs transition-all"
                  >
                    <Search className="h-3.5 w-3.5" />
                    Search
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setFCompany("");
                      setFType("");
                      setFAcctName("");
                      setFRefType("");
                      setFRefNum("");
                      setFStatuses([]);
                      applyPeriodPreset("month");
                      setTimeout(() => loadLedgerEntries(1), 50);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-all"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Reset
                  </button>
                </div>
              </div>
            </div>

            {/* Day Book Table Container */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-indigo-600" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">Account Ledger Entries</h2>
                </div>
                <span className="text-xs text-slate-500">
                  Page {page} of {totalPages} · {entriesTotals.total} entries
                </span>
              </div>

              {entriesLoading ? (
                <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center">
                  <RefreshCw className="h-6 w-6 animate-spin text-indigo-600 mb-2" />
                  <p className="text-xs font-medium">Loading ledger entries...</p>
                </div>
              ) : entries.length === 0 ? (
                <div className="p-12 text-center text-slate-500">
                  <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                    <BookOpen className="h-6 w-6 text-slate-400" />
                  </div>
                  <p className="text-sm font-semibold text-slate-800">No ledger entries found.</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                    Entries are posted automatically on income confirmation / expense approval, or manually via Journal Voucher.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-indigo-50/60 border-b border-indigo-100 text-slate-700">
                        <th className="py-2.5 px-3 font-semibold whitespace-nowrap">Date</th>
                        <th className="py-2.5 px-3 font-semibold whitespace-nowrap min-w-[140px]">Account</th>
                        <th className="py-2.5 px-3 font-semibold whitespace-nowrap">Type</th>
                        <th className="py-2.5 px-3 font-semibold whitespace-nowrap min-w-[180px]">Particulars / Narration</th>
                        <th className="py-2.5 px-3 font-semibold whitespace-nowrap">Voucher / Ref</th>
                        <th className="py-2.5 px-3 font-semibold whitespace-nowrap">Category</th>
                        <th className="py-2.5 px-3 font-semibold whitespace-nowrap">Sub-Category</th>
                        <th className="py-2.5 px-3 font-semibold text-right text-red-700 min-w-[110px]">Debit (₹)</th>
                        <th className="py-2.5 px-3 font-semibold text-right text-emerald-700 min-w-[110px]">Credit (₹)</th>
                        <th className="py-2.5 px-3 font-semibold text-right min-w-[130px]">Closing Balance</th>
                        <th className="py-2.5 px-3 font-semibold text-center whitespace-nowrap">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {/* Opening Balance Row */}
                      <tr className="bg-blue-50/60 border-b-2 border-blue-200">
                        <td colSpan={7} className="py-2 px-3 font-bold text-blue-900 flex items-center gap-1.5">
                          <Bookmark className="h-3.5 w-3.5 text-blue-600" />
                          Opening Balance
                        </td>
                        <td className="py-2 px-3 text-right text-slate-300 font-mono">—</td>
                        <td className="py-2 px-3 text-right text-slate-300 font-mono">—</td>
                        <td className="py-2 px-3 text-right font-bold">
                          {(() => {
                            const b = fmtBal(dayBookOpeningBalance, fType || entries[0]?.account_type);
                            return (
                              <span className={b.isZero ? "text-slate-500" : b.isDr ? "text-red-600" : "text-emerald-600"}>
                                {b.text} {b.label && <small className="text-[10px] font-semibold">{b.label}</small>}
                              </span>
                            );
                          })()}
                        </td>
                        <td></td>
                      </tr>

                      {/* Entries List */}
                      {entries.map((entry) => {
                        const isAuto = AUTO_REF_TYPES.has(entry.reference_type || "");
                        const isCancelled = entry.source_status === "CANCELLED";
                        const bal = fmtBal(entry.running_balance, entry.account_type);
                        const partText = entry.particulars || entry.narration || "";

                        return (
                          <tr key={entry.id} className={`hover:bg-slate-50/80 transition-colors ${isCancelled ? "opacity-60 bg-red-50/20" : ""}`}>
                            <td className="py-2.5 px-3 whitespace-nowrap font-medium text-slate-700">{entry.transaction_date || "—"}</td>
                            <td className="py-2.5 px-3 font-semibold text-slate-900 max-w-[160px] truncate" title={entry.account_name}>
                              {entry.account_name}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${getTypeBadgeClass(entry.account_type)}`}>
                                {entry.account_type}
                              </span>
                              {entry.source_status === "MANUAL" && <span className="ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-amber-100 text-amber-800">Manual</span>}
                              {entry.source_status === "TALLY_IMPORT" && <span className="ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-purple-100 text-purple-800">Tally</span>}
                              {entry.source_status === "OPENING_BALANCE" && <span className="ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-blue-100 text-blue-800">Opening</span>}
                              {entry.source_status === "CANCELLED" && <span className="ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-red-100 text-red-800">Cancelled</span>}
                            </td>
                            <td className="py-2.5 px-3 max-w-[200px] truncate text-slate-600" title={partText}>
                              {partText || <span className="text-slate-300">—</span>}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap font-mono text-[11px]">
                              {entry.voucher_type && <span className="mr-1 px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px]">{entry.voucher_type}</span>}
                              {entry.reference_number ? (
                                <code className="bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-[10px] font-semibold">{entry.reference_number}</code>
                              ) : !entry.voucher_type ? (
                                <span className="text-slate-300">—</span>
                              ) : null}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              {entry.main_category_name ? (
                                <span className="px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 text-[10px] font-medium">{entry.main_category_name}</span>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              {entry.sub_category_name ? (
                                <span className="px-2 py-0.5 rounded-full bg-violet-100 text-violet-800 text-[10px] font-medium">{entry.sub_category_name}</span>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono font-medium text-red-600">
                              {entry.debit_amount > 0 ? fmt(entry.debit_amount) : <span className="text-slate-300">—</span>}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono font-medium text-emerald-600">
                              {entry.credit_amount > 0 ? fmt(entry.credit_amount) : <span className="text-slate-300">—</span>}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono font-bold">
                              <span className={bal.isZero ? "text-slate-500" : bal.isDr ? "text-red-600" : "text-emerald-600"}>
                                {bal.text} {bal.label && <small className="text-[10px] font-semibold">{bal.label}</small>}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <div className="inline-flex items-center gap-1">
                                {entry.reference_number && (
                                  <button
                                    type="button"
                                    onClick={() => openVoucherView(entry.reference_number!, entry.company_id)}
                                    title="View Voucher"
                                    className="p-1 rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-all"
                                  >
                                    <Eye className="h-3.5 w-3.5" />
                                  </button>
                                )}
                                {!isCancelled && (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => openEntryEdit(entry.id)}
                                      title={isAuto ? "Auto-posted entry - edit with caution" : "Edit entry"}
                                      className="p-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-all"
                                    >
                                      <Edit className="h-3.5 w-3.5" />
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => deleteEntry(entry.id)}
                                      title="Delete entry"
                                      className="p-1 rounded bg-red-50 text-red-700 hover:bg-red-100 transition-all"
                                    >
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}

                      {/* Grand Total Row */}
                      <tr className="bg-indigo-50/80 border-t-2 border-indigo-300 font-bold">
                        <td colSpan={7} className="py-2.5 px-3 text-indigo-900">
                          Grand Total ({entries.length} items on page)
                        </td>
                        <td className="py-2.5 px-3 text-right text-red-600 font-mono">{fmt(entriesTotals.total_debit)}</td>
                        <td className="py-2.5 px-3 text-right text-emerald-600 font-mono">{fmt(entriesTotals.total_credit)}</td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          {(() => {
                            const b = fmtBal(entries[0]?.running_balance || 0, fType || entries[0]?.account_type);
                            return (
                              <span className={b.isZero ? "text-slate-500" : b.isDr ? "text-red-600" : "text-emerald-600"}>
                                {b.text} {b.label && <small className="text-[10px] font-semibold">{b.label}</small>}
                              </span>
                            );
                          })()}
                        </td>
                        <td></td>
                      </tr>

                      {/* Daily Average Row */}
                      <tr className="bg-slate-50 text-[11px] text-slate-500 italic border-t border-slate-200">
                        <td colSpan={7} className="py-1.5 px-3">
                          Daily Average ({dayCount} active day{dayCount !== 1 ? "s" : ""})
                        </td>
                        <td className="py-1.5 px-3 text-right font-mono">{fmt(entriesTotals.total_debit / dayCount)}</td>
                        <td className="py-1.5 px-3 text-right font-mono">{fmt(entriesTotals.total_credit / dayCount)}</td>
                        <td colSpan={2}></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="px-5 py-3 border-t border-slate-200 flex items-center justify-between bg-slate-50">
                  <span className="text-xs text-slate-500">
                    Showing page {page} of {totalPages}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={page <= 1}
                      onClick={() => loadLedgerEntries(page - 1)}
                      className="p-1.5 border border-slate-300 rounded bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <span className="text-xs font-bold px-2 text-indigo-700">{page}</span>
                    <button
                      type="button"
                      disabled={page >= totalPages}
                      onClick={() => loadLedgerEntries(page + 1)}
                      className="p-1.5 border border-slate-300 rounded bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════
            TAB 2: ADD ACCOUNT (CREATE NEW LEDGER)
        ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "create" && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 max-w-4xl mx-auto">
            <div className="border-b border-slate-200 pb-4 mb-6 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600">
                  <PlusCircle className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">Add New Ledger Account</h2>
                  <p className="text-xs text-slate-500">Create accounts for Day Book, Chart of Accounts, and Balance Sheet</p>
                </div>
              </div>
            </div>

            <form onSubmit={handleCreateLedger} className="space-y-6">
              {/* Row 1 */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Company *</label>
                  <select
                    required
                    value={cCompany}
                    onChange={(e) => setCCompany(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                  >
                    <option value="">— Select Company —</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Account Type *</label>
                  <select
                    value={cType}
                    onChange={(e) => {
                      const newType = e.target.value;
                      setCType(newType);
                      const defGroup = GROUP_CHIPS[newType]?.default;
                      if (defGroup) setCGroup(defGroup);
                    }}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                  >
                    <optgroup label="Cash & Bank">
                      <option value="CASH">Cash</option>
                      <option value="BANK">Bank Account</option>
                      <option value="UPI">UPI Account</option>
                    </optgroup>
                    <optgroup label="P&L">
                      <option value="INCOME">Income Head</option>
                      <option value="EXPENSE">Expense Head</option>
                    </optgroup>
                    <optgroup label="Balance Sheet">
                      <option value="ASSET">Asset</option>
                      <option value="LIABILITY">Liability</option>
                      <option value="CAPITAL">Capital / Equity</option>
                      <option value="LOAN">Loan</option>
                    </optgroup>
                    <optgroup label="Parties (Balance Sheet)">
                      <option value="SUNDRY_DEBTOR">Sundry Debtors</option>
                      <option value="SUNDRY_CREDITOR">Sundry Creditors</option>
                      <option value="DUTIES_TAXES">Duties & Taxes</option>
                    </optgroup>
                    <optgroup label="Other">
                      <option value="STOCK">Stock / Inventory</option>
                      <option value="PARTY">Party (Legacy)</option>
                    </optgroup>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Account Name *</label>
                  <input
                    type="text"
                    required
                    value={cName}
                    onChange={(e) => setCName(e.target.value)}
                    placeholder="e.g. HDFC Savings A/c, Petty Cash"
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">Use a clear, distinct ledger name.</span>
                </div>
              </div>

              {/* Row 2 */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
                    Account Code <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={cCode}
                    onChange={(e) => setCCode(e.target.value)}
                    placeholder="e.g. HDFC-SAV"
                    maxLength={40}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
                    Account Group <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={cGroup}
                    onChange={(e) => setCGroup(e.target.value)}
                    placeholder="e.g. Indirect Expenses"
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  {/* Smart suggestion chips */}
                  {GROUP_CHIPS[cType]?.chips.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {GROUP_CHIPS[cType].chips.map((chip) => (
                        <button
                          key={chip}
                          type="button"
                          onClick={() => setCGroup(chip)}
                          className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition-all"
                        >
                          {chip}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
                    Description <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={cDesc}
                    onChange={(e) => setCDesc(e.target.value)}
                    placeholder="Brief description"
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>
              </div>

              {/* Conditional Bank Details */}
              {(cType === "BANK" || cType === "UPI") && (
                <div className="p-4 bg-blue-50/70 border border-blue-200 rounded-xl space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-blue-900">
                    <Landmark className="h-4 w-4 text-blue-700" />
                    Bank Account Details
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Account Number</label>
                      <input
                        type="text"
                        value={cAccountNumber}
                        onChange={(e) => setCAccountNumber(e.target.value)}
                        placeholder="e.g. 12345678901234"
                        maxLength={30}
                        className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">IFSC Code</label>
                      <input
                        type="text"
                        value={cIfscCode}
                        onChange={(e) => setCIfscCode(e.target.value.toUpperCase())}
                        placeholder="e.g. HDFC0001234"
                        maxLength={15}
                        className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white uppercase font-mono focus:ring-2 focus:ring-indigo-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Bank Name</label>
                      <input
                        type="text"
                        value={cBankName}
                        onChange={(e) => setCBankName(e.target.value)}
                        placeholder="e.g. HDFC Bank"
                        maxLength={80}
                        className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Opening Balance Section */}
              <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-purple-900">
                  <Scale className="h-4 w-4 text-purple-700" />
                  Opening Balance <span className="text-slate-400 font-normal text-[11px]">(auto-posted to the ledger)</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Opening Balance (₹)</label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={cOB}
                      onChange={(e) => setCOB(e.target.value)}
                      placeholder="0.00"
                      className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none font-mono"
                    />
                    <span className="text-[10px] text-slate-400 mt-1 block">Leave 0 or blank if none.</span>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Balance Type</label>
                    <select
                      value={cOBType}
                      onChange={(e) => setCOBType(e.target.value as any)}
                      className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                    >
                      <option value="DEBIT">Debit (Dr) — Asset / Expense</option>
                      <option value="CREDIT">Credit (Cr) — Liability / Capital / Income</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">Opening Date</label>
                    <input
                      type="date"
                      value={cOBDate}
                      onChange={(e) => setCOBDate(e.target.value)}
                      className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Form Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setCCompany("");
                    setCType("CASH");
                    setCName("");
                    setCCode("");
                    setCGroup("");
                    setCDesc("");
                    setCAccountNumber("");
                    setCIfscCode("");
                    setCBankName("");
                    setCOB("");
                    setCOBType("DEBIT");
                    setCOBDate(new Date().toISOString().slice(0, 10));
                  }}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-all"
                >
                  Reset Form
                </button>
                <button
                  type="submit"
                  disabled={creatingLedger}
                  className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 shadow-sm transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {creatingLedger && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  Create Ledger Account
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════
            TAB 3: CHART OF ACCOUNTS (LIST TABLE)
        ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "cards" && (
          <div className="space-y-4">
            {/* Account Type Stats Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-indigo-500">
                <span className="text-[10px] font-bold uppercase text-slate-500">Total Accounts</span>
                <div className="text-xl font-bold text-slate-900 mt-1">{masters.length}</div>
              </div>
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-emerald-500">
                <span className="text-[10px] font-bold uppercase text-slate-500">Cash / UPI</span>
                <div className="text-xl font-bold text-emerald-600 mt-1">
                  {masters.filter((r) => ["CASH", "UPI"].includes(r.account_type)).length}
                </div>
              </div>
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-blue-500">
                <span className="text-[10px] font-bold uppercase text-slate-500">Bank</span>
                <div className="text-xl font-bold text-blue-600 mt-1">
                  {masters.filter((r) => r.account_type === "BANK").length}
                </div>
              </div>
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-cyan-500">
                <span className="text-[10px] font-bold uppercase text-slate-500">Income</span>
                <div className="text-xl font-bold text-cyan-600 mt-1">
                  {masters.filter((r) => r.account_type === "INCOME").length}
                </div>
              </div>
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs border-l-4 border-l-red-500 col-span-2 sm:col-span-1">
                <span className="text-[10px] font-bold uppercase text-slate-500">Expense</span>
                <div className="text-xl font-bold text-red-600 mt-1">
                  {masters.filter((r) => r.account_type === "EXPENSE").length}
                </div>
              </div>
            </div>

            {/* Info notice */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-amber-600 shrink-0" />
                <span>Shows formally defined master accounts in the Chart of Accounts.</span>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab("txaccounts")}
                className="font-bold text-indigo-700 hover:text-indigo-900 inline-flex items-center gap-1"
              >
                View All Transaction Accounts <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Filter Bar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center gap-3">
              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Company</label>
                <select
                  value={lCompany}
                  onChange={(e) => setLCompany(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Type</label>
                <select
                  value={lType}
                  onChange={(e) => setLType(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Types</option>
                  <option value="CASH">CASH</option>
                  <option value="BANK">BANK</option>
                  <option value="UPI">UPI</option>
                  <option value="INCOME">INCOME</option>
                  <option value="EXPENSE">EXPENSE</option>
                  <option value="STOCK">STOCK</option>
                  <option value="SUNDRY_DEBTOR">SUNDRY_DEBTOR</option>
                  <option value="SUNDRY_CREDITOR">SUNDRY_CREDITOR</option>
                  <option value="DUTIES_TAXES">DUTIES_TAXES</option>
                  <option value="CAPITAL">CAPITAL</option>
                  <option value="LOAN">LOAN</option>
                  <option value="LIABILITY">LIABILITY</option>
                  <option value="ASSET">ASSET</option>
                  <option value="PARTY">PARTY</option>
                </select>
              </div>

              <div className="min-w-[120px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Status</label>
                <select
                  value={lStatus}
                  onChange={(e) => setLStatus(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Statuses</option>
                  <option value="true">Active</option>
                  <option value="false">Inactive</option>
                </select>
              </div>

              <div className="flex-1 min-w-[200px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Search Name</label>
                <input
                  type="text"
                  value={lSearch}
                  onChange={(e) => setLSearch(e.target.value)}
                  placeholder="Search ledger name..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="pt-5">
                <button
                  type="button"
                  onClick={loadMasters}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 shadow-xs flex items-center gap-1.5"
                >
                  <Search className="h-3.5 w-3.5" />
                  Filter
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-indigo-600" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">Chart of Accounts Matrix</h2>
                </div>
                <span className="text-xs text-slate-500">{masters.length} registered accounts</span>
              </div>

              {mastersLoading ? (
                <div className="p-12 text-center text-slate-500">
                  <RefreshCw className="h-6 w-6 animate-spin text-indigo-600 mx-auto mb-2" />
                  <p className="text-xs">Loading ledger accounts...</p>
                </div>
              ) : masters.length === 0 ? (
                <div className="p-12 text-center text-slate-500">
                  <Layers className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No ledger masters found.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                        <th className="py-2.5 px-3">#</th>
                        <th className="py-2.5 px-3">Type</th>
                        <th className="py-2.5 px-3">Account Name</th>
                        <th className="py-2.5 px-3">Group</th>
                        <th className="py-2.5 px-3">Description</th>
                        <th className="py-2.5 px-3">Company</th>
                        <th className="py-2.5 px-3 text-right">Opening Bal</th>
                        <th className="py-2.5 px-3">OB Date</th>
                        <th className="py-2.5 px-3 text-center">Posted</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {masters.map((m, idx) => {
                        const obNum = m.opening_balance || 0;
                        return (
                          <tr key={m.id} className={`hover:bg-slate-50/70 transition-colors ${!m.is_active ? "opacity-60 bg-slate-50" : ""}`}>
                            <td className="py-2.5 px-3 font-mono text-slate-400">{idx + 1}</td>
                            <td className="py-2.5 px-3">
                              <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${getTypeBadgeClass(m.account_type)}`}>
                                {m.account_type}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-slate-900">
                              <div>{m.account_name}</div>
                              {m.account_code && <div className="font-mono text-[10px] text-slate-400">{m.account_code}</div>}
                            </td>
                            <td className="py-2.5 px-3 text-slate-600">{m.parent_group || "—"}</td>
                            <td className="py-2.5 px-3 text-slate-500 max-w-[150px] truncate">{m.description || "—"}</td>
                            <td className="py-2.5 px-3 text-slate-600">{getCompanyName(m.company_id)}</td>
                            <td className="py-2.5 px-3 text-right font-mono font-semibold">
                              {obNum > 0 ? (
                                <span className={m.opening_balance_type === "DEBIT" ? "text-red-600" : "text-emerald-600"}>
                                  {fmt(obNum)} <small className="text-[10px]">{m.opening_balance_type === "DEBIT" ? "Dr" : "Cr"}</small>
                                </span>
                              ) : (
                                <span className="text-slate-400">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-slate-500">{m.opening_balance_date || "—"}</td>
                            <td className="py-2.5 px-3 text-center">
                              {m.opening_balance_posted && obNum > 0 ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-600 inline-block" />
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  m.is_active ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                                }`}
                              >
                                {m.is_active ? "Active" : "Inactive"}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <div className="inline-flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() => drillDown(m.account_type, m.account_name, m.company_id)}
                                  title="View Ledger"
                                  className="p-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-all"
                                >
                                  <Eye className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => openMasterEdit(m.id)}
                                  title="Edit Ledger"
                                  className="p-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200 transition-all"
                                >
                                  <Edit className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => toggleMasterActive(m.id, m.is_active)}
                                  title={m.is_active ? "Deactivate" : "Activate"}
                                  className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                                    m.is_active
                                      ? "bg-slate-100 text-slate-600 hover:bg-red-100 hover:text-red-700"
                                      : "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                                  }`}
                                >
                                  {m.is_active ? "Deact" : "Act"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => deleteMaster(m.id, m.account_name)}
                                  title="Delete Master"
                                  className="p-1 rounded bg-red-50 text-red-700 hover:bg-red-100 transition-all"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
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
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════
            TAB 4: BANK ACCOUNTS
        ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "banks" && (
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <label className="text-xs font-bold uppercase text-slate-500">Company</label>
                <select
                  value={headsCompany}
                  onChange={(e) => setHeadsCompany(e.target.value)}
                  className="text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setHeadsCompany("")}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 hover:bg-slate-50"
                >
                  Reset
                </button>
              </div>

              <span className="text-xs font-semibold text-indigo-700">
                {headsCompany ? `📍 ${getCompanyName(headsCompany)}` : "All Companies"}
              </span>
            </div>

            {/* Bank Accounts Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <Landmark className="h-4 w-4 text-indigo-600" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">Bank Accounts Registry</h2>
                </div>
              </div>

              {banksLoading ? (
                <div className="p-12 text-center text-slate-500">
                  <RefreshCw className="h-6 w-6 animate-spin text-indigo-600 mx-auto mb-2" />
                  <p className="text-xs">Loading bank accounts...</p>
                </div>
              ) : bankMasters.length === 0 && companyBanks.length === 0 ? (
                <div className="p-12 text-center text-slate-500">
                  <Landmark className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No bank accounts found.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                        <th className="py-2.5 px-3">#</th>
                        <th className="py-2.5 px-3">Type</th>
                        <th className="py-2.5 px-3">Account Name</th>
                        <th className="py-2.5 px-3">Code</th>
                        <th className="py-2.5 px-3">Group / Branch</th>
                        <th className="py-2.5 px-3">Bank Name</th>
                        <th className="py-2.5 px-3">Account No.</th>
                        <th className="py-2.5 px-3">IFSC</th>
                        <th className="py-2.5 px-3">Company</th>
                        <th className="py-2.5 px-3 text-right">Opening Bal</th>
                        <th className="py-2.5 px-3 text-right">Balance</th>
                        <th className="py-2.5 px-3 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {bankMasters.map((m, idx) => {
                        const gl = bankHeads.find((h) => h.account_name === m.account_name && String(h.company_id) === String(m.company_id));
                        const ob = parseFloat(String(m.opening_balance || 0));
                        const bal = gl ? gl.balance : ob * (m.opening_balance_type === "DEBIT" ? 1 : -1);
                        const balObj = fmtBal(bal, "BANK");
                        const accMask = m.account_number ? `••••${m.account_number.slice(-4)}` : "—";

                        return (
                          <tr key={m.id} className="hover:bg-slate-50/70 transition-colors">
                            <td className="py-2.5 px-3 font-mono text-slate-400">{idx + 1}</td>
                            <td className="py-2.5 px-3">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold border bg-blue-100 text-blue-800 border-blue-200">
                                BANK
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-slate-900">{m.account_name}</td>
                            <td className="py-2.5 px-3 font-mono text-slate-500">{m.account_code || "—"}</td>
                            <td className="py-2.5 px-3 text-slate-600">{m.parent_group || "—"}</td>
                            <td className="py-2.5 px-3 text-slate-700">{m.bank_name || "—"}</td>
                            <td className="py-2.5 px-3 font-mono">{accMask}</td>
                            <td className="py-2.5 px-3 font-mono text-slate-600">{m.ifsc_code || "—"}</td>
                            <td className="py-2.5 px-3 text-slate-600">{getCompanyName(m.company_id)}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-slate-700">{ob > 0 ? fmt(ob) : "—"}</td>
                            <td className="py-2.5 px-3 text-right font-mono font-bold">
                              <span className={balObj.isZero ? "text-slate-500" : balObj.isDr ? "text-red-600" : "text-emerald-600"}>
                                {balObj.text} {balObj.label && <small className="text-[10px] font-semibold">{balObj.label}</small>}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <div className="inline-flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() => drillDown("BANK", m.account_name, m.company_id)}
                                  title="View Ledger"
                                  className="p-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                                >
                                  <Eye className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => openMasterEdit(m.id)}
                                  title="Edit"
                                  className="p-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200"
                                >
                                  <Edit className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => deleteMaster(m.id, m.account_name)}
                                  title="Delete"
                                  className="p-1 rounded bg-red-50 text-red-700 hover:bg-red-100"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
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
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════
            TAB 5: TRANSACTION ACCOUNTS
        ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "txaccounts" && (
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center gap-3">
              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Company</label>
                <select
                  value={aCompany}
                  onChange={(e) => setACompany(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Account Type</label>
                <select
                  value={aType}
                  onChange={(e) => setAType(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Types</option>
                  <option value="CASH">CASH</option>
                  <option value="BANK">BANK</option>
                  <option value="UPI">UPI</option>
                  <option value="INCOME">INCOME</option>
                  <option value="EXPENSE">EXPENSE</option>
                  <option value="STOCK">STOCK</option>
                  <option value="SUNDRY_DEBTOR">SUNDRY_DEBTOR</option>
                  <option value="SUNDRY_CREDITOR">SUNDRY_CREDITOR</option>
                  <option value="DUTIES_TAXES">DUTIES_TAXES</option>
                  <option value="CAPITAL">CAPITAL</option>
                  <option value="LOAN">LOAN</option>
                  <option value="LIABILITY">LIABILITY</option>
                  <option value="ASSET">ASSET</option>
                  <option value="PARTY">PARTY</option>
                </select>
              </div>

              <div className="flex-1 min-w-[200px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Search Account</label>
                <input
                  type="text"
                  value={aSearch}
                  onChange={(e) => setASearch(e.target.value)}
                  placeholder="Search account name..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="flex items-center gap-2 pt-5">
                <button
                  type="button"
                  onClick={loadTransactionAccounts}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 shadow-xs flex items-center gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setACompany("");
                    setAType("");
                    setASearch("");
                    setTimeout(loadTransactionAccounts, 50);
                  }}
                  className="px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-50"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <ListFilter className="h-4 w-4 text-indigo-600" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">All Transaction Accounts</h2>
                </div>
                <span className="text-xs text-slate-500">
                  {txHeads.filter((r) => !aSearch || r.account_name.toLowerCase().includes(aSearch.toLowerCase())).length} accounts
                </span>
              </div>

              {txLoading ? (
                <div className="p-12 text-center text-slate-500">
                  <RefreshCw className="h-6 w-6 animate-spin text-indigo-600 mx-auto mb-2" />
                  <p className="text-xs">Loading transaction accounts...</p>
                </div>
              ) : txHeads.length === 0 ? (
                <div className="p-12 text-center text-slate-500">
                  <ListFilter className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No transaction accounts found.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                        <th className="py-2.5 px-3">#</th>
                        <th className="py-2.5 px-3">Type</th>
                        <th
                          className="py-2.5 px-3 cursor-pointer select-none hover:text-indigo-600"
                          onClick={() => {
                            setAcctSort((prev) => ({ col: "account_name", dir: prev.col === "account_name" ? prev.dir * -1 : 1 }));
                          }}
                        >
                          Account Name {acctSort.col === "account_name" ? (acctSort.dir === 1 ? "▲" : "▼") : ""}
                        </th>
                        <th className="py-2.5 px-3">Company</th>
                        <th
                          className="py-2.5 px-3 text-right cursor-pointer select-none hover:text-indigo-600"
                          onClick={() => {
                            setAcctSort((prev) => ({ col: "total_debit", dir: prev.col === "total_debit" ? prev.dir * -1 : 1 }));
                          }}
                        >
                          Total Debit {acctSort.col === "total_debit" ? (acctSort.dir === 1 ? "▲" : "▼") : ""}
                        </th>
                        <th
                          className="py-2.5 px-3 text-right cursor-pointer select-none hover:text-indigo-600"
                          onClick={() => {
                            setAcctSort((prev) => ({ col: "total_credit", dir: prev.col === "total_credit" ? prev.dir * -1 : 1 }));
                          }}
                        >
                          Total Credit {acctSort.col === "total_credit" ? (acctSort.dir === 1 ? "▲" : "▼") : ""}
                        </th>
                        <th
                          className="py-2.5 px-3 text-right cursor-pointer select-none hover:text-indigo-600"
                          onClick={() => {
                            setAcctSort((prev) => ({ col: "balance", dir: prev.col === "balance" ? prev.dir * -1 : 1 }));
                          }}
                        >
                          Net Balance {acctSort.col === "balance" ? (acctSort.dir === 1 ? "▲" : "▼") : ""}
                        </th>
                        <th className="py-2.5 px-3">Last Date</th>
                        <th className="py-2.5 px-3 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {txHeads
                        .filter((r) => !aSearch || r.account_name.toLowerCase().includes(aSearch.toLowerCase()))
                        .sort((a, b) => {
                          let av: any = a[acctSort.col];
                          let bv: any = b[acctSort.col];
                          if (typeof av === "string") av = av.toLowerCase();
                          if (typeof bv === "string") bv = bv.toLowerCase();
                          return acctSort.dir * (av < bv ? -1 : av > bv ? 1 : 0);
                        })
                        .map((r, i) => {
                          const balObj = fmtBal(r.balance, r.account_type);
                          const master = txMastersMap[`${r.account_name}|${r.company_id}`];

                          return (
                            <tr key={`${r.account_name}-${r.company_id}`} className="hover:bg-slate-50/70 transition-colors">
                              <td className="py-2.5 px-3 font-mono text-slate-400">{i + 1}</td>
                              <td className="py-2.5 px-3">
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${getTypeBadgeClass(r.account_type)}`}>
                                  {r.account_type}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 font-semibold text-slate-900">{r.account_name}</td>
                              <td className="py-2.5 px-3 text-slate-600">{getCompanyName(r.company_id)}</td>
                              <td className="py-2.5 px-3 text-right font-mono font-medium text-red-600">{fmt(r.total_debit)}</td>
                              <td className="py-2.5 px-3 text-right font-mono font-medium text-emerald-600">{fmt(r.total_credit)}</td>
                              <td className="py-2.5 px-3 text-right font-mono font-bold">
                                <span className={balObj.isZero ? "text-slate-500" : balObj.isDr ? "text-red-600" : "text-emerald-600"}>
                                  {balObj.text} {balObj.label && <small className="text-[10px] font-semibold">{balObj.label}</small>}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-slate-500">{r.last_date || "—"}</td>
                              <td className="py-2.5 px-3 text-center">
                                <div className="inline-flex items-center gap-1">
                                  <button
                                    type="button"
                                    onClick={() => drillDown(r.account_type, r.account_name, r.company_id)}
                                    className="px-2.5 py-1 text-[11px] font-semibold rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 inline-flex items-center gap-1"
                                  >
                                    <BookOpen className="h-3 w-3" /> Ledger
                                  </button>
                                  {master && (
                                    <button
                                      type="button"
                                      onClick={() => openMasterEdit(master.id)}
                                      className="p-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200"
                                      title="Edit Account Master"
                                    >
                                      <Edit className="h-3.5 w-3.5" />
                                    </button>
                                  )}
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
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════
            TAB 6: PARTIES & VENDORS
        ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "parties" && (
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center gap-3">
              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Company</label>
                <select
                  value={pvCompany}
                  onChange={(e) => setPvCompany(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Show</label>
                <select
                  value={pvShow}
                  onChange={(e) => setPvShow(e.target.value as any)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="all">All (Parties + Vendors)</option>
                  <option value="party">Party Ledgers only</option>
                  <option value="vendor">Vendors only</option>
                </select>
              </div>

              <div className="flex-1 min-w-[200px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Search Name / Phone</label>
                <input
                  type="text"
                  value={pvSearch}
                  onChange={(e) => setPvSearch(e.target.value)}
                  placeholder="Name or phone..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="pt-5">
                <button
                  type="button"
                  onClick={loadParties}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 shadow-xs flex items-center gap-1.5"
                >
                  <Search className="h-3.5 w-3.5" />
                  Filter
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-purple-600" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">Parties & Vendors Registry</h2>
                </div>
                <span className="text-xs text-slate-500">
                  {partiesList.filter((r) => !pvSearch || r.name.toLowerCase().includes(pvSearch.toLowerCase())).length} records
                </span>
              </div>

              {partiesLoading ? (
                <div className="p-12 text-center text-slate-500">
                  <RefreshCw className="h-6 w-6 animate-spin text-purple-600 mx-auto mb-2" />
                  <p className="text-xs">Loading parties & vendors...</p>
                </div>
              ) : partiesList.length === 0 ? (
                <div className="p-12 text-center text-slate-500">
                  <Users className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No parties or vendors found.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                        <th className="py-2.5 px-3">Type</th>
                        <th className="py-2.5 px-3">Name</th>
                        <th className="py-2.5 px-3">Code</th>
                        <th className="py-2.5 px-3">Phone / Email</th>
                        <th className="py-2.5 px-3">GSTIN</th>
                        <th className="py-2.5 px-3">Bank A/C</th>
                        <th className="py-2.5 px-3">IFSC</th>
                        <th className="py-2.5 px-3 text-right">Opening Balance</th>
                        <th className="py-2.5 px-3 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {partiesList
                        .filter(
                          (r) =>
                            !pvSearch ||
                            (r.name && r.name.toLowerCase().includes(pvSearch.toLowerCase())) ||
                            (r.phone && r.phone.includes(pvSearch))
                        )
                        .map((r, i) => (
                          <tr key={i} className="hover:bg-slate-50/70 transition-colors">
                            <td className="py-2.5 px-3">
                              <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${getTypeBadgeClass(r.kind)}`}>
                                {r.kind}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-slate-900">{r.name || "—"}</td>
                            <td className="py-2.5 px-3 font-mono text-slate-500">{r.code || "—"}</td>
                            <td className="py-2.5 px-3 text-slate-600">
                              {r.phone && <div>{r.phone}</div>}
                              {r.email && <div className="text-slate-400">{r.email}</div>}
                              {!r.phone && !r.email && <span className="text-slate-300">—</span>}
                            </td>
                            <td className="py-2.5 px-3 font-mono">{r.gstin || "—"}</td>
                            <td className="py-2.5 px-3 font-mono">{r.acct || "—"}</td>
                            <td className="py-2.5 px-3 font-mono text-slate-500">{r.ifsc || "—"}</td>
                            <td className="py-2.5 px-3 text-right font-mono font-medium">
                              {r.ob > 0 ? (
                                <span className={r.ob_type === "DEBIT" ? "text-red-600" : "text-emerald-600"}>
                                  {fmt(r.ob)} <small className="text-[10px]">{r.ob_type === "DEBIT" ? "Dr" : "Cr"}</small>
                                </span>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-center whitespace-nowrap">
                              <div className="inline-flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() => drillDown("PARTY", r.name, r.company_id)}
                                  className="px-2.5 py-1 text-[11px] font-semibold rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 inline-flex items-center gap-1"
                                >
                                  <BookOpen className="h-3 w-3" /> Ledger
                                </button>
                                {r.kind === "PARTY" && r.id && (
                                  <button
                                    type="button"
                                    onClick={() => openMasterEdit(r.id!)}
                                    className="p-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200"
                                    title="Edit Party Master"
                                  >
                                    <Edit className="h-3.5 w-3.5" />
                                  </button>
                                )}
                                {r.kind === "VENDOR" && (
                                  <Link
                                    href="/staff/accounts/vendors"
                                    className="p-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200"
                                    title="Manage in Vendors"
                                  >
                                    <ExternalLink className="h-3.5 w-3.5" />
                                  </Link>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════
            TAB 7: COMPANY SUMMARY
        ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "cwise" && (
          <div className="space-y-6">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center gap-3">
              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Company</label>
                <select
                  value={cwCompany}
                  onChange={(e) => setCwCompany(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Companies</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="min-w-[140px]">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">Account Type</label>
                <select
                  value={cwType}
                  onChange={(e) => setCwType(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Types</option>
                  <option value="CASH">CASH</option>
                  <option value="BANK">BANK</option>
                  <option value="UPI">UPI</option>
                  <option value="INCOME">INCOME</option>
                  <option value="EXPENSE">EXPENSE</option>
                  <option value="STOCK">STOCK</option>
                  <option value="SUNDRY_DEBTOR">SUNDRY_DEBTOR</option>
                  <option value="SUNDRY_CREDITOR">SUNDRY_CREDITOR</option>
                  <option value="DUTIES_TAXES">DUTIES_TAXES</option>
                  <option value="CAPITAL">CAPITAL</option>
                  <option value="LOAN">LOAN</option>
                  <option value="LIABILITY">LIABILITY</option>
                  <option value="ASSET">ASSET</option>
                  <option value="PARTY">PARTY</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-5">
                <button
                  type="button"
                  onClick={loadCompanySummary}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 shadow-xs flex items-center gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setCwCompany("");
                    setCwType("");
                    setTimeout(loadCompanySummary, 50);
                  }}
                  className="px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-50"
                >
                  Reset
                </button>
              </div>
            </div>

            {cwiseLoading ? (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
                <RefreshCw className="h-6 w-6 animate-spin text-indigo-600 mx-auto mb-2" />
                <p className="text-xs">Loading company-wise summary...</p>
              </div>
            ) : cwiseRows.length === 0 ? (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
                <Building2 className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700">No summary data found.</p>
              </div>
            ) : (
              // Grouped by company
              Object.entries(
                cwiseRows.reduce((acc, row) => {
                  if (!acc[row.company_id]) acc[row.company_id] = [];
                  acc[row.company_id].push(row);
                  return acc;
                }, {} as Record<number, CompanySummaryRow[]>)
              ).map(([coId, rows]) => {
                const totalDr = rows.reduce((s, r) => s + (r.total_debit || 0), 0);
                const totalCr = rows.reduce((s, r) => s + (r.total_credit || 0), 0);
                const netBal = totalDr - totalCr;

                return (
                  <div key={coId} className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
                    <div className="px-5 py-3.5 bg-indigo-50/70 border-b border-indigo-100 flex flex-wrap items-center justify-between gap-4">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-5 w-5 text-indigo-700" />
                        <h3 className="text-sm font-bold text-indigo-950">{getCompanyName(coId)}</h3>
                      </div>
                      <div className="flex flex-wrap items-center gap-4 text-xs">
                        <span>
                          <span className="text-slate-500">Accounts:</span> <strong>{rows.length}</strong>
                        </span>
                        <span>
                          <span className="text-slate-500">Total Dr:</span> <strong className="text-red-600">{fmt(totalDr)}</strong>
                        </span>
                        <span>
                          <span className="text-slate-500">Total Cr:</span> <strong className="text-emerald-600">{fmt(totalCr)}</strong>
                        </span>
                        <span>
                          <span className="text-slate-500">Net:</span>{" "}
                          <strong className={netBal > 0 ? "text-red-600" : netBal < 0 ? "text-emerald-600" : "text-slate-600"}>
                            {fmt(Math.abs(netBal))} {netBal > 0 ? "Dr" : netBal < 0 ? "Cr" : ""}
                          </strong>
                        </span>
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                            <th className="py-2.5 px-3">Type</th>
                            <th className="py-2.5 px-3">Account Name</th>
                            <th className="py-2.5 px-3 text-right">Total Debit</th>
                            <th className="py-2.5 px-3 text-right">Total Credit</th>
                            <th className="py-2.5 px-3 text-right">Net Balance</th>
                            <th className="py-2.5 px-3">Last Entry</th>
                            <th className="py-2.5 px-3 text-center">Source</th>
                            <th className="py-2.5 px-3 text-center">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {rows
                            .sort((a, b) => a.account_type.localeCompare(b.account_type) || a.account_name.localeCompare(b.account_name))
                            .map((r, i) => {
                              const balObj = fmtBal(r.balance, r.account_type);
                              return (
                                <tr key={i} className="hover:bg-slate-50/70 transition-colors">
                                  <td className="py-2.5 px-3">
                                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${getTypeBadgeClass(r.account_type)}`}>
                                      {r.account_type}
                                    </span>
                                  </td>
                                  <td className="py-2.5 px-3 font-semibold text-slate-900">{r.account_name}</td>
                                  <td className="py-2.5 px-3 text-right font-mono text-red-600 font-medium">
                                    {r.total_debit > 0 ? fmt(r.total_debit) : "—"}
                                  </td>
                                  <td className="py-2.5 px-3 text-right font-mono text-emerald-600 font-medium">
                                    {r.total_credit > 0 ? fmt(r.total_credit) : "—"}
                                  </td>
                                  <td className="py-2.5 px-3 text-right font-mono font-bold">
                                    <span className={balObj.isZero ? "text-slate-500" : balObj.isDr ? "text-red-600" : "text-emerald-600"}>
                                      {balObj.text} {balObj.label && <small className="text-[10px] font-semibold">{balObj.label}</small>}
                                    </span>
                                  </td>
                                  <td className="py-2.5 px-3 text-slate-500">{r.last_date || "—"}</td>
                                  <td className="py-2.5 px-3 text-center">
                                    {r.has_gl ? (
                                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800">GL</span>
                                    ) : (
                                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-800">OB</span>
                                    )}
                                  </td>
                                  <td className="py-2.5 px-3 text-center whitespace-nowrap">
                                    <div className="inline-flex items-center gap-1">
                                      <button
                                        type="button"
                                        onClick={() => drillDown(r.account_type, r.account_name, r.company_id)}
                                        className="px-2.5 py-1 text-[11px] font-semibold rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 inline-flex items-center gap-1"
                                      >
                                        <BookOpen className="h-3 w-3" /> Ledger
                                      </button>
                                      {r.master_id && (
                                        <button
                                          type="button"
                                          onClick={() => openMasterEdit(r.master_id!)}
                                          className="p-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200"
                                          title="Edit Master"
                                        >
                                          <Edit className="h-3.5 w-3.5" />
                                        </button>
                                      )}
                                    </div>
                                  </td>
                                </tr>
                              );
                            })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════
          MODAL 1: VOUCHER VIEW MODAL (Dual Dr/Cr sides)
      ═══════════════════════════════════════════════════════════════ */}
      {voucherModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden shadow-2xl flex flex-col border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
              <div className="flex items-center gap-2.5">
                <Scale className="h-5 w-5 text-indigo-600" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Voucher Breakdown: {voucherRef}</h3>
                  <span className="text-[11px] text-slate-500">
                    {voucherEntries[0]?.transaction_date ? `Date: ${voucherEntries[0].transaction_date}` : ""}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setVoucherModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              {voucherLoading ? (
                <div className="p-12 text-center text-slate-500">
                  <RefreshCw className="h-6 w-6 animate-spin text-indigo-600 mx-auto mb-2" />
                  <p className="text-xs">Loading voucher details...</p>
                </div>
              ) : voucherEntries.length === 0 ? (
                <p className="text-center text-xs text-slate-500 py-8">No ledger entries found for this voucher reference.</p>
              ) : (
                (() => {
                  const drs = voucherEntries.filter((e) => Number(e.debit_amount || 0) > 0);
                  const crs = voucherEntries.filter((e) => Number(e.credit_amount || 0) > 0);
                  const totDr = drs.reduce((s, e) => s + Number(e.debit_amount || 0), 0);
                  const totCr = crs.reduce((s, e) => s + Number(e.credit_amount || 0), 0);
                  const isBalanced = Math.abs(totDr - totCr) < 0.01;

                  return (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Debit Side */}
                        <div className="border border-red-200 rounded-xl overflow-hidden shadow-xs">
                          <div className="bg-red-50 px-4 py-2.5 border-b border-red-200 text-xs font-bold text-red-900 flex items-center justify-between">
                            <span className="flex items-center gap-1.5">
                              <ArrowRight className="h-4 w-4 text-red-600" /> DEBIT SIDE
                            </span>
                          </div>
                          <table className="w-full text-xs text-left">
                            <thead className="bg-red-50/50 text-[10px] uppercase font-bold text-slate-500 border-b border-red-100">
                              <tr>
                                <th className="py-2 px-3">Account</th>
                                <th className="py-2 px-3">Type</th>
                                <th className="py-2 px-3 text-right">Amount</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-red-50">
                              {drs.map((e, idx) => (
                                <tr key={idx}>
                                  <td className="py-2 px-3 font-semibold text-slate-900">{e.account_name}</td>
                                  <td className="py-2 px-3 font-mono text-[10px] text-slate-500">{e.account_type}</td>
                                  <td className="py-2 px-3 text-right font-mono font-bold text-red-600">{fmt(e.debit_amount)}</td>
                                </tr>
                              ))}
                            </tbody>
                            <tfoot className="bg-red-50 border-t-2 border-red-200 font-bold text-red-950">
                              <tr>
                                <td colSpan={2} className="py-2 px-3">
                                  Total Dr
                                </td>
                                <td className="py-2 px-3 text-right font-mono font-extrabold text-red-700">{fmt(totDr)}</td>
                              </tr>
                            </tfoot>
                          </table>
                        </div>

                        {/* Credit Side */}
                        <div className="border border-emerald-200 rounded-xl overflow-hidden shadow-xs">
                          <div className="bg-emerald-50 px-4 py-2.5 border-b border-emerald-200 text-xs font-bold text-emerald-900 flex items-center justify-between">
                            <span className="flex items-center gap-1.5">
                              <ArrowLeft className="h-4 w-4 text-emerald-600" /> CREDIT SIDE
                            </span>
                          </div>
                          <table className="w-full text-xs text-left">
                            <thead className="bg-emerald-50/50 text-[10px] uppercase font-bold text-slate-500 border-b border-emerald-100">
                              <tr>
                                <th className="py-2 px-3">Account</th>
                                <th className="py-2 px-3">Type</th>
                                <th className="py-2 px-3 text-right">Amount</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-emerald-50">
                              {crs.map((e, idx) => (
                                <tr key={idx}>
                                  <td className="py-2 px-3 font-semibold text-slate-900">{e.account_name}</td>
                                  <td className="py-2 px-3 font-mono text-[10px] text-slate-500">{e.account_type}</td>
                                  <td className="py-2 px-3 text-right font-mono font-bold text-emerald-600">{fmt(e.credit_amount)}</td>
                                </tr>
                              ))}
                            </tbody>
                            <tfoot className="bg-emerald-50 border-t-2 border-emerald-200 font-bold text-emerald-950">
                              <tr>
                                <td colSpan={2} className="py-2 px-3">
                                  Total Cr
                                </td>
                                <td className="py-2 px-3 text-right font-mono font-extrabold text-emerald-700">{fmt(totCr)}</td>
                              </tr>
                            </tfoot>
                          </table>
                        </div>
                      </div>

                      {/* Balance check footer */}
                      <div
                        className={`p-3 rounded-xl text-xs font-bold text-center border ${
                          isBalanced
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : "bg-red-50 text-red-800 border-red-200"
                        }`}
                      >
                        {isBalanced ? "✓ Voucher is perfectly balanced (Dr = Cr)" : "⚠ Warning: Voucher is unbalanced (Dr ≠ Cr)"}
                      </div>
                    </div>
                  );
                })()
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          MODAL 2: EDIT DAY BOOK ENTRY
      ═══════════════════════════════════════════════════════════════ */}
      {editEntryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-xl w-full max-h-[92vh] overflow-y-auto shadow-2xl p-6 border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <Edit className="h-5 w-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Edit Day Book Entry</h3>
              </div>
              <button onClick={() => setEditEntryModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            {AUTO_REF_TYPES.has(eeRefType) && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Auto-posted entry:</strong> Created from an invoice / income / expense. Editing only changes this raw ledger row.
                </span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Date *</label>
                <input
                  type="date"
                  value={eeDate}
                  onChange={(e) => setEeDate(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Dr / Cr *</label>
                <select
                  value={eeEntryType}
                  onChange={(e) => setEeEntryType(e.target.value as any)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="DEBIT">DEBIT (Dr)</option>
                  <option value="CREDIT">CREDIT (Cr)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Amount (₹) *</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={eeAmount}
                  onChange={(e) => setEeAmount(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 font-mono focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Voucher Type</label>
                <select
                  value={eeVoucherType}
                  onChange={(e) => setEeVoucherType(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">— None —</option>
                  <option value="Receipt">Receipt</option>
                  <option value="Payment">Payment</option>
                  <option value="Journal">Journal</option>
                  <option value="Contra">Contra</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Account Type</label>
                <select
                  value={eeAccountType}
                  onChange={(e) => setEeAccountType(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="CASH">CASH</option>
                  <option value="BANK">BANK</option>
                  <option value="UPI">UPI</option>
                  <option value="INCOME">INCOME</option>
                  <option value="EXPENSE">EXPENSE</option>
                  <option value="STOCK">STOCK</option>
                  <option value="SUNDRY_DEBTOR">SUNDRY_DEBTOR</option>
                  <option value="SUNDRY_CREDITOR">SUNDRY_CREDITOR</option>
                  <option value="DUTIES_TAXES">DUTIES_TAXES</option>
                  <option value="CAPITAL">CAPITAL</option>
                  <option value="LOAN">LOAN</option>
                  <option value="LIABILITY">LIABILITY</option>
                  <option value="ASSET">ASSET</option>
                  <option value="PARTY">PARTY</option>
                </select>
              </div>

              <div className="relative">
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Account Name *</label>
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={eeAccountName}
                    onChange={(e) => {
                      setEeAccountName(e.target.value);
                      setShowAcctDrop(false);
                    }}
                    className="flex-1 text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  <button
                    type="button"
                    onClick={searchEeAccounts}
                    className="px-2.5 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg hover:bg-indigo-100"
                    title="Search Account"
                  >
                    <Search className="h-3.5 w-3.5" />
                  </button>
                </div>
                {showAcctDrop && eeAcctSuggestions.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 max-h-40 overflow-y-auto bg-white border border-slate-200 rounded-lg shadow-lg z-30 divide-y divide-slate-100">
                    {eeAcctSuggestions.map((name, i) => (
                      <div
                        key={i}
                        onClick={() => {
                          setEeAccountName(name);
                          setShowAcctDrop(false);
                        }}
                        className="px-3 py-2 text-xs text-slate-700 hover:bg-indigo-50 cursor-pointer"
                      >
                        {name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {PARTY_LIKE_TYPES.has(eeAccountType) && (
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Party Type</label>
                <select
                  value={eePartyType}
                  onChange={(e) => setEePartyType(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="CUSTOMER">CUSTOMER</option>
                  <option value="VENDOR">VENDOR</option>
                  <option value="EMPLOYEE">EMPLOYEE</option>
                  <option value="EXTERNAL">EXTERNAL</option>
                </select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Reference Number</label>
                <input
                  type="text"
                  value={eeRefNum}
                  onChange={(e) => setEeRefNum(e.target.value)}
                  placeholder="e.g. IE-2024-001"
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="relative">
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Particulars</label>
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={eeParticulars}
                    onChange={(e) => {
                      setEeParticulars(e.target.value);
                      setShowPartDrop(false);
                    }}
                    placeholder="Counter-account or description"
                    className="flex-1 text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  <button
                    type="button"
                    onClick={searchEeParticulars}
                    className="px-2.5 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg hover:bg-indigo-100"
                    title="Search Particulars"
                  >
                    <Search className="h-3.5 w-3.5" />
                  </button>
                </div>
                {showPartDrop && eeParticularsSuggestions.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 max-h-40 overflow-y-auto bg-white border border-slate-200 rounded-lg shadow-lg z-30 divide-y divide-slate-100">
                    {eeParticularsSuggestions.map((p, i) => (
                      <div
                        key={i}
                        onClick={() => {
                          setEeParticulars(p);
                          setShowPartDrop(false);
                        }}
                        className="px-3 py-2 text-xs text-slate-700 hover:bg-indigo-50 cursor-pointer"
                      >
                        {p}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Narration / Notes</label>
              <input
                type="text"
                value={eeNarration}
                onChange={(e) => setEeNarration(e.target.value)}
                placeholder="Additional notes"
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">
                Counter-entry ID <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <input
                type="number"
                value={eeCounterId}
                onChange={(e) => setEeCounterId(e.target.value)}
                placeholder="Paired counter entry ID"
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 font-mono focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditEntryModalOpen(false)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={eeSaving}
                onClick={saveEntryEdit}
                className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
              >
                {eeSaving && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          MODAL 3: EDIT LEDGER MASTER
      ═══════════════════════════════════════════════════════════════ */}
      {editMasterModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-xl w-full max-h-[92vh] overflow-y-auto shadow-2xl p-6 border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <Edit className="h-5 w-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Edit Ledger Account</h3>
              </div>
              <button onClick={() => setEditMasterModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-center gap-4 text-slate-700">
              <span>
                <strong>Type:</strong> <span className="font-bold text-indigo-700">{eTypeDisplay}</span>
              </span>
              <span>
                <strong>Company:</strong> <span className="font-semibold">{eCompanyDisplay}</span>
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Account Name *</label>
                <input
                  type="text"
                  required
                  value={eName}
                  onChange={(e) => setEName(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Account Code</label>
                <input
                  type="text"
                  value={eCode}
                  onChange={(e) => setECode(e.target.value)}
                  maxLength={40}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Account Group</label>
                <input
                  type="text"
                  value={eGroup}
                  onChange={(e) => setEGroup(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">Description</label>
                <input
                  type="text"
                  value={eDesc}
                  onChange={(e) => setEDesc(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>

            {/* Bank details if BANK or UPI */}
            {(eTypeDisplay === "BANK" || eTypeDisplay === "UPI") && (
              <div className="p-4 bg-blue-50/70 border border-blue-200 rounded-xl space-y-3">
                <div className="text-xs font-bold text-blue-900 flex items-center gap-1.5">
                  <Landmark className="h-4 w-4 text-blue-700" /> Bank Account Details
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Account Number</label>
                    <input
                      type="text"
                      value={eAccountNumber}
                      onChange={(e) => setEAccountNumber(e.target.value)}
                      className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">IFSC Code</label>
                    <input
                      type="text"
                      value={eIfscCode}
                      onChange={(e) => setEIfscCode(e.target.value.toUpperCase())}
                      className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white uppercase font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Bank Name</label>
                    <input
                      type="text"
                      value={eBankName}
                      onChange={(e) => setEBankName(e.target.value)}
                      className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Opening Balance */}
            <div className="p-4 bg-purple-50/60 border border-purple-200 rounded-xl space-y-3">
              <div className="text-xs font-bold text-purple-900 flex items-center gap-1.5">
                <Scale className="h-4 w-4 text-purple-700" /> Opening Balance
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Amount (₹)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={eOB}
                    onChange={(e) => setEOB(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Balance Type</label>
                  <select
                    value={eOBType}
                    onChange={(e) => setEOBType(e.target.value as any)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                  >
                    <option value="DEBIT">Debit (Dr)</option>
                    <option value="CREDIT">Credit (Cr)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Opening Date</label>
                  <input
                    type="date"
                    value={eOBDate}
                    onChange={(e) => setEOBDate(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditMasterModalOpen(false)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={eSaving}
                onClick={saveMasterEdit}
                className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
              >
                {eSaving && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          MODAL 4: ADD PARTY MODAL (VENDOR, EXTERNAL, PARTNER)
      ═══════════════════════════════════════════════════════════════ */}
      {addPartyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[92vh] overflow-y-auto shadow-2xl p-6 border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <UserPlus className="h-5 w-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Add Party / Vendor</h3>
              </div>
              <button onClick={() => setAddPartyModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Step 1: Type Selection */}
            {apStep === 1 && (
              <div className="space-y-4 py-2">
                <p className="text-xs text-slate-500 font-medium">Select the party classification to proceed:</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Vendor Card */}
                  <div
                    onClick={() => {
                      setApType("VENDOR");
                      setApStep(2);
                    }}
                    className="p-5 rounded-xl border-2 border-amber-300 bg-amber-50/50 hover:bg-amber-100/60 cursor-pointer text-center space-y-2 transition-all"
                  >
                    <Store className="h-8 w-8 text-amber-600 mx-auto" />
                    <div className="text-sm font-bold text-slate-900">Vendor</div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Supplier · Manufacturer
                      <br />
                      Full GST &amp; Bank profiles
                    </p>
                  </div>

                  {/* External Party Card */}
                  <div
                    onClick={() => {
                      setApType("EXTERNAL");
                      setApStep(2);
                    }}
                    className="p-5 rounded-xl border-2 border-purple-300 bg-purple-50/50 hover:bg-purple-100/60 cursor-pointer text-center space-y-2 transition-all"
                  >
                    <Users className="h-8 w-8 text-purple-600 mx-auto" />
                    <div className="text-sm font-bold text-slate-900">External Party</div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Any person or entity
                      <br />
                      Quick one-off entries
                    </p>
                  </div>

                  {/* Official Partner Card */}
                  <div
                    onClick={() => {
                      setApType("PARTNER");
                      setApStep(2);
                    }}
                    className="p-5 rounded-xl border-2 border-emerald-300 bg-emerald-50/50 hover:bg-emerald-100/60 cursor-pointer text-center space-y-2 transition-all"
                  >
                    <Handshake className="h-8 w-8 text-emerald-600 mx-auto" />
                    <div className="text-sm font-bold text-slate-900">Official Partner</div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Dealer · Distributor
                      <br />
                      Service Center
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Forms */}
            {apStep === 2 && (
              <div className="space-y-4">
                <button
                  type="button"
                  onClick={() => setApStep(1)}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                >
                  <ChevronLeft className="h-4 w-4" /> Back to Party Type Options
                </button>

                {/* VENDOR FORM */}
                {apType === "VENDOR" && (
                  <div className="space-y-4">
                    {/* Sub-tabs for Vendor */}
                    <div className="flex border-b border-slate-200 gap-2">
                      {[
                        { id: "basic", label: "Basic Info" },
                        { id: "contacts", label: "Contacts" },
                        { id: "address", label: "Address" },
                        { id: "bank", label: "Bank & Payment" }
                      ].map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setApVendorTab(t.id as any)}
                          className={`px-3 py-1.5 text-xs font-semibold border-b-2 -mb-px transition-all ${
                            apVendorTab === t.id ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-800"
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>

                    {/* Vendor Tab: Basic */}
                    {apVendorTab === "basic" && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Vendor Name *</label>
                            <input
                              type="text"
                              value={apVName}
                              onChange={(e) => {
                                const name = e.target.value;
                                setApVName(name);
                                const words = name.toUpperCase().replace(/[^A-Z0-9 ]/g, "").split(" ").filter(Boolean);
                                const prefix = words.slice(0, 4).map((w) => w[0]).join("");
                                setApVCode(prefix + Date.now().toString().slice(-4));
                              }}
                              placeholder="Enter vendor name"
                              className="w-full text-xs border border-slate-300 rounded-lg p-2"
                            />
                          </div>

                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Vendor Code *</label>
                            <input
                              type="text"
                              value={apVCode}
                              onChange={(e) => setApVCode(e.target.value.toUpperCase())}
                              placeholder="Auto-generated..."
                              className="w-full text-xs border border-slate-300 rounded-lg p-2 font-mono uppercase"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Vendor Type</label>
                            <select
                              value={apVType}
                              onChange={(e) => setApVType(e.target.value)}
                              className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                            >
                              <option value="BOTH">Both (Product & Service)</option>
                              <option value="PRODUCT">Product Only</option>
                              <option value="SERVICE">Service Only</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Phone</label>
                            <input
                              type="text"
                              value={apVPhone}
                              onChange={(e) => setApVPhone(e.target.value)}
                              placeholder="Primary phone"
                              className="w-full text-xs border border-slate-300 rounded-lg p-2"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Email</label>
                            <input
                              type="email"
                              value={apVEmail}
                              onChange={(e) => setApVEmail(e.target.value)}
                              placeholder="Email address"
                              className="w-full text-xs border border-slate-300 rounded-lg p-2"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">GST Number</label>
                            <input
                              type="text"
                              maxLength={15}
                              value={apVGst}
                              onChange={(e) => setApVGst(e.target.value.toUpperCase())}
                              placeholder="15-char GSTIN"
                              className="w-full text-xs border border-slate-300 rounded-lg p-2 uppercase font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">PAN Number</label>
                            <input
                              type="text"
                              maxLength={10}
                              value={apVPan}
                              onChange={(e) => setApVPan(e.target.value.toUpperCase())}
                              placeholder="10-char PAN"
                              className="w-full text-xs border border-slate-300 rounded-lg p-2 uppercase font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">GST Type</label>
                            <select
                              value={apVGstType}
                              onChange={(e) => setApVGstType(e.target.value)}
                              className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                            >
                              <option value="CGST_SGST">CGST + SGST (Intra-state)</option>
                              <option value="IGST">IGST (Inter-state)</option>
                            </select>
                          </div>
                        </div>

                        {/* Applicable Companies */}
                        <div className="p-3 bg-purple-50/60 border border-purple-200 rounded-xl space-y-2">
                          <label className="block text-[10px] font-bold uppercase text-slate-700">Applicable Companies *</label>
                          <select
                            onChange={(e) => {
                              const val = e.target.value;
                              if (!val) return;
                              const c = companies.find((x) => String(x.id) === String(val));
                              if (c && !apSelectedCos.some((sc) => String(sc.id) === String(c.id))) {
                                setApSelectedCos([...apSelectedCos, { id: c.id, name: c.company_name || c.name || String(c.id) }]);
                              }
                              e.target.value = "";
                            }}
                            className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                          >
                            <option value="">— Add Applicable Company —</option>
                            {companies.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.company_name || c.name}
                              </option>
                            ))}
                          </select>
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {apSelectedCos.map((sc) => (
                              <span
                                key={sc.id}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800"
                              >
                                {sc.name}
                                <button
                                  type="button"
                                  onClick={() => setApSelectedCos(apSelectedCos.filter((x) => x.id !== sc.id))}
                                  className="text-purple-600 hover:text-purple-900"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Vendor Tab: Contacts */}
                    {apVendorTab === "contacts" && (
                      <div className="space-y-4">
                        <div className="text-xs font-bold text-indigo-700">Contact Person 1 (Primary)</div>
                        <div className="grid grid-cols-3 gap-3">
                          <input
                            type="text"
                            value={apVC1Name}
                            onChange={(e) => setApVC1Name(e.target.value)}
                            placeholder="Name"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVC1Phone}
                            onChange={(e) => setApVC1Phone(e.target.value)}
                            placeholder="Phone"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVC1Desig}
                            onChange={(e) => setApVC1Desig(e.target.value)}
                            placeholder="Designation"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                        </div>

                        <div className="text-xs font-bold text-indigo-700 pt-2 border-t border-slate-100">
                          Contact Person 2 (Secondary)
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                          <input
                            type="text"
                            value={apVC2Name}
                            onChange={(e) => setApVC2Name(e.target.value)}
                            placeholder="Name"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVC2Phone}
                            onChange={(e) => setApVC2Phone(e.target.value)}
                            placeholder="Phone"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVC2Desig}
                            onChange={(e) => setApVC2Desig(e.target.value)}
                            placeholder="Designation"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Website URL</label>
                          <input
                            type="url"
                            value={apVWebsite}
                            onChange={(e) => setApVWebsite(e.target.value)}
                            placeholder="https://www.example.com"
                            className="w-full text-xs border border-slate-300 rounded-lg p-2"
                          />
                        </div>
                      </div>
                    )}

                    {/* Vendor Tab: Address */}
                    {apVendorTab === "address" && (
                      <div className="space-y-4">
                        <div>
                          <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Primary Address</label>
                          <textarea
                            value={apVAddress}
                            onChange={(e) => setApVAddress(e.target.value)}
                            rows={2}
                            placeholder="Full address"
                            className="w-full text-xs border border-slate-300 rounded-lg p-2"
                          />
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                          <input
                            type="text"
                            maxLength={6}
                            value={apVPincode}
                            onChange={(e) => {
                              setApVPincode(e.target.value);
                              if (e.target.value.length === 6) apLookupPin(e.target.value, "Vendor");
                            }}
                            placeholder="6-digit PIN"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVCity}
                            onChange={(e) => setApVCity(e.target.value)}
                            placeholder="City"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVState}
                            onChange={(e) => setApVState(e.target.value)}
                            placeholder="State"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                        </div>
                      </div>
                    )}

                    {/* Vendor Tab: Bank */}
                    {apVendorTab === "bank" && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                          <input
                            type="text"
                            value={apVBankName}
                            onChange={(e) => setApVBankName(e.target.value)}
                            placeholder="Bank Name"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVBankBranch}
                            onChange={(e) => setApVBankBranch(e.target.value)}
                            placeholder="Branch Name"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <input
                            type="text"
                            value={apVAcctNo}
                            onChange={(e) => setApVAcctNo(e.target.value)}
                            placeholder="Account Number"
                            className="text-xs border border-slate-300 rounded-lg p-2 font-mono"
                          />
                          <input
                            type="text"
                            maxLength={11}
                            value={apVIfsc}
                            onChange={(e) => setApVIfsc(e.target.value.toUpperCase())}
                            placeholder="IFSC Code"
                            className="text-xs border border-slate-300 rounded-lg p-2 uppercase font-mono"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <input
                            type="text"
                            value={apVAcctHolder}
                            onChange={(e) => setApVAcctHolder(e.target.value)}
                            placeholder="Account Holder Name"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                          <input
                            type="text"
                            value={apVUpi}
                            onChange={(e) => setApVUpi(e.target.value)}
                            placeholder="UPI ID"
                            className="text-xs border border-slate-300 rounded-lg p-2"
                          />
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => setAddPartyModalOpen(false)}
                        className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        disabled={apSaving}
                        onClick={handleVendorSubmit}
                        className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
                      >
                        {apSaving && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                        Save Vendor
                      </button>
                    </div>
                  </div>
                )}

                {/* EXTERNAL PARTY FORM */}
                {apType === "EXTERNAL" && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Name *</label>
                        <input
                          type="text"
                          required
                          value={apExtName}
                          onChange={(e) => setApExtName(e.target.value)}
                          placeholder="Full person / entity name"
                          className="w-full text-xs border border-slate-300 rounded-lg p-2.5"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Mobile Number *</label>
                        <input
                          type="tel"
                          required
                          value={apExtPhone}
                          onChange={(e) => setApExtPhone(e.target.value)}
                          placeholder="10-digit mobile number"
                          className="w-full text-xs border border-slate-300 rounded-lg p-2.5"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Email</label>
                      <input
                        type="email"
                        value={apExtEmail}
                        onChange={(e) => setApExtEmail(e.target.value)}
                        placeholder="Email address"
                        className="w-full text-xs border border-slate-300 rounded-lg p-2.5"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold uppercase text-slate-700 mb-1">Notes</label>
                      <textarea
                        rows={2}
                        value={apExtNotes}
                        onChange={(e) => setApExtNotes(e.target.value)}
                        placeholder="Any additional notes..."
                        className="w-full text-xs border border-slate-300 rounded-lg p-2"
                      />
                    </div>

                    <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => setAddPartyModalOpen(false)}
                        className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        disabled={apSaving}
                        onClick={handleExternalSubmit}
                        className="px-5 py-2 bg-purple-600 text-white rounded-lg text-xs font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                      >
                        {apSaving && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                        Save Party
                      </button>
                    </div>
                  </div>
                )}

                {/* OFFICIAL PARTNER INFO */}
                {apType === "PARTNER" && (
                  <div className="p-6 bg-emerald-50/70 border border-emerald-300 rounded-xl text-center space-y-3">
                    <Handshake className="h-10 w-10 text-emerald-600 mx-auto" />
                    <h4 className="text-sm font-bold text-slate-900">Official Partner Onboarding</h4>
                    <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
                      Dealers, Distributors, and Service Centers are managed through the Official Partner Portal with KYC and territory assignment.
                    </p>
                    <Link
                      href="/staff/official-partners"
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700"
                    >
                      <ExternalLink className="h-3.5 w-3.5" /> Go to Partner Management
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
