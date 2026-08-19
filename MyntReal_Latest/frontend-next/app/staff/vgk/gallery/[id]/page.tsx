"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface GalleryFile {
  id: number;
  file_url: string;
  file_type: "photo" | "video";
  file_name: string;
  thumbnail_url?: string;
  file_size: number;
}

interface GallerySet {
  id: number;
  title: string;
  description?: string;
  status: string;
  files: GalleryFile[];
}

export default function GalleryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useStaffAuth();
  const galleryId = params.id as string;
  
  const [gallery, setGallery] = useState<GallerySet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchGallery = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/vgk/gallery/${galleryId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch gallery");
      setGallery(data.gallery);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGallery();
  }, [token, galleryId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const files = Array.from(e.target.files);
    
    setUploading(true);
    const formData = new FormData();
    files.forEach(file => formData.append("files", file));
    
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/vgk/gallery/${galleryId}/files`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      
      // Refresh gallery
      await fetchGallery();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteFile = async (fileId: number) => {
    if (!confirm("Remove this file from the gallery?")) return;
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/vgk/gallery/${galleryId}/files/${fileId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to delete file");
      
      setGallery(prev => {
        if (!prev) return prev;
        return { ...prev, files: prev.files.filter(f => f.id !== fileId) };
      });
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (loading) return <div className="p-20 text-center text-gray-500"><i className="fas fa-spinner fa-spin text-3xl"></i></div>;
  if (error || !gallery) return <div className="p-10 text-center text-red-500">{error || "Not found"}</div>;

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/staff/vgk/gallery" className="w-10 h-10 bg-white border border-gray-200 rounded-full flex items-center justify-center text-gray-500 hover:text-brand-warning hover:border-brand-warning shadow-sm transition-all">
            <i className="fas fa-arrow-left"></i>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{gallery.title}</h1>
            <p className="text-sm text-gray-500 mt-1">{gallery.description || "No description"} � {gallery.files.length} items</p>
          </div>
        </div>
        
        <div className="flex gap-3">
          <input 
            type="file" 
            multiple 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            className="hidden" 
            accept="image/*,video/*"
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="px-6 py-2.5 bg-brand-warning text-white font-semibold rounded-lg shadow hover:bg-yellow-500 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {uploading ? <><i className="fas fa-spinner fa-spin"></i> Uploading...</> : <><i className="fas fa-upload"></i> Upload Media</>}
          </button>
        </div>
      </div>

      {gallery.files.length === 0 ? (
        <div className="text-center py-32 bg-white rounded-xl border border-gray-100 shadow-sm border-dashed">
          <div className="w-20 h-20 mx-auto bg-gray-50 rounded-full flex items-center justify-center mb-4 text-gray-300">
            <i className="fas fa-cloud-upload-alt text-4xl"></i>
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Gallery is Empty</h3>
          <p className="text-gray-500 mb-6">Upload photos or videos to start building this gallery.</p>
          <button onClick={() => fileInputRef.current?.click()} className="px-6 py-2.5 bg-gray-900 text-white font-semibold rounded-lg shadow hover:bg-black transition-colors">
            Browse Files
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {gallery.files.map(file => (
            <div key={file.id} className="bg-gray-100 rounded-xl overflow-hidden relative group aspect-square shadow-sm border border-gray-200">
              {file.file_type === "video" ? (
                <video src={file.file_url} className="w-full h-full object-cover" controls preload="metadata" />
              ) : (
                <img src={file.file_url} alt={file.file_name} className="w-full h-full object-cover" />
              )}
              
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                <a href={file.file_url} target="_blank" rel="noreferrer" className="w-10 h-10 bg-white/20 hover:bg-white/40 backdrop-blur text-white rounded-full flex items-center justify-center transition-colors">
                  <i className="fas fa-external-link-alt"></i>
                </a>
                <button onClick={() => handleDeleteFile(file.id)} className="w-10 h-10 bg-red-500/80 hover:bg-red-500 text-white rounded-full flex items-center justify-center backdrop-blur transition-colors">
                  <i className="fas fa-trash"></i>
                </button>
              </div>
              
              <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent">
                <p className="text-white text-xs font-semibold truncate">{file.file_name}</p>
                <p className="text-white/70 text-[10px] mt-0.5">{(file.file_size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
