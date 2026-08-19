"use client";

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Download, Check, X, Edit, Trash } from 'lucide-react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function CustomPage() {
  const { data, error, isLoading } = useSWR('/staff/mnr/expenses-management', fetcher);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const handleApprove = (id: string) => {
    console.log(`Approving ${id}`);
    // add API call here
  };

  const handleReject = (id: string) => {
    console.log(`Rejecting ${id}`);
    // add API call here
  };

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Expenses Management</h1>
          <p className="text-sm text-gray-500 mt-1">Auto-mapped data viewer for staff/mnr/expenses-management</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" className="flex items-center gap-2">
            <Download className="w-4 h-4" /> Export
          </Button>
          <Button className="flex items-center gap-2">
            Primary Action
          </Button>
        </div>
      </div>

      <Card className="shadow-sm border-gray-200">
        <CardHeader className="bg-white border-b border-gray-100">
          <CardTitle>Data Overview</CardTitle>
          <CardDescription>Manage your {title.toLowerCase()} records here.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-gray-50/50">
                <TableRow>
                  <TableHead className="w-[50px]">ID</TableHead>
                  <TableHead>Details</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-gray-500">Loading data...</TableCell>
                  </TableRow>
                ) : error ? (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-red-500">Failed to load data</TableCell>
                  </TableRow>
                ) : data && data.items && data.items.length > 0 ? (
                  data.items.map((item: any) => (
                    <TableRow key={item.id} className="hover:bg-gray-50/50 transition-colors">
                      <TableCell className="font-medium text-gray-900">{item.id}</TableCell>
                      <TableCell className="text-gray-600">{item.name || 'N/A'}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-blue-50 text-blue-700 hover:bg-blue-100">
                          {item.status || 'Active'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end space-x-2">
                          <Button size="sm" variant="ghost" onClick={() => handleApprove(item.id)} className="text-green-600 hover:text-green-700 hover:bg-green-50">
                            <Check className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleReject(item.id)} className="text-red-600 hover:text-red-700 hover:bg-red-50">
                            <X className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="ghost" className="text-gray-600 hover:text-gray-900 hover:bg-gray-100">
                            <Edit className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-gray-500">No records found.</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
