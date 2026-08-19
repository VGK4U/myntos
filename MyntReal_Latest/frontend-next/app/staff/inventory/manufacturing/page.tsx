"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function ManufacturingPage() {
  return (
    <GenericDataTable 
      title="Manufacturing"
      endpoint="/staff/inventory/manufacturing"
      subtitle="Auto-mapped data viewer for staff/inventory/manufacturing"
    />
  );
}
