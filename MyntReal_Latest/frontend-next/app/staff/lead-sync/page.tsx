"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function LeadSyncPage() {
  return (
    <GenericDataTable 
      title="Lead Sync"
      endpoint="/staff/lead-sync"
      subtitle="Auto-mapped data viewer for staff/lead-sync"
    />
  );
}
