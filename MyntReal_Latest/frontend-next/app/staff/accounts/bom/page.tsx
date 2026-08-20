"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Plus,
  Search,
  Filter,
  Loader2,
  FileText,
  AlertTriangle,
} from "lucide-react";

interface BOMEntry {
  id: number;
  bom_code: string;
  bom_name: string;
  finished_product_name: string;
  company_name: string;
  estimated_cost: number;
  status: string;
  created_at?: string;
  components_count?: number;
}

export default function BOMPage() {
  const { token } = useStaffAuth();
  const [boms, setBoms] = useState<BOMEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    if (!token) return;

    const fetchBOMs = async () => {
      try {
        setLoading(true);
        setError("");
        const res = await api.get("/staff/accounts/boms");
        if (res.data && res.data.boms) {
          setBoms(res.data.boms);
        } else if (res.data && Array.isArray(res.data)) {
          setBoms(res.data);
        } else if (res.data?.items) {
          setBoms(res.data.items);
        } else {
          setBoms([]);
        }
      } catch (err: any) {
        console.warn("Failed to fetch BOMs", err);
        setError("Failed to load Bill of Materials. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    fetchBOMs();
  }, [token]);

  const filteredBOMs = useMemo(() => {
    return boms.filter((b) => {
      const matchesSearch =
        b.bom_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        b.bom_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        b.finished_product_name?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesStatus =
        statusFilter === "all" || b.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [boms, searchTerm, statusFilter]);

  const formatCurrency = (amt: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
    }).format(amt || 0);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return <Badge variant="default" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">{status}</Badge>;
      case "DRAFT":
        return <Badge variant="outline" className="bg-amber-100 text-amber-800 border-none">{status}</Badge>;
      case "PENDING_APPROVAL":
        return <Badge variant="secondary" className="bg-blue-100 text-blue-800">{status}</Badge>;
      case "REJECTED":
        return <Badge variant="destructive" className="bg-red-100 text-red-800 hover:bg-red-100">{status}</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const summary = {
    total: boms.length,
    approved: boms.filter((b) => b.status === "APPROVED").length,
    drafts: boms.filter((b) => b.status === "DRAFT").length,
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
            Bill of Materials
          </h1>
          <p className="text-sm text-gray-500 mt-2">
            Create and manage product recipes with components
          </p>
        </div>
        <div className="flex space-x-3">
          <Button asChild>
            <Link href="/staff/accounts/bom/create">
              <Plus className="mr-2 h-4 w-4" /> Create BOM
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="shadow-sm border-l-4 border-l-primary">
          <CardContent className="p-6">
            <p className="text-xs font-bold text-muted-foreground uppercase">Total BOMs</p>
            <p className="text-3xl font-bold text-foreground mt-2">{summary.total}</p>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-l-4 border-l-emerald-500">
          <CardContent className="p-6">
            <p className="text-xs font-bold text-muted-foreground uppercase">Approved</p>
            <p className="text-3xl font-bold text-emerald-600 mt-2">{summary.approved}</p>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-l-4 border-l-amber-500">
          <CardContent className="p-6">
            <p className="text-xs font-bold text-muted-foreground uppercase">Drafts</p>
            <p className="text-3xl font-bold text-amber-600 mt-2">{summary.drafts}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-sm border-gray-200">
        <CardHeader className="bg-gray-50/50 border-b pb-4 pt-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5 text-gray-500" />
              <CardTitle className="text-lg">BOM Records</CardTitle>
              <Badge variant="secondary" className="ml-2 font-normal">
                {filteredBOMs.length} records
              </Badge>
            </div>
            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search BOMs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-white"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[140px] bg-white">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="APPROVED">Approved</SelectItem>
                  <SelectItem value="DRAFT">Draft</SelectItem>
                  <SelectItem value="PENDING_APPROVAL">Pending</SelectItem>
                  <SelectItem value="REJECTED">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex flex-col justify-center items-center h-64 text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
              <p>Loading Bill of Materials...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col justify-center items-center h-64 text-red-500">
              <AlertTriangle className="h-8 w-8 mb-4" />
              <p>{error}</p>
            </div>
          ) : filteredBOMs.length === 0 ? (
            <div className="flex flex-col justify-center items-center h-64 text-muted-foreground">
              <FileText className="h-12 w-12 mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900 mb-1">No BOMs found</h3>
              <p className="text-sm">Create your first Bill of Materials to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-gray-50">
                  <TableRow>
                    <TableHead className="font-semibold text-gray-600">BOM Code</TableHead>
                    <TableHead className="font-semibold text-gray-600">Name</TableHead>
                    <TableHead className="font-semibold text-gray-600">Product</TableHead>
                    <TableHead className="font-semibold text-gray-600">Company</TableHead>
                    <TableHead className="font-semibold text-gray-600 text-right">Est. Cost</TableHead>
                    <TableHead className="font-semibold text-gray-600 text-center">Status</TableHead>
                    <TableHead className="font-semibold text-gray-600 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredBOMs.map((bom) => (
                    <TableRow key={bom.id} className="hover:bg-gray-50/50">
                      <TableCell className="font-medium text-primary">
                        {bom.bom_code}
                      </TableCell>
                      <TableCell className="font-medium">{bom.bom_name}</TableCell>
                      <TableCell className="text-gray-600">
                        {bom.finished_product_name}
                      </TableCell>
                      <TableCell className="text-gray-600">
                        {bom.company_name}
                      </TableCell>
                      <TableCell className="text-right font-mono font-medium">
                        {formatCurrency(bom.estimated_cost)}
                      </TableCell>
                      <TableCell className="text-center">
                        {getStatusBadge(bom.status)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                          className="text-primary hover:text-primary/80"
                        >
                          <Link href={`/staff/accounts/bom/${bom.id}`}>View / Edit</Link>
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
