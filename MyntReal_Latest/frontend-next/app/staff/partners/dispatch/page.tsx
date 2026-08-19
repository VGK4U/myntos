"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function DispatchPage() {
  return (
    <GenericDataTable 
      title="Dispatch"
      endpoint="/staff/partners/dispatch"
      subtitle="Auto-mapped data viewer for staff/partners/dispatch"
    />
  );
}
