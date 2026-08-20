"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function TrackerPage() {
  return (
    <GenericDataTable 
      title="Tracker"
      endpoint="/staff/tasks/tracker"
      subtitle="Auto-mapped data viewer for staff/tasks/tracker"
    />
  );
}
