"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ProcurementPage() {
  return (
    <GenericDataTable 
      title="Procurement"
      endpoint="/staff/inventory/procurement"
      subtitle="Auto-mapped data viewer for staff/inventory/procurement"
    />
  );
}
