"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";

export default function EVSchemePage() {
  const { user } = useMemberAuth();

  const [activeTab, setActiveTab] = useState("overview");
  const [directs, setDirects] = useState<number>(0);
  const [claims, setClaims] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const TARGET_SALES = 25;

  useEffect(() => {
    if (!user) return;
    
    setLoading(true);
    Promise.all([
      api.get(`/api/v1/ev/benefits?audience=vgk4u`).catch(() => ({ data: [] })),
      api.get('/ev-scooter-claims/my-claims').catch(() => ({ data: { claims: [] } }))
    ]).then(([teamRes, claimsRes]) => {
      if (teamRes.data && Array.isArray(teamRes.data)) {
        setDirects(teamRes.data.length);
      }
      if (claimsRes.data && claimsRes.data.claims) {
        setClaims(claimsRes.data.claims);
      }
    }).finally(() => {
      setLoading(false);
    });
  }, [user]);

  const progressPercentage = Math.min(100, Math.round((directs / TARGET_SALES) * 100));
  const remainingSales = Math.max(0, TARGET_SALES - directs);

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">EV Vehicle Scheme</h1>
          <p className="text-sm text-gray-500 mt-2">Achieve your sales targets to unlock exclusive VGK Electric Vehicle (EV) rewards.</p>
        </div>
      </div>

      {/* Target Progress Banner */}
      <div className="bg-gradient-to-r from-green-900 to-green-800 rounded-2xl p-8 text-white shadow-xl mb-8 relative overflow-hidden shrink-0">
        <i className="fas fa-car-side absolute right-[-10%] top-[-20px] text-[180px] opacity-10 transform -rotate-12"></i>
        <div className="relative z-10">
          <div className="flex justify-between items-end mb-4">
            <div>
              <p className="text-sm font-bold text-green-300 uppercase tracking-wider mb-1">Current Progress</p>
              <h2 className="text-3xl font-bold">{loading ? '...' : directs} / {TARGET_SALES} <span className="text-lg font-normal text-green-200">Direct Sales</span></h2>
            </div>
            <div className="text-right">
              <span className={`text-xs font-bold px-3 py-1 rounded-full uppercase shadow-sm ${directs >= TARGET_SALES ? 'bg-yellow-400 text-yellow-900' : 'bg-white text-green-900'}`}>
                {directs >= TARGET_SALES ? 'Unlocked' : 'In Progress'}
              </span>
            </div>
          </div>
          
          <div className="w-full bg-green-950 rounded-full h-3 mb-2 overflow-hidden shadow-inner border border-green-700/50">
            <div className="bg-gradient-to-r from-green-400 to-yellow-400 h-3 rounded-full transition-all duration-1000" style={{ width: `${progressPercentage}%` }}></div>
          </div>
          <div className="flex justify-between text-xs font-medium text-green-200">
            <span>Started: July 1, 2026</span>
            <span>{remainingSales > 0 ? `${remainingSales} Sales remaining to unlock EV` : 'Target Achieved!'}</span>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="flex space-x-6 px-6 pt-4 shrink-0 border-b border-gray-200">
          <button 
            onClick={() => setActiveTab("overview")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'overview' ? 'border-green-600 text-green-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            Scheme Details
          </button>
          <button 
            onClick={() => setActiveTab("claims")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'claims' ? 'border-green-600 text-green-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            My Claims
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-0">
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 h-full">
              {/* Left Column: Requirements */}
              <div className="p-8 border-r border-gray-100 bg-gray-50/30">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
                  <i className="fas fa-check-double text-green-600 mr-3 text-2xl"></i> Eligibility Criteria
                </h3>
                
                <div className="space-y-6">
                  <div className="flex gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold shrink-0 ${directs >= 25 ? 'bg-green-500 text-white' : 'bg-green-100 text-green-700'}`}>
                      {directs >= 25 ? <i className="fas fa-check"></i> : '1'}
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900">25 Direct Property Sales</h4>
                      <p className="text-sm text-gray-600 mt-1">You must close 25 direct real estate sales within the VGK Network.</p>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold shrink-0 ${user?.kyc_status === 'Approved' ? 'bg-green-500 text-white' : 'bg-green-100 text-green-700'}`}>
                      {user?.kyc_status === 'Approved' ? <i className="fas fa-check"></i> : '2'}
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900">Active KYC & Bank Details</h4>
                      <p className="text-sm text-gray-600 mt-1">Your member profile must be fully verified by the administration.</p>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="w-10 h-10 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-bold shrink-0">3</div>
                    <div>
                      <h4 className="font-bold text-gray-900">Maintain Minimum Tier</h4>
                      <p className="text-sm text-gray-600 mt-1">You must hold at least a SILVER tier status at the time of claim.</p>
                    </div>
                  </div>
                </div>

                <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                  <i className="fas fa-info-circle mr-2"></i> Only sales completed after January 1, 2026 are counted towards the current EV scheme.
                </div>
              </div>

              {/* Right Column: Reward Showcase */}
              <div className="p-8 bg-white flex flex-col items-center justify-center text-center">
                <div className="w-48 h-48 rounded-full bg-green-50 mb-6 flex items-center justify-center border-4 border-green-100 shadow-inner relative">
                  <i className="fas fa-bolt text-yellow-400 text-8xl z-10"></i>
                  <i className="fas fa-car-side text-green-600 text-6xl absolute z-20 top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 mt-4 opacity-90"></i>
                </div>
                
                <h3 className="text-2xl font-bold text-gray-900 mb-2">Tata Tiago EV (Base Model)</h3>
                <p className="text-gray-500 max-w-md mx-auto mb-8">
                  Complete your 25 direct sales target and drive away in a brand new electric vehicle, fully sponsored by the VGK Network!
                </p>

                <button 
                  disabled={directs < TARGET_SALES || user?.kyc_status !== 'Approved'} 
                  className={`px-8 py-3 font-bold rounded-lg shadow-sm border transition-colors ${directs >= TARGET_SALES && user?.kyc_status === 'Approved' ? 'bg-green-600 text-white hover:bg-green-700 border-green-700 cursor-pointer' : 'bg-gray-200 text-gray-400 border-gray-300 cursor-not-allowed'}`}
                >
                  <i className={directs >= TARGET_SALES ? "fas fa-gift mr-2" : "fas fa-lock mr-2"}></i> 
                  Claim EV Reward
                </button>
                <p className="text-xs text-gray-400 mt-3 uppercase tracking-wider font-bold">
                  {remainingSales > 0 ? `${remainingSales} Sales Remaining to Unlock` : (user?.kyc_status !== 'Approved' ? 'Complete KYC to Claim' : 'Ready to Claim!')}
                </p>
              </div>
            </div>
          )}

          {activeTab === "claims" && (
            <div className="p-6">
               {loading ? (
                 <div className="flex justify-center p-12">
                   <i className="fas fa-circle-notch fa-spin text-4xl text-green-600"></i>
                 </div>
               ) : claims.length === 0 ? (
                 <div className="p-12 text-center text-gray-500 border border-dashed border-gray-300 rounded-xl bg-gray-50">
                   <i className="fas fa-file-invoice text-4xl mb-4 text-gray-300"></i>
                   <h3 className="text-lg font-bold text-gray-900 mb-1">No Active Claims</h3>
                   <p>You have not initiated any EV reward claims yet.</p>
                 </div>
               ) : (
                 <div className="space-y-4">
                   {claims.map((claim, i) => (
                     <div key={i} className="border border-gray-200 rounded-lg p-5 bg-white shadow-sm flex items-center justify-between">
                       <div>
                         <h4 className="font-bold text-gray-900 mb-1">{claim.ev_model || 'EV Scheme Vehicle'}</h4>
                         <p className="text-sm text-gray-500">Claimed on: {claim.created_at ? new Date(claim.created_at).toLocaleDateString() : 'Unknown'}</p>
                       </div>
                       <div>
                         <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                           claim.claim_status === 'Delivered' ? 'bg-green-100 text-green-700' :
                           claim.claim_status === 'Pending' ? 'bg-amber-100 text-amber-700' :
                           'bg-blue-100 text-blue-700'
                         }`}>
                           {claim.claim_status}
                         </span>
                       </div>
                     </div>
                   ))}
                 </div>
               )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
