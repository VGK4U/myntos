"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function MetaCreativeStudioPage() {
  const { hasRole } = useStaffAuth();
  
  const [activeTab, setActiveTab] = useState("images");

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Creative Studio</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your ad creatives, generate AI copy, and preview how ads will look on Meta platforms.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/marketing/meta/dashboard" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-arrow-left mr-2"></i> Back to Ads
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-upload mr-2"></i> Upload Asset
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="flex space-x-6 px-6 pt-4 shrink-0 border-b border-gray-200">
          <button 
            onClick={() => setActiveTab("images")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'images' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            <i className="fas fa-image mr-2"></i> Image Assets
          </button>
          <button 
            onClick={() => setActiveTab("videos")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'videos' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            <i className="fas fa-video mr-2"></i> Video Assets
          </button>
          <button 
            onClick={() => setActiveTab("copy")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'copy' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            <i className="fas fa-pen-nib mr-2"></i> AI Copywriter
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
          
          {activeTab === "images" && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {/* Asset 1 */}
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm group">
                <div className="h-48 bg-gray-200 relative flex items-center justify-center">
                  <i className="fas fa-home text-4xl text-gray-400"></i>
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center space-x-3">
                    <button className="w-10 h-10 rounded-full bg-white text-gray-900 flex items-center justify-center hover:bg-gray-100"><i className="fas fa-eye"></i></button>
                    <button className="w-10 h-10 rounded-full bg-white text-gray-900 flex items-center justify-center hover:bg-gray-100"><i className="fas fa-download"></i></button>
                  </div>
                </div>
                <div className="p-3">
                  <p className="text-sm font-bold text-gray-900 truncate">VGK_Exterior_HD.jpg</p>
                  <p className="text-xs text-gray-500 mt-1">1080x1080 • 2.4MB</p>
                </div>
              </div>

              {/* Asset 2 */}
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm group">
                <div className="h-48 bg-gray-200 relative flex items-center justify-center">
                  <i className="fas fa-solar-panel text-4xl text-gray-400"></i>
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center space-x-3">
                    <button className="w-10 h-10 rounded-full bg-white text-gray-900 flex items-center justify-center hover:bg-gray-100"><i className="fas fa-eye"></i></button>
                    <button className="w-10 h-10 rounded-full bg-white text-gray-900 flex items-center justify-center hover:bg-gray-100"><i className="fas fa-download"></i></button>
                  </div>
                </div>
                <div className="p-3">
                  <p className="text-sm font-bold text-gray-900 truncate">Solar_Roof_Promo.png</p>
                  <p className="text-xs text-gray-500 mt-1">1080x1920 • 3.1MB</p>
                </div>
              </div>
              
              {/* Asset Upload Box */}
              <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center h-full min-h-[250px] text-gray-500 hover:bg-gray-100 hover:border-indigo-400 transition-colors cursor-pointer">
                <i className="fas fa-cloud-upload-alt text-3xl mb-3"></i>
                <p className="text-sm font-medium">Drag & Drop new image</p>
                <p className="text-xs mt-1">Max size: 10MB</p>
              </div>
            </div>
          )}

          {activeTab === "videos" && (
            <div className="text-center py-16 text-gray-500">
              <i className="fas fa-video-slash text-4xl mb-4 text-gray-300"></i>
              <h3 className="text-lg font-bold text-gray-900 mb-2">No Video Assets</h3>
              <p>Upload video files (.mp4, .mov) for Reels and Stories.</p>
            </div>
          )}

          {activeTab === "copy" && (
            <div className="flex flex-col md:flex-row gap-8 h-full">
              {/* Generator Form */}
              <div className="w-full md:w-1/2 flex flex-col">
                <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex-1">
                  <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                    <i className="fas fa-robot text-indigo-500 mr-2"></i> AI Copy Generator
                  </h2>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Product / Service</label>
                      <input type="text" placeholder="e.g. VGK Builders 2BHK Apartments" className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Key Selling Points</label>
                      <textarea rows={3} placeholder="e.g. Close to metro, solar powered, no EMI till possession" className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none resize-none"></textarea>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Tone</label>
                        <select className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
                          <option>Professional</option>
                          <option>Exciting & Urgent</option>
                          <option>Luxury</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
                        <select className="w-full border border-gray-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
                          <option>Facebook Feed</option>
                          <option>Instagram Reels</option>
                          <option>LinkedIn</option>
                        </select>
                      </div>
                    </div>
                    
                    <button className="w-full py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-medium rounded-lg shadow-sm hover:from-indigo-600 hover:to-purple-700 transition-colors flex items-center justify-center">
                      <i className="fas fa-magic mr-2"></i> Generate Copy
                    </button>
                  </div>
                </div>
              </div>

              {/* Preview Area */}
              <div className="w-full md:w-1/2 flex flex-col justify-center items-center">
                <div className="w-full max-w-sm bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                  <div className="p-3 border-b border-gray-100 flex items-center">
                    <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mr-3">
                      <i className="fab fa-facebook-f"></i>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-gray-900">MyntReal Official</p>
                      <p className="text-[10px] text-gray-500">Sponsored • <i className="fas fa-globe-americas"></i></p>
                    </div>
                  </div>
                  <div className="p-3 text-sm text-gray-800">
                    <p className="whitespace-pre-wrap">Looking for your dream home in Mumbai? 🏙️</p>
                    <p className="mt-2">Discover VGK Builders' premium 2BHK apartments. Located just 5 minutes from the metro, with 100% solar-powered common areas.</p>
                    <p className="mt-2 font-bold text-blue-600">No EMI till possession!</p>
                  </div>
                  <div className="h-48 bg-gray-200 flex items-center justify-center">
                    <i className="fas fa-image text-3xl text-gray-400"></i>
                  </div>
                  <div className="p-3 bg-gray-50 flex justify-between items-center">
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">VGKBUILDERS.COM</p>
                      <p className="text-sm font-bold text-gray-900">Book Your Site Visit Today</p>
                    </div>
                    <button className="px-4 py-1.5 bg-gray-200 text-gray-900 font-bold text-sm rounded">
                      Learn more
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
