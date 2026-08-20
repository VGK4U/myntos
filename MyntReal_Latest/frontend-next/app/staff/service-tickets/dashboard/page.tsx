"use client";

import React, { useState, useEffect } from 'react';
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Ticket, AlertTriangle, CheckCircle2, Clock, Activity, Package, RefreshCw } from "lucide-react";

export default function DashboardPage() {
  const { token } = useStaffAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);
  
  const fetchStats = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const response = await api.get('/tickets/service/dashboard-stats', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching dashboard stats:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [token]);

  if (loading || !stats) {
    return (
      <div className="p-8 bg-gray-50/50 min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-gray-500 animate-pulse">
          <Activity className="w-8 h-8" />
          <p>Loading Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50/50 min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Service Tickets Dashboard</h1>
          <p className="text-gray-500 mt-1">Monitor service operations, track SLA performance, and view team productivity metrics.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={fetchStats}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button className="bg-indigo-600 hover:bg-indigo-700 text-white">
            Generate Report
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="bg-white border border-gray-200">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="procurement">Procurement</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-6">
          {/* Main KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="border-l-4 border-l-blue-600 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Total Tickets</p>
                    <h3 className="text-3xl font-bold text-gray-900 mt-2">{stats.total_tickets}</h3>
                  </div>
                  <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
                    <Ticket className="w-6 h-6" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-amber-500 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Open Tickets</p>
                    <h3 className="text-3xl font-bold text-gray-900 mt-2">{stats.open_tickets}</h3>
                  </div>
                  <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
                    <Activity className="w-6 h-6" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-emerald-500 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Resolved (Today)</p>
                    <h3 className="text-3xl font-bold text-gray-900 mt-2">{stats.resolved_today}</h3>
                  </div>
                  <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-rose-500 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-500">SLA Breached</p>
                    <h3 className="text-3xl font-bold text-gray-900 mt-2">{stats.sla_breached}</h3>
                  </div>
                  <div className="p-3 bg-rose-50 text-rose-600 rounded-xl">
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent Tickets List */}
            <Card className="col-span-2 shadow-sm border border-gray-200">
              <CardHeader className="pb-3 border-b border-gray-100 bg-white rounded-t-xl">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="w-5 h-5 text-gray-500" />
                  Recent Tickets
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 bg-white rounded-b-xl">
                <div className="divide-y divide-gray-100 max-h-[400px] overflow-y-auto">
                  {stats.recent_tickets?.map((ticket: any) => (
                    <div key={ticket.id} className="p-4 hover:bg-gray-50 flex flex-col sm:flex-row sm:items-center justify-between transition-colors cursor-pointer gap-4">
                      <div className="flex flex-col gap-1">
                        <span className="font-semibold text-gray-900 text-sm">#{ticket.ticket_id} - {ticket.issue_category}</span>
                        <span className="text-xs text-gray-500 line-clamp-1 max-w-[400px]">{ticket.issue_description}</span>
                      </div>
                      <div className="flex items-center gap-4 shrink-0">
                        <span className="text-xs text-gray-400 font-medium">
                          {new Date(ticket.created_date).toLocaleDateString()}
                        </span>
                        <Badge variant="outline" className={
                          ticket.sub_status === 'new' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                          ticket.sub_status === 'closed' || ticket.sub_status === 'work_complete' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          'bg-amber-50 text-amber-700 border-amber-200'
                        }>
                          {ticket.sub_status.replace(/_/g, ' ').toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  ))}
                  {(!stats.recent_tickets || stats.recent_tickets.length === 0) && (
                    <div className="p-8 text-center text-gray-500">No recent tickets found.</div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* SLA Performance */}
            <Card className="shadow-sm border border-gray-200">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">SLA Performance</CardTitle>
                <CardDescription>Overall compliance metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="mb-8">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-700">Within SLA</span>
                    <span className="text-sm font-bold text-gray-900">{stats.sla_compliance}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3">
                    <div 
                      className={`h-3 rounded-full ${stats.sla_compliance > 90 ? 'bg-emerald-500' : stats.sla_compliance > 75 ? 'bg-amber-500' : 'bg-rose-500'}`} 
                      style={{ width: `${stats.sla_compliance}%` }}
                    ></div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gradient-to-br from-indigo-50 to-white p-4 rounded-xl border border-indigo-100 text-center shadow-sm">
                    <div className="text-2xl font-bold text-indigo-600">{stats.avg_resolution_hours}h</div>
                    <div className="text-xs text-indigo-900/60 font-medium mt-1 uppercase tracking-wider">Avg Resolution</div>
                  </div>
                  <div className="bg-gradient-to-br from-indigo-50 to-white p-4 rounded-xl border border-indigo-100 text-center shadow-sm">
                    <div className="text-2xl font-bold text-indigo-600">{stats.avg_response_hours}h</div>
                    <div className="text-xs text-indigo-900/60 font-medium mt-1 uppercase tracking-wider">Avg Response</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="procurement" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="border-l-4 border-l-purple-500 shadow-sm">
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Awaiting Spares</p>
                    <h3 className="text-3xl font-bold text-gray-900 mt-2">{stats.awaiting_spares}</h3>
                  </div>
                  <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
                    <Package className="w-6 h-6" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="performance">
           <Card className="shadow-sm border border-gray-200">
             <CardHeader>
               <CardTitle>Team Performance</CardTitle>
               <CardDescription>Metrics and breakdown available soon.</CardDescription>
             </CardHeader>
           </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
