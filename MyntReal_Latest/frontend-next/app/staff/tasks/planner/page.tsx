"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function DayPlannerPage() {
  const { token } = useStaffAuth();
  const [currentDate, setCurrentDate] = useState(new Date());

  const timeSlots = [
    "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", 
    "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", 
    "05:00 PM", "06:00 PM"
  ];

  const events = [
    { time: "09:00 AM", title: "Daily Standup Meeting", type: "MEETING", duration: 1 },
    { time: "11:00 AM", title: "Follow up with Solar Leads", type: "CALL", duration: 1 },
    { time: "02:00 PM", title: "Q3 Strategy Planning", type: "WORK", duration: 2 },
    { time: "05:00 PM", title: "Client Demo: EcoDrive", type: "MEETING", duration: 1 }
  ];

  const prevDay = () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() - 1);
    setCurrentDate(d);
  };

  const nextDay = () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + 1);
    setCurrentDate(d);
  };

  const getEventForSlot = (time: string) => {
    return events.find(e => e.time === time);
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Day Planner</h1>
          <p className="text-sm text-gray-500 mt-2">Organize your daily schedule, meetings, and dedicated focus time.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/tasks" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-tasks mr-2"></i> Task Board
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Schedule Event
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {/* Calendar Header */}
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <button onClick={prevDay} className="p-2 text-gray-500 hover:text-indigo-600 transition-colors">
            <i className="fas fa-chevron-left"></i>
          </button>
          
          <div className="text-center">
            <h2 className="text-xl font-bold text-gray-900">
              {currentDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
            </h2>
            {currentDate.toDateString() === new Date().toDateString() && (
              <span className="inline-block mt-1 bg-green-100 text-green-700 text-xs font-bold px-2 py-0.5 rounded uppercase">Today</span>
            )}
          </div>
          
          <button onClick={nextDay} className="p-2 text-gray-500 hover:text-indigo-600 transition-colors">
            <i className="fas fa-chevron-right"></i>
          </button>
        </div>

        {/* Schedule Grid */}
        <div className="divide-y divide-gray-100">
          {timeSlots.map(time => {
            const event = getEventForSlot(time);
            return (
              <div key={time} className="flex min-h-[80px] hover:bg-gray-50 transition-colors group">
                <div className="w-24 shrink-0 p-4 border-r border-gray-100 text-right">
                  <span className="text-sm font-medium text-gray-500">{time}</span>
                </div>
                <div className="flex-1 p-2 relative">
                  {event ? (
                    <div className={`absolute top-2 left-2 right-4 bottom-2 p-3 rounded-lg border-l-4 shadow-sm cursor-pointer hover:shadow-md transition-all ${
                      event.type === 'MEETING' ? 'bg-purple-50 border-purple-500 hover:bg-purple-100' :
                      event.type === 'CALL' ? 'bg-blue-50 border-blue-500 hover:bg-blue-100' :
                      'bg-indigo-50 border-indigo-500 hover:bg-indigo-100'
                    }`}
                    style={{ height: `calc(${event.duration * 100}% - 1rem)`, zIndex: 10 }}
                    >
                      <h4 className="font-bold text-gray-900">{event.title}</h4>
                      <p className="text-xs text-gray-600 mt-1">
                        <i className={`fas ${
                          event.type === 'MEETING' ? 'fa-users text-purple-400' :
                          event.type === 'CALL' ? 'fa-phone-alt text-blue-400' :
                          'fa-laptop text-indigo-400'
                        } mr-1`}></i>
                        {event.type}
                      </p>
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center px-4 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="text-sm font-medium text-indigo-500 hover:text-indigo-700">
                        <i className="fas fa-plus mr-1"></i> Add item
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
