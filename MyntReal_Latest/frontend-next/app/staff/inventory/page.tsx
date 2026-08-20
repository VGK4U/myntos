"use client";

import React, { useState, useEffect } from "react";
import { useStaffAuth } from "@/components/staff/StaffAuthProvider";
import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";

export default function InventoryDispatchPage() {
  const { user } = useStaffAuth();
  const [activeTab, setActiveTab] = useState("battery");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData(activeTab);
  }, [activeTab]);

  const fetchData = async (type: string) => {
    setLoading(true);
    try {
      const response = await api.get(`/staff/inventory/dispatch/${type}`);
      setData(response.items || []);
    } catch (error) {
      console.error(`Failed to fetch ${type} dispatch data`, error);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    if (!status) return null;
    const lower = status.toLowerCase();
    if (lower === "dispatched" || lower === "delivered") return <Badge className="bg-green-500">{status}</Badge>;
    if (lower === "pending") return <Badge variant="secondary">{status}</Badge>;
    return <Badge variant="outline">{status}</Badge>;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Inventory Management</h1>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="battery">Batteries</TabsTrigger>
          <TabsTrigger value="vehicle">Vehicles</TabsTrigger>
          <TabsTrigger value="charger">Chargers</TabsTrigger>
        </TabsList>

        <Card className="mt-6 border-0 shadow-sm ring-1 ring-slate-200/50">
          <CardHeader className="bg-slate-50/50 border-b pb-4">
            <CardTitle className="text-xl">
              {activeTab === "battery" ? "Battery Dispatch Records" :
               activeTab === "vehicle" ? "Vehicle Dispatch Records" :
               "Charger Dispatch Records"}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-8 text-center text-muted-foreground animate-pulse">Loading dispatch data...</div>
            ) : data.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">No records found.</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-slate-50/50">
                    <TableRow>
                      <TableHead>Dispatch Date</TableHead>
                      {activeTab === "vehicle" && <TableHead>Vehicle No.</TableHead>}
                      {activeTab === "vehicle" && <TableHead>Model & Color</TableHead>}
                      {activeTab === "battery" && <TableHead>Serial No.</TableHead>}
                      {activeTab === "battery" && <TableHead>Battery Spec</TableHead>}
                      {activeTab === "charger" && <TableHead>Charger No.</TableHead>}
                      {activeTab === "charger" && <TableHead>Charger Spec</TableHead>}
                      <TableHead>Vendor</TableHead>
                      <TableHead>Invoice No.</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.map((item) => (
                      <TableRow key={item.id} className="hover:bg-slate-50/50 transition-colors">
                        <TableCell>
                          {item.dispatch_date ? format(new Date(item.dispatch_date), "dd MMM yyyy") : "-"}
                        </TableCell>
                        
                        {activeTab === "vehicle" && (
                          <>
                            <TableCell className="font-medium">{item.vehicle_no || "-"}</TableCell>
                            <TableCell>{item.vehicle_model} {item.vehicle_color ? `(${item.vehicle_color})` : ""}</TableCell>
                          </>
                        )}

                        {activeTab === "battery" && (
                          <>
                            <TableCell className="font-medium">{item.battery_serial_no || "-"}</TableCell>
                            <TableCell>{item.battery_spec || "-"}</TableCell>
                          </>
                        )}

                        {activeTab === "charger" && (
                          <>
                            <TableCell className="font-medium">{item.charger_no || "-"}</TableCell>
                            <TableCell>{item.charger_spec || "-"}</TableCell>
                          </>
                        )}

                        <TableCell>{item.vendor_code || "-"}</TableCell>
                        <TableCell>{item.vendor_invoice_no || item.sales_invoice_no || "-"}</TableCell>
                        <TableCell>{getStatusBadge(item.status)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </Tabs>
    </div>
  );
}
