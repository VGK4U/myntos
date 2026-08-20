"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ConsolidatedPage() {
  return (
    <GenericDataTable 
      title="Consolidated"
      endpoint="/staff/consolidated"
      subtitle="Auto-mapped data viewer for staff/consolidated"
    />
  );
}
