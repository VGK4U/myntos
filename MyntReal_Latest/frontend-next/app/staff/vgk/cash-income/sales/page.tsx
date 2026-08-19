"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function SalesPage() {
  return (
    <GenericDataTable 
      title="Sales"
      endpoint="/staff/vgk/cash-income/sales"
      subtitle="Auto-mapped data viewer for staff/vgk/cash-income/sales"
    />
  );
}
