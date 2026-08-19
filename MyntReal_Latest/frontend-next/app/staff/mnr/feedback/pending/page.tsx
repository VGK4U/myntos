"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function PendingPage() {
  return (
    <GenericDataTable 
      title="Pending"
      endpoint="/staff/mnr/feedback/pending"
      subtitle="Auto-mapped data viewer for staff/mnr/feedback/pending"
    />
  );
}
