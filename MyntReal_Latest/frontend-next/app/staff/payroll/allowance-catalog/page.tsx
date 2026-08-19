"use client";

import React from 'react';
import GenericDataTable from '@/components/GenericDataTable';

export default function AllowanceCatalogPage() {
  return (
    <GenericDataTable 
      title="Allowance Catalog"
      endpoint="/staff/payroll/allowance-catalog"
      subtitle="Auto-mapped data viewer for staff/payroll/allowance-catalog"
    />
  );
}
