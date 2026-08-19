"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function BomPage() {
  return (
    <GenericDataTable 
      title="Bom"
      endpoint="/staff/inventory/bom"
      subtitle="Auto-mapped data viewer for staff/inventory/bom"
    />
  );
}
