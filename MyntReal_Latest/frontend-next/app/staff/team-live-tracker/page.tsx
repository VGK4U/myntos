"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TeamLiveTrackerPage() {
  return (
    <GenericDataTable 
      title="Team Live Tracker"
      endpoint="/staff/team-live-tracker"
      subtitle="Auto-mapped data viewer for staff/team-live-tracker"
    />
  );
}
