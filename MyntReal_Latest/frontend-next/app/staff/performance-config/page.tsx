"use client";

import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useStaffAuth } from '@/components/staff/AuthProvider';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function PerformanceConfigPage() {
  const { user } = useStaffAuth();
  
  const [month, setMonth] = useState<string>("0");
  const [year, setYear] = useState<string>(new Date().getFullYear().toString());
  
  const [targetsData, setTargetsData] = useState<any>(null);
  const [reportData, setReportData] = useState<any>(null);
  
  const [loadingTargets, setLoadingTargets] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);

  const loadTargets = async () => {
    setLoadingTargets(true);
    try {
      const res = await api.get('/performance/employee-targets', {
        params: { month: parseInt(month), year: parseInt(year) }
      });
      if (res.data.success) {
        setTargetsData(res.data);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to load targets");
    } finally {
      setLoadingTargets(false);
    }
  };

  const loadReport = async () => {
    setLoadingReport(true);
    try {
      const dFrom = `${year}-${month.padStart(2, '0')}-01`;
      const dTo = new Date(parseInt(year), parseInt(month), 0).toISOString().split('T')[0]; // last day of month
      
      const res = await api.get('/performance/report', {
        params: { date_from: dFrom, date_to: dTo }
      });
      if (res.data.success) {
        setReportData(res.data);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to load report");
    } finally {
      setLoadingReport(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Performance Configuration & Report</h1>
      </div>

      <Tabs defaultValue="targets" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="targets">Employee Targets</TabsTrigger>
          <TabsTrigger value="report">Performance Report</TabsTrigger>
          <TabsTrigger value="incentive">Incentive Config</TabsTrigger>
          <TabsTrigger value="bonus">Quarterly Bonus</TabsTrigger>
        </TabsList>

        <TabsContent value="targets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Per-Employee KPI Targets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-4 mb-6">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Month</label>
                  <Select value={month} onValueChange={setMonth}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="Select Month" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">All / Default</SelectItem>
                      <SelectItem value="1">January</SelectItem>
                      <SelectItem value="2">February</SelectItem>
                      <SelectItem value="3">March</SelectItem>
                      <SelectItem value="4">April</SelectItem>
                      <SelectItem value="5">May</SelectItem>
                      <SelectItem value="6">June</SelectItem>
                      <SelectItem value="7">July</SelectItem>
                      <SelectItem value="8">August</SelectItem>
                      <SelectItem value="9">September</SelectItem>
                      <SelectItem value="10">October</SelectItem>
                      <SelectItem value="11">November</SelectItem>
                      <SelectItem value="12">December</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Year</label>
                  <Select value={year} onValueChange={setYear}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue placeholder="Select Year" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="2025">2025</SelectItem>
                      <SelectItem value="2026">2026</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={loadTargets} disabled={loadingTargets}>
                  {loadingTargets ? 'Loading...' : 'Load Targets'}
                </Button>
              </div>

              {targetsData ? (
                <div className="rounded-md border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Employee</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Department</TableHead>
                        <TableHead>Total Weight</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {targetsData.employees.map((emp: any) => (
                        <TableRow key={emp.employee_id}>
                          <TableCell className="font-medium">
                            {emp.name} <br />
                            <span className="text-xs text-muted-foreground">{emp.emp_code}</span>
                          </TableCell>
                          <TableCell>{emp.role}</TableCell>
                          <TableCell>{emp.department}</TableCell>
                          <TableCell>{emp.total_weight}%</TableCell>
                        </TableRow>
                      ))}
                      {targetsData.employees.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center py-6 text-muted-foreground">
                            No employees found.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  Select month and year to load targets.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="report" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Report</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-4 mb-6">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Month</label>
                  <Select value={month} onValueChange={setMonth}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="Select Month" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">January</SelectItem>
                      <SelectItem value="2">February</SelectItem>
                      <SelectItem value="3">March</SelectItem>
                      <SelectItem value="4">April</SelectItem>
                      <SelectItem value="5">May</SelectItem>
                      <SelectItem value="6">June</SelectItem>
                      <SelectItem value="7">July</SelectItem>
                      <SelectItem value="8">August</SelectItem>
                      <SelectItem value="9">September</SelectItem>
                      <SelectItem value="10">October</SelectItem>
                      <SelectItem value="11">November</SelectItem>
                      <SelectItem value="12">December</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Year</label>
                  <Select value={year} onValueChange={setYear}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue placeholder="Select Year" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="2025">2025</SelectItem>
                      <SelectItem value="2026">2026</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={loadReport} disabled={loadingReport || month === "0"}>
                  {loadingReport ? 'Generating...' : 'Generate Report'}
                </Button>
              </div>

              {reportData ? (
                <div className="rounded-md border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Employee</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Department</TableHead>
                        <TableHead>Score</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {reportData.data.map((row: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium">{row.employee_name}</TableCell>
                          <TableCell>{row.role_name}</TableCell>
                          <TableCell>{row.department_name}</TableCell>
                          <TableCell>{row.overall_score}%</TableCell>
                        </TableRow>
                      ))}
                      {reportData.data.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center py-6 text-muted-foreground">
                            No data for selected period.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  Select month and year to generate report.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="incentive" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Incentive Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-10 text-muted-foreground">
                Incentive configuration panel loaded via API parameters.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="bonus" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Quarterly Bonus Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-10 text-muted-foreground">
                Quarterly Bonus config panel loaded via API parameters.
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
