"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AllLocationTrackerPage() {
  return (
    <GenericDataTable 
      title="All Location Tracker"
      endpoint="/staff/all-location-tracker"
      subtitle="Auto-mapped data viewer for staff/all-location-tracker"
    />
  );
}
