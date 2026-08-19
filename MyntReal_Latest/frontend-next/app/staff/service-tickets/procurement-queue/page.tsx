"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ProcurementQueuePage() {
  return (
    <GenericDataTable 
      title="Procurement Queue"
      endpoint="/staff/service-tickets/procurement-queue"
      subtitle="Auto-mapped data viewer for staff/service-tickets/procurement-queue"
    />
  );
}
