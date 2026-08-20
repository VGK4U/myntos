"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";

interface Task {
  id: number;
  title: string;
  description: string;
  assigned_to_name?: string;
  created_by_name?: string;
  priority: string;
  status: string;
  due_date: string;
  created_at: string;
}

export default function TaskTrackerPage() {
  const { user } = useStaffAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"assigned-to-me" | "assigned-by-me" | "all">("assigned-to-me");
  
  const [stats, setStats] = useState({
    pending: 0,
    inProgress: 0,
    completed: 0
  });

  useEffect(() => {
    fetchTasks();
  }, [activeTab]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      let endpoint = `/staff/tasks`;
      if (activeTab === "assigned-to-me") endpoint = `/staff/tasks/assigned-to-me`;
      if (activeTab === "assigned-by-me") endpoint = `/staff/tasks/assigned-by-me`;

      const res = await api.get(endpoint);
      const data = res.data.items || res.data || [];
      setTasks(data);

      if (activeTab === "assigned-to-me") {
        setStats({
          pending: data.filter((t: any) => t.status === 'Pending' || t.status === 'Todo').length,
          inProgress: data.filter((t: any) => t.status === 'In Progress').length,
          completed: data.filter((t: any) => t.status === 'Completed' || t.status === 'Done').length,
        });
      }
    } catch (err) {
      console.warn("Failed to fetch tasks", err);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  const getPriorityBadge = (priority: string) => {
    const p = (priority || "").toLowerCase();
    if (p === 'high' || p === 'urgent') return <span className="text-rose-600 font-bold bg-rose-50 px-2 py-0.5 rounded text-xs"><i className="fas fa-fire mr-1"></i>High</span>;
    if (p === 'medium') return <span className="text-amber-600 font-bold bg-amber-50 px-2 py-0.5 rounded text-xs">Medium</span>;
    return <span className="text-slate-500 font-bold bg-slate-50 px-2 py-0.5 rounded text-xs">Low</span>;
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s.includes('progress')) return <span className="px-2.5 py-1 bg-blue-100 text-blue-700 rounded-lg text-xs font-bold uppercase tracking-wider">In Progress</span>;
    if (s.includes('complet') || s.includes('done')) return <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold uppercase tracking-wider">Completed</span>;
    if (s.includes('review')) return <span className="px-2.5 py-1 bg-amber-100 text-amber-700 rounded-lg text-xs font-bold uppercase tracking-wider">Review</span>;
    return <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-bold uppercase tracking-wider">To Do</span>;
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-50 border border-violet-100 text-violet-700 text-xs font-bold uppercase tracking-wider mb-2">
            Workspace
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Task Manager</h1>
          <p className="text-slate-500 mt-1">Organize workflows, track progress, and collaborate seamlessly.</p>
        </div>
        
        <div className="flex gap-3">
          <button className="px-5 py-2.5 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center gap-2 text-sm">
            <i className="fas fa-plus"></i> Create Task
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      {activeTab === 'assigned-to-me' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex items-center gap-4">
            <div className="w-12 h-12 bg-slate-100 text-slate-600 rounded-xl flex items-center justify-center text-xl">
              <i className="fas fa-inbox"></i>
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500">To Do</p>
              <p className="text-2xl font-black text-slate-900">{stats.pending}</p>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center text-xl">
              <i className="fas fa-spinner fa-spin-pulse"></i>
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500">In Progress</p>
              <p className="text-2xl font-black text-slate-900">{stats.inProgress}</p>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex items-center gap-4">
            <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center text-xl">
              <i className="fas fa-check-double"></i>
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500">Completed</p>
              <p className="text-2xl font-black text-slate-900">{stats.completed}</p>
            </div>
          </div>
        </div>
      )}

      {/* Segments Navigation */}
      <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap gap-2 mb-6">
        {[
          { id: "assigned-to-me", label: "My Tasks", icon: "fa-user-check" },
          { id: "assigned-by-me", label: "Delegated By Me", icon: "fa-share-square" },
          { id: "all", label: "Department Feed", icon: "fa-globe" }
        ].map(s => (
          <button 
            key={s.id}
            onClick={() => setActiveTab(s.id as any)}
            className={`flex-1 min-w-[120px] px-4 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${
              activeTab === s.id 
                ? 'bg-violet-50 text-violet-700 shadow-sm border border-violet-100' 
                : 'text-slate-500 hover:bg-slate-50 border border-transparent'
            }`}
          >
            <i className={`fas ${s.icon}`}></i> {s.label}
          </button>
        ))}
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Task Details</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Priority</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Due Date</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    <i className="fas fa-circle-notch fa-spin text-3xl mb-3"></i>
                    <p className="font-medium">Loading Tasks...</p>
                  </td>
                </tr>
              ) : tasks.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center text-slate-500">
                    <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center text-3xl text-slate-400 mx-auto mb-4">
                      <i className="fas fa-check"></i>
                    </div>
                    <p className="font-bold text-slate-700 text-lg mb-1">You're all caught up!</p>
                    <p className="text-sm">There are no tasks pending in this queue.</p>
                  </td>
                </tr>
              ) : (
                tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-violet-50/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <p className="font-bold text-slate-900 group-hover:text-violet-700 transition-colors">{task.title}</p>
                        <p className="text-xs text-slate-500 mt-1 truncate max-w-sm">{task.description}</p>
                        <div className="flex gap-2 mt-2">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded">
                            <i className="fas fa-user-tag mr-1"></i> {activeTab === 'assigned-by-me' ? `TO: ${task.assigned_to_name || 'Unassigned'}` : `FROM: ${task.created_by_name || 'System'}`}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {getPriorityBadge(task.priority)}
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(task.status)}
                    </td>
                    <td className="px-6 py-4">
                      {task.due_date ? (
                        <p className={`text-sm font-bold ${new Date(task.due_date) < new Date() && task.status !== 'Completed' ? 'text-rose-600' : 'text-slate-700'}`}>
                          {new Date(task.due_date).toLocaleDateString()}
                        </p>
                      ) : (
                        <span className="text-slate-400 text-sm italic">No due date</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-2 text-violet-600 bg-violet-50 hover:bg-violet-100 hover:text-violet-800 rounded-lg transition-colors font-bold text-sm inline-flex items-center gap-2">
                        Open <i className="fas fa-chevron-right text-xs"></i>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
