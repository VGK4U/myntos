"use client";

import React, { useState } from "react";
import { useMemberAuth } from "@/contexts/MemberAuthContext";

export default function MemberAwardsPage() {
  const { user } = useMemberAuth();

  const [activeTab, setActiveTab] = useState("achievements");

  const awards = [
    { id: 1, title: 'Star Performer - Q1', date: '2026-03-31', type: 'Trophy', status: 'RECEIVED', icon: 'fa-trophy', color: 'text-yellow-500' },
    { id: 2, title: 'Century Club (100 Directs)', date: '2026-07-15', type: 'Gold Coin', status: 'PENDING_DELIVERY', icon: 'fa-coins', color: 'text-amber-500' },
    { id: 3, title: 'Solar Champion', date: '2025-12-20', type: 'Certificate', status: 'RECEIVED', icon: 'fa-certificate', color: 'text-blue-500' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Awards & Recognition</h1>
          <p className="text-sm text-gray-500 mt-2">View your achievements, company awards, and special recognition milestones.</p>
        </div>
      </div>

      <div className="flex space-x-6 mb-6 shrink-0 border-b border-gray-200">
        <button 
          onClick={() => setActiveTab("achievements")}
          className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'achievements' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          <i className="fas fa-medal mr-2"></i> My Achievements
        </button>
        <button 
          onClick={() => setActiveTab("leaderboard")}
          className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'leaderboard' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          <i className="fas fa-list-ol mr-2"></i> Company Leaderboard
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
          
          {activeTab === "achievements" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              
              {awards.map(award => (
                <div key={award.id} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden group hover:shadow-md transition-shadow">
                  <div className="p-6 text-center border-b border-gray-100">
                    <div className={`w-20 h-20 mx-auto rounded-full bg-gray-50 flex items-center justify-center text-4xl mb-4 border border-gray-100 shadow-inner ${award.color}`}>
                      <i className={`fas ${award.icon}`}></i>
                    </div>
                    <h3 className="font-bold text-gray-900 text-lg mb-1">{award.title}</h3>
                    <p className="text-sm text-gray-500">{award.type}</p>
                  </div>
                  <div className="p-4 bg-gray-50 flex justify-between items-center text-sm">
                    <span className="text-gray-500 font-medium">{new Date(award.date).toLocaleDateString()}</span>
                    <span className={`font-bold px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider ${
                      award.status === 'RECEIVED' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {award.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}

              {/* Empty placeholder for next milestone */}
              <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-center p-8 opacity-75">
                <div className="w-16 h-16 rounded-full bg-gray-200 text-gray-400 flex items-center justify-center text-2xl mb-4">
                  <i className="fas fa-lock"></i>
                </div>
                <h3 className="font-bold text-gray-600 mb-1">Double Century Club</h3>
                <p className="text-xs text-gray-500">Reach 200 direct referrals to unlock the Platinum Trophy.</p>
                <div className="w-full bg-gray-200 h-2 rounded-full mt-4">
                  <div className="bg-gray-400 h-2 rounded-full" style={{ width: '72%' }}></div>
                </div>
                <p className="text-[10px] font-bold text-gray-400 uppercase mt-2">145 / 200 Completed</p>
              </div>

            </div>
          )}

          {activeTab === "leaderboard" && (
            <div className="max-w-4xl mx-auto">
              <div className="bg-gradient-to-r from-indigo-900 to-purple-900 rounded-t-xl p-6 text-white flex justify-between items-center shadow-lg">
                <div>
                  <h2 className="text-xl font-bold mb-1">National Leaderboard</h2>
                  <p className="text-sm text-indigo-200">Top performers across the VGK Network (August 2026)</p>
                </div>
                <i className="fas fa-globe-asia text-5xl opacity-20"></i>
              </div>
              
              <div className="bg-white border border-gray-200 rounded-b-xl overflow-hidden shadow-sm">
                <table className="w-full text-left">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center w-16">Rank</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Member</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Tier</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Points / Sales</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    
                    {/* Rank 1 */}
                    <tr className="bg-yellow-50/30">
                      <td className="p-4 text-center">
                        <i className="fas fa-medal text-yellow-500 text-2xl"></i>
                      </td>
                      <td className="p-4 font-bold text-gray-900 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-yellow-500 text-white flex items-center justify-center text-xs">SP</div>
                        Suresh Pillai
                      </td>
                      <td className="p-4"><span className="text-xs font-bold px-2 py-1 bg-gray-900 text-white rounded uppercase">Platinum</span></td>
                      <td className="p-4 text-right font-bold text-gray-900">42,500 <span className="text-[10px] text-gray-500 ml-1">Pts</span></td>
                    </tr>

                    {/* Rank 2 */}
                    <tr className="bg-gray-50/50">
                      <td className="p-4 text-center">
                        <i className="fas fa-medal text-gray-400 text-2xl"></i>
                      </td>
                      <td className="p-4 font-bold text-gray-900 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gray-400 text-white flex items-center justify-center text-xs">MR</div>
                        Meera Reddy
                      </td>
                      <td className="p-4"><span className="text-xs font-bold px-2 py-1 bg-gray-900 text-white rounded uppercase">Platinum</span></td>
                      <td className="p-4 text-right font-bold text-gray-900">38,100 <span className="text-[10px] text-gray-500 ml-1">Pts</span></td>
                    </tr>

                    {/* Rank 3 */}
                    <tr className="bg-orange-50/20">
                      <td className="p-4 text-center">
                        <i className="fas fa-medal text-orange-400 text-2xl"></i>
                      </td>
                      <td className="p-4 font-bold text-gray-900 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-orange-400 text-white flex items-center justify-center text-xs">AJ</div>
                        Amit Jain
                      </td>
                      <td className="p-4"><span className="text-xs font-bold px-2 py-1 bg-yellow-500 text-white rounded uppercase">Gold</span></td>
                      <td className="p-4 text-right font-bold text-gray-900">35,200 <span className="text-[10px] text-gray-500 ml-1">Pts</span></td>
                    </tr>

                    {/* Spacer */}
                    <tr><td colSpan={4} className="p-2 bg-gray-50 text-center"><i className="fas fa-ellipsis-v text-gray-300"></i></td></tr>

                    {/* Current User */}
                    <tr className="bg-indigo-50/50 border-indigo-100">
                      <td className="p-4 text-center font-bold text-indigo-600">42</td>
                      <td className="p-4 font-bold text-indigo-900 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs border-2 border-indigo-200">
                          {user?.first_name.charAt(0)}{user?.last_name.charAt(0)}
                        </div>
                        You ({user?.first_name})
                      </td>
                      <td className="p-4"><span className="text-xs font-bold px-2 py-1 bg-yellow-500 text-white rounded uppercase">{user?.tier || 'Gold'}</span></td>
                      <td className="p-4 text-right font-bold text-indigo-700">12,450 <span className="text-[10px] text-indigo-400 ml-1">Pts</span></td>
                    </tr>

                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
