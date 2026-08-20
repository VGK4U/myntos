"use client";
import React, { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

export function WALeadModal({ isOpen, onClose, leadId, phone, name, companyId }: any) {
  const [mode, setMode] = useState<'company'|'direct'>('company');
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTpl, setSelectedTpl] = useState<string>('');
  const [message, setMessage] = useState('');
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{msg: string, success: boolean}|null>(null);

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
      setResult(null);
      setMessage('');
      setSelectedTpl('');
      setVariables({});
    }
  }, [isOpen, mode]);

  const loadTemplates = async () => {
    try {
      const url = mode === 'company' ? '/whatsapp-config/templates/approved' : '/whatsapp-config/templates?is_active=true';
      const res = await api.get(url);
      setTemplates(res.data?.templates || []);
    } catch (e) {
      console.warn("Failed to load WA templates", e);
    }
  };

  const handleSend = async () => {
    if (!message) return;
    if (mode === 'direct') {
      const cleaned = (phone || '').replace(/\D/g, '').slice(-10);
      const waUrl = cleaned ? `https://wa.me/91${cleaned}?text=${encodeURIComponent(message)}` : `https://wa.me/?text=${encodeURIComponent(message)}`;
      window.open(waUrl, '_blank');
      setResult({ msg: 'WhatsApp opened. Activity logged.', success: true });
      try {
        await api.post(`/whatsapp-config/crm-lead-send/${leadId}/log-direct`, { phone, message_body: message, template_id: selectedTpl || null });
      } catch (e) {}
      setTimeout(onClose, 2500);
    } else {
      setLoading(true);
      try {
        const res = await api.post(`/whatsapp-config/crm-lead-send/${leadId}`, {
          phone,
          template_id: selectedTpl ? parseInt(selectedTpl, 10) : null,
          custom_message: !selectedTpl ? message : null,
          variable_values: variables,
          send_mode: 'company'
        });
        if (res.data?.success) {
          setResult({ msg: `Sent via Meta. WAMID: ${res.data.wamid || 'N/A'}`, success: true });
          setTimeout(onClose, 3000);
        } else {
          setResult({ msg: res.data?.reason || 'Unknown error', success: false });
        }
      } catch (e: any) {
        setResult({ msg: e.message || 'Error', success: false });
      }
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle><i className="fab fa-whatsapp text-green-500 mr-2"></i>Send WhatsApp</DialogTitle>
          <DialogDescription>{name} · {phone}</DialogDescription>
        </DialogHeader>

        <div className="flex gap-2 p-1 bg-slate-100 rounded-lg mb-4">
          <button onClick={() => setMode('company')} className={`flex-1 py-2 text-sm font-bold rounded-md ${mode === 'company' ? 'bg-white shadow text-green-700' : 'text-slate-500'}`}>
            Company WA
          </button>
          <button onClick={() => setMode('direct')} className={`flex-1 py-2 text-sm font-bold rounded-md ${mode === 'direct' ? 'bg-white shadow text-teal-700' : 'text-slate-500'}`}>
            Direct WA
          </button>
        </div>

        <div className="mb-4">
          <label className="text-xs font-bold text-slate-500 uppercase">Template</label>
          <select className="w-full border p-2 rounded-md mt-1 text-sm" value={selectedTpl} onChange={(e) => {
            const val = e.target.value;
            setSelectedTpl(val);
            const tpl = templates.find(t => t.id.toString() === val);
            if (tpl) {
              setMessage(tpl.body_text || '');
            } else {
              setMessage('');
            }
          }}>
            <option value="">{mode === 'company' ? '-- No Template (Custom not allowed) --' : '-- Write Custom Message --'}</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>

        <div className="mb-4">
          <label className="text-xs font-bold text-slate-500 uppercase">Message</label>
          <textarea 
            className="w-full border p-2 rounded-md mt-1 text-sm h-32" 
            value={message} 
            onChange={(e) => setMessage(e.target.value)}
            disabled={mode === 'company' && !!selectedTpl}
          ></textarea>
        </div>

        {result && (
          <div className={`p-3 rounded-md text-sm mb-4 ${result.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {result.msg}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSend} disabled={loading} className={mode === 'company' ? 'bg-green-600 hover:bg-green-700' : 'bg-teal-600 hover:bg-teal-700'}>
            {loading ? 'Sending...' : (mode === 'company' ? 'Send via Meta' : 'Open WhatsApp')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
