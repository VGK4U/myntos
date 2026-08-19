"use client";

import React, { useState } from 'react';
import GenericDataTable from '@/components/GenericDataTable';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Activity, Plus, RefreshCcw, Download, CheckCircle, Briefcase, FileText } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function CyclesPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleAction = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  const pageTitle: string = "Cycles";

  return (
    <div className="flex flex-col w-full space-y-6 p-8 bg-slate-50 min-h-screen">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900">Cycles Dashboard</h1>
          <p className="text-muted-foreground mt-2 text-lg">
            Manage, analyze, and oversee data data in the Premium Enterprise V2 system.
          </p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" onClick={handleAction} disabled={isRefreshing} className="shadow-sm hover:shadow">
            <RefreshCcw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" className="shadow-sm hover:shadow">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button className="bg-primary text-primary-foreground shadow hover:shadow-md">
            <Plus className="mr-2 h-4 w-4" />
            Create New
          </Button>
        </div>
      </div>

      {/* Stats Cards Section */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-l-4 border-l-blue-500 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cycles</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">1,248</div>
            <p className="text-xs text-muted-foreground mt-1">
              +20.1% from last month
            </p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-green-500 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Approved</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">843</div>
            <p className="text-xs text-muted-foreground mt-1">
              +15% approval rate
            </p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-amber-500 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Action</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">142</div>
            <p className="text-xs text-muted-foreground mt-1">
              Requires immediate attention
            </p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-purple-500 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Reports</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">24</div>
            <p className="text-xs text-muted-foreground mt-1">
              Generated this week
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Area */}
      <Tabs defaultValue="overview" className="space-y-6" value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 lg:w-[400px] p-1 bg-slate-200/50">
          <TabsTrigger value="overview" className="rounded-sm">Overview</TabsTrigger>
          <TabsTrigger value="analytics" className="rounded-sm">Analytics</TabsTrigger>
          <TabsTrigger value="settings" className="rounded-sm">Settings</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="space-y-4">
          <Card className="shadow-sm border-0 ring-1 ring-slate-200">
            <CardHeader className="bg-slate-50/50 border-b pb-4">
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle className="text-xl">Data View</CardTitle>
                  <CardDescription>
                    Comprehensive data management and administration interface.
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  {/* Contextual Actions */}
                  {(pageTitle === 'Runs' || pageTitle === 'Cycles') ? (
                    <Button variant="secondary" size="sm" onClick={handleAction}>Run Payroll Cycle</Button>
                  ) : (pageTitle === 'Leaves' || pageTitle === 'Approvals') ? (
                    <Button variant="secondary" size="sm" onClick={handleAction}>Approve Selected</Button>
                  ) : (pageTitle === 'KRA' || pageTitle === 'Performance') ? (
                    <Button variant="secondary" size="sm" onClick={handleAction}>Update KPIs</Button>
                  ) : (
                    <Button variant="secondary" size="sm" onClick={handleAction}>Process Records</Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="min-h-[500px] w-full p-4">
                <GenericDataTable 
                  title="Cycles"
                  endpoint="/staff/payroll/cycles"
                  subtitle="Auto-mapped Premium Enterprise V2 data viewer for /staff/payroll/cycles"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="analytics">
          <Card className="min-h-[400px] flex items-center justify-center bg-slate-50/50 border-dashed">
            <div className="text-center space-y-2">
              <Activity className="h-10 w-10 text-slate-300 mx-auto" />
              <h3 className="text-lg font-medium text-slate-900">Analytics Dashboard</h3>
              <p className="text-sm text-slate-500">Advanced insights will appear here in the next update.</p>
            </div>
          </Card>
        </TabsContent>
        <TabsContent value="settings">
          <Card className="min-h-[400px] flex items-center justify-center bg-slate-50/50 border-dashed">
            <div className="text-center space-y-2">
              <FileText className="h-10 w-10 text-slate-300 mx-auto" />
              <h3 className="text-lg font-medium text-slate-900">Configuration</h3>
              <p className="text-sm text-slate-500">Module specific settings are currently being configured.</p>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
