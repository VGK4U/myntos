"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface GallerySet {
  id: number;
  gallery_type: "photo" | "video";
  vgk_category?: string;
  title: string;
  description?: string;
  status: string;
  thumbnail_url?: string;
  file_count: number;
  created_at: string;
}

export default function GalleryManagerPage() {
  const { token } = useStaffAuth();
  const [galleries, setGalleries] = useState<GallerySet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const router = useRouter();

  const fetchGalleries = async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/vgk/gallery?per_page=50`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch galleries");
      setGalleries(data.galleries || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGalleries();
  }, [token]);

  const handleCreateGallery = async () => {
    const title = prompt("Enter a title for the new gallery:");
    if (!title) return;
    setCreating(true);
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/vgk/gallery`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ title, description: "New gallery created from portal" })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create gallery");
      router.push(`/staff/vgk/gallery/${data.id}`);
    } catch (err: any) {
      alert(err.message);
      setCreating(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <i className="fas fa-images text-brand-warning"></i>
            Gallery Manager
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage photo and video gallery sets for the public website and app.</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={handleCreateGallery}
            disabled={creating}
            className="px-4 py-2 bg-brand-warning text-white font-semibold rounded-lg shadow hover:bg-yellow-500 transition-colors flex items-center gap-2 text-sm disabled:opacity-50"
          >
            {creating ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-folder-plus"></i>} 
            Create New Gallery
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 border-l-4 border-red-500 rounded-md">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center py-20 text-gray-400">
          <div className="flex flex-col items-center gap-3">
            <i className="fas fa-spinner fa-spin text-3xl"></i>
            <p>Loading galleries...</p>
          </div>
        </div>
      ) : galleries.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="w-16 h-16 mx-auto bg-gray-50 rounded-full flex items-center justify-center mb-3">
            <i className="fas fa-images text-2xl text-gray-300"></i>
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-1">No Galleries Found</h3>
          <p className="text-gray-500 mb-6">Start by creating a new photo or video gallery.</p>
          <button className="px-6 py-2 bg-gray-900 text-white font-semibold rounded-lg shadow hover:bg-black transition-colors">
            Create First Gallery
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {galleries.map((gallery) => (
            <Link 
              key={gallery.id} 
              href={`/staff/vgk/gallery/${gallery.id}`}
              className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-md transition-shadow group flex flex-col"
            >
              <div className="h-48 bg-gray-100 relative overflow-hidden">
                {gallery.thumbnail_url ? (
                  <img src={gallery.thumbnail_url} alt={gallery.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-gray-300">
                    <i className={`fas fa-${gallery.gallery_type === "video" ? "film" : "image"} text-4xl mb-2`}></i>
                    <span className="text-sm font-medium">No Thumbnail</span>
                  </div>
                )}
                <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm text-white text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5">
                  <i className={`fas fa-${gallery.gallery_type === "video" ? "video" : "camera"}`}></i>
                  {gallery.file_count} items
                </div>
              </div>
              
              <div className="p-4 flex-1 flex flex-col">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide
                    ${gallery.gallery_type === "video" ? "bg-red-50 text-red-600" : "bg-purple-50 text-purple-600"}`}>
                    {gallery.gallery_type}
                  </span>
                  {gallery.vgk_category && (
                    <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-gray-100 text-gray-600">
                      {gallery.vgk_category}
                    </span>
                  )}
                  <span className={`ml-auto w-2 h-2 rounded-full ${gallery.status === "active" ? "bg-green-500" : "bg-gray-300"}`} title={gallery.status}></span>
                </div>
                
                <h3 className="font-bold text-gray-900 mb-1 line-clamp-1">{gallery.title}</h3>
                <p className="text-sm text-gray-500 line-clamp-2 flex-1">{gallery.description || "No description provided."}</p>
                
                <div className="mt-4 pt-3 border-t border-gray-50 flex items-center justify-between text-xs text-gray-400">
                  <span>ID: #{gallery.id}</span>
                  <span>{new Date(gallery.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
