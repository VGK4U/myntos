"use client";

import { useEffect, useState } from "react";
import { useStaffAuth } from "@/components/providers/staff-auth-provider";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2, Plus, Search, Building, Users, IndianRupee } from "lucide-react";
import { toast } from "sonner";

interface PayrollProfile {
  id: number;
  employee_name: string;
  employee_code: string;
  company_name: string;
  employment_type: string;
  ctc_monthly: number;
  ctc_annual: number;
  is_active: boolean;
}

interface Company {
  id: number;
  name: string;
}

export default function PayrollPage() {
  const { user } = useStaffAuth();
  const [profiles, setProfiles] = useState<PayrollProfile[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCompany, setSelectedCompany] = useState<string>("all");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [profilesRes, companiesRes] = await Promise.all([
        api.get("/staff/payroll/profiles"),
        api.get("/staff/payroll/companies")
      ]);

      if (profilesRes.success) {
        setProfiles(profilesRes.data);
      }
      if (companiesRes.success) {
        setCompanies(companiesRes.companies);
      }
    } catch (error) {
      console.error("Error fetching payroll data:", error);
      toast.error("Failed to load payroll data");
    } finally {
      setLoading(false);
    }
  };

  const filteredProfiles = profiles.filter((profile) => {
    const matchesSearch = profile.employee_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          profile.employee_code.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCompany = selectedCompany === "all" || profile.company_name === selectedCompany;
    return matchesSearch && matchesCompany;
  });

  const totalMonthlyCtc = filteredProfiles.reduce((acc, curr) => acc + curr.ctc_monthly, 0);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Payroll Management</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Manage staff payroll profiles, cycles, and statutory details.</p>
        </div>
        <Button className="bg-primary text-white">
          <Plus className="mr-2 h-4 w-4" /> New Profile
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-slate-900 border-none shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-blue-600 dark:text-blue-400">Total Employees</CardTitle>
            <Users className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900 dark:text-white">{filteredProfiles.length}</div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Active payroll profiles</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-slate-800 dark:to-slate-900 border-none shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-green-600 dark:text-green-400">Monthly Run Rate</CardTitle>
            <IndianRupee className="h-4 w-4 text-green-600 dark:text-green-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              ₹{(totalMonthlyCtc / 100000).toFixed(2)}L
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Total monthly CTC</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-fuchsia-50 dark:from-slate-800 dark:to-slate-900 border-none shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-purple-600 dark:text-purple-400">Companies</CardTitle>
            <Building className="h-4 w-4 text-purple-600 dark:text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900 dark:text-white">{companies.length}</div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Accessible companies</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-gray-200 dark:border-gray-800 shadow-sm">
        <CardHeader className="border-b border-gray-100 dark:border-gray-800 pb-4">
          <div className="flex flex-col sm:flex-row justify-between gap-4 items-center">
            <CardTitle>Payroll Profiles</CardTitle>
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
                <Input
                  placeholder="Search employee..."
                  className="pl-9 bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                <SelectTrigger className="w-full sm:w-48 bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800">
                  <SelectValue placeholder="All Companies" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Companies</SelectItem>
                  {companies.map((c) => (
                    <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : filteredProfiles.length === 0 ? (
            <div className="flex flex-col justify-center items-center h-64 text-gray-500">
              <Users className="h-12 w-12 mb-4 text-gray-300 dark:text-gray-600" />
              <p className="text-lg font-medium">No profiles found</p>
              <p className="text-sm">Try adjusting your search or filters</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-gray-50 dark:bg-gray-900">
                  <TableRow>
                    <TableHead className="font-semibold">Employee</TableHead>
                    <TableHead className="font-semibold">Company</TableHead>
                    <TableHead className="font-semibold">Type</TableHead>
                    <TableHead className="font-semibold text-right">Monthly CTC</TableHead>
                    <TableHead className="font-semibold text-right">Annual CTC</TableHead>
                    <TableHead className="font-semibold text-center">Status</TableHead>
                    <TableHead className="text-right font-semibold">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredProfiles.map((profile) => (
                    <TableRow key={profile.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-medium text-gray-900 dark:text-gray-100">{profile.employee_name}</span>
                          <span className="text-xs text-gray-500">{profile.employee_code}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border-none">
                          {profile.company_name}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">{profile.employment_type}</span>
                      </TableCell>
                      <TableCell className="text-right font-medium text-gray-900 dark:text-gray-100">
                        ₹{profile.ctc_monthly.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right text-gray-500">
                        ₹{profile.ctc_annual.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant={profile.is_active ? "default" : "secondary"} className={profile.is_active ? "bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400" : ""}>
                          {profile.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/30">
                          View
                        </Button>
                      </TableCell>
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
