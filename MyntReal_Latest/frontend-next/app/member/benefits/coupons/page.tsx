"use client";

import React, { useState } from "react";
import { useMemberAuth } from "@/contexts/MemberAuthContext";

export default function MemberCouponsPage() {
  const { user } = useMemberAuth();

  const [activeTab, setActiveTab] = useState("available");
  
  const coupons = [
    { id: 'CPN-VGK-001', code: 'SOLAR50', discount: '50%', maxAmount: 15000, type: 'Solar Installation', validUntil: '2026-12-31', status: 'AVAILABLE' },
    { id: 'CPN-VGK-002', code: 'MYNTREAL10', discount: '10%', maxAmount: 50000, type: 'Property Booking', validUntil: '2026-09-30', status: 'AVAILABLE' },
    { id: 'CPN-VGK-003', code: 'INTDES20', discount: '20%', maxAmount: 25000, type: 'Interior Design', validUntil: '2026-08-31', status: 'AVAILABLE' },
    { id: 'CPN-VGK-004', code: 'FREELEGAL', discount: '100%', maxAmount: 10000, type: 'Legal Consulting', validUntil: '2026-06-30', status: 'USED' },
  ];

  const filteredCoupons = activeTab === 'available' ? coupons.filter(c => c.status === 'AVAILABLE') : coupons.filter(c => c.status === 'USED');

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
        
        {filteredCoupons.map((coupon, idx) => (
          <div key={idx} className={`rounded-xl shadow-sm border relative overflow-hidden flex flex-col ${coupon.status === 'AVAILABLE' ? 'bg-white border-amber-100 hover:border-amber-300' : 'bg-gray-50 border-gray-200 opacity-75'}`}>
            
            {/* Top decorative circle */}
            <div className={`absolute -right-4 -top-4 w-16 h-16 rounded-full ${coupon.status === 'AVAILABLE' ? 'bg-amber-50' : 'bg-gray-100'}`}></div>
            
            <div className="p-6 flex-1">
              <div className="flex justify-between items-start mb-4">
                <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${coupon.status === 'AVAILABLE' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}`}>
                  {coupon.status}
                </span>
                <i className={`fas ${coupon.status === 'AVAILABLE' ? 'fa-tags text-amber-400' : 'fa-times-circle text-gray-400'} text-xl relative z-10`}></i>
              </div>
              
              <h3 className="text-3xl font-black text-gray-900 mb-1">{coupon.discount} OFF</h3>
              <p className="font-bold text-gray-700 mb-4">{coupon.type}</p>
              
              <div className="space-y-1.5 mb-6">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Max Discount:</span>
                  <span className="font-bold text-gray-900">₹{coupon.maxAmount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Valid Until:</span>
                  <span className={`font-bold ${coupon.status === 'AVAILABLE' ? 'text-amber-600' : 'text-gray-500'}`}>
                    {new Date(coupon.validUntil).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <div className={`border-t border-dashed p-4 flex items-center justify-between ${coupon.status === 'AVAILABLE' ? 'border-amber-200 bg-amber-50' : 'border-gray-300 bg-gray-100'}`}>
              <div className="font-mono font-bold text-lg tracking-wider text-gray-900 select-all">
                {coupon.code}
              </div>
              {coupon.status === 'AVAILABLE' && (
                <button className="text-amber-600 hover:text-amber-700 font-bold text-sm bg-white px-3 py-1.5 rounded border border-amber-200 shadow-sm transition-colors">
                  Copy Code
                </button>
              )}
            </div>
            
            {/* Cutout effects for ticket look */}
            <div className={`absolute bottom-[66px] -left-2 w-4 h-4 rounded-full ${coupon.status === 'AVAILABLE' ? 'bg-amber-100' : 'bg-gray-200'}`}></div>
            <div className={`absolute bottom-[66px] -right-2 w-4 h-4 rounded-full ${coupon.status === 'AVAILABLE' ? 'bg-amber-100' : 'bg-gray-200'}`}></div>
          </div>
        ))}
        
        {filteredCoupons.length === 0 && (
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
