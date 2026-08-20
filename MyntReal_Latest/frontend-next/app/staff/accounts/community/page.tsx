"use client";

import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import api from '@/lib/api';
import { useStaffAuth } from '@/contexts/StaffAuthContext';
import { Users, CheckCircle, Award, Handshake, RefreshCw, Copy, Check, X, FileText, Edit, Play, Pause, Trash, PlusCircle, ListCheck } from 'lucide-react';
import { toast } from 'sonner';

interface Registration {
  id: number;
  user_partner_code: string;
  association_name: string;
  primary_name: string;
  primary_phone_1: string;
  service_name: string;
  area: string;
  district: string;
  state: string;
  pin_code: string;
  referral_type: string;
  ref1_name: string;
  ref1_code: string;
  ref1_member_id: string;
  kyc_documents: string[];
  status: string;
}

interface Service {
  id: number;
  service_name: string;
  short_name: string;
  start_date: string;
  end_date: string;
  applicable_verticals: string[];
  banner_images: string[];
  status: string;
}

export default function CommunityServicesPage() {
  const { user } = useStaffAuth();
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [loadingRegs, setLoadingRegs] = useState(true);
  const [loadingServices, setLoadingServices] = useState(true);

  // Form states for creating a new service
  const [newService, setNewService] = useState({
    service_name: '',
    short_name: '',
    description: '',
    start_date: '',
    end_date: '',
    applicable_verticals: ['Solar']
  });

  const fetchRegistrations = async () => {
    setLoadingRegs(true);
    try {
      const res = await api.get('/community-services/admin/registrations');
      if (res.data.success) {
        setRegistrations(res.data.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingRegs(false);
    }
  };

  const fetchServices = async () => {
    setLoadingServices(true);
    try {
      const res = await api.get('/community-services/admin/services');
      if (res.data.success) {
        setServices(res.data.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingServices(false);
    }
  };

  useEffect(() => {
    fetchRegistrations();
    fetchServices();
  }, []);

  const handleApprove = async (id: number) => {
    if (!confirm('Are you sure you want to approve this registration?')) return;
    try {
      const res = await api.post(`/community-services/admin/registrations/${id}/approve`);
      if (res.data.success) {
        if (typeof toast !== 'undefined' && toast.success) toast.success('Registration approved successfully');
        fetchRegistrations();
      }
    } catch (e) {
      console.error(e);
      if (typeof toast !== 'undefined' && toast.error) toast.error('Approval failed');
    }
  };

  const handleReject = async (id: number) => {
    if (!confirm('Are you sure you want to reject this registration?')) return;
    try {
      const res = await api.post(`/community-services/admin/registrations/${id}/reject`);
      if (res.data.success) {
        if (typeof toast !== 'undefined' && toast.success) toast.success('Registration rejected');
        fetchRegistrations();
      }
    } catch (e) {
      console.error(e);
      if (typeof toast !== 'undefined' && toast.error) toast.error('Rejection failed');
    }
  };

  const handleCreateService = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Dummy formData generation just as a skeleton to map what was needed
      const formData = new FormData();
      formData.append('service_name', newService.service_name);
      formData.append('short_name', newService.short_name);
      formData.append('description', newService.description);
      formData.append('start_date', newService.start_date);
      formData.append('end_date', newService.end_date);
      formData.append('applicable_verticals', JSON.stringify(newService.applicable_verticals));

      const res = await api.post('/community-services/admin/services', formData);
      if (res.data.success) {
        if (typeof toast !== 'undefined' && toast.success) toast.success('Service created successfully');
        fetchServices();
        setNewService({
          service_name: '', short_name: '', description: '', start_date: '', end_date: '', applicable_verticals: ['Solar']
        });
      }
    } catch (e) {
      console.error(e);
      if (typeof toast !== 'undefined' && toast.error) toast.error('Failed to create service');
    }
  };

  const handleVerticalToggle = (val: string) => {
    setNewService(prev => ({
      ...prev,
      applicable_verticals: prev.applicable_verticals.includes(val) 
        ? prev.applicable_verticals.filter(v => v !== val)
        : [...prev.applicable_verticals, val]
    }));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    if (typeof toast !== 'undefined' && toast.success) toast.success('Copied to clipboard');
  };

  const pendingRegs = registrations.filter(r => r.status === 'PENDING').length;
  const approvedRegs = registrations.filter(r => r.status === 'APPROVED').length;
  const activeServices = services.filter(s => s.status === 'ACTIVE').length;

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-gradient-to-br from-violet-600 to-purple-800 rounded-xl p-6 text-white shadow-lg flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Handshake className="h-6 w-6" />
            Community Services Seva Manager
          </h1>
          <p className="opacity-90 mt-1 text-sm">
            Configure seva schemas, manage partner registrations, verify documents, and track seva ledger releases.
          </p>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-slate-200">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="bg-violet-100 p-3 rounded-xl text-violet-600">
              <Users className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{pendingRegs}</div>
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-1">Pending Approvals</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200">
          <CardContent className="p-6 flex items-center gap-4 bg-emerald-50/50">
            <div className="bg-emerald-100 p-3 rounded-xl text-emerald-600">
              <CheckCircle className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{approvedRegs}</div>
              <div className="text-xs font-bold text-emerald-700 uppercase tracking-wider mt-1">Approved Communities</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-amber-200">
          <CardContent className="p-6 flex items-center gap-4 bg-amber-50/50">
            <div className="bg-amber-100 p-3 rounded-xl text-amber-600">
              <Award className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{activeServices}</div>
              <div className="text-xs font-bold text-amber-700 uppercase tracking-wider mt-1">Active Services</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs Section */}
      <Tabs defaultValue="reg" className="w-full">
        <TabsList className="w-full justify-start p-1 bg-white border h-auto flex-wrap gap-1 rounded-lg">
          <TabsTrigger value="reg" className="flex-1 py-2.5 data-[state=active]:bg-violet-600 data-[state=active]:text-white rounded-md text-sm font-semibold transition-all">
            <Users className="h-4 w-4 mr-2" />
            Registrations Approvals
          </TabsTrigger>
          <TabsTrigger value="service" className="flex-1 py-2.5 data-[state=active]:bg-violet-600 data-[state=active]:text-white rounded-md text-sm font-semibold transition-all">
            <PlusCircle className="h-4 w-4 mr-2" />
            Configure Seva Service
          </TabsTrigger>
          <TabsTrigger value="list" className="flex-1 py-2.5 data-[state=active]:bg-violet-600 data-[state=active]:text-white rounded-md text-sm font-semibold transition-all">
            <ListCheck className="h-4 w-4 mr-2" />
            Active Services List
          </TabsTrigger>
        </TabsList>

        <TabsContent value="reg" className="mt-6">
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between bg-slate-50/80 border-b pb-4 pt-4 rounded-t-xl">
              <CardTitle className="text-base font-bold flex items-center gap-2 text-slate-800">
                <Users className="h-5 w-5 text-violet-600" />
                Inbound Registrations Queue
              </CardTitle>
              <Button variant="outline" size="sm" onClick={fetchRegistrations} className="h-8">
                <RefreshCw className="h-3.5 w-3.5 mr-2" />
                Refresh
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-slate-50/50">
                    <TableRow>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">ID</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Login ID</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Community Details</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Service Schema</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Area / Location</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Referral CPs</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Documents</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Status</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500 text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loadingRegs ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-8 text-slate-500">
                          <div className="flex justify-center items-center gap-2">
                            <RefreshCw className="h-4 w-4 animate-spin" /> Loading registrations...
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : registrations.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-8 text-slate-500">No community registrations submitted yet.</TableCell>
                      </TableRow>
                    ) : registrations.map(r => (
                      <TableRow key={r.id} className="hover:bg-slate-50/80">
                        <TableCell className="font-semibold text-slate-900">#{r.id}</TableCell>
                        <TableCell>
                          {r.user_partner_code ? (
                            <Badge variant="outline" className="cursor-pointer bg-slate-50 hover:bg-slate-100 font-mono text-xs border-slate-300 transition-colors" onClick={() => copyToClipboard(r.user_partner_code)}>
                              {r.user_partner_code} <Copy className="h-3 w-3 ml-1.5 text-slate-400" />
                            </Badge>
                          ) : <span className="text-slate-400">—</span>}
                        </TableCell>
                        <TableCell>
                          <div className="font-bold text-slate-900 text-sm">{r.association_name || 'N/A'}</div>
                          <div className="text-[13px] text-slate-500 mt-0.5">Rep: {r.primary_name}</div>
                          <div className="text-[13px] text-slate-500">{r.primary_phone_1}</div>
                        </TableCell>
                        <TableCell><Badge variant="secondary" className="bg-slate-100 text-slate-700 hover:bg-slate-200">{r.service_name || 'N/A'}</Badge></TableCell>
                        <TableCell>
                          <div className="text-sm text-slate-800">{r.area}</div>
                          <div className="text-[12px] text-slate-500 mt-0.5">{r.district}, {r.state} ({r.pin_code})</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-[11px] font-bold text-violet-600">{r.referral_type?.toUpperCase().replace('_', ' ') || 'DIRECT'}</div>
                          <div className="text-[13px] text-slate-600 mt-0.5">{r.ref1_name || '—'}</div>
                          <div className="text-[12px] font-mono font-medium text-slate-500">{r.ref1_code || (r.ref1_member_id ? `CP #${r.ref1_member_id}` : '—')}</div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {r.kyc_documents?.length > 0 ? (
                              r.kyc_documents.map((doc, idx) => (
                                <a key={idx} href={`/storage/${doc}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[11px] font-medium border border-sky-200 px-2 py-1 rounded bg-sky-50 text-sky-700 hover:bg-sky-100 transition-colors">
                                  <FileText className="h-3 w-3" /> Doc {idx + 1}
                                </a>
                              ))
                            ) : <span className="text-slate-400 text-xs font-medium">None</span>}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`
                            ${r.status === 'PENDING' ? 'bg-amber-50 text-amber-700 border-amber-200' : ''}
                            ${r.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : ''}
                            ${r.status === 'REJECTED' ? 'bg-red-50 text-red-700 border-red-200' : ''}
                          `}>
                            {r.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {r.status === 'PENDING' ? (
                            <div className="flex justify-end gap-1.5">
                              <Button size="sm" variant="outline" className="h-7 text-xs bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100 hover:text-emerald-800 transition-colors" onClick={() => handleApprove(r.id)}>
                                <Check className="h-3.5 w-3.5 mr-1" /> Approve
                              </Button>
                              <Button size="sm" variant="outline" className="h-7 text-xs bg-red-50 text-red-700 border-red-200 hover:bg-red-100 hover:text-red-800 transition-colors" onClick={() => handleReject(r.id)}>
                                <X className="h-3.5 w-3.5 mr-1" /> Reject
                              </Button>
                              <Button size="sm" variant="outline" className="h-7 px-2 text-violet-700 border-violet-200 hover:bg-violet-50 transition-colors">
                                <Edit className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center justify-end gap-2">
                              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mr-1">Processed</span>
                              <Button size="sm" variant="outline" className="h-7 px-2 text-violet-700 border-violet-200 hover:bg-violet-50 transition-colors">
                                <Edit className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="service" className="mt-6">
          <Card className="max-w-4xl mx-auto shadow-sm border-slate-200">
            <CardHeader className="border-b bg-slate-50/50 pb-4 pt-5">
              <CardTitle className="flex items-center gap-2 text-lg text-slate-800">
                <PlusCircle className="h-5 w-5 text-violet-600" />
                Create New Seva Schema
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <form className="space-y-6" onSubmit={handleCreateService}>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div className="col-span-2 space-y-2.5">
                    <Label className="text-slate-700 font-semibold">Service Name <span className="text-red-500">*</span></Label>
                    <Input 
                      placeholder="e.g. Ganesh Utsav Seva 2026" 
                      required 
                      value={newService.service_name}
                      onChange={e => setNewService({...newService, service_name: e.target.value})}
                      className="focus-visible:ring-violet-500"
                    />
                  </div>
                  <div className="space-y-2.5">
                    <Label className="text-slate-700 font-semibold">Short Name <span className="text-red-500">*</span></Label>
                    <Input 
                      placeholder="e.g. GANESH26" 
                      required 
                      value={newService.short_name}
                      onChange={e => setNewService({...newService, short_name: e.target.value})}
                      className="focus-visible:ring-violet-500"
                    />
                  </div>
                </div>

                <div className="space-y-2.5">
                  <Label className="text-slate-700 font-semibold">Description (Markdown / Rich content)</Label>
                  <Textarea 
                    placeholder="Specify Seva guidelines, rules, and payout policies..." 
                    rows={4}
                    value={newService.description}
                    onChange={e => setNewService({...newService, description: e.target.value})}
                    className="focus-visible:ring-violet-500 resize-none"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-2.5">
                    <Label className="text-slate-700 font-semibold">Start Date <span className="text-red-500">*</span></Label>
                    <Input 
                      type="date" 
                      required 
                      value={newService.start_date}
                      onChange={e => setNewService({...newService, start_date: e.target.value})}
                      className="focus-visible:ring-violet-500"
                    />
                  </div>
                  <div className="space-y-2.5">
                    <Label className="text-slate-700 font-semibold">End Date <span className="text-red-500">*</span></Label>
                    <Input 
                      type="date" 
                      required 
                      value={newService.end_date}
                      onChange={e => setNewService({...newService, end_date: e.target.value})}
                      className="focus-visible:ring-violet-500"
                    />
                  </div>
                </div>

                <div className="space-y-3 p-4 bg-slate-50 border border-slate-100 rounded-lg">
                  <Label className="text-slate-700 font-semibold block mb-1">Applicable Verticals</Label>
                  <div className="flex flex-wrap gap-6">
                    {['Solar', 'EV', 'Spares'].map(vert => (
                      <div key={vert} className="flex items-center space-x-2">
                        <Checkbox 
                          id={`vert-${vert}`} 
                          checked={newService.applicable_verticals.includes(vert)}
                          onCheckedChange={() => handleVerticalToggle(vert)}
                          className="data-[state=checked]:bg-violet-600 data-[state=checked]:border-violet-600"
                        />
                        <label 
                          htmlFor={`vert-${vert}`} 
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-slate-700 cursor-pointer"
                        >
                          {vert === 'EV' ? 'EV Scooter' : vert === 'Spares' ? 'EV Spares' : vert}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-5 border-t border-slate-100">
                  <Button variant="outline" type="reset" onClick={() => setNewService({service_name: '', short_name: '', description: '', start_date: '', end_date: '', applicable_verticals: ['Solar']})}>
                    Reset Form
                  </Button>
                  <Button type="submit" className="bg-violet-600 hover:bg-violet-700 text-white shadow-sm transition-colors">
                    Save Seva Service
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="list" className="mt-6">
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="bg-slate-50/80 border-b pb-4 pt-4 rounded-t-xl">
              <CardTitle className="text-base font-bold flex items-center gap-2 text-slate-800">
                <ListCheck className="h-5 w-5 text-violet-600" />
                Configured Seva Services
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-slate-50/50">
                    <TableRow>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">ID</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Service Name</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Short Name</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Duration</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Verticals</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Banners</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500">Status</TableHead>
                      <TableHead className="text-xs font-bold uppercase text-slate-500 text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loadingServices ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-slate-500">
                           <div className="flex justify-center items-center gap-2">
                             <RefreshCw className="h-4 w-4 animate-spin" /> Loading services...
                           </div>
                        </TableCell>
                      </TableRow>
                    ) : services.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-slate-500">No community services configured yet.</TableCell>
                      </TableRow>
                    ) : services.map(s => (
                      <TableRow key={s.id} className="hover:bg-slate-50/80">
                        <TableCell className="font-semibold text-slate-900">#{s.id}</TableCell>
                        <TableCell className="font-bold text-slate-900 text-sm">{s.service_name}</TableCell>
                        <TableCell>
                          <code className="bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs font-bold font-mono border border-slate-200">{s.short_name}</code>
                        </TableCell>
                        <TableCell>
                          <div className="text-[13px] text-slate-700 font-medium">{new Date(s.start_date).toLocaleDateString('en-IN')} to {new Date(s.end_date).toLocaleDateString('en-IN')}</div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {s.applicable_verticals?.map(v => (
                              <Badge key={v} variant="secondary" className="bg-violet-100 text-violet-800 hover:bg-violet-200 text-[10px] uppercase tracking-wider">{v}</Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          {s.banner_images?.length > 0 ? (
                            <Badge variant="outline" className="bg-sky-50 text-sky-700 border-sky-200">
                              {s.banner_images.length} Banners
                            </Badge>
                          ) : <span className="text-slate-400 text-xs font-medium">None</span>}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={s.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}>
                            {s.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1.5">
                            <Button size="sm" variant="outline" className="h-7 px-2 text-violet-700 border-violet-200 hover:bg-violet-50 transition-colors">
                              <Edit className="h-3.5 w-3.5" />
                            </Button>
                            <Button size="sm" variant="outline" className="h-7 px-2 text-amber-700 border-amber-200 hover:bg-amber-50 transition-colors" title={s.status === 'ACTIVE' ? "Pause" : "Resume"}>
                              {s.status === 'ACTIVE' ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                            </Button>
                            <Button size="sm" variant="outline" className="h-7 px-2 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700 transition-colors">
                              <Trash className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
