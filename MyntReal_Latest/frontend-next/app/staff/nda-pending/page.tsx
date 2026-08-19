"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function NdaPendingPage() {
  return (
    <GenericDataTable 
      title="Nda Pending"
      endpoint="/staff/nda-pending"
      subtitle="Auto-mapped data viewer for staff/nda-pending"
    />
  );
}
