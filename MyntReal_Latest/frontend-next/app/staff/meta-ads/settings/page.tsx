"use client";

import React from 'react';
import { 
  Settings, 
  Key, 
  CreditCard, 
  Bell, 
  ShieldCheck,
  Globe,
  RefreshCw
} from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-white shadow-md shadow-gray-900/20">
          <Settings className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Integration Settings</h1>
          <p className="text-gray-500 text-sm">Configure your Meta Business Manager connections and API preferences.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="md:col-span-1 space-y-1">
          {[
            { id: 'connection', name: 'Meta Connection', icon: Globe, active: true },
            { id: 'billing', name: 'Billing Accounts', icon: CreditCard, active: false },
            { id: 'api', name: 'API Credentials', icon: Key, active: false },
            { id: 'notifications', name: 'Notifications', icon: Bell, active: false },
            { id: 'permissions', name: 'Access & Roles', icon: ShieldCheck, active: false }
          ].map((tab) => (
            <button 
              key={tab.id}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                tab.active 
                  ? 'bg-indigo-50 text-indigo-700' 
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <tab.icon className={`w-4 h-4 ${tab.active ? 'text-indigo-600' : 'text-gray-400'}`} />
              {tab.name}
            </button>
          ))}
        </div>

        <div className="md:col-span-3 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-100">
              <h3 className="text-lg font-bold text-gray-900 mb-1">Meta Business Account</h3>
              <p className="text-sm text-gray-500">Connect your Meta Business Manager to sync campaigns, leads, and analytics.</p>
            </div>
            
            <div className="p-6">
              <div className="flex items-center justify-between p-4 border border-emerald-200 bg-emerald-50/50 rounded-lg">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center border border-gray-200 shadow-sm">
                    <Globe className="w-6 h-6 text-[#1877F2]" />
                  </div>
                  <div>
                    <h4 className="font-bold text-gray-900">MyntReal Official</h4>
                    <p className="text-sm text-gray-500">Business ID: 1029384756102</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center text-sm font-medium text-emerald-700 bg-emerald-100 px-3 py-1 rounded-full">
                    <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                    Connected
                  </span>
                  <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                    Disconnect
                  </button>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <h4 className="font-medium text-gray-900">Sync Preferences</h4>
                <div className="space-y-3">
                  {[
                    { title: "Auto-sync Leads", desc: "Automatically import new leads from Meta forms every 5 minutes." },
                    { title: "Sync Campaign Metrics", desc: "Update spend, reach, and conversion data daily." },
                    { title: "Sync Creatives", desc: "Import ad images and videos to the Creative Studio." }
                  ].map((pref, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="mt-0.5 relative flex items-center">
                        <input type="checkbox" defaultChecked className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{pref.title}</p>
                        <p className="text-xs text-gray-500">{pref.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-gray-100 flex justify-end gap-3">
                <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
                  <RefreshCw className="w-4 h-4" />
                  Force Sync Now
                </button>
                <button className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors">
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CheckCircle(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}
