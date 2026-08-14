"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

export default function StaffSecuritySettingsPage() {
  const { token } = useStaffAuth();
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  
  const [passwords, setPasswords] = useState({
    current_password: "",
    new_password: "",
    confirm_password: ""
  });

  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [showQrModal, setShowQrModal] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPasswords(prev => ({ ...prev, [name]: value }));
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    if (passwords.new_password !== passwords.confirm_password) {
      setError("New passwords do not match.");
      return;
    }

    if (passwords.new_password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);
    setSuccess(false);
    
    // Simulate API call
    setTimeout(() => {
      setLoading(false);
      setSuccess(true);
      setPasswords({ current_password: "", new_password: "", confirm_password: "" });
      setTimeout(() => setSuccess(false), 3000);
    }, 1200);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col md:flex-row gap-8">
      {/* Settings Sidebar Nav */}
      <div className="w-full md:w-64 shrink-0 space-y-2">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 px-3">Settings Menu</h2>
        
        <Link href="/staff/settings/profile" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-user-circle text-lg w-6 text-gray-400"></i>
          Profile & Preferences
        </Link>
        
        <Link href="/staff/settings/security" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center bg-indigo-50 text-indigo-700">
          <i className="fas fa-shield-alt text-lg w-6 text-indigo-600"></i>
          Security & 2FA
        </Link>
        
        <Link href="/staff/settings/audit-logs" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-history text-lg w-6 text-gray-400"></i>
          Audit & Activity Logs
        </Link>
      </div>

      {/* Main Content */}
      <div className="flex-1 space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Security & Authentication</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your password, two-factor authentication, and active sessions.</p>
        </div>

        {/* Change Password */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-100 bg-gray-50/50">
            <h2 className="text-lg font-bold text-gray-900">Change Password</h2>
            <p className="text-sm text-gray-500">Ensure your account is using a long, random password to stay secure.</p>
          </div>
          
          <form onSubmit={handlePasswordSubmit} className="p-6 space-y-4 max-w-xl">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg flex items-start">
                <i className="fas fa-exclamation-circle mt-0.5 mr-2"></i> {error}
              </div>
            )}
            
            {success && (
              <div className="p-3 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg flex items-start">
                <i className="fas fa-check-circle mt-0.5 mr-2"></i> Password successfully updated.
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
              <input type="password" name="current_password" required value={passwords.current_password} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
            </div>
            
            <div className="pt-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
              <input type="password" name="new_password" required value={passwords.new_password} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
              <input type="password" name="confirm_password" required value={passwords.confirm_password} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
            </div>
            
            <div className="pt-4">
              <button 
                type="submit" 
                disabled={loading}
                className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors disabled:opacity-70"
              >
                {loading ? "Updating..." : "Update Password"}
              </button>
            </div>
          </form>
        </div>

        {/* Two Factor Auth */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Two-Factor Authentication (2FA)</h2>
              <p className="text-sm text-gray-500">Add additional security to your account using an authenticator app.</p>
            </div>
            <div>
              <span className={`inline-block px-3 py-1 text-xs font-bold rounded-full border ${twoFactorEnabled ? 'bg-green-50 text-green-700 border-green-200' : 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                {twoFactorEnabled ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
          </div>
          
          <div className="p-6 flex items-start gap-6">
            <div className="w-16 h-16 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center text-3xl shrink-0">
              <i className="fas fa-mobile-alt"></i>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 mb-2">Authenticator App</h3>
              <p className="text-sm text-gray-600 mb-4 max-w-2xl">
                Use an authenticator app like Google Authenticator, Authy, or Microsoft Authenticator to generate one-time security codes. You will be asked to enter a code every time you log in.
              </p>
              
              {twoFactorEnabled ? (
                <button 
                  onClick={() => setTwoFactorEnabled(false)}
                  className="px-4 py-2 border border-red-200 text-red-600 bg-red-50 hover:bg-red-100 font-medium rounded-lg transition-colors text-sm"
                >
                  Disable 2FA
                </button>
              ) : (
                <button 
                  onClick={() => setShowQrModal(true)}
                  className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors text-sm shadow-sm"
                >
                  Set up 2FA
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Active Sessions */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Active Sessions</h2>
              <p className="text-sm text-gray-500">Manage devices currently logged in to your account.</p>
            </div>
            <button className="text-sm font-medium text-red-600 hover:text-red-800">
              Log out all other devices
            </button>
          </div>
          
          <div className="divide-y divide-gray-100">
            <div className="p-6 flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-10 h-10 bg-indigo-50 text-indigo-500 rounded-full flex items-center justify-center text-xl mr-4 shrink-0">
                  <i className="fas fa-laptop"></i>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-900 flex items-center">
                    Windows 11 • Chrome 
                    <span className="ml-2 bg-green-100 text-green-700 text-[10px] font-bold px-2 py-0.5 rounded uppercase">Current Session</span>
                  </h3>
                  <p className="text-xs text-gray-500">IP: 192.168.1.42 • Active right now</p>
                </div>
              </div>
            </div>
            
            <div className="p-6 flex items-center justify-between hover:bg-gray-50 transition-colors">
              <div className="flex items-center">
                <div className="w-10 h-10 bg-gray-100 text-gray-500 rounded-full flex items-center justify-center text-xl mr-4 shrink-0">
                  <i className="fas fa-mobile-alt"></i>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-900">iPhone 14 • Safari</h3>
                  <p className="text-xs text-gray-500">IP: 104.28.21.14 • Last active 2 hours ago</p>
                </div>
              </div>
              <button className="text-gray-400 hover:text-red-600 p-2">
                <i className="fas fa-sign-out-alt"></i>
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* 2FA Setup Modal Mockup */}
      {showQrModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex justify-between items-center">
              <h3 className="font-bold text-gray-900">Configure 2FA</h3>
              <button onClick={() => setShowQrModal(false)} className="text-gray-400 hover:text-gray-600">
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="p-6 flex flex-col items-center text-center">
              <p className="text-sm text-gray-600 mb-4">Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)</p>
              
              <div className="w-48 h-48 bg-gray-100 rounded-lg border border-gray-200 mb-4 flex items-center justify-center text-gray-400">
                <i className="fas fa-qrcode text-6xl"></i>
              </div>
              
              <p className="text-xs text-gray-500 mb-4">Or enter this code manually: <span className="font-mono font-bold text-gray-800">A4B9 X2P1 M9K8 L3W2</span></p>
              
              <div className="w-full pt-4 border-t border-gray-100">
                <label className="block text-sm font-medium text-gray-700 mb-1 text-left">Enter 6-digit verification code</label>
                <input type="text" placeholder="000000" className="w-full border border-gray-300 rounded-lg p-2.5 text-center text-lg tracking-widest font-mono focus:ring-2 focus:ring-indigo-500 outline-none mb-4" />
                
                <button 
                  onClick={() => { setTwoFactorEnabled(true); setShowQrModal(false); }}
                  className="w-full py-2.5 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors"
                >
                  Verify and Enable
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
