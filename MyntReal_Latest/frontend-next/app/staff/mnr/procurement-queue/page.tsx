"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ProcurementQueuePage() {
  return (
    <GenericDataTable 
      title="Procurement Queue"
      endpoint="/staff/mnr/procurement-queue"
      subtitle="Auto-mapped data viewer for staff/mnr/procurement-queue"
    />
  );
}
