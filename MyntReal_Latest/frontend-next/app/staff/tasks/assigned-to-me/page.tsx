"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AssignedToMePage() {
  return (
    <GenericDataTable 
      title="Assigned To Me"
      endpoint="/staff/tasks/assigned-to-me"
      subtitle="Auto-mapped data viewer for staff/tasks/assigned-to-me"
    />
  );
}
