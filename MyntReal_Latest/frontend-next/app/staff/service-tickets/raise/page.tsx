"use client";

import React, { useState } from 'react';

export default function RaisePage() {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    // Submit to /staff/service-tickets/raise
    setTimeout(() => setIsSubmitting(false), 1000);
  };

  return (
    <div className="p-8 bg-gray-50 min-h-screen flex justify-center">
      <div className="max-w-2xl w-full">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Raise a Service Ticket</h1>
          <p className="text-gray-500 mt-2">Submit a new request for IT support, maintenance, or procurement.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Ticket Type</label>
              <select className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all">
                <option>Technical Support</option>
                <option>Hardware Request</option>
                <option>Software Access</option>
                <option>Maintenance</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Priority Level</label>
              <div className="flex gap-4">
                {['Low', 'Medium', 'High', 'Critical'].map(p => (
                  <label key={p} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="priority" className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300" />
                    <span className="text-sm text-gray-700">{p}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
              <input type="text" placeholder="Brief description of the issue" className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all" required />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Detailed Description</label>
              <textarea rows={5} placeholder="Provide as much detail as possible..." className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all resize-none" required></textarea>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Attachments (Optional)</label>
              <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg hover:border-indigo-500 transition-colors cursor-pointer bg-gray-50">
                <div className="space-y-1 text-center">
                  <div className="text-sm text-gray-600">
                    <span className="text-indigo-600 font-medium hover:text-indigo-500">Upload a file</span> or drag and drop
                  </div>
                  <p className="text-xs text-gray-500">PNG, JPG, PDF up to 10MB</p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-100 flex justify-end gap-4">
              <button type="button" className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors">Cancel</button>
              <button type="submit" disabled={isSubmitting} className={`px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors shadow-sm ${isSubmitting ? 'opacity-70 cursor-not-allowed' : ''}`}>
                {isSubmitting ? 'Submitting...' : 'Submit Ticket'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
