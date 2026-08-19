"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function QueuePage() {
  return (
    <GenericDataTable 
      title="Queue"
      endpoint="/staff/service-tickets/queue"
      subtitle="Auto-mapped data viewer for staff/service-tickets/queue"
    />
  );
}
