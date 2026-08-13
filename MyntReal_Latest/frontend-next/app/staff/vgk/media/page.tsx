"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface MediaItem {
  id: number;
  media_type: string;
  vgk_category?: string;
  title: string;
  description?: string;
  status: string;
  thumbnail_url?: string;
  published_at?: string;
  created_at: string;
  created_by_name?: string;
  click_count: number;
  share_count: number;
  reactions: Record<string, number>;
}

export default function MediaManagerPage() {
  const { token } = useStaffAuth();
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterType, setFilterType] = useState("all");

  const fetchMedia = async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      let url = `${getApiUrl()}/api/v1/vgk/media?per_page=50`;
      if (filterType !== "all") {
        url += `&media_type=${filterType}`;
      }
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch media");
      setItems(data.items || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMedia();
  }, [token, filterType]);

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this media item?")) return;
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/vgk/media/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to delete");
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <i className="fas fa-photo-video text-brand-warning"></i>
            Media Manager
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage blogs, YouTube videos, publications, and images.</p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm shadow-sm focus:ring-2 focus:ring-brand-warning focus:border-transparent outline-none"
          >
            <option value="all">All Media Types</option>
            <option value="blog">Blogs</option>
            <option value="youtube">YouTube Videos</option>
            <option value="publication">Publications</option>
            <option value="image">Images</option>
          </select>
          <Link href="/staff/vgk/media/add" className="px-4 py-2 bg-brand-warning text-white font-semibold rounded-lg shadow hover:bg-yellow-500 transition-colors flex items-center gap-2 text-sm">
            <i className="fas fa-plus"></i> Add New Media
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 border-l-4 border-red-500 rounded-md">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 text-gray-700 text-xs uppercase font-semibold">
              <tr>
                <th className="px-6 py-4">Thumbnail</th>
                <th className="px-6 py-4">Title & Type</th>
                <th className="px-6 py-4">Stats</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                    <i className="fas fa-spinner fa-spin text-2xl mb-2"></i>
                    <p>Loading media...</p>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                    <div className="w-16 h-16 mx-auto bg-gray-50 rounded-full flex items-center justify-center mb-3">
                      <i className="fas fa-folder-open text-2xl text-gray-300"></i>
                    </div>
                    <p>No media items found.</p>
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-6 py-4">
                      {item.thumbnail_url ? (
                        <div className="w-16 h-16 rounded-lg overflow-hidden border border-gray-200">
                          <img src={item.thumbnail_url} alt="thumb" className="w-full h-full object-cover" />
                        </div>
                      ) : (
                        <div className="w-16 h-16 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center">
                          <i className={`fas fa-${item.media_type === "youtube" ? "play-circle text-red-500" : item.media_type === "blog" ? "newspaper text-blue-500" : item.media_type === "publication" ? "book text-green-500" : "image text-purple-500"} text-xl`}></i>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-900">{item.title}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide
                          ${item.media_type === "youtube" ? "bg-red-50 text-red-600" : 
                            item.media_type === "blog" ? "bg-blue-50 text-blue-600" : 
                            item.media_type === "publication" ? "bg-green-50 text-green-600" : "bg-purple-50 text-purple-600"}`}>
                          {item.media_type}
                        </span>
                        {item.vgk_category && (
                          <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-gray-100 text-gray-600">
                            {item.vgk_category}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-4 text-xs">
                        <div className="flex flex-col items-center">
                          <span className="font-bold text-gray-900">{item.click_count || 0}</span>
                          <span className="text-gray-400">Views</span>
                        </div>
                        <div className="flex flex-col items-center">
                          <span className="font-bold text-gray-900">{item.share_count || 0}</span>
                          <span className="text-gray-400">Shares</span>
                        </div>
                        <div className="flex flex-col items-center">
                          <span className="font-bold text-gray-900">
                            {(item.reactions?.like || 0) + (item.reactions?.love || 0) + (item.reactions?.shoutout || 0)}
                          </span>
                          <span className="text-gray-400">Reacts</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                        item.status === "active" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-700"
                      }`}>
                        {item.status === "active" ? "? Active" : "? " + item.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button className="p-2 text-gray-400 hover:text-brand-warning transition-colors" title="Edit (Coming soon)">
                          <i className="fas fa-edit"></i>
                        </button>
                        <button onClick={() => handleDelete(item.id)} className="p-2 text-gray-400 hover:text-red-500 transition-colors" title="Delete">
                          <i className="fas fa-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
