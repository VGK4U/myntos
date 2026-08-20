"use client";

import React, { useState } from 'react';
import { 
  Palette, 
  Image as ImageIcon, 
  Video, 
  Upload, 
  Filter, 
  MoreHorizontal,
  CheckCircle2
} from 'lucide-react';

export default function CreativeStudioPage() {
  const [activeTab, setActiveTab] = useState('all');

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center text-white shadow-md shadow-pink-500/20">
              <Palette className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Creative Studio</h1>
          </div>
          <p className="text-gray-500">Manage, organize, and analyze your ad creatives across all campaigns.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg font-medium hover:bg-rose-700 transition-colors shadow-sm">
          <Upload className="w-4 h-4" />
          Upload Creative
        </button>
      </div>

      <div className="flex items-center justify-between border-b border-gray-200 pb-4">
        <div className="flex gap-2">
          {['all', 'images', 'videos', 'carousels'].map((tab) => (
            <button 
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                activeTab === tab 
                  ? 'bg-rose-50 text-rose-700 border border-rose-200' 
                  : 'text-gray-600 hover:bg-gray-50 border border-transparent'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
          <Filter className="w-4 h-4" />
          Filter
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((item) => (
          <div key={item} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden group hover:shadow-md transition-all">
            <div className="aspect-square bg-gray-100 relative overflow-hidden flex items-center justify-center group-hover:bg-gray-200 transition-colors">
              {item % 3 === 0 ? <Video className="w-12 h-12 text-gray-300" /> : <ImageIcon className="w-12 h-12 text-gray-300" />}
              <div className="absolute top-2 right-2">
                <div className="w-6 h-6 rounded-full bg-white/90 shadow-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                </div>
              </div>
            </div>
            <div className="p-4">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="font-medium text-gray-900 line-clamp-1">Creative_Asset_v{item}.jpg</h3>
                  <p className="text-xs text-gray-500">{item % 3 === 0 ? 'Video' : 'Image'} • 1080x1080</p>
                </div>
                <button className="text-gray-400 hover:text-gray-600">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </div>
              <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-100 text-xs">
                <div>
                  <span className="text-gray-500 block">CTR</span>
                  <span className="font-medium text-gray-900">{(Math.random() * 3 + 1).toFixed(2)}%</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Status</span>
                  <span className="font-medium text-emerald-600">Active</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
