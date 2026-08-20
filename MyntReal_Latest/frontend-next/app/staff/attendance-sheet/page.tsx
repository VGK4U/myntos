"use client";

import React, { useState, useEffect } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, Users, CheckCircle, XCircle, Clock, FileText, Download, ChevronLeft, ChevronRight, AlertCircle, RefreshCw } from "lucide-react";

export default function AttendanceSheetPage() {
  const { user } = useStaffAuth();
  
  const [loading, setLoading] = useState(true);
  const [monthYear, setMonthYear] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  
  const [data, setData] = useState<any>(null);
  const [empStatus, setEmpStatus] = useState("active");
  const [search, setSearch] = useState("");

  const fetchAttendanceSheet = async () => {
    if (!user) return;
    setLoading(true);
    try {
      // Use the appropriate monthly endpoint based on the API schema we saw
      // Assuming HR/Admin can see all, managers see their team. 
      // If user has 'ea', 'vgk4u', 'hr', we use /monthly/{month_year}
      // Otherwise, we use /manager/team-monthly/{manager_id}/{month_year}
      
      const roleCode = user?.role?.role_code?.toLowerCase() || '';
      const isAdmin = roleCode === 'hr' || roleCode === 'ea' || roleCode === 'vgk4u' || user.emp_code === 'MR10001';
      
      const endpoint = isAdmin 
        ? `/staff/attendance-sheet/monthly/${monthYear}?emp_status=${empStatus}`
        : `/staff/attendance-sheet/manager/team-monthly/${user.id}/${monthYear}?emp_status=${empStatus}`;
        
      const res = await api.get(endpoint).catch((err) => {
          // fallback if endpoint is not exactly matching the standard
          if(isAdmin) return api.get(`/staff/attendance-sheet/monthly/${monthYear}?emp_status=${empStatus}`);
          throw err;
      });

      setData(res.data);
    } catch (err) {
      console.error("Failed to fetch attendance sheet", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAttendanceSheet();
  }, [user, monthYear, empStatus]);

  const handlePrevMonth = () => {
    const [year, month] = monthYear.split('-').map(Number);
    let newYear = year;
    let newMonth = month - 1;
    if (newMonth === 0) {
      newMonth = 12;
      newYear -= 1;
    }
    setMonthYear(`${newYear}-${String(newMonth).padStart(2, '0')}`);
  };

  const handleNextMonth = () => {
    const [year, month] = monthYear.split('-').map(Number);
    let newYear = year;
    let newMonth = month + 1;
    if (newMonth === 13) {
      newMonth = 1;
      newYear += 1;
    }
    setMonthYear(`${newYear}-${String(newMonth).padStart(2, '0')}`);
  };

  const formatMonthDisplay = (my: string) => {
    const [year, month] = my.split('-');
    const date = new Date(Number(year), Number(month) - 1, 1);
    return date.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  };

  // Extract employees and filter by search
  const employees = (data?.employees || []).filter((emp: any) => 
    emp.employee_name?.toLowerCase().includes(search.toLowerCase()) || 
    emp.employee_code?.toLowerCase().includes(search.toLowerCase())
  );

  const dates = data?.dates || [];

  return (
    <div className="p-6 lg:p-8 max-w-[1800px] mx-auto min-h-screen bg-slate-50/30">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
            <Calendar className="w-6 h-6 text-indigo-600" />
            Monthly Attendance Sheet
          </h1>
          <p className="text-slate-500 text-sm mt-1">Review and approve team attendance records</p>
        </div>
        
        <div className="flex items-center gap-3 bg-white p-2 rounded-xl shadow-sm border border-slate-200">
          <Button variant="ghost" size="icon" onClick={handlePrevMonth} className="h-8 w-8 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="font-semibold text-slate-700 min-w-[120px] text-center">
            {formatMonthDisplay(monthYear)}
          </div>
          <Button variant="ghost" size="icon" onClick={handleNextMonth} className="h-8 w-8 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card className="shadow-sm border-slate-200 border-l-4 border-l-blue-500">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Total Team</p>
              <h3 className="text-2xl font-black text-slate-800">{data?.totals?.total_employees || data?.totals?.team_size || 0}</h3>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-sm border-slate-200 border-l-4 border-l-emerald-500">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Total Marked Hrs</p>
              <h3 className="text-2xl font-black text-slate-800">{data?.totals?.total_marked_hours?.toFixed(1) || 0}</h3>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-sm border-slate-200 border-l-4 border-l-purple-500">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Total Approved Hrs</p>
              <h3 className="text-2xl font-black text-slate-800">{data?.totals?.total_approved_hours?.toFixed(1) || 0}</h3>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-sm border-slate-200 border-l-4 border-l-amber-500">
          <CardContent className="p-6 flex items-center gap-5">
            <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Exception Days</p>
              <h3 className="text-2xl font-black text-slate-800">{data?.totals?.total_exception_days || 0}</h3>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-sm border-slate-200 mb-8 overflow-hidden">
        <CardHeader className="bg-white border-b border-slate-100 py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <CardTitle className="text-lg font-bold text-slate-800">Attendance Records</CardTitle>
          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input 
                placeholder="Search employee..." 
                className="pl-9 bg-slate-50"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={empStatus} onValueChange={setEmpStatus}>
              <SelectTrigger className="w-full sm:w-[140px] bg-slate-50">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active Staff</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="all">All Staff</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" className="gap-2" onClick={fetchAttendanceSheet}>
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : employees.length === 0 ? (
            <div className="text-center py-16 text-slate-500">
              <Users className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-lg font-medium text-slate-600">No attendance data found</p>
              <p className="text-sm">Try adjusting your filters or search term.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table className="min-w-max border-collapse">
                <TableHeader className="bg-slate-50 sticky top-0 z-10 shadow-sm">
                  <TableRow>
                    <TableHead className="w-[280px] sticky left-0 bg-slate-50 shadow-[1px_0_0_0_#e2e8f0] font-bold text-slate-700">Employee Details</TableHead>
                    <TableHead className="text-center bg-blue-50/50 font-bold text-slate-700">Present</TableHead>
                    <TableHead className="text-center bg-red-50/50 font-bold text-slate-700">Absent</TableHead>
                    <TableHead className="text-center bg-amber-50/50 font-bold text-slate-700">Leaves</TableHead>
                    <TableHead className="text-center bg-emerald-50/50 font-bold text-slate-700">Eligible</TableHead>
                    {dates.map((d: string) => {
                      const dateObj = new Date(d);
                      const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
                      return (
                        <TableHead key={d} className={`text-center min-w-[80px] border-l border-slate-100 ${isWeekend ? 'bg-slate-100' : ''}`}>
                          <div className="flex flex-col items-center">
                            <span className="text-xs text-slate-500 font-medium">{dateObj.toLocaleDateString('en-US', { weekday: 'short' })}</span>
                            <span className={`text-sm font-bold ${isWeekend ? 'text-slate-600' : 'text-slate-800'}`}>{dateObj.getDate()}</span>
                          </div>
                        </TableHead>
                      );
                    })}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {employees.map((emp: any) => (
                    <TableRow key={emp.employee_id} className="hover:bg-slate-50/50 transition-colors">
                      <TableCell className="sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] group-hover:bg-slate-50/80 transition-colors p-4">
                        <div className="flex flex-col">
                          <span className="font-bold text-slate-800">{emp.employee_name}</span>
                          <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                            <Badge variant="outline" className="px-1.5 py-0 text-[10px] bg-slate-50">{emp.employee_code}</Badge>
                            {emp.department}
                          </span>
                        </div>
                      </TableCell>
                      
                      <TableCell className="text-center font-bold text-blue-600 bg-blue-50/10">
                        {emp.summary?.present_days_count || 0}
                      </TableCell>
                      <TableCell className="text-center font-bold text-red-600 bg-red-50/10">
                        {emp.summary?.absences_count || 0}
                      </TableCell>
                      <TableCell className="text-center font-bold text-amber-600 bg-amber-50/10">
                        {emp.summary?.leaves_days?.toFixed(1) || 0}
                      </TableCell>
                      <TableCell className="text-center font-black text-emerald-600 bg-emerald-50/10">
                        {emp.summary?.eligible_days?.toFixed(1) || 0}
                      </TableCell>
                      
                      {dates.map((d: string) => {
                        const cellData = emp.dates?.[d];
                        const dateObj = new Date(d);
                        const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
                        
                        let cellContent = "-";
                        let cellColor = "text-slate-400";
                        let bgClass = isWeekend ? "bg-slate-50" : "";
                        
                        if (cellData) {
                          if (cellData.status === "unmarked") {
                            cellContent = "M"; // Missing
                            cellColor = "text-slate-300";
                          } else {
                            // Show hours or status
                            if (cellData.attendance_status === "present") {
                              cellContent = "P";
                              cellColor = "text-emerald-600 font-bold";
                              bgClass = "bg-emerald-50/30";
                            } else if (cellData.attendance_status === "absent") {
                              cellContent = "A";
                              cellColor = "text-red-500 font-bold";
                              bgClass = "bg-red-50/30";
                            } else if (cellData.attendance_status === "half_day") {
                              cellContent = "HD";
                              cellColor = "text-amber-500 font-bold";
                              bgClass = "bg-amber-50/30";
                            } else if (cellData.attendance_status?.includes("leave")) {
                              cellContent = "L";
                              cellColor = "text-purple-500 font-bold";
                              bgClass = "bg-purple-50/30";
                            } else if (cellData.attendance_status === "holiday") {
                              cellContent = "H";
                              cellColor = "text-blue-500 font-bold";
                              bgClass = "bg-blue-50/30";
                            } else if (cellData.attendance_status === "weekend") {
                              cellContent = "W";
                              cellColor = "text-slate-500 font-bold";
                              bgClass = "bg-slate-100";
                            } else {
                              cellContent = cellData.marked_hours > 0 ? cellData.marked_hours.toString() : "-";
                              cellColor = "text-slate-700 font-medium";
                            }
                            
                            // Indicate if it's manual override / mismatch
                            if (cellData.reconciliation_status === "mismatch_warning" || cellData.reconciliation_status === "manual_override") {
                              cellContent += "*";
                              cellColor = "text-amber-600 font-black";
                            }
                          }
                        }

                        return (
                          <TableCell key={d} className={`text-center border-l border-slate-100/50 p-2 ${bgClass}`}>
                            <div className={`w-8 h-8 mx-auto flex items-center justify-center rounded-md ${cellColor}`}>
                              {cellContent}
                            </div>
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
