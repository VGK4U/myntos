"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Loader2, Plus, CheckCircle2, Clock, PlayCircle, AlertCircle, Inbox, Send, Users } from "lucide-react";

interface Task {
  id: number;
  task_code: string;
  title: string;
  description: string;
  primary_assignee_name?: string;
  creator_name?: string;
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
    completed: 0,
    overdue: 0
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
      
      const data = res.data.tasks || res.data.items || res.data || [];
      setTasks(data);

      if (res.data.summary) {
        setStats({
          pending: res.data.summary.pending || 0,
          inProgress: res.data.summary.in_progress || 0,
          completed: res.data.summary.completed || 0,
          overdue: res.data.summary.overdue || 0,
        });
      } else {
        setStats({
          pending: data.filter((t: any) => t.status === 'pending').length,
          inProgress: data.filter((t: any) => t.status === 'in_progress').length,
          completed: data.filter((t: any) => t.status === 'completed').length,
          overdue: 0
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
    if (p === 'high' || p === 'urgent') return <Badge variant="destructive" className="font-bold">High</Badge>;
    if (p === 'medium') return <Badge variant="outline" className="bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-100 font-bold">Medium</Badge>;
    return <Badge variant="secondary" className="bg-slate-100 text-slate-800 hover:bg-slate-100 font-bold">Low</Badge>;
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s.includes('progress')) return <Badge variant="outline" className="bg-blue-100 text-blue-800 border-blue-200">In Progress</Badge>;
    if (s.includes('complet') || s.includes('done')) return <Badge variant="outline" className="bg-emerald-100 text-emerald-800 border-emerald-200">Completed</Badge>;
    if (s.includes('review')) return <Badge variant="outline" className="bg-purple-100 text-purple-800 border-purple-200">Review</Badge>;
    if (s.includes('cancel')) return <Badge variant="outline" className="bg-rose-100 text-rose-800 border-rose-200">Cancelled</Badge>;
    return <Badge variant="outline" className="bg-slate-100 text-slate-800 border-slate-200">Pending</Badge>;
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto min-h-screen">
      
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <Badge variant="outline" className="mb-2 bg-violet-50 text-violet-700 border-violet-200">
            Workspace
          </Badge>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Task Manager</h1>
          <p className="text-slate-500 mt-1">Organize workflows, track progress, and collaborate seamlessly.</p>
        </div>
        
        <div className="flex gap-3">
          <Button className="font-bold shadow-lg bg-slate-900 hover:bg-slate-800 text-white rounded-xl" size="lg">
            <Plus className="w-4 h-4 mr-2" /> Create Task
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card className="border-none shadow-md shadow-slate-200/50">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="w-12 h-12 bg-slate-100 text-slate-600 rounded-xl flex items-center justify-center">
              <Clock className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500">Pending</p>
              <p className="text-3xl font-black text-slate-900">{stats.pending}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-none shadow-md shadow-slate-200/50">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center">
              <PlayCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500">In Progress</p>
              <p className="text-3xl font-black text-slate-900">{stats.inProgress}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-none shadow-md shadow-slate-200/50">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500">Completed</p>
              <p className="text-3xl font-black text-slate-900">{stats.completed}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-none shadow-md shadow-slate-200/50">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="w-12 h-12 bg-rose-50 text-rose-600 rounded-xl flex items-center justify-center">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-500">Overdue</p>
              <p className="text-3xl font-black text-slate-900">{stats.overdue}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="assigned-to-me" className="w-full" onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="mb-6 bg-white border border-slate-200 shadow-sm rounded-xl p-1 h-auto flex-wrap">
          <TabsTrigger value="assigned-to-me" className="rounded-lg px-6 py-3 font-bold data-[state=active]:bg-violet-50 data-[state=active]:text-violet-700 data-[state=active]:shadow-none">
            <Inbox className="w-4 h-4 mr-2" /> My Tasks
          </TabsTrigger>
          <TabsTrigger value="assigned-by-me" className="rounded-lg px-6 py-3 font-bold data-[state=active]:bg-violet-50 data-[state=active]:text-violet-700 data-[state=active]:shadow-none">
            <Send className="w-4 h-4 mr-2" /> Delegated By Me
          </TabsTrigger>
          <TabsTrigger value="all" className="rounded-lg px-6 py-3 font-bold data-[state=active]:bg-violet-50 data-[state=active]:text-violet-700 data-[state=active]:shadow-none">
            <Users className="w-4 h-4 mr-2" /> Department Feed
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-0 outline-none">
          <Card className="border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-slate-50">
                  <TableRow>
                    <TableHead className="font-bold text-slate-500">Task Details</TableHead>
                    <TableHead className="font-bold text-slate-500">Priority</TableHead>
                    <TableHead className="font-bold text-slate-500">Status</TableHead>
                    <TableHead className="font-bold text-slate-500">Due Date</TableHead>
                    <TableHead className="font-bold text-slate-500 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="h-48 text-center">
                        <Loader2 className="w-8 h-8 animate-spin mx-auto text-violet-500 mb-4" />
                        <p className="text-slate-500 font-medium">Loading Tasks...</p>
                      </TableCell>
                    </TableRow>
                  ) : tasks.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="h-64 text-center">
                        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                          <CheckCircle2 className="w-8 h-8 text-slate-400" />
                        </div>
                        <p className="font-bold text-slate-900 text-lg">You're all caught up!</p>
                        <p className="text-slate-500 mt-1">There are no tasks pending in this queue.</p>
                      </TableCell>
                    </TableRow>
                  ) : (
                    tasks.map((task) => (
                      <TableRow key={task.id} className="hover:bg-slate-50/80 cursor-pointer group">
                        <TableCell>
                          <div className="flex flex-col max-w-[400px]">
                            <p className="font-bold text-slate-900 group-hover:text-violet-700 transition-colors flex items-center">
                              {task.task_code && <span className="text-xs text-slate-400 mr-2 font-mono">[{task.task_code}]</span>}
                              {task.title}
                            </p>
                            <p className="text-sm text-slate-500 mt-1 truncate">{task.description}</p>
                            <div className="mt-2 flex gap-2">
                              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded">
                                {activeTab === 'assigned-by-me' 
                                  ? `TO: ${task.primary_assignee_name || 'Unassigned'}` 
                                  : `FROM: ${task.creator_name || 'System'}`}
                              </span>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>{getPriorityBadge(task.priority)}</TableCell>
                        <TableCell>{getStatusBadge(task.status)}</TableCell>
                        <TableCell>
                          {task.due_date ? (
                            <p className={`text-sm font-medium ${new Date(task.due_date) < new Date() && !['completed', 'cancelled'].includes(task.status?.toLowerCase()) ? 'text-rose-600 font-bold' : 'text-slate-700'}`}>
                              {new Date(task.due_date).toLocaleDateString()}
                            </p>
                          ) : (
                            <span className="text-slate-400 text-sm italic">No due date</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" className="text-violet-600 hover:text-violet-700 hover:bg-violet-50 font-bold">
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
