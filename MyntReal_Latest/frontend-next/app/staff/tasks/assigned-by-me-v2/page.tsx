"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AssignedByMeV2Page() {
  return (
    <GenericDataTable 
      title="Assigned By Me V2"
      endpoint="/staff/tasks/assigned-by-me-v2"
      subtitle="Auto-mapped data viewer for staff/tasks/assigned-by-me-v2"
    />
  );
}
