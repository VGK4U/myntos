"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface ServiceJob {
  id: number;
  job_number: string;
  ticket_number: string;
  vehicle_model: string;
  technician: string;
  stage: string; // INTAKE, DIAGNOSIS, WAITING_PARTS, REPAIRING, QC, READY
  estimated_completion: string;
}

export default function ServiceTrackingPage() {
  const { token } = useStaffAuth();
  const [jobs, setJobs] = useState<ServiceJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    
    // Simulating fetching active service jobs
    const fetchJobs = async () => {
      setLoading(true);
      setTimeout(() => {
        setJobs([
          { id: 1, job_number: "JOB-2041", ticket_number: "T-1045", vehicle_model: "EV Scooter Pro", technician: "Rajesh K.", stage: "INTAKE", estimated_completion: "2026-08-15" },
          { id: 2, job_number: "JOB-2038", ticket_number: "T-1042", vehicle_model: "Solar Inverter 5kW", technician: "Amit S.", stage: "DIAGNOSIS", estimated_completion: "2026-08-14" },
          { id: 3, job_number: "JOB-2035", ticket_number: "T-1038", vehicle_model: "EV Battery Pack", technician: "Manoj D.", stage: "WAITING_PARTS", estimated_completion: "2026-08-18" },
          { id: 4, job_number: "JOB-2030", ticket_number: "T-1030", vehicle_model: "EV Scooter Lite", technician: "Rajesh K.", stage: "REPAIRING", estimated_completion: "2026-08-14" },
          { id: 5, job_number: "JOB-2025", ticket_number: "T-1022", vehicle_model: "Solar Panel 400W", technician: "Suresh P.", stage: "QC", estimated_completion: "2026-08-14" },
        ]);
        setLoading(false);
      }, 500);
    };

    fetchJobs();
  }, [token]);

  const stages = [
    { key: "INTAKE", label: "Intake", icon: "fa-clipboard-list", color: "gray" },
    { key: "DIAGNOSIS", label: "Diagnosis", icon: "fa-search", color: "indigo" },
    { key: "WAITING_PARTS", label: "Waiting Parts", icon: "fa-box-open", color: "amber" },
    { key: "REPAIRING", label: "In Repair", icon: "fa-wrench", color: "blue" },
    { key: "QC", label: "Quality Check", icon: "fa-check-double", color: "purple" },
    { key: "READY", label: "Ready", icon: "fa-flag-checkered", color: "green" },
  ];

  const renderJobCard = (job: ServiceJob) => (
    <div key={job.id} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-3 hover:shadow-md transition-shadow cursor-pointer">
      <div className="flex justify-between items-start mb-2">
        <span className="font-bold text-sm text-gray-900">{job.job_number}</span>
        <span className="text-xs font-medium text-gray-500">{job.ticket_number}</span>
      </div>
      <p className="text-sm font-medium text-indigo-600 mb-2 truncate">{job.vehicle_model}</p>
      <div className="flex justify-between items-center text-xs text-gray-500 mt-3 pt-3 border-t border-gray-100">
        <span className="flex items-center"><i className="fas fa-user-wrench mr-1"></i> {job.technician}</span>
        <span>Due: {new Date(job.estimated_completion).toLocaleDateString([], {month:'short', day:'numeric'})}</span>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-[1600px] mx-auto h-[calc(100vh-80px)] flex flex-col">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Service Center Tracking (Kanban)</h1>
          <p className="text-sm text-gray-500 mt-2">Drag and drop jobs across service stages to update status in real-time.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/service/dashboard" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-chart-pie mr-2"></i> Dashboard
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-barcode mr-2"></i> Scan Job Card
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center text-indigo-500">
            <i className="fas fa-circle-notch fa-spin text-4xl mb-3"></i>
            <p className="text-sm font-medium">Loading Shop Floor...</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto pb-4">
          <div className="flex space-x-4 min-w-max h-full">
            {stages.map(stage => (
              <div key={stage.key} className="w-80 flex flex-col bg-gray-50/80 rounded-xl border border-gray-200">
                {/* Column Header */}
                <div className="p-4 border-b border-gray-200 bg-white rounded-t-xl shrink-0 flex justify-between items-center">
                  <div className="flex items-center space-x-2">
                    <div className={`w-8 h-8 rounded-lg bg-${stage.color}-100 text-${stage.color}-600 flex items-center justify-center`}>
                      <i className={`fas ${stage.icon}`}></i>
                    </div>
                    <h3 className="font-bold text-gray-800">{stage.label}</h3>
                  </div>
                  <span className="bg-gray-100 text-gray-600 text-xs font-bold px-2 py-1 rounded-full">
                    {jobs.filter(j => j.stage === stage.key).length}
                  </span>
                </div>
                
                {/* Column Content (Droppable area conceptually) */}
                <div className="flex-1 overflow-y-auto p-3">
                  {jobs.filter(j => j.stage === stage.key).map(renderJobCard)}
                  
                  {jobs.filter(j => j.stage === stage.key).length === 0 && (
                    <div className="h-24 border-2 border-dashed border-gray-200 rounded-lg flex items-center justify-center text-gray-400 text-sm font-medium">
                      Drop here
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
