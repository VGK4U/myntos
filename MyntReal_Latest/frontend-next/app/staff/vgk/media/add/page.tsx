"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

export default function AddMediaPage() {
  const router = useRouter();
  const { token } = useStaffAuth();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [formData, setFormData] = useState({
    media_type: "blog",
    title: "",
    description: "",
    body: "",
    url: "",
    thumbnail_url: "",
    status: "active"
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    
    setLoading(true);
    setError("");
    
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/vgk/media`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create media item");
      
      router.push("/staff/vgk/media");
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="mb-6 flex items-center gap-4">
        <Link href="/staff/vgk/media" className="w-10 h-10 bg-white border border-gray-200 rounded-full flex items-center justify-center text-gray-500 hover:text-brand-warning hover:border-brand-warning shadow-sm transition-all">
          <i className="fas fa-arrow-left"></i>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Add New Media</h1>
          <p className="text-sm text-gray-500 mt-1">Publish a new blog, video, or publication to the network.</p>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 border-l-4 border-red-500 rounded-md">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Media Type <span className="text-red-500">*</span></label>
              <select
                name="media_type"
                value={formData.media_type}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none transition-all"
                required
              >
                <option value="blog">Blog Post</option>
                <option value="youtube">YouTube Video</option>
                <option value="publication">Publication / Document</option>
                <option value="image">Image Gallery Link</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Status</label>
              <select
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none transition-all"
              >
                <option value="active">Active (Published)</option>
                <option value="draft">Draft</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Title <span className="text-red-500">*</span></label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="Enter media title"
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none transition-all"
                required
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Short Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Brief summary..."
                rows={2}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none transition-all resize-none"
              ></textarea>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Full Body Content (Optional for Videos)</label>
              <textarea
                name="body"
                value={formData.body}
                onChange={handleChange}
                placeholder="Write full article here..."
                rows={6}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none transition-all resize-y"
              ></textarea>
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Target URL / Video ID</label>
              <input
                type="text"
                name="url"
                value={formData.url}
                onChange={handleChange}
                placeholder="https://..."
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none transition-all"
              />
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Thumbnail URL</label>
              <input
                type="text"
                name="thumbnail_url"
                value={formData.thumbnail_url}
                onChange={handleChange}
                placeholder="https://..."
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none transition-all"
              />
            </div>
          </div>
          
          <div className="pt-4 border-t border-gray-100 flex justify-end gap-3">
            <Link href="/staff/vgk/media" className="px-6 py-3 bg-white border border-gray-200 text-gray-700 font-semibold rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
              Cancel
            </Link>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-brand-warning text-white font-semibold rounded-lg shadow hover:bg-yellow-500 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <><i className="fas fa-spinner fa-spin"></i> Publishing...</>
              ) : (
                <><i className="fas fa-paper-plane"></i> Publish Media</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
