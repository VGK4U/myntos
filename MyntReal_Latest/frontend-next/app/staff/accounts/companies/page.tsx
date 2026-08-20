"use client";

import { useState, useEffect } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Building2, Plus, Trash2, MapPin, Tag, Landmark, Loader2, Save, ExternalLink } from "lucide-react";

interface Company {
  id: number;
  company_name?: string;
  name?: string;
  company_code?: string;
  code?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  gst_number?: string;
  pan_number?: string;
  cin_number?: string;
  is_active: boolean;
  is_marketplace_endpoint: boolean;
}

interface Category {
  id: number;
  name: string;
  slug: string;
  icon: string;
  is_active: boolean;
}

interface BankAccount {
  id: number;
  bank_name: string;
  branch?: string;
  account_number: string;
  ifsc_code?: string;
  account_type: string;
  is_primary: boolean;
  is_active: boolean;
  notes?: string;
}

const MASTER_CATEGORIES = [
  { name: 'ETC Training', slug: 'etc-training', icon: 'fas fa-graduation-cap', description: 'ETC Training Program' },
  { name: 'EV B2B', slug: 'ev-b2b', icon: 'fas fa-building', description: 'EV Business to Business' },
  { name: 'EV B2C', slug: 'ev-b2c', icon: 'fas fa-car', description: 'EV Business to Consumer' },
  { name: 'EV Spares', slug: 'ev-spares', icon: 'fas fa-cogs', description: 'EV Spare Parts' },
  { name: 'Insurance', slug: 'insurance', icon: 'fas fa-shield-alt', description: 'Insurance Services' },
  { name: 'Real Dreams', slug: 'real-dreams', icon: 'fas fa-home', description: 'Real Dreams Property' },
  { name: 'Solar', slug: 'solar', icon: 'fas fa-solar-panel', description: 'Solar Energy Solutions' }
];

export default function CompaniesPage() {
  const { token } = useStaffAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isBankOpen, setIsBankOpen] = useState(false);
  
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [loadingBanks, setLoadingBanks] = useState(false);
  const [selectedBank, setSelectedBank] = useState<BankAccount | null>(null);

  // Form states
  const [formData, setFormData] = useState<Partial<Company>>({});
  const [bankFormData, setBankFormData] = useState<Partial<BankAccount>>({});
  const [selectedCatToAdd, setSelectedCatToAdd] = useState("");

  const fetchCompanies = async () => {
    setLoading(true);
    try {
      const res = await api.get("/staff/accounts/companies?status_filter=ALL&page_size=100");
      setCompanies(res.data.companies || []);
    } catch (err: any) {
      alert("Failed to load companies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchCompanies();
  }, [token]);

  const handleCreate = async () => {
    if (!formData.company_name || !formData.company_code) {
      alert("Name and Code are required");
      return;
    }
    try {
      await api.post("/staff/accounts/companies", {
        company_name: formData.company_name,
        company_code: formData.company_code.toUpperCase(),
        address: formData.address || null,
        gst_number: formData.gst_number?.toUpperCase() || null,
        is_marketplace_endpoint: formData.is_marketplace_endpoint || false
      });
      setIsCreateOpen(false);
      setFormData({});
      fetchCompanies();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create company");
    }
  };

  const handleUpdate = async () => {
    if (!selectedCompany?.id || !formData.company_name) return;
    try {
      await api.put(`/staff/accounts/companies/${selectedCompany.id}`, {
        company_name: formData.company_name,
        is_active: formData.is_active,
        address: formData.address || null,
        city: formData.city || null,
        state: formData.state || null,
        pincode: formData.pincode || null,
        gst_number: formData.gst_number?.toUpperCase() || null,
        pan_number: formData.pan_number?.toUpperCase() || null,
        cin_number: formData.cin_number?.toUpperCase() || null,
        is_marketplace_endpoint: formData.is_marketplace_endpoint || false
      });
      setIsEditOpen(false);
      fetchCompanies();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to update company");
    }
  };

  const handleDelete = async () => {
    if (!selectedCompany?.id) return;
    if (!confirm(`Are you sure you want to delete this company?`)) return;
    try {
      await api.delete(`/staff/accounts/companies/${selectedCompany.id}`);
      setIsEditOpen(false);
      fetchCompanies();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete company");
    }
  };

  const openEditModal = (comp: Company) => {
    setSelectedCompany(comp);
    setFormData({
      company_name: comp.company_name || comp.name || "",
      company_code: comp.company_code || comp.code || "",
      is_active: comp.is_active !== false,
      address: comp.address || "",
      city: comp.city || "",
      state: comp.state || "",
      pincode: comp.pincode || "",
      gst_number: comp.gst_number || "",
      pan_number: comp.pan_number || "",
      cin_number: comp.cin_number || "",
      is_marketplace_endpoint: comp.is_marketplace_endpoint || false
    });
    fetchCategories(comp.id);
    fetchBankAccounts(comp.id);
    setIsEditOpen(true);
  };

  const fetchCategories = async (companyId: number) => {
    setLoadingCategories(true);
    try {
      const res = await api.get(`/signup-categories/admin?company_id=${companyId}&include_inactive=true`);
      setCategories(res.data.categories || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCategories(false);
    }
  };

  const toggleCategory = async (catId: number) => {
    if (!selectedCompany) return;
    try {
      await api.post(`/signup-categories/${catId}/toggle?company_id=${selectedCompany.id}`);
      fetchCategories(selectedCompany.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to toggle category");
    }
  };

  const addCategory = async () => {
    if (!selectedCompany || !selectedCatToAdd) return;
    const mc = MASTER_CATEGORIES.find(c => c.slug === selectedCatToAdd);
    if (!mc) return;
    try {
      await api.post(`/signup-categories/create?company_id=${selectedCompany.id}`, {
        name: mc.name,
        slug: mc.slug,
        description: mc.description,
        icon: mc.icon,
        display_order: categories.length + 1
      });
      setSelectedCatToAdd("");
      fetchCategories(selectedCompany.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to add category");
    }
  };

  const fetchBankAccounts = async (companyId: number) => {
    setLoadingBanks(true);
    try {
      const res = await api.get(`/staff/accounts/companies/${companyId}/bank-accounts`);
      setBankAccounts(res.data.bank_accounts || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingBanks(false);
    }
  };

  const openBankModal = (bank: BankAccount | null = null) => {
    setSelectedBank(bank);
    if (bank) {
      setBankFormData({
        bank_name: bank.bank_name,
        branch: bank.branch || "",
        account_number: bank.account_number,
        ifsc_code: bank.ifsc_code || "",
        account_type: bank.account_type || "CURRENT",
        is_primary: bank.is_primary || false,
        notes: bank.notes || ""
      });
    } else {
      setBankFormData({ account_type: "CURRENT", is_primary: false });
    }
    setIsBankOpen(true);
  };

  const saveBankAccount = async () => {
    if (!selectedCompany) return;
    if (!bankFormData.bank_name || !bankFormData.account_number) {
      alert("Bank name and Account number are required");
      return;
    }
    
    const payload = {
      bank_name: bankFormData.bank_name,
      branch: bankFormData.branch || null,
      account_number: bankFormData.account_number,
      ifsc_code: bankFormData.ifsc_code?.toUpperCase() || null,
      account_type: bankFormData.account_type,
      is_primary: bankFormData.is_primary,
      notes: bankFormData.notes || null
    };

    try {
      if (selectedBank) {
        await api.put(`/staff/accounts/companies/${selectedCompany.id}/bank-accounts/${selectedBank.id}`, payload);
      } else {
        await api.post(`/staff/accounts/companies/${selectedCompany.id}/bank-accounts`, payload);
      }
      setIsBankOpen(false);
      fetchBankAccounts(selectedCompany.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to save bank account");
    }
  };

  const deleteBankAccount = async () => {
    if (!selectedCompany || !selectedBank) return;
    if (!confirm("Delete this bank account?")) return;
    try {
      await api.delete(`/staff/accounts/companies/${selectedCompany.id}/bank-accounts/${selectedBank.id}`);
      setIsBankOpen(false);
      fetchBankAccounts(selectedCompany.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete bank account");
    }
  };

  const availableCategories = MASTER_CATEGORIES.filter(
    mc => !categories.some(c => c.slug.toLowerCase() === mc.slug.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Building2 className="text-indigo-600 w-6 h-6" />
            Companies
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage associated companies and their categories</p>
        </div>
        <Button onClick={() => { setFormData({ is_marketplace_endpoint: false }); setIsCreateOpen(true); }} className="bg-indigo-600 hover:bg-indigo-700">
          <Plus className="w-4 h-4 mr-2" /> Add Company
        </Button>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="w-5 h-5 text-gray-500" /> Companies
          </CardTitle>
          <span className="text-sm text-gray-500">{companies.length} companies</span>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center p-8"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>
          ) : companies.length === 0 ? (
            <div className="text-center p-12 text-gray-500">
              <Building2 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900">No Companies Found</h3>
              <p>Add your first company to get started</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {companies.map(comp => (
                <div 
                  key={comp.id} 
                  onClick={() => openEditModal(comp)}
                  className="bg-white border border-gray-200 rounded-xl p-5 cursor-pointer hover:border-indigo-500 hover:shadow-md transition-all group"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                        {comp.company_name || comp.name}
                        {comp.is_marketplace_endpoint && (
                          <Badge variant="secondary" className="bg-indigo-50 text-indigo-700 text-[10px]">Mkt Endpoint</Badge>
                        )}
                      </h3>
                      <p className="text-sm text-gray-500">{comp.company_code || comp.code}</p>
                    </div>
                    <Badge className={comp.is_active ? "bg-green-100 text-green-700 hover:bg-green-100" : "bg-red-100 text-red-700 hover:bg-red-100"} variant="outline">
                      {comp.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500 mt-4">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> {(comp.address || 'No address').substring(0, 30)}
                    </span>
                    {comp.gst_number && (
                      <span className="flex items-center gap-1">
                        <Tag className="w-3 h-3" /> {comp.gst_number}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Company</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Company Name *</Label>
              <Input value={formData.company_name || ""} onChange={e => setFormData({...formData, company_name: e.target.value})} placeholder="Enter company name" />
            </div>
            <div className="space-y-2">
              <Label>Short Code *</Label>
              <Input value={formData.company_code || ""} onChange={e => setFormData({...formData, company_code: e.target.value})} placeholder="e.g., MRL" />
            </div>
            <div className="space-y-2">
              <Label>Address</Label>
              <Textarea value={formData.address || ""} onChange={e => setFormData({...formData, address: e.target.value})} placeholder="Company address" rows={2} />
            </div>
            <div className="space-y-2">
              <Label>GST Number</Label>
              <Input value={formData.gst_number || ""} onChange={e => setFormData({...formData, gst_number: e.target.value})} placeholder="GST registration number" maxLength={15} />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox id="is_marketplace" checked={formData.is_marketplace_endpoint || false} onCheckedChange={(checked) => setFormData({...formData, is_marketplace_endpoint: checked as boolean})} />
              <div className="grid gap-1.5 leading-none">
                <label htmlFor="is_marketplace" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  Marketplace Endpoint
                </label>
                <p className="text-xs text-indigo-600">Sells marketplace items to customers</p>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} className="bg-indigo-600 hover:bg-indigo-700"><Save className="w-4 h-4 mr-2"/> Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Company</DialogTitle>
          </DialogHeader>
          
          <Tabs defaultValue="details" className="mt-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="categories">Categories</TabsTrigger>
              <TabsTrigger value="banks">Bank Accounts</TabsTrigger>
            </TabsList>
            
            <TabsContent value="details" className="space-y-4 pt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2 col-span-2">
                  <Label>Company Name *</Label>
                  <Input value={formData.company_name || ""} onChange={e => setFormData({...formData, company_name: e.target.value})} />
                </div>
                <div className="space-y-2">
                  <Label>Short Code</Label>
                  <Input value={formData.company_code || ""} disabled className="bg-gray-50" />
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={formData.is_active ? "true" : "false"} onValueChange={(val) => setFormData({...formData, is_active: val === "true"})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Active</SelectItem>
                      <SelectItem value="false">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 col-span-2">
                  <Label>Address</Label>
                  <Textarea value={formData.address || ""} onChange={e => setFormData({...formData, address: e.target.value})} rows={2} />
                </div>
                <div className="space-y-2">
                  <Label>City</Label>
                  <Input value={formData.city || ""} onChange={e => setFormData({...formData, city: e.target.value})} />
                </div>
                <div className="space-y-2">
                  <Label>State</Label>
                  <Input value={formData.state || ""} onChange={e => setFormData({...formData, state: e.target.value})} />
                </div>
                <div className="space-y-2">
                  <Label>Pincode</Label>
                  <Input value={formData.pincode || ""} onChange={e => setFormData({...formData, pincode: e.target.value})} maxLength={10} />
                </div>
                <div className="space-y-2">
                  <Label>GST Number</Label>
                  <Input value={formData.gst_number || ""} onChange={e => setFormData({...formData, gst_number: e.target.value})} maxLength={15} />
                </div>
                <div className="space-y-2">
                  <Label>PAN Number</Label>
                  <Input value={formData.pan_number || ""} onChange={e => setFormData({...formData, pan_number: e.target.value})} maxLength={15} />
                </div>
                <div className="space-y-2">
                  <Label>CIN Number</Label>
                  <Input value={formData.cin_number || ""} onChange={e => setFormData({...formData, cin_number: e.target.value})} maxLength={25} />
                </div>
                <div className="col-span-2 flex items-center space-x-2 pt-2">
                  <Checkbox id="edit_is_marketplace" checked={formData.is_marketplace_endpoint || false} onCheckedChange={(checked) => setFormData({...formData, is_marketplace_endpoint: checked as boolean})} />
                  <div className="grid gap-1.5 leading-none">
                    <label htmlFor="edit_is_marketplace" className="text-sm font-medium leading-none">
                      Marketplace Endpoint
                    </label>
                    <p className="text-xs text-indigo-600">Sells marketplace items to customers</p>
                  </div>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="categories" className="space-y-4 pt-4">
              <div className="flex items-center gap-2 mb-4">
                <Select value={selectedCatToAdd} onValueChange={setSelectedCatToAdd}>
                  <SelectTrigger className="flex-1"><SelectValue placeholder="-- Select category to add --" /></SelectTrigger>
                  <SelectContent>
                    {availableCategories.map(mc => (
                      <SelectItem key={mc.slug} value={mc.slug}>{mc.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button onClick={addCategory} disabled={!selectedCatToAdd} className="bg-indigo-600 hover:bg-indigo-700">
                  <Plus className="w-4 h-4 mr-1" /> Add
                </Button>
              </div>

              {loadingCategories ? (
                <div className="flex justify-center p-4"><Loader2 className="w-6 h-6 animate-spin text-indigo-600" /></div>
              ) : categories.length === 0 ? (
                <div className="text-center p-4 text-gray-500 text-sm">No categories assigned.</div>
              ) : (
                <div className="space-y-2">
                  {categories.map(cat => (
                    <div key={cat.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{cat.name}</p>
                        <p className="text-xs font-mono text-gray-500">{cat.slug}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500">{cat.is_active ? 'Active' : 'Inactive'}</span>
                        <Checkbox checked={cat.is_active !== false} onCheckedChange={() => toggleCategory(cat.id)} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="text-right mt-4">
                <a href={`/staff/signup-categories?company_id=${selectedCompany?.id}`} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline flex items-center justify-end gap-1 font-medium">
                  <ExternalLink className="w-3 h-3" /> Advanced Management
                </a>
              </div>
            </TabsContent>

            <TabsContent value="banks" className="space-y-4 pt-4">
              <div className="flex justify-end mb-4">
                <Button onClick={() => openBankModal()} size="sm" className="bg-indigo-600 hover:bg-indigo-700">
                  <Plus className="w-4 h-4 mr-1" /> Add Bank Account
                </Button>
              </div>

              {loadingBanks ? (
                <div className="flex justify-center p-4"><Loader2 className="w-6 h-6 animate-spin text-indigo-600" /></div>
              ) : bankAccounts.length === 0 ? (
                <div className="text-center p-4 text-gray-500 text-sm">No bank accounts added yet.</div>
              ) : (
                <div className="space-y-2">
                  {bankAccounts.map(bank => (
                    <div key={bank.id} onClick={() => openBankModal(bank)} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100 cursor-pointer hover:border-indigo-300">
                      <div className="flex items-center gap-3">
                        <Landmark className="w-5 h-5 text-indigo-500" />
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-gray-900">{bank.bank_name}</p>
                            {bank.is_primary && <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 text-[10px] px-1.5 py-0">Primary</Badge>}
                            {!bank.is_active && <Badge variant="destructive" className="text-[10px] px-1.5 py-0">Inactive</Badge>}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                            <span className="font-mono">{bank.account_number}</span>
                            <span>•</span>
                            <span>{bank.account_type}</span>
                            <span>•</span>
                            <span>{bank.ifsc_code}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
          
          <DialogFooter className="flex justify-between items-center sm:justify-between pt-4 mt-4 border-t border-gray-100">
            <Button variant="destructive" onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              <Trash2 className="w-4 h-4 mr-2" /> Delete
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancel</Button>
              <Button onClick={handleUpdate} className="bg-indigo-600 hover:bg-indigo-700">
                <Save className="w-4 h-4 mr-2" /> Update
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bank Account Modal */}
      <Dialog open={isBankOpen} onOpenChange={setIsBankOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedBank ? 'Edit Bank Account' : 'Add Bank Account'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2 col-span-2 md:col-span-1">
                <Label>Bank Name *</Label>
                <Input value={bankFormData.bank_name || ""} onChange={e => setBankFormData({...bankFormData, bank_name: e.target.value})} placeholder="e.g. HDFC Bank" />
              </div>
              <div className="space-y-2 col-span-2 md:col-span-1">
                <Label>Branch</Label>
                <Input value={bankFormData.branch || ""} onChange={e => setBankFormData({...bankFormData, branch: e.target.value})} placeholder="Branch name/city" />
              </div>
              <div className="space-y-2 col-span-2 md:col-span-1">
                <Label>Account Number *</Label>
                <Input value={bankFormData.account_number || ""} onChange={e => setBankFormData({...bankFormData, account_number: e.target.value})} placeholder="Account number" />
              </div>
              <div className="space-y-2 col-span-2 md:col-span-1">
                <Label>IFSC Code</Label>
                <Input value={bankFormData.ifsc_code || ""} onChange={e => setBankFormData({...bankFormData, ifsc_code: e.target.value.toUpperCase()})} placeholder="IFSC" maxLength={11} className="uppercase" />
              </div>
              <div className="space-y-2 col-span-2 md:col-span-1">
                <Label>Account Type</Label>
                <Select value={bankFormData.account_type || "CURRENT"} onValueChange={(val) => setBankFormData({...bankFormData, account_type: val})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CURRENT">Current</SelectItem>
                    <SelectItem value="SAVINGS">Savings</SelectItem>
                    <SelectItem value="OD">Overdraft (OD)</SelectItem>
                    <SelectItem value="CC">Cash Credit (CC)</SelectItem>
                    <SelectItem value="UPI">UPI</SelectItem>
                    <SelectItem value="CASH">Cash</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 col-span-2 md:col-span-1 flex items-center mt-6">
                <div className="flex items-center space-x-2">
                  <Checkbox id="is_primary" checked={bankFormData.is_primary || false} onCheckedChange={(c) => setBankFormData({...bankFormData, is_primary: c as boolean})} />
                  <label htmlFor="is_primary" className="text-sm font-medium leading-none">Primary Account</label>
                </div>
              </div>
              <div className="space-y-2 col-span-2">
                <Label>Notes</Label>
                <Input value={bankFormData.notes || ""} onChange={e => setBankFormData({...bankFormData, notes: e.target.value})} placeholder="Optional notes" />
              </div>
            </div>
          </div>
          <DialogFooter className="flex justify-between items-center sm:justify-between">
            {selectedBank ? (
              <Button variant="destructive" onClick={deleteBankAccount} size="sm">
                <Trash2 className="w-4 h-4 mr-2" /> Delete
              </Button>
            ) : <div></div>}
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsBankOpen(false)} size="sm">Cancel</Button>
              <Button onClick={saveBankAccount} className="bg-indigo-600 hover:bg-indigo-700" size="sm">
                <Save className="w-4 h-4 mr-2" /> Save
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
