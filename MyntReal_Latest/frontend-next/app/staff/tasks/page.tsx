"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Task {
  id: number;
  title: string;
  description: string;
  assigned_to: string;
  assigned_by: string;
  priority: string; // HIGH, MEDIUM, LOW
  status: string; // TODO, IN_PROGRESS, REVIEW, DONE
  due_date: string;
  project?: string;
}

export default function TaskTrackerPage() {
  const { token, hasRole } = useStaffAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("my_tasks"); // my_tasks, assigned_by_me, team_tasks

  useEffect(() => {
    // Simulating API fetch
    const fetchTasks = async () => {
      setLoading(true);
      setTimeout(() => {
        setTasks([
          { id: 1, title: "Prepare Q3 Sales Report", description: "Compile data from all CRM leads for Q3 and create presentation.", assigned_to: "Me", assigned_by: "Manager", priority: "HIGH", status: "IN_PROGRESS", due_date: "2026-08-16", project: "Quarterly Review" },
          { id: 2, title: "Follow up with Solar Leads", description: "Call the 15 new leads from Meta Ads campaign.", assigned_to: "Me", assigned_by: "System", priority: "MEDIUM", status: "TODO", due_date: "2026-08-14", project: "Sales" },
          { id: 3, title: "Submit Expense Receipts", description: "Upload hotel receipts for the Pune trip.", assigned_to: "Me", assigned_by: "HR", priority: "LOW", status: "TODO", due_date: "2026-08-20" },
          { id: 4, title: "Review New Marketing Collateral", description: "Check the brochure designs.", assigned_to: "Me", assigned_by: "Manager", priority: "MEDIUM", status: "REVIEW", due_date: "2026-08-15", project: "Marketing" },
          { id: 5, title: "Onboard EcoDrive Motors", description: "Help them set up their vendor profile.", assigned_to: "Priya Desai", assigned_by: "Me", priority: "HIGH", status: "IN_PROGRESS", due_date: "2026-08-14", project: "VGK Network" },
        ]);
        setLoading(false);
      }, 500);
    };

    fetchTasks();
  }, [token]);

  const filteredTasks = tasks.filter(t => {
    if (activeTab === "my_tasks") return t.assigned_to === "Me";
    if (activeTab === "assigned_by_me") return t.assigned_by === "Me";
    return true; // Team Tasks
  });

  const statuses = [
    { key: "TODO", label: "To Do", color: "gray" },
    { key: "IN_PROGRESS", label: "In Progress", color: "blue" },
    { key: "REVIEW", label: "In Review", color: "amber" },
    { key: "DONE", label: "Completed", color: "green" }
  ];

  const renderTaskCard = (task: Task) => (
    <div key={task.id} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-3 hover:shadow-md transition-shadow cursor-pointer group">
      <div className="flex justify-between items-start mb-2">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
          task.priority === 'HIGH' ? 'bg-red-100 text-red-700' :
          task.priority === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
          'bg-gray-100 text-gray-700'
        }`}>
          {task.priority}
        </span>
        {task.project && (
          <span className="text-[10px] text-gray-500 font-medium bg-gray-50 px-2 py-0.5 rounded border border-gray-100">
            <i className="fas fa-folder text-gray-400 mr-1"></i> {task.project}
          </span>
        )}
      </div>
      <h4 className="font-bold text-gray-900 text-sm mb-1 leading-tight group-hover:text-indigo-600 transition-colors">{task.title}</h4>
      <p className="text-xs text-gray-500 line-clamp-2 mb-3">{task.description}</p>
      
      <div className="flex justify-between items-center text-xs border-t border-gray-50 pt-2">
        <div className="flex items-center text-gray-600">
          <i className="far fa-calendar-alt mr-1 text-gray-400"></i>
          <span className={new Date(task.due_date) < new Date() && task.status !== 'DONE' ? 'text-red-500 font-bold' : ''}>
            {new Date(task.due_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}
          </span>
        </div>
        
        <div className="flex items-center gap-1">
          {activeTab === "assigned_by_me" ? (
            <div className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-[8px]" title={`Assigned to: ${task.assigned_to}`}>
              {task.assigned_to.charAt(0)}
            </div>
          ) : (
            <div className="w-5 h-5 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center font-bold text-[8px]" title={`By: ${task.assigned_by}`}>
              {task.assigned_by.charAt(0)}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-[1600px] mx-auto h-[calc(100vh-80px)] flex flex-col">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Task Tracker</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your daily deliverables, delegate work, and track team progress.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/tasks/planner" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-calendar-day mr-2"></i> Day Planner
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> New Task
          </button>
        </div>
      </div>

      <div className="flex space-x-6 mb-6 shrink-0 border-b border-gray-200">
        <button 
          onClick={() => setActiveTab("my_tasks")}
          className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'my_tasks' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          <i className="fas fa-tasks mr-2"></i> My Tasks
        </button>
        <button 
          onClick={() => setActiveTab("assigned_by_me")}
          className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'assigned_by_me' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          <i className="fas fa-paper-plane mr-2"></i> Delegated by Me
        </button>
        {hasRole(['MANAGER', 'ADMIN']) && (
          <button 
            onClick={() => setActiveTab("team_tasks")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'team_tasks' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            <i className="fas fa-users mr-2"></i> Team Overview
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <i className="fas fa-spinner fa-spin text-4xl text-indigo-500"></i>
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto pb-4">
          <div className="flex space-x-4 min-w-max h-full">
            {statuses.map(status => (
              <div key={status.key} className="w-80 flex flex-col bg-gray-50/80 rounded-xl border border-gray-200">
                {/* Column Header */}
                <div className={`p-4 border-b-2 border-${status.color}-400 bg-white rounded-t-xl shrink-0 flex justify-between items-center`}>
                  <h3 className="font-bold text-gray-800">{status.label}</h3>
                  <span className="bg-gray-100 text-gray-600 text-xs font-bold px-2 py-0.5 rounded-full">
                    {filteredTasks.filter(t => t.status === status.key).length}
                  </span>
                </div>
                
                {/* Column Content */}
                <div className="flex-1 overflow-y-auto p-3">
                  {filteredTasks.filter(t => t.status === status.key).map(renderTaskCard)}
                  
                  {filteredTasks.filter(t => t.status === status.key).length === 0 && (
                    <div className="h-24 border-2 border-dashed border-gray-200 rounded-lg flex flex-col items-center justify-center text-gray-400 text-sm font-medium">
                      No tasks
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
