"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function VGKConfigPage() {
  const { hasRole } = useStaffAuth();
  const [activeTab, setActiveTab] = useState("tiers");
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // If we had a real API, we'd fetch these configs. Using state for UI mockup.
  const [tierConfig, setTierConfig] = useState({
    bronze: { req_referrals: 0, platform_fee: 10 },
    silver: { req_referrals: 5, platform_fee: 8 },
    gold: { req_referrals: 15, platform_fee: 6 },
    platinum: { req_referrals: 30, platform_fee: 4 }
  });

  const handleSave = () => {
    setIsSaving(true);
    setSaved(false);
    setTimeout(() => {
      setIsSaving(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }, 1000);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">VGK Network Configuration</h1>
          <p className="text-sm text-gray-500 mt-2">Manage membership tiers, platform fees, and network-wide rules.</p>
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={handleSave}
            disabled={isSaving}
            className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors flex items-center min-w-[120px] justify-center"
          >
            {isSaving ? <i className="fas fa-spinner fa-spin"></i> : saved ? <><i className="fas fa-check mr-2"></i> Saved</> : "Save Changes"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-1 overflow-hidden min-h-0">
        {/* Sidebar Nav */}
        <div className="w-64 border-r border-gray-100 bg-gray-50/50 p-4 shrink-0 flex flex-col space-y-2">
          <button 
            onClick={() => setActiveTab("tiers")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'tiers' ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-layer-group text-lg w-6 ${activeTab === 'tiers' ? 'text-indigo-600' : 'text-gray-400'}`}></i>
            Membership Tiers
          </button>
          
          <button 
            onClick={() => setActiveTab("payouts")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'payouts' ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-money-bill-wave text-lg w-6 ${activeTab === 'payouts' ? 'text-indigo-600' : 'text-gray-400'}`}></i>
            Payout Rules
          </button>
          
          <button 
            onClick={() => setActiveTab("vendors")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'vendors' ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-store-alt text-lg w-6 ${activeTab === 'vendors' ? 'text-indigo-600' : 'text-gray-400'}`}></i>
            Vendor Settings
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8 bg-white">
          
          {activeTab === "tiers" && (
            <div className="max-w-3xl">
              <h2 className="text-xl font-bold text-gray-900 mb-6 pb-2 border-b border-gray-100">Membership Tiers & Requirements</h2>
              
              <div className="space-y-6">
                {/* Bronze */}
                <div className="bg-orange-50 border border-orange-100 rounded-xl p-5">
                  <div className="flex items-center mb-4">
                    <div className="w-10 h-10 bg-orange-200 text-orange-700 rounded-full flex items-center justify-center font-bold text-lg mr-3 shadow-sm">B</div>
                    <h3 className="font-bold text-gray-900 text-lg">Bronze Tier (Default)</h3>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Required Referrals</label>
                      <input type="number" disabled value={tierConfig.bronze.req_referrals} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm bg-gray-100" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Platform Deduction Fee (%)</label>
                      <input type="number" value={tierConfig.bronze.platform_fee} onChange={(e) => setTierConfig({...tierConfig, bronze: {...tierConfig.bronze, platform_fee: parseInt(e.target.value)}})} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                  </div>
                </div>

                {/* Silver */}
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
                  <div className="flex items-center mb-4">
                    <div className="w-10 h-10 bg-gray-300 text-gray-700 rounded-full flex items-center justify-center font-bold text-lg mr-3 shadow-sm">S</div>
                    <h3 className="font-bold text-gray-900 text-lg">Silver Tier</h3>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Required Referrals</label>
                      <input type="number" value={tierConfig.silver.req_referrals} onChange={(e) => setTierConfig({...tierConfig, silver: {...tierConfig.silver, req_referrals: parseInt(e.target.value)}})} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Platform Deduction Fee (%)</label>
                      <input type="number" value={tierConfig.silver.platform_fee} onChange={(e) => setTierConfig({...tierConfig, silver: {...tierConfig.silver, platform_fee: parseInt(e.target.value)}})} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                  </div>
                </div>

                {/* Gold */}
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-5">
                  <div className="flex items-center mb-4">
                    <div className="w-10 h-10 bg-yellow-300 text-yellow-800 rounded-full flex items-center justify-center font-bold text-lg mr-3 shadow-sm">G</div>
                    <h3 className="font-bold text-gray-900 text-lg">Gold Tier</h3>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Required Referrals</label>
                      <input type="number" value={tierConfig.gold.req_referrals} onChange={(e) => setTierConfig({...tierConfig, gold: {...tierConfig.gold, req_referrals: parseInt(e.target.value)}})} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Platform Deduction Fee (%)</label>
                      <input type="number" value={tierConfig.gold.platform_fee} onChange={(e) => setTierConfig({...tierConfig, gold: {...tierConfig.gold, platform_fee: parseInt(e.target.value)}})} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                  </div>
                </div>

                {/* Platinum */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                  <div className="flex items-center mb-4">
                    <div className="w-10 h-10 bg-gradient-to-tr from-gray-200 to-white text-gray-900 rounded-full flex items-center justify-center font-bold text-lg mr-3 shadow-sm">P</div>
                    <h3 className="font-bold text-white text-lg">Platinum Tier</h3>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Required Referrals</label>
                      <input type="number" value={tierConfig.platinum.req_referrals} onChange={(e) => setTierConfig({...tierConfig, platinum: {...tierConfig.platinum, req_referrals: parseInt(e.target.value)}})} className="w-full border border-gray-700 bg-gray-800 text-white rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Platform Deduction Fee (%)</label>
                      <input type="number" value={tierConfig.platinum.platform_fee} onChange={(e) => setTierConfig({...tierConfig, platinum: {...tierConfig.platinum, platform_fee: parseInt(e.target.value)}})} className="w-full border border-gray-700 bg-gray-800 text-white rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "payouts" && (
            <div className="max-w-3xl text-gray-500">
              <h2 className="text-xl font-bold text-gray-900 mb-6 pb-2 border-b border-gray-100">Payout Rules & Thresholds</h2>
              <div className="p-12 text-center bg-gray-50 rounded-xl border border-gray-200">
                <i className="fas fa-tools text-4xl mb-4 text-gray-300"></i>
                <p>Payout configurations are locked by Super Admin.</p>
              </div>
            </div>
          )}

          {activeTab === "vendors" && (
            <div className="max-w-3xl text-gray-500">
              <h2 className="text-xl font-bold text-gray-900 mb-6 pb-2 border-b border-gray-100">Global Vendor Settings</h2>
              <div className="p-12 text-center bg-gray-50 rounded-xl border border-gray-200">
                <i className="fas fa-tools text-4xl mb-4 text-gray-300"></i>
                <p>Vendor settlement configuration module coming in v2.</p>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
