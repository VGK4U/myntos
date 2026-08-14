"use client";

import React, { useState } from "react";
import { useMemberAuth } from "@/contexts/MemberAuthContext";

export default function MemberSettingsPage() {
  const { user } = useMemberAuth();
  
  const [activeTab, setActiveTab] = useState("profile");
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccessMsg("");
    setTimeout(() => {
      setLoading(false);
      setSuccessMsg("Settings updated successfully!");
      setTimeout(() => setSuccessMsg(""), 3000);
    }, 1000);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Account Settings</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your profile, KYC verification, banking details, and security.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col md:flex-row">
        
        {/* Sidebar Nav */}
        <div className="w-full md:w-64 border-r border-gray-100 bg-gray-50/50 p-4 shrink-0 flex flex-col space-y-2">
          <button 
            onClick={() => setActiveTab("profile")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'profile' ? 'bg-amber-50 text-amber-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-user-circle text-lg w-6 ${activeTab === 'profile' ? 'text-amber-600' : 'text-gray-400'}`}></i>
            My Profile
          </button>
          
          <button 
            onClick={() => setActiveTab("kyc")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'kyc' ? 'bg-amber-50 text-amber-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-id-card text-lg w-6 ${activeTab === 'kyc' ? 'text-amber-600' : 'text-gray-400'}`}></i>
            KYC Verification
          </button>
          
          <button 
            onClick={() => setActiveTab("bank")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'bank' ? 'bg-amber-50 text-amber-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-university text-lg w-6 ${activeTab === 'bank' ? 'text-amber-600' : 'text-gray-400'}`}></i>
            Bank Details
          </button>

          <button 
            onClick={() => setActiveTab("security")}
            className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center ${activeTab === 'security' ? 'bg-amber-50 text-amber-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <i className={`fas fa-shield-alt text-lg w-6 ${activeTab === 'security' ? 'text-amber-600' : 'text-gray-400'}`}></i>
            Security & Password
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8">
          
          {successMsg && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg flex items-center">
              <i className="fas fa-check-circle mr-2 text-lg"></i>
              {successMsg}
            </div>
          )}

          {activeTab === "profile" && (
            <form onSubmit={handleSave} className="max-w-2xl">
              <h2 className="text-xl font-bold text-gray-900 mb-6 pb-2 border-b border-gray-100">Profile Information</h2>
              
              <div className="flex items-center gap-6 mb-8">
                <div className="w-24 h-24 rounded-full bg-gray-200 flex items-center justify-center text-3xl text-gray-500 font-bold border-4 border-white shadow-md relative overflow-hidden">
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity cursor-pointer">
                    <i className="fas fa-camera text-white"></i>
                  </div>
                  {user?.first_name.charAt(0)}{user?.last_name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-lg">Member ID: {user?.vgk_id}</h3>
                  <p className="text-sm text-gray-500">Joined: Jan 15, 2026</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                  <input type="text" defaultValue={user?.first_name} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                  <input type="text" defaultValue={user?.last_name} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                  <input type="email" defaultValue={user?.email} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                  <input type="tel" defaultValue={user?.phone} disabled className="w-full border border-gray-200 bg-gray-50 rounded-lg p-2.5 text-sm text-gray-500" />
                  <p className="text-[10px] text-gray-400 mt-1">Contact support to change your registered number.</p>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Communication Address</label>
                  <textarea rows={3} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none resize-none" defaultValue="402, Sunshine Apartments, Linking Road, Bandra West, Mumbai 400050"></textarea>
                </div>
              </div>
              
              <button type="submit" disabled={loading} className="px-6 py-2.5 bg-gray-900 text-white font-bold rounded-lg shadow-sm hover:bg-gray-800 transition-colors disabled:opacity-70">
                {loading ? "Saving..." : "Save Profile"}
              </button>
            </form>
          )}

          {activeTab === "kyc" && (
            <div className="max-w-2xl">
              <h2 className="text-xl font-bold text-gray-900 mb-2">KYC Verification</h2>
              <p className="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">KYC is mandatory to receive commission payouts.</p>
              
              {user?.kyc_status === 'VERIFIED' ? (
                <div className="p-6 bg-green-50 border border-green-200 rounded-xl flex items-start gap-4">
                  <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-xl shrink-0">
                    <i className="fas fa-check-circle"></i>
                  </div>
                  <div>
                    <h3 className="font-bold text-green-900 text-lg">KYC Verified</h3>
                    <p className="text-sm text-green-700 mt-1">Your documents have been approved. You are eligible for payouts.</p>
                    <button className="mt-3 text-sm font-bold text-green-700 hover:underline">View Uploaded Documents</button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSave} className="space-y-6">
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start text-amber-800 text-sm mb-6">
                    <i className="fas fa-exclamation-triangle mt-0.5 mr-3 text-amber-500"></i>
                    <div>
                      <strong>Action Required:</strong> Please upload a clear copy of your PAN Card and Aadhar Card for verification. Verification usually takes 24-48 hours.
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">PAN Card Number</label>
                    <input type="text" placeholder="ABCDE1234F" className="w-full md:w-1/2 border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none uppercase" />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Upload PAN Card (Front)</label>
                    <input type="file" className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-bold file:bg-amber-50 file:text-amber-700 hover:file:bg-amber-100 cursor-pointer border border-gray-300 rounded-lg bg-white" />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Aadhar Card Number</label>
                    <input type="text" placeholder="XXXX XXXX XXXX" className="w-full md:w-1/2 border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Upload Aadhar Card (Front & Back)</label>
                    <input type="file" className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-bold file:bg-amber-50 file:text-amber-700 hover:file:bg-amber-100 cursor-pointer border border-gray-300 rounded-lg bg-white" />
                  </div>

                  <button type="submit" disabled={loading} className="px-6 py-2.5 bg-gray-900 text-white font-bold rounded-lg shadow-sm hover:bg-gray-800 transition-colors disabled:opacity-70">
                    {loading ? "Submitting..." : "Submit for Verification"}
                  </button>
                </form>
              )}
            </div>
          )}

          {activeTab === "bank" && (
            <div className="max-w-2xl">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Bank Account Details</h2>
              <p className="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">Enter your primary bank account where your commission and referral earnings will be transferred.</p>
              
              <form onSubmit={handleSave} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Account Holder Name</label>
                  <input type="text" required placeholder="As per bank records" className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Account Number</label>
                  <input type="password" required placeholder="Enter Account Number" className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Account Number</label>
                  <input type="text" required placeholder="Re-enter Account Number" className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                </div>
                
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">IFSC Code</label>
                    <input type="text" required placeholder="e.g. SBIN0001234" className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none uppercase" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Bank Name</label>
                    <input type="text" readOnly className="w-full border border-gray-200 bg-gray-50 rounded-lg p-2.5 text-sm outline-none text-gray-500" placeholder="Auto-filled from IFSC" />
                  </div>
                </div>

                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800 flex items-start">
                  <i className="fas fa-info-circle mt-0.5 mr-3"></i>
                  Name on Bank Account must exactly match the Name on PAN Card submitted in KYC.
                </div>
                
                <button type="submit" disabled={loading} className="px-6 py-2.5 bg-gray-900 text-white font-bold rounded-lg shadow-sm hover:bg-gray-800 transition-colors disabled:opacity-70">
                  {loading ? "Saving..." : "Update Bank Details"}
                </button>
              </form>
            </div>
          )}

          {activeTab === "security" && (
            <div className="max-w-2xl">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Security & Passwords</h2>
              <p className="text-sm text-gray-500 mb-6 pb-4 border-b border-gray-100">Manage your primary login password and your secondary transaction password (required for withdrawals).</p>
              
              <div className="space-y-10">
                <form onSubmit={handleSave} className="space-y-5">
                  <h3 className="font-bold text-gray-800">Change Login Password</h3>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
                    <input type="password" required className="w-full md:w-2/3 border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                    <input type="password" required className="w-full md:w-2/3 border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-amber-500 outline-none" />
                  </div>
                  <button type="submit" disabled={loading} className="px-6 py-2 bg-gray-900 text-white font-bold rounded-lg shadow-sm hover:bg-gray-800 transition-colors disabled:opacity-70 text-sm">
                    {loading ? "Updating..." : "Update Password"}
                  </button>
                </form>

                <form onSubmit={handleSave} className="space-y-5 pt-6 border-t border-gray-100">
                  <h3 className="font-bold text-gray-800 flex items-center">
                    Secondary Transaction Password
                    <span className="ml-3 bg-red-100 text-red-700 text-[10px] font-bold px-2 py-0.5 rounded-full">NOT SET</span>
                  </h3>
                  <p className="text-sm text-gray-500">This 6-digit PIN is required to authorize wallet withdrawals or fund transfers to other members.</p>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Set 6-Digit PIN</label>
                    <input type="password" required maxLength={6} placeholder="••••••" className="w-full md:w-1/3 border border-gray-300 rounded-lg p-2.5 text-center tracking-[1em] font-mono text-lg focus:ring-2 focus:ring-amber-500 outline-none" />
                  </div>
                  <button type="submit" disabled={loading} className="px-6 py-2 bg-gray-900 text-white font-bold rounded-lg shadow-sm hover:bg-gray-800 transition-colors disabled:opacity-70 text-sm">
                    {loading ? "Saving..." : "Set Transaction PIN"}
                  </button>
                </form>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
