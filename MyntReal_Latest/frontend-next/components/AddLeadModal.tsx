"use client";
import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

export function AddLeadModal({ isOpen, onClose, onSave }: any) {
  const [formData, setFormData] = useState({
    name: '', phone: '', company_id: '', priority: 'medium', status: 'new'
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const res = await api.post('/crm/leads', formData);
      if (res.data?.success || res.status === 201) {
        onSave();
        onClose();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add New Lead</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4 py-4">
          <div>
            <label className="text-sm font-bold mb-1 block">Name *</label>
            <input className="w-full border p-2 rounded" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
          </div>
          <div>
            <label className="text-sm font-bold mb-1 block">Phone *</label>
            <input className="w-full border p-2 rounded" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} />
          </div>
          <div>
            <label className="text-sm font-bold mb-1 block">Priority</label>
            <select className="w-full border p-2 rounded" value={formData.priority} onChange={e => setFormData({...formData, priority: e.target.value})}>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-bold mb-1 block">Status</label>
            <select className="w-full border p-2 rounded" value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})}>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="interested">Interested</option>
            </select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={loading}>{loading ? 'Saving...' : 'Save Lead'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
