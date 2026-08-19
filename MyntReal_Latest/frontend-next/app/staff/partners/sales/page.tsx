"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SalesPage() {
  return (
    <GenericDataTable 
      title="Sales"
      endpoint="/staff/partners/sales"
      subtitle="Auto-mapped data viewer for staff/partners/sales"
    />
  );
}
