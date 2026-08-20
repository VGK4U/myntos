"use client";

import React, { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Search,
  Plus,
  Building2,
  Phone,
  Mail,
  MapPin,
  CheckCircle,
  XCircle,
  Edit,
  RefreshCw,
  Sun,
} from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

interface SolarVendor {
  id: number;
  vendor_name: string;
  vendor_code: string;
  phone?: string;
  email?: string;
  city?: string;
  state?: string;
  gst_number?: string;
  mnre_empanelled?: boolean;
  mnre_reg_no?: string;
  contact_person?: string;
  address?: string;
  pincode?: string;
  website?: string;
  solar_products?: string[];
  notes?: string;
  is_active?: boolean;
  created_at?: string;
}

export default function SolarVendorsPage() {
  const { token } = useStaffAuth();
  const [vendors, setVendors] = useState<SolarVendor[]>([]);
  const [filtered, setFiltered] = useState<SolarVendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editVendor, setEditVendor] = useState<SolarVendor | null>(null);
  const [saving, setSaving] = useState(false);

  // Form state
  const [form, setForm] = useState({
    vendor_name: "",
    vendor_code: "",
    phone: "",
    email: "",
    city: "",
    state: "",
    gst_number: "",
    mnre_empanelled: false,
    mnre_reg_no: "",
    contact_person: "",
    address: "",
    pincode: "",
    website: "",
    notes: "",
  });

  const loadVendors = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/crm/solar-vendors");
      const data = res.data;
      const list: SolarVendor[] = data.vendors || data.data || data || [];
      setVendors(list);
      setFiltered(list);
    } catch (err: any) {
      toast.error("Failed to load solar vendors");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) loadVendors();
  }, [token, loadVendors]);

  useEffect(() => {
    const q = search.toLowerCase();
    if (!q) {
      setFiltered(vendors);
    } else {
      setFiltered(
        vendors.filter(
          (v) =>
            v.vendor_name?.toLowerCase().includes(q) ||
            v.vendor_code?.toLowerCase().includes(q) ||
            v.city?.toLowerCase().includes(q) ||
            v.phone?.includes(q) ||
            v.email?.toLowerCase().includes(q)
        )
      );
    }
  }, [search, vendors]);

  const openAdd = () => {
    setEditVendor(null);
    setForm({
      vendor_name: "",
      vendor_code: "",
      phone: "",
      email: "",
      city: "",
      state: "",
      gst_number: "",
      mnre_empanelled: false,
      mnre_reg_no: "",
      contact_person: "",
      address: "",
      pincode: "",
      website: "",
      notes: "",
    });
    setShowModal(true);
  };

  const openEdit = (v: SolarVendor) => {
    setEditVendor(v);
    setForm({
      vendor_name: v.vendor_name || "",
      vendor_code: v.vendor_code || "",
      phone: v.phone || "",
      email: v.email || "",
      city: v.city || "",
      state: v.state || "",
      gst_number: v.gst_number || "",
      mnre_empanelled: v.mnre_empanelled || false,
      mnre_reg_no: v.mnre_reg_no || "",
      contact_person: v.contact_person || "",
      address: v.address || "",
      pincode: v.pincode || "",
      website: v.website || "",
      notes: v.notes || "",
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.vendor_name.trim()) {
      toast.error("Vendor name is required");
      return;
    }
    setSaving(true);
    try {
      if (editVendor) {
        await api.put(`/staff/accounts/vendors/${editVendor.id}`, form);
        toast.success("Vendor updated successfully");
      } else {
        await api.post("/staff/accounts/vendors", form);
        toast.success("Vendor added successfully");
      }
      setShowModal(false);
      loadVendors();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to save vendor");
    } finally {
      setSaving(false);
    }
  };

  const empanelledCount = vendors.filter((v) => v.mnre_empanelled).length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Sun className="w-6 h-6 text-amber-500" />
            Solar Vendors
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage MNRE-empanelled and other solar vendors
          </p>
        </div>
        <Button
          onClick={openAdd}
          className="bg-teal-700 hover:bg-teal-800 text-white gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Vendor
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-teal-50 rounded-lg">
              <Building2 className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Vendors</p>
              <p className="text-xl font-bold text-gray-900">{vendors.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">MNRE Empanelled</p>
              <p className="text-xl font-bold text-gray-900">{empanelledCount}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-amber-50 rounded-lg">
              <XCircle className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Not Empanelled</p>
              <p className="text-xl font-bold text-gray-900">
                {vendors.length - empanelledCount}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <MapPin className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Cities</p>
              <p className="text-xl font-bold text-gray-900">
                {new Set(vendors.map((v) => v.city).filter(Boolean)).size}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-3 items-center flex-wrap">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search by name, code, city, phone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadVendors}
              className="gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader className="pb-2 pt-4 px-4 flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-semibold text-gray-700">
            Vendor List
          </CardTitle>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {filtered.length} vendor{filtered.length !== 1 ? "s" : ""}
          </span>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center items-center py-16">
              <RefreshCw className="w-6 h-6 text-teal-600 animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <Building2 className="w-10 h-10 mx-auto mb-3 text-gray-200" />
              <p className="font-medium">No solar vendors found</p>
              <p className="text-sm mt-1">
                {search ? "Try a different search term" : "Add your first solar vendor"}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Vendor</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Contact</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Location</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">GST</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">MNRE Status</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((v, idx) => (
                    <tr key={v.id ?? idx} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-semibold text-gray-900">{v.vendor_name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{v.vendor_code}</p>
                      </td>
                      <td className="px-4 py-3">
                        {v.phone && (
                          <div className="flex items-center gap-1 text-gray-700">
                            <Phone className="w-3 h-3 text-gray-400" />
                            {v.phone}
                          </div>
                        )}
                        {v.email && (
                          <div className="flex items-center gap-1 text-gray-500 text-xs mt-0.5">
                            <Mail className="w-3 h-3 text-gray-400" />
                            {v.email}
                          </div>
                        )}
                        {!v.phone && !v.email && <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-gray-700">
                          <MapPin className="w-3 h-3 text-gray-400" />
                          {v.city || "—"}
                          {v.state && <span className="text-gray-400"> / {v.state}</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {v.gst_number ? (
                          <code className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono">
                            {v.gst_number}
                          </code>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {v.mnre_empanelled ? (
                          <div>
                            <Badge className="bg-green-100 text-green-700 border-0 gap-1">
                              <CheckCircle className="w-3 h-3" />
                              Empanelled
                            </Badge>
                            {v.mnre_reg_no && (
                              <p className="text-xs text-gray-500 mt-1">
                                Reg: {v.mnre_reg_no}
                              </p>
                            )}
                          </div>
                        ) : (
                          <Badge variant="secondary" className="text-gray-500">
                            Not Empanelled
                          </Badge>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEdit(v)}
                          className="gap-1.5 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                        >
                          <Edit className="w-3.5 h-3.5" />
                          Edit
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sun className="w-5 h-5 text-amber-500" />
              {editVendor ? `Edit: ${editVendor.vendor_name}` : "Add Solar Vendor"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            {/* Basic Info */}
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Basic Info</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Vendor Name *</Label>
                  <Input
                    value={form.vendor_name}
                    onChange={(e) => setForm({ ...form, vendor_name: e.target.value })}
                    placeholder="Solar Company Pvt Ltd"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs">Vendor Code</Label>
                  <Input
                    value={form.vendor_code}
                    onChange={(e) => setForm({ ...form, vendor_code: e.target.value })}
                    placeholder="SOL001"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs">Contact Person</Label>
                  <Input
                    value={form.contact_person}
                    onChange={(e) => setForm({ ...form, contact_person: e.target.value })}
                    placeholder="Name"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs">Phone</Label>
                  <Input
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="9876543210"
                    className="mt-1"
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Email</Label>
                  <Input
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="vendor@example.com"
                    className="mt-1"
                  />
                </div>
              </div>
            </div>

            {/* Location */}
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Location</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">City</Label>
                  <Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} placeholder="Mumbai" className="mt-1" />
                </div>
                <div>
                  <Label className="text-xs">State</Label>
                  <Input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} placeholder="Maharashtra" className="mt-1" />
                </div>
                <div>
                  <Label className="text-xs">Pincode</Label>
                  <Input value={form.pincode} onChange={(e) => setForm({ ...form, pincode: e.target.value })} placeholder="400001" className="mt-1" />
                </div>
                <div>
                  <Label className="text-xs">GST Number</Label>
                  <Input value={form.gst_number} onChange={(e) => setForm({ ...form, gst_number: e.target.value })} placeholder="27AAAPL1234C1ZV" className="mt-1" />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Address</Label>
                  <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Full address" className="mt-1" />
                </div>
              </div>
            </div>

            {/* MNRE */}
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">MNRE Details</p>
              <div className="grid grid-cols-2 gap-3 items-center">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="mnre"
                    checked={form.mnre_empanelled}
                    onChange={(e) => setForm({ ...form, mnre_empanelled: e.target.checked })}
                    className="w-4 h-4 accent-teal-600"
                  />
                  <Label htmlFor="mnre" className="text-sm font-medium cursor-pointer">
                    MNRE Empanelled
                  </Label>
                </div>
                {form.mnre_empanelled && (
                  <div>
                    <Label className="text-xs">MNRE Reg. No.</Label>
                    <Input value={form.mnre_reg_no} onChange={(e) => setForm({ ...form, mnre_reg_no: e.target.value })} placeholder="REG/2024/001" className="mt-1" />
                  </div>
                )}
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label className="text-xs">Notes</Label>
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Any additional notes..."
                rows={2}
                className="mt-1 w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2 border-t">
              <Button variant="outline" onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving}
                className="bg-teal-700 hover:bg-teal-800 text-white"
              >
                {saving ? "Saving..." : editVendor ? "Update Vendor" : "Add Vendor"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
