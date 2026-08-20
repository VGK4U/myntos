"use client";
import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

export function CRMLeadEditor({ isOpen, onClose, leadId, onSave }: any) {
  const [lead, setLead] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && leadId) {
      loadLead();
    }
  }, [isOpen, leadId]);

  const loadLead = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/crm/unified-my-leads?lead_id=${leadId}`);
      const leadData = res.data?.data?.[0] || res.data?.leads?.[0] || res.data?.[0];
      setLead(leadData || { id: leadId, name: 'Unknown' });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      await api.put(`/crm/leads/${leadId}`, lead);
      onSave();
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Lead</DialogTitle>
        </DialogHeader>
        {loading && !lead ? (
          <div className="p-8 text-center"><i className="fas fa-spinner fa-spin text-2xl"></i></div>
        ) : lead ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
            <div>
              <label className="text-sm font-bold mb-1 block">Lead Name</label>
              <input className="w-full border p-2 rounded" value={lead.name || ''} onChange={e => setLead({...lead, name: e.target.value})} />
            </div>
            <div>
              <label className="text-sm font-bold mb-1 block">Phone</label>
              <input className="w-full border p-2 rounded" value={lead.phone || ''} onChange={e => setLead({...lead, phone: e.target.value})} />
            </div>
            <div>
              <label className="text-sm font-bold mb-1 block">Email</label>
              <input className="w-full border p-2 rounded" value={lead.email || ''} onChange={e => setLead({...lead, email: e.target.value})} />
            </div>
            <div>
              <label className="text-sm font-bold mb-1 block">Status</label>
              <select className="w-full border p-2 rounded" value={lead.status || 'new'} onChange={e => setLead({...lead, status: e.target.value})}>
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="interested">Interested</option>
                <option value="qualified">Qualified</option>
                <option value="proposal">Proposal</option>
                <option value="won">Won</option>
                <option value="lost">Lost</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-bold mb-1 block">Priority</label>
              <select className="w-full border p-2 rounded" value={lead.priority || 'medium'} onChange={e => setLead({...lead, priority: e.target.value})}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-red-500">Failed to load lead.</div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={loading}>{loading ? 'Saving...' : 'Save Changes'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
