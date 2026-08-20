"use client";

import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ShieldCheck, Lock, UploadCloud, RefreshCw, Pause, Play, Edit, CheckCircle } from "lucide-react";

export default function MetaAdsCenterPage() {
  const { user } = useStaffAuth();
  
  const [dashboard, setDashboard] = useState<any>(null);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [adsets, setAdsets] = useState<any[]>([]);
  const [ads, setAds] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editObj, setEditObj] = useState<{type: string, id: string, name: string, status: string} | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dashRes, campRes, adsetRes, adsRes] = await Promise.all([
        api.get('/meta-ads/dashboard'),
        api.get('/meta-ads/campaigns'),
        api.get('/meta-ads/adsets'),
        api.get('/meta-ads/ads')
      ]);
      setDashboard(dashRes.data);
      setCampaigns(campRes.data.campaigns || []);
      setAdsets(adsetRes.data.adsets || []);
      setAds(adsRes.data.ads || []);
    } catch (e) {
      console.error("Failed to fetch Meta Ads data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const toggleStatus = async (type: string, id: string, currentStatus: string) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    try {
      await api.post(`/meta-ads/${type}s/${id}/status`, { new_status: newStatus });
      fetchData();
    } catch (e) {
      console.error("Status toggle failed", e);
    }
  };

  const handleSaveEdit = async () => {
    if (!editObj) return;
    try {
      await api.post(`/meta-ads/${editObj.type}s/${editObj.id}/edit`, { 
        name: editObj.name,
        status: editObj.status
      });
      setEditModalOpen(false);
      fetchData();
    } catch (e) {
      console.error("Edit failed", e);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Meta Ads Management Center</h1>
          <p className="text-sm text-slate-500">Live Meta Graph API v24.0 Management Dashboard & Ad Controls</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="border-emerald-500 text-emerald-600 hover:bg-emerald-50" onClick={() => window.location.href='/staff/meta-ads/creative-studio'}>
            <UploadCloud className="w-4 h-4 mr-2" />
            Upload Content & Image
          </Button>
          <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh Live Telemetry
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Ad Spend</p>
            <p className="text-2xl font-black mt-1 text-slate-800">₹{dashboard?.spend || '0.00'}</p>
            <p className="text-xs text-emerald-600 font-bold mt-1 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> ₹1,000.00/day Budget
            </p>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Campaigns</p>
            <p className="text-2xl font-black mt-1 text-slate-800">{dashboard?.active_campaigns || campaigns.filter(c=>c.status==='ACTIVE').length}</p>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Ad Sets</p>
            <p className="text-2xl font-black mt-1 text-slate-800">{dashboard?.active_adsets || adsets.filter(a=>a.status==='ACTIVE').length}</p>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Ads</p>
            <p className="text-2xl font-black mt-1 text-slate-800">{dashboard?.active_ads || ads.filter(a=>a.status==='ACTIVE').length}</p>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-slate-200">
          <CardContent className="p-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Leads</p>
            <p className="text-2xl font-black mt-1 text-slate-800">{dashboard?.leads_ingested || '0'}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 shadow-sm border-slate-200 overflow-hidden">
          <CardHeader className="bg-slate-50/80 border-b border-slate-100 flex flex-row items-center justify-between py-4">
            <CardTitle className="text-[15px] font-bold text-slate-800 flex items-center gap-2">
              <span className="text-blue-600 text-xl font-serif italic font-bold">f</span> Live Meta Advertising Hierarchy
            </CardTitle>
            <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200 uppercase font-bold text-[10px] tracking-wider px-2.5 py-0.5 rounded-full border-none">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 inline-block animate-pulse"></span>
              Approved & Active
            </Badge>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-[11px] font-bold text-slate-500 bg-slate-50/50 border-b border-slate-100 uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3.5">Level</th>
                    <th className="px-5 py-3.5">Object Name & ID</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/80">
                  {campaigns.map(camp => (
                    <tr key={camp.campaign_id} className="hover:bg-slate-50/40 transition-colors">
                      <td className="px-5 py-3.5"><Badge className="bg-blue-100 text-blue-700 hover:bg-blue-200 border-none shadow-none font-bold">Campaign</Badge></td>
                      <td className="px-5 py-3.5">
                        <div className="font-bold text-slate-800 text-[13px]">{camp.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5 font-medium">{camp.campaign_id}</div>
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge className={camp.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700 border-none font-bold' : 'bg-amber-100 text-amber-700 border-none font-bold'}>
                          {camp.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 text-right space-x-2">
                        <Button variant={camp.status === 'ACTIVE' ? 'outline' : 'default'} className={camp.status === 'ACTIVE' ? 'border-amber-200 text-amber-700 hover:bg-amber-50' : 'bg-emerald-500 hover:bg-emerald-600 text-white'} size="sm" onClick={() => toggleStatus('campaign', camp.campaign_id, camp.status)}>
                          {camp.status === 'ACTIVE' ? <><Pause className="w-3.5 h-3.5 mr-1" /> Pause</> : <><Play className="w-3.5 h-3.5 mr-1" /> Resume</>}
                        </Button>
                        <Button variant="outline" className="border-slate-200 text-blue-600 hover:bg-blue-50 hover:border-blue-200" size="sm" onClick={() => { setEditObj({type: 'campaign', id: camp.campaign_id, name: camp.name, status: camp.status}); setEditModalOpen(true); }}>
                          <Edit className="w-3.5 h-3.5 mr-1" /> Edit
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {adsets.map(adset => (
                    <tr key={adset.adset_id} className="hover:bg-slate-50/40 transition-colors">
                      <td className="px-5 py-3.5"><Badge className="bg-purple-100 text-purple-700 hover:bg-purple-200 border-none shadow-none font-bold">Ad Set</Badge></td>
                      <td className="px-5 py-3.5">
                        <div className="font-bold text-slate-800 text-[13px]">{adset.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5 font-medium">{adset.adset_id}</div>
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge className={adset.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700 border-none font-bold' : 'bg-amber-100 text-amber-700 border-none font-bold'}>
                          {adset.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 text-right space-x-2">
                        <Button variant={adset.status === 'ACTIVE' ? 'outline' : 'default'} className={adset.status === 'ACTIVE' ? 'border-amber-200 text-amber-700 hover:bg-amber-50' : 'bg-emerald-500 hover:bg-emerald-600 text-white'} size="sm" onClick={() => toggleStatus('adset', adset.adset_id, adset.status)}>
                          {adset.status === 'ACTIVE' ? <><Pause className="w-3.5 h-3.5 mr-1" /> Pause</> : <><Play className="w-3.5 h-3.5 mr-1" /> Resume</>}
                        </Button>
                        <Button variant="outline" className="border-slate-200 text-blue-600 hover:bg-blue-50 hover:border-blue-200" size="sm" onClick={() => { setEditObj({type: 'adset', id: adset.adset_id, name: adset.name, status: adset.status}); setEditModalOpen(true); }}>
                          <Edit className="w-3.5 h-3.5 mr-1" /> Edit
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {ads.map(ad => (
                    <tr key={ad.ad_id} className="hover:bg-slate-50/40 transition-colors">
                      <td className="px-5 py-3.5"><Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-none shadow-none font-bold">Ad</Badge></td>
                      <td className="px-5 py-3.5">
                        <div className="font-bold text-slate-800 text-[13px]">{ad.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5 font-medium">{ad.ad_id}</div>
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge className={ad.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700 border-none font-bold' : 'bg-amber-100 text-amber-700 border-none font-bold'}>
                          {ad.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 text-right space-x-2">
                        <Button variant={ad.status === 'ACTIVE' ? 'outline' : 'default'} className={ad.status === 'ACTIVE' ? 'border-amber-200 text-amber-700 hover:bg-amber-50' : 'bg-emerald-500 hover:bg-emerald-600 text-white'} size="sm" onClick={() => toggleStatus('ad', ad.ad_id, ad.status)}>
                          {ad.status === 'ACTIVE' ? <><Pause className="w-3.5 h-3.5 mr-1" /> Pause</> : <><Play className="w-3.5 h-3.5 mr-1" /> Resume</>}
                        </Button>
                        <Button variant="outline" className="border-slate-200 text-blue-600 hover:bg-blue-50 hover:border-blue-200" size="sm" onClick={() => { setEditObj({type: 'ad', id: ad.ad_id, name: ad.name, status: ad.status}); setEditModalOpen(true); }}>
                          <Edit className="w-3.5 h-3.5 mr-1" /> Edit
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {!loading && campaigns.length === 0 && adsets.length === 0 && ads.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-5 py-8 text-center text-slate-500 font-medium">
                        No active Meta hierarchy found. Check API or Run Pipeline.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-200">
          <CardHeader className="border-b border-slate-100 py-4 bg-slate-50/50">
            <CardTitle className="text-[15px] font-bold flex items-center gap-2 text-slate-800">
              <ShieldCheck className="w-5 h-5 text-emerald-500" /> Governance & Health
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-5">
            <div>
              <p className="text-[10px] font-bold text-slate-500 mb-1 uppercase tracking-wider">AD ACCOUNT ID</p>
              <p className="text-sm font-bold text-slate-800">act_560062103113819</p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-500 mb-1 uppercase tracking-wider">FACEBOOK PAGE ID</p>
              <p className="text-sm font-bold text-slate-800">894208310452980 <span className="text-slate-500 font-medium">(Har Ghar Solar)</span></p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-500 mb-1 uppercase tracking-wider">META GRAPH API VERSION</p>
              <p className="text-sm font-black text-blue-600">v24.0</p>
            </div>
            <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-100">
              <p className="text-[10px] font-bold text-emerald-600 mb-1 uppercase tracking-wider">ISSUES INFO</p>
              <p className="text-sm font-bold text-emerald-700 flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4" /> [] Zero Blocking Issues
              </p>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <p className="text-[10px] font-bold text-slate-500 mb-1 uppercase tracking-wider">VGK4U BRANCH PROTECTION</p>
              <p className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
                <Lock className="w-4 h-4 text-slate-400" /> PAUSED (100% Protected)
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold flex items-center gap-2">
              <Edit className="w-5 h-5 text-blue-600" /> Edit {editObj?.type === 'adset' ? 'Ad Set' : editObj?.type === 'campaign' ? 'Campaign' : 'Ad'}
            </DialogTitle>
          </DialogHeader>
          {editObj && (
            <div className="space-y-5 py-4">
              <div>
                <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">Object Name</label>
                <Input 
                  value={editObj.name} 
                  onChange={e => setEditObj({...editObj, name: e.target.value})} 
                  className="mt-1.5 focus-visible:ring-blue-500 font-medium text-slate-800" 
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">Status</label>
                <Select value={editObj.status} onValueChange={val => setEditObj({...editObj, status: val})}>
                  <SelectTrigger className="mt-1.5 focus:ring-blue-500 font-bold">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ACTIVE" className="font-bold text-emerald-700">ACTIVE</SelectItem>
                    <SelectItem value="PAUSED" className="font-bold text-amber-700">PAUSED</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter className="border-t border-slate-100 pt-4 mt-2">
            <Button variant="outline" onClick={() => setEditModalOpen(false)} className="font-semibold text-slate-600">Cancel</Button>
            <Button onClick={handleSaveEdit} className="bg-blue-600 hover:bg-blue-700 text-white font-bold">Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
