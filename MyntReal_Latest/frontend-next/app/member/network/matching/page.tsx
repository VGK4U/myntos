"use client";

import React from "react";
import { useMemberAuth } from "@/contexts/MemberAuthContext";

export default function MatchingNetworkPage() {
  const { user } = useMemberAuth();

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Matching Network Tree</h1>
          <p className="text-sm text-gray-500 mt-2">View your left and right legs, track Pair Volumes (PV), and monitor your matching bonuses.</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-purple-600 text-white font-medium rounded-lg shadow-sm hover:bg-purple-700 transition-colors">
            <i className="fas fa-sitemap mr-2"></i> Place New Member
          </button>
        </div>
      </div>

      {/* Network Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 shrink-0">
        
        {/* Left Leg Stats */}
        <div className="bg-gradient-to-br from-blue-50 to-white rounded-xl shadow-sm border border-blue-100 p-6 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
          <h3 className="font-bold text-blue-900 mb-4 text-lg border-b border-blue-100 pb-2">Left Leg Status</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-blue-600 uppercase font-bold tracking-wider mb-1">Total Members</p>
              <p className="text-2xl font-bold text-gray-900">145</p>
            </div>
            <div>
              <p className="text-xs text-blue-600 uppercase font-bold tracking-wider mb-1">Total Volume (PV)</p>
              <p className="text-2xl font-bold text-gray-900">42,500</p>
            </div>
            <div className="col-span-2 mt-2 pt-2 border-t border-blue-100/50">
              <p className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-1">Carry Forward Volume</p>
              <p className="text-lg font-bold text-blue-700">12,500 PV</p>
            </div>
          </div>
        </div>

        {/* Right Leg Stats */}
        <div className="bg-gradient-to-br from-purple-50 to-white rounded-xl shadow-sm border border-purple-100 p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-1 h-full bg-purple-500"></div>
          <h3 className="font-bold text-purple-900 mb-4 text-lg border-b border-purple-100 pb-2">Right Leg Status</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-purple-600 uppercase font-bold tracking-wider mb-1">Total Members</p>
              <p className="text-2xl font-bold text-gray-900">89</p>
            </div>
            <div>
              <p className="text-xs text-purple-600 uppercase font-bold tracking-wider mb-1">Total Volume (PV)</p>
              <p className="text-2xl font-bold text-gray-900">30,000</p>
            </div>
            <div className="col-span-2 mt-2 pt-2 border-t border-purple-100/50">
              <p className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-1">Carry Forward Volume</p>
              <p className="text-lg font-bold text-purple-700">0 PV</p>
            </div>
          </div>
        </div>

      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col relative">
        <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center z-10">
          <h3 className="font-bold text-gray-900">Genealogy View</h3>
          <div className="flex gap-2 text-xs font-bold text-gray-500 uppercase">
            <span className="flex items-center"><span className="w-3 h-3 rounded-full bg-green-500 mr-1"></span> Active</span>
            <span className="flex items-center ml-3"><span className="w-3 h-3 rounded-full bg-gray-300 mr-1"></span> Inactive</span>
            <span className="flex items-center ml-3"><span className="w-3 h-3 border border-dashed border-gray-400 rounded-full bg-white mr-1"></span> Empty Space</span>
          </div>
        </div>

        {/* Binary Tree Visualization Area */}
        <div className="flex-1 overflow-auto bg-gray-50/50 relative p-8 flex justify-center min-w-[800px]">
          
          {/* Tree Structure */}
          <div className="flex flex-col items-center">
            
            {/* Root Node (Current User) */}
            <div className="relative group cursor-pointer z-10">
              <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-amber-400 to-yellow-600 flex items-center justify-center font-bold text-xl text-white shadow-lg border-4 border-white mb-2 relative z-10">
                <i className="fas fa-crown"></i>
              </div>
              <div className="text-center absolute w-32 left-1/2 transform -translate-x-1/2">
                <p className="text-sm font-bold text-gray-900 truncate">You</p>
                <p className="text-[10px] font-bold text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full inline-block mt-1 border border-gray-200">{user?.vgk_id}</p>
              </div>
            </div>

            {/* Connecting Line from Root to Level 1 */}
            <div className="w-px h-12 bg-gray-300 relative z-0 mt-8"></div>
            <div className="w-[400px] h-px bg-gray-300 relative z-0"></div>

            {/* Level 1 Nodes */}
            <div className="flex justify-between w-[400px] relative z-10 mt-0">
              
              {/* Level 1 Left */}
              <div className="flex flex-col items-center relative">
                <div className="w-px h-8 bg-gray-300"></div>
                <div className="w-14 h-14 rounded-full bg-green-500 flex items-center justify-center font-bold text-lg text-white shadow-md border-2 border-white mb-2 hover:scale-110 transition-transform cursor-pointer">
                  RS
                </div>
                <div className="text-center w-24">
                  <p className="text-xs font-bold text-gray-900 truncate">Rahul Sharma</p>
                  <p className="text-[9px] text-gray-500">145 / 32</p>
                </div>

                {/* Level 2 (Left child of Left child) */}
                <div className="absolute top-[100px] -left-[60px] flex flex-col items-center">
                  <div className="w-px h-8 bg-gray-300 absolute -top-8 left-1/2 transform -translate-x-1/2"></div>
                  <div className="w-[120px] h-px bg-gray-300 absolute -top-8 left-1/2"></div>
                  
                  <div className="w-px h-8 bg-gray-300 absolute -top-8 -left-[60px]"></div>
                  <div className="w-12 h-12 rounded-full bg-green-500 absolute -top-0 -left-[84px] flex items-center justify-center text-white border-2 border-white text-sm font-bold cursor-pointer hover:scale-110 shadow-sm">
                    VK
                  </div>
                  <p className="text-[10px] font-bold absolute top-14 -left-[90px] w-20 text-center">Vikas K.</p>

                  <div className="w-px h-8 bg-gray-300 absolute -top-8 left-[60px]"></div>
                  <div className="w-12 h-12 rounded-full bg-gray-300 absolute -top-0 left-[36px] flex items-center justify-center text-white border-2 border-white text-sm font-bold cursor-pointer hover:scale-110 shadow-sm">
                    SJ
                  </div>
                  <p className="text-[10px] font-bold absolute top-14 left-[30px] w-20 text-center text-gray-500">Sonia J.</p>
                </div>
              </div>

              {/* Level 1 Right */}
              <div className="flex flex-col items-center relative">
                <div className="w-px h-8 bg-gray-300"></div>
                <div className="w-14 h-14 rounded-full bg-green-500 flex items-center justify-center font-bold text-lg text-white shadow-md border-2 border-white mb-2 hover:scale-110 transition-transform cursor-pointer">
                  PD
                </div>
                <div className="text-center w-24">
                  <p className="text-xs font-bold text-gray-900 truncate">Priya Desai</p>
                  <p className="text-[9px] text-gray-500">89 / 40</p>
                </div>

                {/* Level 2 (Right child of Right child) */}
                <div className="absolute top-[100px] -right-[60px] flex flex-col items-center">
                  <div className="w-px h-8 bg-gray-300 absolute -top-8 right-1/2 transform translate-x-1/2"></div>
                  <div className="w-[120px] h-px bg-gray-300 absolute -top-8 right-1/2"></div>
                  
                  <div className="w-px h-8 bg-gray-300 absolute -top-8 -right-[60px]"></div>
                  <div className="w-12 h-12 rounded-full bg-white border-2 border-dashed border-gray-300 absolute -top-0 -right-[84px] flex items-center justify-center text-gray-400 text-sm font-bold cursor-pointer hover:bg-purple-50 hover:text-purple-600 transition-colors hover:border-purple-300">
                    <i className="fas fa-plus"></i>
                  </div>
                  <p className="text-[10px] font-bold absolute top-14 -right-[90px] w-20 text-center text-gray-400 uppercase">Place Here</p>

                  <div className="w-px h-8 bg-gray-300 absolute -top-8 right-[60px]"></div>
                  <div className="w-12 h-12 rounded-full bg-green-500 absolute -top-0 right-[36px] flex items-center justify-center text-white border-2 border-white text-sm font-bold cursor-pointer hover:scale-110 shadow-sm">
                    MR
                  </div>
                  <p className="text-[10px] font-bold absolute top-14 right-[30px] w-20 text-center">Mohit R.</p>
                </div>
              </div>

            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
