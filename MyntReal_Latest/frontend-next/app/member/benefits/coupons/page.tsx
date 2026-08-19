"use client";

import React, { useState, useEffect } from "react";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";

export default function MemberCouponsPage() {
  const { user } = useMemberAuth();

  const [activeTab, setActiveTab] = useState("available");
  const [loading, setLoading] = useState(true);
  const [coupons, setCoupons] = useState<any[]>([]);
  
  useEffect(() => {
    if (!user) return;

    api.get(`/api/v1/vgk-member/coupons/activate?audience=vgk4u`)
      .then(res => {
        if (res.data && res.data.success && res.data.data) {
          const { legacy_coupons = [], enhanced_coupons = [] } = res.data.data;
          
          const mappedLegacy = legacy_coupons.map((c: any) => ({
            id: c.id,
            code: c.id.substring(0, 8).toUpperCase(),
            discount: 'Variable',
            maxAmount: 0,
            type: c.package_type || 'Legacy Package',
            validUntil: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString(),
            status: (c.status || 'AVAILABLE').toUpperCase()
          }));
          
          const mappedEnhanced = enhanced_coupons.map((c: any) => ({
            id: c.id,
            code: c.coupon_code || `ENH-${c.id.substring(0, 5)}`.toUpperCase(),
            discount: 'Property Discount',
            maxAmount: c.package_value || 0,
            type: c.package_tier || 'Enhanced Package',
            validUntil: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString(),
            status: (c.status || 'AVAILABLE').toUpperCase()
          }));
          
          setCoupons([...mappedLegacy, ...mappedEnhanced]);
        }
      })
      .catch(err => console.error("Failed to fetch coupons", err))
      .finally(() => setLoading(false));
  }, [user]);

  const filteredCoupons = activeTab === 'available' ? coupons.filter(c => c.status === 'AVAILABLE' || c.status === 'ACTIVE') : coupons.filter(c => c.status !== 'AVAILABLE' && c.status !== 'ACTIVE');

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">My Coupons & Offers</h1>
          <p className="text-sm text-gray-500 mt-2">Access exclusive discounts for VGK properties, solar installations, and partner services.</p>
        </div>
      </div>

      <div className="flex space-x-6 mb-6 shrink-0 border-b border-gray-200">
        <button 
          onClick={() => setActiveTab("available")}
          className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'available' ? 'border-amber-500 text-amber-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          <i className="fas fa-ticket-alt mr-2"></i> Available Coupons
        </button>
        <button 
          onClick={() => setActiveTab("used")}
          className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'used' ? 'border-amber-500 text-amber-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          <i className="fas fa-history mr-2"></i> Used / Expired
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 flex-1 overflow-y-auto content-start pb-6">
        
        {loading ? (
           <div className="col-span-full py-16 flex justify-center">
             <i className="fas fa-circle-notch fa-spin text-4xl text-amber-500"></i>
           </div>
        ) : filteredCoupons.map((coupon, idx) => (
          <div key={idx} className={`rounded-xl shadow-sm border relative overflow-hidden flex flex-col ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'bg-white border-amber-100 hover:border-amber-300' : 'bg-gray-50 border-gray-200 opacity-75'}`}>
            
            {/* Top decorative circle */}
            <div className={`absolute -right-4 -top-4 w-16 h-16 rounded-full ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'bg-amber-50' : 'bg-gray-100'}`}></div>
            
            <div className="p-6 flex-1">
              <div className="flex justify-between items-start mb-4">
                <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}`}>
                  {coupon.status}
                </span>
                <i className={`fas ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'fa-tags text-amber-400' : 'fa-times-circle text-gray-400'} text-xl relative z-10`}></i>
              </div>
              
              <h3 className="text-3xl font-black text-gray-900 mb-1">{coupon.discount} {coupon.discount !== 'Variable' && coupon.discount !== 'Property Discount' ? 'OFF' : ''}</h3>
              <p className="font-bold text-gray-700 mb-4">{coupon.type}</p>
              
              <div className="space-y-1.5 mb-6">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Max Discount:</span>
                  <span className="font-bold text-gray-900">₹{coupon.maxAmount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Valid Until:</span>
                  <span className={`font-bold ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'text-amber-600' : 'text-gray-500'}`}>
                    {new Date(coupon.validUntil).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <div className={`border-t border-dashed p-4 flex items-center justify-between ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'border-amber-200 bg-amber-50' : 'border-gray-300 bg-gray-100'}`}>
              <div className="font-mono font-bold text-lg tracking-wider text-gray-900 select-all">
                {coupon.code}
              </div>
              {(coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE') && (
                <button className="text-amber-600 hover:text-amber-700 font-bold text-sm bg-white px-3 py-1.5 rounded border border-amber-200 shadow-sm transition-colors">
                  Copy Code
                </button>
              )}
            </div>
            
            {/* Cutout effects for ticket look */}
            <div className={`absolute bottom-[66px] -left-2 w-4 h-4 rounded-full ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'bg-amber-100' : 'bg-gray-200'}`}></div>
            <div className={`absolute bottom-[66px] -right-2 w-4 h-4 rounded-full ${coupon.status === 'AVAILABLE' || coupon.status === 'ACTIVE' ? 'bg-amber-100' : 'bg-gray-200'}`}></div>
          </div>
        ))}
        
        {!loading && filteredCoupons.length === 0 && (
          <div className="col-span-full py-16 text-center text-gray-500">
            <i className="fas fa-ticket-alt text-4xl mb-4 text-gray-300"></i>
            <h3 className="text-lg font-bold text-gray-900 mb-1">No Coupons Found</h3>
            <p>You don't have any {activeTab} coupons at the moment.</p>
          </div>
        )}

      </div>
    </div>
  );
}
