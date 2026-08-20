"use client";

import { useState } from "react";
import api from "@/lib/api";

export default function CRMImportPage() {
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [sheetUrl, setSheetUrl] = useState("");

  const handlePreview = async () => {
    if (!sheetUrl) return;
    setLoading(true);
    try {
      const res = await api.post('/staff/crm/import/preview', { url: sheetUrl });
      setPreviewData(res.data);
    } catch (err) {
      console.error("Preview failed", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
            <i className="fab fa-google text-emerald-600"></i>
          </div>
          Import Leads from Google Sheets
        </h1>
        <p className="text-gray-500">
          Sync Facebook Lead Ads exports or Google Form responses directly into CRM — no CSV download needed.
        </p>
      </div>

      {/* How it works */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <div className="bg-gray-50 border-b border-gray-200 p-4 font-bold text-gray-900 flex items-center gap-2">
          <i className="fas fa-info-circle text-gray-400"></i> How this works
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold shrink-0">1</div>
            <div>
              <h6 className="font-bold text-gray-900 m-0">Facebook exports leads to Google Sheets automatically</h6>
              <p className="text-sm text-gray-600 m-0">On your Facebook Lead Ads form → CRM Setup tab → connect Google Sheets. Facebook will push every new lead into the sheet in real-time.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold shrink-0">2</div>
            <div>
              <h6 className="font-bold text-gray-900 m-0">Share your Google Sheet publicly (view only)</h6>
              <p className="text-sm text-gray-600 m-0">Open the sheet → File → Share → Anyone with the link → Viewer. Copy the sheet URL.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold shrink-0">3</div>
            <div>
              <h6 className="font-bold text-gray-900 m-0">Paste the URL below and click Import</h6>
              <p className="text-sm text-gray-600 m-0">We'll read all rows, auto-detect columns, skip duplicates, and create CRM leads for all new entries.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Import Form */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <div className="bg-gray-50 border-b border-gray-200 p-4 font-bold text-gray-900 flex items-center gap-2">
          <i className="fas fa-file-import text-gray-400"></i> Import Settings
        </div>
        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Google Sheet URL <span className="text-rose-500">*</span></label>
            <input 
              type="url" 
              value={sheetUrl}
              onChange={(e) => setSheetUrl(e.target.value)}
              className="w-full bg-gray-50 border border-gray-300 rounded-lg py-3 px-4 text-gray-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-inner" 
              placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit..." 
            />
            <p className="text-xs text-gray-500 mt-2">Paste the full Google Sheets URL. The sheet must be shared as "Anyone with the link can view".</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Lead Source Label</label>
              <select className="w-full bg-white border border-gray-300 rounded-lg py-2.5 px-3 text-gray-900">
                <option>Facebook Ads</option>
                <option>Google Form</option>
                <option>Manual Upload</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Sheet Tab (gid)</label>
              <input type="text" className="w-full bg-white border border-gray-300 rounded-lg py-2.5 px-3 text-gray-900" defaultValue="0" />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Skip Duplicates?</label>
              <select className="w-full bg-white border border-gray-300 rounded-lg py-2.5 px-3 text-gray-900">
                <option>Yes — skip if phone in CRM</option>
                <option>No — import all rows</option>
              </select>
            </div>
          </div>
          
          <div className="pt-2 flex gap-3">
            <button onClick={handlePreview} disabled={loading} className="px-6 py-3 bg-white border border-gray-300 text-gray-700 font-bold rounded-lg hover:bg-gray-50 transition-colors shadow-sm flex items-center gap-2">
              {loading ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-eye"></i>} Preview Columns
            </button>
            <button disabled={loading} className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg transition-colors shadow-sm flex items-center gap-2">
              <i className="fas fa-cloud-download-alt"></i> Import to CRM
            </button>
          </div>
        </div>
      </div>

      {previewData && (
        <div className="animate-in fade-in slide-in-from-bottom-4">
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-gray-50 border-b border-gray-200 p-4 font-bold text-gray-900 flex items-center gap-2">
              <i className="fas fa-table text-gray-400"></i> Sheet Preview
            </div>
            <div className="p-6">
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-lg bg-gray-50 border border-gray-100 text-center">
                  <div className="text-2xl font-bold text-gray-900">{previewData.totalRows}</div>
                  <div className="text-xs font-medium text-gray-500 uppercase">Total Rows</div>
                </div>
                <div className="p-4 rounded-lg bg-gray-50 border border-gray-100 text-center">
                  <div className="text-2xl font-bold text-gray-900">{previewData.columns}</div>
                  <div className="text-xs font-medium text-gray-500 uppercase">Columns</div>
                </div>
                <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-100 text-center">
                  <div className="text-2xl font-bold text-emerald-700">{previewData.mapped}</div>
                  <div className="text-xs font-medium text-emerald-600 uppercase">Mapped successfully</div>
                </div>
              </div>
              <div className="mb-4">
                <h6 className="font-bold text-emerald-600 text-sm mb-2"><i className="fas fa-check-circle mr-1"></i>Detected CRM Columns:</h6>
                <div className="flex flex-wrap gap-2">
                  {previewData.mappedFields.map((f: string) => (
                    <span key={f} className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-xs font-medium">{f}</span>
                  ))}
                </div>
              </div>
              <div className="overflow-x-auto border border-gray-200 rounded-lg">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-900 text-white text-xs">
                    <tr>
                      <th className="px-4 py-2">Name</th>
                      <th className="px-4 py-2">Phone</th>
                      <th className="px-4 py-2">City</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {previewData.previewRows.map((r: any, i: number) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-2">{r.name}</td>
                        <td className="px-4 py-2 font-mono text-xs">{r.phone}</td>
                        <td className="px-4 py-2">{r.city}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
