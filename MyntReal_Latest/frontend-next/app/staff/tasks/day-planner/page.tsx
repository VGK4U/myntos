"use client";

import { useState } from "react";

export default function DayPlanner() {
  const [tasks, setTasks] = useState([
    { id: 1, title: "Morning Standup", time: "09:00 AM", duration: "30m", type: "meeting", status: "completed" },
    { id: 2, title: "Review Lead Conversions", time: "10:00 AM", duration: "1h", type: "focus", status: "in-progress" },
    { id: 3, title: "Client Call: Sarah Jenkins", time: "11:30 AM", duration: "45m", type: "call", status: "pending" },
    { id: 4, title: "Lunch Break", time: "01:00 PM", duration: "1h", type: "break", status: "pending" },
    { id: 5, title: "Prepare Monthly Report", time: "02:00 PM", duration: "2h", type: "focus", status: "pending" },
  ]);

  return (
    <div className="p-6 max-w-7xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Day Planner</h1>
          <p className="text-sm text-gray-500 mt-1">Organize your schedule and track daily tasks.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-5 py-2.5 bg-brand-warning text-white rounded-lg text-sm font-bold shadow-md shadow-brand-warning/20 hover:bg-amber-600 transition-colors">
            <i className="fas fa-plus mr-2"></i> Add Task
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Timeline */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between mb-6">
             <h3 className="text-lg font-bold text-gray-900">Today's Schedule</h3>
             <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full border border-gray-200">
               {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'long', day: 'numeric' })}
             </span>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
            <div className="space-y-4">
              {tasks.map((task) => (
                <div key={task.id} className={`p-4 rounded-xl border-l-4 shadow-sm flex items-start gap-4 transition-all hover:shadow-md ${
                  task.status === "completed" ? "bg-gray-50 border-gray-300 opacity-75" :
                  task.status === "in-progress" ? "bg-white border-brand-warning" : "bg-white border-blue-400"
                }`}>
                  <div className="w-16 flex-shrink-0 text-center">
                    <span className="text-sm font-bold text-gray-900 block">{task.time.split(' ')[0]}</span>
                    <span className="text-xs text-gray-500">{task.time.split(' ')[1]}</span>
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <h4 className={`text-base font-bold ${task.status === "completed" ? "text-gray-500 line-through" : "text-gray-900"}`}>
                        {task.title}
                      </h4>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">
                          <i className="far fa-clock mr-1"></i> {task.duration}
                        </span>
                      </div>
                    </div>
                    
                    <div className="mt-3 flex items-center justify-between">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                        task.type === "meeting" ? "bg-purple-50 text-purple-700 border-purple-200" :
                        task.type === "focus" ? "bg-blue-50 text-blue-700 border-blue-200" :
                        task.type === "call" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                        "bg-gray-100 text-gray-700 border-gray-200"
                      }`}>
                        {task.type.toUpperCase()}
                      </span>
                      
                      <div className="flex gap-2">
                        {task.status !== "completed" && (
                          <button className="w-8 h-8 rounded-lg flex items-center justify-center text-emerald-600 hover:bg-emerald-50 border border-transparent hover:border-emerald-200 transition-colors">
                            <i className="fas fa-check"></i>
                          </button>
                        )}
                        <button className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors">
                          <i className="fas fa-ellipsis-v"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Mini Tools */}
        <div className="space-y-6">
          {/* Calendar Widget */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-wider">Mini Calendar</h3>
            <div className="bg-gray-50 rounded-lg p-4 text-center border border-gray-200">
               <p className="text-sm text-gray-500">Interactive Calendar will render here.</p>
            </div>
          </div>

          {/* Quick Notes */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col h-64">
            <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-wider">Quick Notes</h3>
            <textarea 
              className="flex-1 w-full bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700 focus:ring-brand-warning focus:border-brand-warning resize-none"
              placeholder="Jot down quick thoughts here..."
            ></textarea>
          </div>
        </div>

      </div>
    </div>
  );
}
