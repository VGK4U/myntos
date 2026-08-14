"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

export default function AIMarketingProPage() {
  const { token } = useStaffAuth();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("meta_ads"); // meta_ads, auto_replies, segment_builder

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">AI Marketing Pro</span>
          </h1>
          <p className="text-sm text-gray-500 mt-2">Automate your Meta Ads, segment audiences, and deploy intelligent auto-responders.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/crm/dashboard" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-arrow-left mr-2"></i> CRM Dashboard
          </Link>
          <button className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-lg shadow-sm hover:opacity-90 transition-opacity">
            <i className="fas fa-magic mr-2"></i> New AI Campaign
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-1 overflow-hidden min-h-0">
        {/* Sidebar Nav */}
        <div className="w-64 border-r border-gray-100 bg-gray-50/50 p-4 shrink-0 flex flex-col space-y-2">
          <button 
            onClick={() => setActiveTab("meta_ads")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'meta_ads' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fab fa-facebook-square text-lg w-6 ${activeTab === 'meta_ads' ? 'text-blue-600' : 'text-gray-400'}`}></i>
            Meta Ads Sync
          </button>
          
          <button 
            onClick={() => setActiveTab("auto_replies")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'auto_replies' ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-robot text-lg w-6 ${activeTab === 'auto_replies' ? 'text-indigo-600' : 'text-gray-400'}`}></i>
            Smart Auto-Replies
          </button>
          
          <button 
            onClick={() => setActiveTab("segment_builder")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'segment_builder' ? 'bg-purple-50 text-purple-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-filter text-lg w-6 ${activeTab === 'segment_builder' ? 'text-purple-600' : 'text-gray-400'}`}></i>
            Audience Segments
          </button>
          
          <div className="mt-auto p-4 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white shadow-inner">
            <h4 className="font-bold mb-1">AI Tokens</h4>
            <p className="text-2xl font-bold">12,450</p>
            <p className="text-xs text-indigo-100 mt-2">Refreshes next month</p>
            <button className="mt-3 w-full bg-white/20 hover:bg-white/30 py-1.5 rounded text-sm font-medium transition-colors">
              Upgrade Plan
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8 bg-white">
          {activeTab === "meta_ads" && (
            <div className="space-y-6 max-w-4xl">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Meta (Facebook/Instagram) Lead Sync</h2>
                <p className="text-gray-500 mb-6">Automatically pull leads from your active Meta ad campaigns directly into the CRM pipeline.</p>
              </div>
              
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 flex items-start space-x-4">
                <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center text-blue-600 text-2xl shadow-sm shrink-0">
                  <i className="fab fa-meta"></i>
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900">Account Connected</h3>
                  <p className="text-sm text-gray-600 mt-1">MyntReal Official Page (ID: 10482910384)</p>
                  <p className="text-sm font-medium text-green-600 mt-2"><i className="fas fa-check-circle mr-1"></i> Sync is Active</p>
                </div>
                <button className="px-4 py-2 border border-blue-300 text-blue-700 font-medium rounded-lg hover:bg-blue-100 transition-colors">
                  Disconnect
                </button>
              </div>

              <h3 className="font-bold text-gray-900 mt-8 mb-4">Active Campaigns</h3>
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase">Campaign Name</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase text-center">Status</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase text-center">Leads Generated</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase text-right">Cost per Lead</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr className="hover:bg-gray-50">
                      <td className="p-4 font-medium text-gray-900">Summer Real Estate Offer 2026</td>
                      <td className="p-4 text-center"><span className="bg-green-100 text-green-800 text-[10px] font-bold px-2 py-1 rounded">ACTIVE</span></td>
                      <td className="p-4 text-center font-bold text-indigo-600">142</td>
                      <td className="p-4 text-right">₹ 245.50</td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                      <td className="p-4 font-medium text-gray-900">Solar Panel Commercial B2B</td>
                      <td className="p-4 text-center"><span className="bg-green-100 text-green-800 text-[10px] font-bold px-2 py-1 rounded">ACTIVE</span></td>
                      <td className="p-4 text-center font-bold text-indigo-600">89</td>
                      <td className="p-4 text-right">₹ 512.00</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === "auto_replies" && (
            <div className="space-y-6 max-w-4xl">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Smart Auto-Replies</h2>
                <p className="text-gray-500 mb-6">Configure AI-powered responses for WhatsApp and email to engage leads instantly.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-gray-200 rounded-xl p-5 hover:border-indigo-300 transition-colors cursor-pointer group">
                  <div className="flex justify-between items-center mb-4">
                    <div className="w-10 h-10 bg-green-100 text-green-600 rounded-lg flex items-center justify-center text-xl">
                      <i className="fab fa-whatsapp"></i>
                    </div>
                    <div className="w-10 h-6 bg-green-500 rounded-full relative">
                      <div className="w-4 h-4 bg-white rounded-full absolute top-1 right-1"></div>
                    </div>
                  </div>
                  <h3 className="font-bold text-gray-900 mb-1 group-hover:text-indigo-600">WhatsApp Welcome Bot</h3>
                  <p className="text-sm text-gray-500 line-clamp-2">Automatically greets new leads from Meta ads and asks 3 qualifying questions.</p>
                </div>

                <div className="border border-gray-200 rounded-xl p-5 hover:border-indigo-300 transition-colors cursor-pointer group">
                  <div className="flex justify-between items-center mb-4">
                    <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center text-xl">
                      <i className="fas fa-envelope"></i>
                    </div>
                    <div className="w-10 h-6 bg-gray-300 rounded-full relative">
                      <div className="w-4 h-4 bg-white rounded-full absolute top-1 left-1"></div>
                    </div>
                  </div>
                  <h3 className="font-bold text-gray-900 mb-1 group-hover:text-indigo-600">Email Follow-up Sequence</h3>
                  <p className="text-sm text-gray-500 line-clamp-2">Sends a 3-day drip campaign to leads marked as 'Interested' but not yet converted.</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "segment_builder" && (
            <div className="space-y-6 max-w-4xl flex flex-col items-center justify-center text-center mt-12">
              <div className="w-24 h-24 bg-purple-50 text-purple-400 rounded-full flex items-center justify-center text-4xl mb-4">
                <i className="fas fa-users-cog"></i>
              </div>
              <h2 className="text-2xl font-bold text-gray-900">AI Audience Segmentation</h2>
              <p className="text-gray-500 max-w-md">Our AI automatically clusters your leads based on behavior, purchase intent, and demographics.</p>
              
              <button className="mt-4 px-6 py-3 bg-purple-600 text-white font-medium rounded-lg shadow-sm hover:bg-purple-700 transition-colors flex items-center">
                <i className="fas fa-bolt mr-2"></i> Run Segmentation Analysis
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
