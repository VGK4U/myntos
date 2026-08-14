"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

export default function StaffProfileSettingsPage() {
  const { token } = useStaffAuth();
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  
  const [formData, setFormData] = useState({
    first_name: "Rahul",
    last_name: "Sharma",
    email: "rahul.sharma@myntreal.com",
    phone: "+91 9876543210",
    designation: "Senior Sales Executive",
    department: "CRM & Sales",
    bio: "Passionate about helping clients find their dream homes and green energy solutions.",
    timezone: "Asia/Kolkata",
    notifications_email: true,
    notifications_sms: false,
    notifications_whatsapp: true
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({ ...prev, [name]: checked }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccess(false);
    
    // Simulate API call
    setTimeout(() => {
      setLoading(false);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    }, 1200);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col md:flex-row gap-8">
      {/* Settings Sidebar Nav */}
      <div className="w-full md:w-64 shrink-0 space-y-2">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 px-3">Settings Menu</h2>
        
        <Link href="/staff/settings/profile" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center bg-indigo-50 text-indigo-700">
          <i className="fas fa-user-circle text-lg w-6 text-indigo-600"></i>
          Profile & Preferences
        </Link>
        
        <Link href="/staff/settings/security" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-shield-alt text-lg w-6 text-gray-400"></i>
          Security & 2FA
        </Link>
        
        <Link href="/staff/settings/audit-logs" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-history text-lg w-6 text-gray-400"></i>
          Audit & Activity Logs
        </Link>
      </div>

      {/* Main Content */}
      <div className="flex-1">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Profile & Preferences</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your personal information, display settings, and notification preferences.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          {/* Profile Header */}
          <div className="p-8 border-b border-gray-100 bg-gray-50/50 flex items-center gap-6">
            <div className="relative">
              <div className="w-24 h-24 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-3xl font-bold">
                {formData.first_name.charAt(0)}{formData.last_name.charAt(0)}
              </div>
              <button type="button" className="absolute bottom-0 right-0 w-8 h-8 bg-white border border-gray-200 rounded-full flex items-center justify-center text-gray-600 hover:text-indigo-600 shadow-sm transition-colors">
                <i className="fas fa-camera text-sm"></i>
              </button>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{formData.first_name} {formData.last_name}</h2>
              <p className="text-sm text-gray-500">{formData.designation} • {formData.department}</p>
            </div>
          </div>

          <div className="p-8 space-y-8">
            {/* Personal Details */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-4 pb-2 border-b border-gray-100">Personal Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                  <input type="text" name="first_name" value={formData.first_name} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                  <input type="text" name="last_name" value={formData.last_name} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email Address (Work)</label>
                  <input type="email" name="email" value={formData.email} disabled className="w-full border border-gray-300 rounded-lg p-2.5 text-sm bg-gray-50 text-gray-500" />
                  <p className="text-xs text-gray-400 mt-1">Contact HR to change your work email.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                  <input type="tel" name="phone" value={formData.phone} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Short Bio</label>
                  <textarea name="bio" rows={3} value={formData.bio} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-y"></textarea>
                </div>
              </div>
            </div>

            {/* System Preferences */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-4 pb-2 border-b border-gray-100">System Preferences</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                  <select name="timezone" value={formData.timezone} onChange={handleChange} className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white">
                    <option value="Asia/Kolkata">India Standard Time (IST)</option>
                    <option value="Asia/Dubai">Gulf Standard Time (GST)</option>
                    <option value="UTC">Coordinated Universal Time (UTC)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Notifications */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-4 pb-2 border-b border-gray-100">Notification Channels</h3>
              <div className="space-y-4">
                <label className="flex items-center space-x-3">
                  <input type="checkbox" name="notifications_email" checked={formData.notifications_email} onChange={handleChange} className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Email Notifications</p>
                    <p className="text-xs text-gray-500">Receive daily summaries and critical alerts via email.</p>
                  </div>
                </label>
                <label className="flex items-center space-x-3">
                  <input type="checkbox" name="notifications_sms" checked={formData.notifications_sms} onChange={handleChange} className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">SMS Alerts</p>
                    <p className="text-xs text-gray-500">Receive urgent system alerts via text message.</p>
                  </div>
                </label>
                <label className="flex items-center space-x-3">
                  <input type="checkbox" name="notifications_whatsapp" checked={formData.notifications_whatsapp} onChange={handleChange} className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">WhatsApp Bot Integration</p>
                    <p className="text-xs text-gray-500">Receive lead assignments and approvals via WhatsApp.</p>
                  </div>
                </label>
              </div>
            </div>
          </div>

          <div className="p-6 bg-gray-50 border-t border-gray-100 flex justify-between items-center">
            {success ? (
              <span className="text-green-600 font-medium text-sm flex items-center">
                <i className="fas fa-check-circle mr-2"></i> Profile updated successfully
              </span>
            ) : (
              <span></span>
            )}
            <button 
              type="submit" 
              disabled={loading}
              className="px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors disabled:opacity-70 flex items-center"
            >
              {loading ? <><i className="fas fa-spinner fa-spin mr-2"></i> Saving...</> : "Save Preferences"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
