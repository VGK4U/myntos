"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";

export default function TelecallingDialerPage() {
  const { token } = useStaffAuth();
  const [activeCall, setActiveCall] = useState<any>(null);
  const [callStatus, setCallStatus] = useState("IDLE"); // IDLE, DIALING, CONNECTED
  const [callDuration, setCallDuration] = useState(0);

  const [queue, setQueue] = useState<any[]>([]);

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        const res = await api.get(`/api/v1`);
        setQueue(res.data?.items || []);
      } catch (err) {
        console.warn("Failed to fetch dialer queue", err);
        setQueue([]);
      }
    };
    fetchQueue();
  }, [token]);

  // Timer for active calls
  useEffect(() => {
    let interval: any;
    if (callStatus === "CONNECTED") {
      interval = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else {
      setCallDuration(0);
    }
    return () => clearInterval(interval);
  }, [callStatus]);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleDial = async (lead: any) => {
    setActiveCall(lead);
    setCallStatus("DIALING");
    
    try {
      await api.post('/staff/crm/dialer/call', { lead_id: lead.id });
      setCallStatus("CONNECTED");
    } catch (err) {
      console.error("Dial failed", err);
      setCallStatus("IDLE");
      setActiveCall(null);
    }
  };

  const handleHangup = async () => {
    try {
      await api.post('/staff/crm/dialer/hangup', { lead_id: activeCall?.id });
    } catch (err) {
      console.error("Hangup failed", err);
    } finally {
      setCallStatus("IDLE");
      setActiveCall(null);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col md:flex-row gap-6">
      
      {/* Left Column: Call Queue & History */}
      <div className="w-full md:w-2/3 space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Telecalling Dialer</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your daily call queue, log interactions, and auto-dial leads.</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
            <h2 className="font-bold text-gray-900">Today's Call Queue</h2>
            <span className="bg-indigo-100 text-indigo-800 text-xs font-bold px-2 py-1 rounded-full">4 Pending</span>
          </div>
          
          <div className="divide-y divide-gray-100">
            {queue.map((lead: any) => (
              <div key={lead.id} className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                <div className="flex flex-col">
                  <span className="font-bold text-gray-900">{lead.name}</span>
                  <span className="text-sm text-gray-500">{lead.phone} • {lead.type}</span>
                </div>
                <div className="flex items-center space-x-4">
                  <span className="text-xs font-medium text-gray-400">{lead.time || "Anytime"}</span>
                  <button 
                    onClick={() => handleDial(lead)}
                    disabled={callStatus !== "IDLE"}
                    className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors shadow-sm ${
                      callStatus !== "IDLE" ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-green-500 text-white hover:bg-green-600'
                    }`}
                  >
                    <i className="fas fa-phone"></i>
                  </button>
                </div>
              </div>
            ))}
            {queue.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                No leads in the queue today.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Column: Dialer Interface */}
      <div className="w-full md:w-1/3">
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden sticky top-6">
          <div className="bg-gray-900 p-6 text-center text-white relative">
            {callStatus === "IDLE" ? (
              <>
                <div className="w-20 h-20 mx-auto bg-gray-800 rounded-full flex items-center justify-center text-3xl mb-4 text-gray-500">
                  <i className="fas fa-user"></i>
                </div>
                <h3 className="text-lg font-bold">Ready to Call</h3>
                <p className="text-sm text-gray-400">Select a lead from the queue</p>
              </>
            ) : (
              <>
                {/* Pulse animation for dialing/connected */}
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-green-500/20 rounded-full animate-ping"></div>
                <div className="w-20 h-20 mx-auto bg-gray-800 rounded-full flex items-center justify-center text-3xl mb-4 text-white relative z-10 border-2 border-green-500">
                  {activeCall?.name.charAt(0)}
                </div>
                <h3 className="text-lg font-bold relative z-10">{activeCall?.name}</h3>
                <p className="text-sm text-gray-300 mb-2 relative z-10">{activeCall?.phone}</p>
                <p className={`text-sm font-medium relative z-10 ${callStatus === "DIALING" ? 'text-amber-400 animate-pulse' : 'text-green-400'}`}>
                  {callStatus === "DIALING" ? "Dialing..." : formatDuration(callDuration)}
                </p>
              </>
            )}
          </div>

          <div className="p-6 bg-gray-50">
            {/* Dialpad */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, '*', 0, '#'].map((num) => (
                <button key={num} className="bg-white border border-gray-200 rounded-lg p-3 text-lg font-bold text-gray-700 hover:bg-gray-100 shadow-sm transition-colors">
                  {num}
                </button>
              ))}
            </div>

            <div className="flex justify-center space-x-4">
              <button className="w-14 h-14 bg-gray-200 text-gray-600 rounded-full flex items-center justify-center hover:bg-gray-300 transition-colors shadow-sm">
                <i className="fas fa-microphone-slash"></i>
              </button>
              
              {callStatus === "IDLE" ? (
                <button className="w-16 h-16 bg-green-500 text-white rounded-full flex items-center justify-center text-xl hover:bg-green-600 transition-colors shadow-md">
                  <i className="fas fa-phone"></i>
                </button>
              ) : (
                <button 
                  onClick={handleHangup}
                  className="w-16 h-16 bg-red-500 text-white rounded-full flex items-center justify-center text-xl hover:bg-red-600 transition-colors shadow-md animate-bounce-slight"
                >
                  <i className="fas fa-phone-slash"></i>
                </button>
              )}
              
              <button className="w-14 h-14 bg-gray-200 text-gray-600 rounded-full flex items-center justify-center hover:bg-gray-300 transition-colors shadow-sm">
                <i className="fas fa-volume-up"></i>
              </button>
            </div>
          </div>
          
          {callStatus === "CONNECTED" && (
            <div className="p-4 border-t border-gray-100 bg-white">
              <textarea 
                className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:ring-2 focus:border-indigo-500 outline-none" 
                rows={3} 
                placeholder="Type call notes here..."
              ></textarea>
              <button className="w-full mt-2 bg-indigo-600 text-white py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors">
                Save Notes
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
