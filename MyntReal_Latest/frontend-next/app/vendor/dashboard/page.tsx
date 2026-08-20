"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Store, ChartBar, Tags, ShoppingCart, Receipt, QrCode, Wrench, Edit, ShareAlt, LogOut } from "lucide-react";

// Mock API Call - in real app would use axios/fetch
const API = '/api/v1';

export default function VendorDashboard() {
  const router = useRouter();
  const [vendorInfo, setVendorInfo] = useState<any>(null);

  useEffect(() => {
    // We mock the API call here since we are just converting the frontend layout
    // Replace this with actual API fetch later
    setVendorInfo({
      vendor_code: "VND-8372",
      vendor_name: "Super Electronics Vendor",
      category_name: "Electronics",
      city: "Mumbai",
      pincode: "400001",
      status: "ACTIVE",
      total_transactions: 142,
      total_business_value: 450000,
      total_discount_given: 12000,
      flat_discount_pct: 10,
      phone: "9876543210",
      email: "contact@superelec.com",
      gst_number: "27ABCDE1234F1Z5",
      address_line1: "123 Tech Street",
      shop_description: "Best electronics shop in town.",
      qr_b64: "", // mock base64
      qr_url: "https://vgk4u.com/v/VND-8372"
    });
  }, []);

  if (!vendorInfo) return <div className="p-8 text-center text-gray-500">Loading vendor details...</div>;

  return (
    <div className="min-h-screen bg-green-50 font-sans">
      {/* Topbar */}
      <div className="sticky top-0 z-50 flex h-[60px] items-center justify-between bg-gradient-to-br from-emerald-900 to-emerald-600 px-6 text-white shadow-md">
        <div className="flex items-center gap-3 text-[17px] font-extrabold">
          <Store className="h-5 w-5" />
          <span>Vendor Portal</span>
          <span className="rounded-full border border-white/30 bg-white/20 px-3 py-1 text-xs font-bold">
            {vendorInfo.vendor_code}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm opacity-90">{vendorInfo.vendor_name}</span>
          <button 
            onClick={() => router.push('/vendor/login')}
            className="flex items-center gap-1 rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20"
          >
            <LogOut className="h-4 w-4" /> Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl p-6">
        {/* Header */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-gradient-to-br from-emerald-900 to-emerald-600 p-6 text-white shadow-lg">
          <div>
            <h1 className="text-2xl font-extrabold">{vendorInfo.vendor_name}</h1>
            <p className="mt-1 text-sm opacity-85">
              {vendorInfo.category_name} · {vendorInfo.city} {vendorInfo.pincode}
            </p>
          </div>
          <span className={`rounded-full px-4 py-1.5 text-xs font-bold ${
            vendorInfo.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
          }`}>
            {vendorInfo.status}
          </span>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="mb-6 flex h-auto flex-wrap gap-0 overflow-hidden rounded-xl border-2 border-emerald-200 bg-white p-0">
            <TabsTrigger value="overview" className="flex items-center gap-2 rounded-none border-r-2 border-emerald-200 px-5 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white">
              <ChartBar className="h-4 w-4" /> Overview
            </TabsTrigger>
            <TabsTrigger value="products" className="flex items-center gap-2 rounded-none border-r-2 border-emerald-200 px-5 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white">
              <Tags className="h-4 w-4" /> Categories
            </TabsTrigger>
            <TabsTrigger value="marketplace" className="flex items-center gap-2 rounded-none border-r-2 border-emerald-200 px-5 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white">
              <ShoppingCart className="h-4 w-4" /> Marketplace
            </TabsTrigger>
            <TabsTrigger value="transactions" className="flex items-center gap-2 rounded-none border-r-2 border-emerald-200 px-5 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white">
              <Receipt className="h-4 w-4" /> Transactions
            </TabsTrigger>
            <TabsTrigger value="qr" className="flex items-center gap-2 rounded-none border-r-2 border-emerald-200 px-5 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white">
              <QrCode className="h-4 w-4" /> QR Code
            </TabsTrigger>
            <TabsTrigger value="returns" className="flex items-center gap-2 rounded-none px-5 py-3 data-[state=active]:bg-emerald-600 data-[state=active]:text-white">
              <Wrench className="h-4 w-4" /> Returns
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <Card className="border-2 border-emerald-100 shadow-sm">
                <CardContent className="p-5">
                  <div className="mb-1 text-xs font-bold uppercase tracking-wider text-gray-500">Transactions</div>
                  <div className="text-3xl font-extrabold text-emerald-600">{vendorInfo.total_transactions}</div>
                </CardContent>
              </Card>
              <Card className="border-2 border-emerald-100 shadow-sm">
                <CardContent className="p-5">
                  <div className="mb-1 text-xs font-bold uppercase tracking-wider text-gray-500">Business Generated</div>
                  <div className="text-3xl font-extrabold text-blue-600">₹{vendorInfo.total_business_value?.toLocaleString('en-IN')}</div>
                </CardContent>
              </Card>
              <Card className="border-2 border-emerald-100 shadow-sm">
                <CardContent className="p-5">
                  <div className="mb-1 text-xs font-bold uppercase tracking-wider text-gray-500">Discount Given</div>
                  <div className="text-3xl font-extrabold text-amber-600">₹{vendorInfo.total_discount_given?.toLocaleString('en-IN')}</div>
                </CardContent>
              </Card>
              <Card className="border-2 border-emerald-100 shadow-sm">
                <CardContent className="p-5">
                  <div className="mb-1 text-xs font-bold uppercase tracking-wider text-gray-500">Flat Discount</div>
                  <div className="text-3xl font-extrabold text-emerald-600">{vendorInfo.flat_discount_pct}%</div>
                </CardContent>
              </Card>
            </div>

            <Card className="border-2 border-emerald-100 shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="flex items-center gap-2 text-lg font-bold text-emerald-900">
                  <Store className="h-5 w-5" /> Shop Details
                </CardTitle>
                <button className="flex items-center gap-1 rounded-lg border-2 border-emerald-600 px-3 py-1.5 text-xs font-bold text-emerald-600 hover:bg-emerald-50">
                  <Edit className="h-3 w-3" /> Edit
                </button>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-gray-700">
                <div className="flex"><span className="w-32 text-gray-500">Category</span> <span className="font-medium">{vendorInfo.category_name}</span></div>
                <div className="flex"><span className="w-32 text-gray-500">Phone</span> <span className="font-medium">{vendorInfo.phone}</span></div>
                <div className="flex"><span className="w-32 text-gray-500">Email</span> <span className="font-medium">{vendorInfo.email}</span></div>
                <div className="flex"><span className="w-32 text-gray-500">GST</span> <span className="font-medium">{vendorInfo.gst_number || '—'}</span></div>
                <div className="flex"><span className="w-32 text-gray-500">Address</span> <span className="font-medium">{vendorInfo.address_line1}, {vendorInfo.city} {vendorInfo.pincode}</span></div>
                <div className="flex"><span className="w-32 text-gray-500">Description</span> <span className="font-medium">{vendorInfo.shop_description || '—'}</span></div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="transactions">
            <Card className="border-2 border-emerald-100 shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold text-emerald-900">
                  <Receipt className="h-5 w-5" /> Purchase History
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center text-gray-500 py-10 italic">Transactions will be populated by the API integration.</div>
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>
      </main>
    </div>
  );
}
